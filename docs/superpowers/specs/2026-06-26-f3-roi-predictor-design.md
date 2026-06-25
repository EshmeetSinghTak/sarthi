# F3 — ROI Predictor: Design

**Date:** 2026-06-26
**Status:** Approved (revisable — user may revisit details during implementation)
**Builds on:** F2 University Shortlister (`backend/app/tools/shortlist.py`, `backend/data/universities.json`)

## Goal

Give a student a financial reality-check on a study-abroad degree: **cost vs. salary vs. EMI**, per university. Mirrors the CLAUDE.md Phase-2 "money slide" (F2 + F3 shown together) and the §0 "next up: F3" item. All figures are approximate, guidance-only.

## Constraints

- **No Claude / no paid LLMs** in the product (CLAUDE.md §0 hard constraint). The ROI math is fully deterministic Python — no model call needed for the numbers; the agent only narrates the returned data.
- Follow the existing F2 pattern: a pure, independently-testable function underneath a thin LangChain `@tool` wrapper. Data in a JSON file under `backend/data/`.

## Decisions (from brainstorming)

1. **Scope:** per-university ROI (not a single-scenario calculator).
2. **Salary data:** hand-curated `field × country` table *schema*, populated with *real public figures* (H1B LCA disclosure medians + levels.fyi), source cited in the data note. Not per-university salary fields (variation is field-driven, avoids false precision).
3. **Loan terms:** accepted as tool args with sensible defaults; full rate × tenure sensitivity table available on drill-down.
4. **List + grid reconciliation:** the per-university list shows one **base-case** row each; a **full rate × tenure sensitivity grid** is returned only when the student drills into a single named university.

## Architecture

Mirrors F2 exactly.

### New data file — `backend/data/salary_priors.json`

```jsonc
{
  "data_note": "Approximate median new-grad salaries for guidance only — NOT a guarantee. Sources: US H1B LCA disclosure data + levels.fyi medians (USD/yr). Living costs are rough annual estimates. Always verify.",
  "currency": "USD",
  "living_cost_usd_per_year": { "US": 18000, "Canada": 15000 },
  "starting_salary_usd": {
    "US":     { "Computer Science": 0, "AI/ML": 0, "Data Science": 0, "Robotics": 0,
                "Electrical Engineering": 0, "Mechanical Engineering": 0,
                "Civil Engineering": 0, "Business/MBA": 0 },
    "Canada": { "...": 0 }
  }
}
```

Salary/living numbers are filled with real public figures at build time. Fields match `universities.json`'s `fields_taxonomy` exactly (8 fields × 2 countries = 16 salary cells).

### New module — `backend/app/tools/roi.py`

Pure functions (testable) + two `@tool` wrappers:

- `_emi(principal_inr, annual_rate_pct, years) -> float` — standard amortization; `r == 0` falls back to `principal / months`.
- `_prestige_multiplier(competitiveness: int) -> float` — `ROI_PRESTIGE_BASE + ROI_PRESTIGE_STEP * (competitiveness - 1)` → range 0.9 (comp 1) … 1.1 (comp 5). Documented, mild ±10%. Coefficients from config.
- `roi_for_university(uni, field, country, loan_inr_lakh, interest_rate, tenure_years, years) -> dict` — the per-uni computation.
- `roi(field, country?, universities?, loan_inr_lakh?, interest_rate?, tenure_years?, years?, limit?) -> dict` — list over matching unis, sorted by best ROI.
- `roi_breakdown(university, field?, loan_inr_lakh?, years?) -> dict` — single uni + sensitivity grid.

### Config — no hardcoded constants (user preference)

**Never hardcode tunable values.** Every magic number lives in one place — `config.py` for financial/scoring constants, `salary_priors.json` for data. No literals scattered in `roi.py` logic.

Named constants in `config.py` (with comments explaining each):

- `USD_PER_INR` — moved here from `shortlist.py`; both tools import it (one source of truth).
- `ROI_DEFAULT_INTEREST_RATE` (10.5 %), `ROI_DEFAULT_TENURE_YEARS` (8), `ROI_DEFAULT_LOAN_FRACTION` (0.70), `ROI_DEFAULT_YEARS` (2), `ROI_LIST_LIMIT` (6).
- `ROI_SENSITIVITY_RATES` (`[9, 10.5, 12]`), `ROI_SENSITIVITY_TENURES` (`[5, 8, 10]`).
- `ROI_PRESTIGE_BASE` (0.9), `ROI_PRESTIGE_STEP` (0.05) — for the prestige multiplier.

Data-like values (salaries, living costs) live in `salary_priors.json`, not config. Tool function signatures keep these as default-arg values *sourced from the config constants* (e.g. `interest_rate: float = ROI_DEFAULT_INTEREST_RATE`), so callers can override and there is still a single definition.

## The two tools

### `estimate_roi(field, country?, universities?, loan_inr_lakh?, interest_rate?, tenure_years?, years?)`

Base-case **list**. Filters universities by field (hard filter when recognised) and country, OR uses an explicit `universities` name list so it chains directly after `shortlist_universities`. Returns one row per uni:

- `name, country, city, qs_rank`
- `total_cost_inr_lakh` (tuition + living, over `years`)
- `expected_salary_inr_lakh_per_year` (post prestige multiplier)
- `loan_inr_lakh` (arg, else 70% of total cost)
- `monthly_emi_inr`
- `emi_to_income_pct`
- `payback_years`

Sorted by best ROI (lowest payback / strongest salary-to-cost). Returns up to `limit` (default ~6) rows.

### `roi_breakdown(university, field?, loan_inr_lakh?, years?)`

Single named uni + **sensitivity grid**: rates × tenures from `ROI_SENSITIVITY_RATES` (`[9, 10.5, 12]` %) and `ROI_SENSITIVITY_TENURES` (`[5, 8, 10]` yr) in config, each cell = monthly EMI (INR). Plus the base metrics and total interest at the default cell.

## The math (deterministic)

- **Total cost** = (`tuition_usd` + `living_cost_usd_per_year[country]`) × `years`, → INR lakh via `USD_PER_INR`.
- **Expected salary** = `starting_salary_usd[country][field]` × `_prestige_multiplier(competitiveness)`, → INR.
- **Loan** = `loan_inr_lakh` arg, else 70% of total cost (Priya persona default).
- **EMI** = `P·r·(1+r)ⁿ / ((1+r)ⁿ − 1)`, `r` = monthly rate, `n` = months. Defaults **10.5% / 8 yr**.
- **Payback years** = total repayment (EMI × n) ÷ annual salary.
- **EMI-to-income %** = monthly EMI ÷ monthly salary.

### Defaults

All sourced from `config.py` constants (see "Config — no hardcoded constants"): `interest_rate = ROI_DEFAULT_INTEREST_RATE` (10.5), `tenure_years = ROI_DEFAULT_TENURE_YEARS` (8), `loan = ROI_DEFAULT_LOAN_FRACTION` (0.70) of cost, `years = ROI_DEFAULT_YEARS` (2).

## Wiring & presentation

- Register both tools in `agent.py` `TOOLS` and `ToolNode(TOOLS)`; export from `tools/__init__.py`.
- Extend `prompts.py` "YOUR TOOLS" section:
  - When to call `estimate_roi` (student asks "is it worth it?", cost/salary/EMI, or right after a shortlist) vs. `roi_breakdown` (student names one uni / asks about loan terms).
  - Render the list as a markdown table: `University | Cost | Salary/yr | EMI/mo | Payback`; render the grid as a small rate × tenure table.
  - Keep the "all figures approximate, verify" caveat. Reaffirm loan guidance is advisory (final underwriting = lending partner).

## Testing (first tests in the repo)

`backend/tests/test_roi.py` (pytest):

- **EMI known value:** ₹10 L @ 10% / 10 yr ≈ ₹13,215/mo (assert within ±₹5).
- **`roi()` smoke:** a fixed scenario returns rows with all expected keys and positive numbers.
- **Sanity:** higher salary → fewer payback years; higher rate → higher EMI; `r == 0` branch.

(F1/F2 have no tests yet; F3 introduces the pattern since financial output must be verifiable.)

## Out of scope (YAGNI)

Real-time FX, post-tax / cost-of-living-adjusted salary, multi-year salary growth curves, charts/graphs (chat markdown tables only), and real loan eligibility / underwriting (that is F5).

## Build sequence

1. Move `USD_PER_INR` to `config.py` and add the named `ROI_*` constants there; update `shortlist.py` import. (No hardcoded literals in `roi.py`.)
2. Create `salary_priors.json` (schema + real public figures).
3. Write `roi.py` pure functions; add `test_roi.py`; make tests pass (TDD).
4. Add the two `@tool` wrappers; export from `tools/__init__.py`.
5. Register in `agent.py`; extend `prompts.py`.
6. Manual end-to-end check in chat (with `SARTHI_MODEL_DEFAULT=meta/llama-3.3-70b-instruct` to dodge deepseek rate limits).
