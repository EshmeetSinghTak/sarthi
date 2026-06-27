# SARTHI F5 — Loan Eligibility + Personalized Offer (Design Spec)

**Date:** 2026-06-27
**Status:** Approved (design), pending implementation plan
**Author:** Rath (solo) + Claude

---

## 1. Problem & Goal

SARTHI's whole thesis is turning a 12-month mentor relationship into a natural
loan conversion (Phase 4 "Fund": *"Based on what I know, you'd likely qualify
for ~₹45L at ~10.2%."*). F5 builds the **indicative eligibility + personalized
offer engine** that makes that moment real.

**Goal:** given what SARTHI knows about a student's finances, produce an
*indicative* education-loan offer — eligible amount, rate band, EMI, repayment
shape — with an explainable "why" reason chain, framed strictly as advisory.

### Non-goals (YAGNI)
- **Not** a real loan approval. No Poonawalla API (mocked / integration-ready).
- **Not** auto-filling a loan application form — that's F6.
- **No** persistence/database in v1 — offers are recomputed on demand.
- **No** trained ML model (see §3 — we have no labeled data; a synthetic model
  would be fabrication). The engine is rule-based behind an ML-ready seam.

---

## 2. Decisions (from brainstorming)

1. **Two surfaces:** an in-chat offer card (agent renders) **and** a dedicated
   `/loan` page (form + live sliders). One shared engine feeds both.
2. **Engine:** transparent rule-based, with a reason chain, built behind a single
   `assess_eligibility()` entry point so a real ML model could replace the
   internals later without touching callers.
3. **Policy data:** real, **sourced** figures from publicly published Indian
   education-loan rate cards / eligibility norms, baked into
   `data/loan_policy.json` with a citations note. (Researched at build time.)
4. **Approval likelihood:** a qualitative **eligibility strength**
   (Strong / Moderate / Limited) backed by explicit reasons — no fabricated
   numeric probability.
5. **Compliance:** advisory framing, RBI digital-lending aligned, explainability
   by default. SARTHI guides; the lender underwrites.

### Why not train an ML model on scraped data
Supervised eligibility prediction needs **labeled** applications (features →
approved/denied/rate). Lenders publish their **policies** (rate cards, LTV caps,
income norms) but never their **approval datasets** (confidential, legally
protected). Without real labels the only option is inventing them — a model that
looks rigorous (even with SHAP) but predicts from fabricated patterns, violating
the no-fabrication guardrail. We therefore use real *policy* data in a
transparent rules engine, and design the interface so a real model can slot in
*if* labeled data ever becomes available.

---

## 3. Architecture

```
data/loan_policy.json (real, sourced figures)
        │
        ▼
app/loan.py ── assess_eligibility(inputs) -> offer      [pure engine, ML-ready seam]
        │                          │
        ├── tools/loan.py @tool loan_offer ──► chat offer card (agent renders markdown)
        └── server.py POST /loan/offer ──────► /loan page (form + live sliders)
```

One pure engine; two thin consumers. Stateless. Policy numbers in JSON, behavior
tunables in `config.py`, nothing hardcoded in `loan.py`. Mirrors the existing
ROI/SOP pattern (pure module → `@tool` → REST endpoint → page).

---

## 4. The Engine — `backend/app/loan.py`

**Single public entry point** (the ML-ready seam):

```
assess_eligibility(
    loan_amount_inr_lakh: float,
    co_applicant_income_inr_lakh_per_year: float,
    collateral_value_inr_lakh: float = 0.0,
    country: str | None = None,
    tenure_years: int | None = None,        # default from config
    existing_emi_inr_per_month: float = 0.0,
) -> dict
```

All callers go through this function; the rule logic lives in an internal
`_rule_engine(...)` that a future model can replace.

### Reused math
`_emi(principal, annual_rate_pct, years)` and the FX constant are reused from the
ROI module (`app/tools/roi.py`) — do not duplicate. A new inverse,
`_max_principal_for_emi(max_emi, annual_rate_pct, years)`, computes the largest
principal whose EMI fits a budget (inverts the amortization formula; rate≤0 →
`max_emi * months`).

### Rule logic (every threshold from policy/config)
1. **Secured vs unsecured.** Collateral that covers the requested amount (per
   `secured_ltv_pct`) → secured (lower rate band, higher cap); else unsecured.
2. **Eligible amount = min(** requested, product cap, serviceability cap **)** where
   - *product cap* = `unsecured_cap_inr_lakh` (unsecured) **or**
     `min(secured_ltv_pct% × collateral, secured_max_inr_lakh)` (secured);
   - *serviceability cap* = `_max_principal_for_emi(max_emi, mid_rate, tenure)`,
     with `max_emi = foir_pct% × (annual_income/12) − existing_emi`
     (floored at 0).
3. **Rate band** = policy `rate_bands[secured|unsecured]` (low–high) shifted by
   `country_rate_adjustment_pct[country]`.
4. **Moratorium** = `moratorium_months_default`.
5. **Representative EMI** = `_emi(eligible, mid_rate, tenure)` (post-moratorium).
6. **Eligibility strength:**
   - *Strong* — serviceability comfortable (`emi_to_income_pct ≤
     LOAN_STRENGTH_STRONG_EMI_PCT`) and no shortfall vs requested.
   - *Moderate* — fits but tight (`≤ LOAN_STRENGTH_MODERATE_EMI_PCT`) or a cap
     trims the requested amount modestly.
   - *Limited* — serviceability binds hard, large shortfall, or income ≈ 0.
7. **Reason chain** — each binding factor appends
   `{factor, impact, detail}` (e.g. `{"factor": "Co-applicant income",
   "impact": "limits amount", "detail": "EMI capped at 50% of monthly income"}`).

### Output dict
`requested_inr_lakh`, `eligible_inr_lakh`, `secured` (bool),
`collateral_value_inr_lakh`, `indicative_rate_low_pct`,
`indicative_rate_high_pct`, `tenure_years`, `moratorium_months`,
`representative_emi_inr`, `emi_to_income_pct`,
`eligibility_strength` ("strong"|"moderate"|"limited"), `reasons` (list),
`shortfall_inr_lakh`, `disclaimers` (list of str), `policy_note` (str, sources).

---

## 5. Data & Config

### `backend/data/loan_policy.json` (real, sourced)
Keys: `data_note` (sources + as-of date), `currency`, `unsecured_cap_inr_lakh`,
`secured_ltv_pct`, `secured_max_inr_lakh`, `foir_pct`, `rate_bands`
(`{"secured": {"low", "high"}, "unsecured": {"low", "high"}}`),
`country_rate_adjustment_pct` (`{"US", "Canada", "default"}`),
`moratorium_months_default`, `processing_fee_pct`.

`data_note` cites publicly published rate cards / eligibility pages (e.g.
Credila, Avanse, SBI, Bank of Baroda) with the month/year captured, and states
the figures are indicative and lender-set in reality. Real values are gathered
during the implementation's research task.

### `backend/app/config.py` (behavior tunables only — no policy numbers)
`LOAN_DEFAULT_TENURE_YEARS`, `LOAN_STRENGTH_STRONG_EMI_PCT`,
`LOAN_STRENGTH_MODERATE_EMI_PCT`, `LOAN_POLICY_PATH`.

---

## 6. Agent Tool + REST Endpoint

### `backend/app/tools/loan.py` — `@tool loan_offer(...)`
Same parameters as `assess_eligibility`. Returns the offer as a JSON string.
Docstring instructs the agent to gather inputs conversationally (using what it
already remembers), to call this when the student asks about loan eligibility /
"how much can I get" / "what would my EMI be", and to present the result as an
*indicative* offer — never an approval. Registered in `agent.TOOLS` and named in
`SYSTEM_PROMPT`.

### `backend/app/server.py` — `POST /loan/offer`
Cookie-scoped (consistent with the app; identity resolved via `auth`, not the
body). Pydantic request model mirrors the engine inputs. Calls
`assess_eligibility`, returns the offer JSON. Reached from the web app via
`/api/agent/loan/offer`.

---

## 7. Frontend — `/loan` page

- New route `sarthi-web/src/app/(app)/loan/page.tsx` under the shared AppShell.
- Nav entry in `sarthi-web/src/lib/nav.ts` (`{ href: "/loan", label: "Loan",
  icon: "wallet" }`); `IconWallet` already exists; extend the shell's icon map.
- **Input form:** loan amount, co-applicant annual income, collateral value,
  country select, tenure slider.
- **Offer card:** eligible amount, rate band, representative EMI, a
  Strong/Moderate/Limited **strength badge**, the **reason chain**, shortfall (if
  any), and the advisory disclaimer.
- **Live recompute:** amount and tenure sliders re-call the endpoint (debounced)
  so the EMI/strength update as the student explores.
- Twilight-indigo/saffron theme, framer-motion, accessible — matching chat/SOP.

---

## 8. Compliance (baked in, non-negotiable)

Every offer (chat + page) carries: *"Indicative estimate by SARTHI, not a loan
sanction. Final amount, rate, and approval rest with the lender after
verification of income, collateral, and academics."* The reason chain provides
explainability by default; the framing keeps SARTHI advisory (RBI digital-lending
aligned — the NBFC underwrites). `disclaimers` is always populated by the engine,
so no surface can accidentally omit it.

---

## 9. Testing

- **`backend/tests/test_loan.py`** (pure engine, exhaustive): serviceability cap
  binds; unsecured cap binds; secured LTV cap; rate band differs secured vs
  unsecured; country rate adjustment applied; strength = strong/moderate/limited
  across scenarios; reason chain always non-empty; disclaimers always present;
  edge cases — zero income → Limited with a clear reason, zero collateral →
  unsecured, requested ≫ eligible → positive `shortfall_inr_lakh`,
  `_max_principal_for_emi` inverts `_emi` (round-trip within tolerance).
- **`backend/tests/test_loan_tool.py`**: `loan_offer` returns valid JSON with all
  documented keys.
- **`backend/tests/test_loan_api.py`**: `POST /loan/offer` via FastAPI TestClient
  (cookie-scoped, following `test_sop_api`).
- **Frontend:** `tsc --noEmit` + `next build` clean; manual browser pass (no FE
  test harness).
- Existing suite stays green.

---

## 10. Files

**New:** `backend/app/loan.py`, `backend/app/tools/loan.py`,
`backend/data/loan_policy.json`, `backend/tests/test_loan.py`,
`backend/tests/test_loan_tool.py`, `backend/tests/test_loan_api.py`,
`sarthi-web/src/app/(app)/loan/page.tsx`.
**Modified:** `backend/app/config.py`, `backend/app/tools/__init__.py`,
`backend/app/agent.py` (register tool), `backend/app/prompts.py`,
`backend/app/server.py`, `sarthi-web/src/lib/nav.ts`,
`sarthi-web/src/components/AppShell.tsx` (icon map if needed), `CLAUDE.md`.

---

## 11. Build-time Research Task

Compile `loan_policy.json` from real published Indian education-loan policies
(unsecured caps, secured LTV, FOIR/income norms, rate bands for secured vs
unsecured, moratorium norms, processing fees), citing each source and the as-of
date in `data_note`. Figures are indicative; the engine and disclaimers make that
explicit.
