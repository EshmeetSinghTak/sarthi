# F3 — ROI Predictor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deterministic ROI Predictor (cost vs. salary vs. EMI, per university) to SARTHI, exposed to the agent as two LangChain tools.

**Architecture:** Mirrors F2. Pure, testable functions in `backend/app/tools/roi.py` over a new `backend/data/salary_priors.json` (field×country salaries, real public figures). Two `@tool` wrappers (`estimate_roi`, `roi_breakdown`) registered in the agent graph. Every tunable constant lives in `config.py` — nothing hardcoded in logic.

**Tech Stack:** Python 3.14, LangChain/LangGraph, pytest (newly added), JSON data files.

## Global Constraints

- **No Claude / no paid LLMs in the product.** ROI math is pure Python; no model call for the numbers. (CLAUDE.md §0)
- **Never hardcode tunable values.** FX rate, loan defaults, sensitivity grid, prestige coefficients → `config.py`. Salaries/living costs → `salary_priors.json`. No literals in `roi.py` logic. (User preference)
- **Follow the F2 pattern:** pure function underneath a thin `@tool` wrapper; data in `backend/data/*.json`.
- **All run commands** assume working dir `backend/` and the venv interpreter `./.venv/Scripts/python`.
- **Windows console is cp1252** — any throwaway script printing model/Hindi output needs `sys.stdout.reconfigure(encoding="utf-8")` (not needed for pytest).
- **Figures are approximate, guidance-only** — every data file carries a `data_note`; the agent always adds a "verify" caveat.

---

### Task 1: Test toolchain + config constants (no hardcoding) + FX move

**Files:**
- Modify: `backend/app/config.py` (add domain constants at module level)
- Modify: `backend/app/tools/shortlist.py:24` (import `USD_PER_INR` from config instead of defining it)
- Create: `backend/pytest.ini`
- Create: `backend/requirements-dev.txt`
- Create: `backend/tests/__init__.py` (empty)
- Test: `backend/tests/test_config.py`

**Interfaces:**
- Produces: `config.USD_PER_INR: float`, `config.ROI_DEFAULT_INTEREST_RATE: float`, `config.ROI_DEFAULT_TENURE_YEARS: int`, `config.ROI_DEFAULT_LOAN_FRACTION: float`, `config.ROI_DEFAULT_YEARS: int`, `config.ROI_LIST_LIMIT: int`, `config.ROI_SENSITIVITY_RATES: tuple[float,...]`, `config.ROI_SENSITIVITY_TENURES: tuple[int,...]`, `config.ROI_PRESTIGE_BASE: float`, `config.ROI_PRESTIGE_STEP: float`. `config.BACKEND_DIR` already exists.

- [ ] **Step 1: Install pytest into the venv**

Run:
```bash
cd backend && ./.venv/Scripts/python -m pip install pytest
```
Expected: ends with `Successfully installed ... pytest-<version> ...`

- [ ] **Step 2: Record the dev dependency**

Create `backend/requirements-dev.txt`:
```
pytest
```

- [ ] **Step 3: Configure pytest**

Create `backend/pytest.ini`:
```ini
[pytest]
pythonpath = .
testpaths = tests
```

- [ ] **Step 4: Create the tests package marker**

Create empty file `backend/tests/__init__.py` (no content).

- [ ] **Step 5: Write the failing config test**

Create `backend/tests/test_config.py`:
```python
from app import config


def test_usd_per_inr_present_and_positive():
    assert config.USD_PER_INR > 0


def test_roi_constants_present():
    assert config.ROI_DEFAULT_INTEREST_RATE == 10.5
    assert config.ROI_DEFAULT_TENURE_YEARS == 8
    assert config.ROI_DEFAULT_LOAN_FRACTION == 0.70
    assert config.ROI_DEFAULT_YEARS == 2
    assert config.ROI_LIST_LIMIT == 6
    assert config.ROI_SENSITIVITY_RATES == (9.0, 10.5, 12.0)
    assert config.ROI_SENSITIVITY_TENURES == (5, 8, 10)
    assert config.ROI_PRESTIGE_BASE == 0.9
    assert config.ROI_PRESTIGE_STEP == 0.05


def test_shortlist_uses_shared_fx():
    from app.tools import shortlist
    assert shortlist.USD_PER_INR == config.USD_PER_INR
```

- [ ] **Step 6: Run the test to verify it fails**

Run: `cd backend && ./.venv/Scripts/python -m pytest tests/test_config.py -v`
Expected: FAIL — `AttributeError: module 'app.config' has no attribute 'USD_PER_INR'`

- [ ] **Step 7: Add the constants to config.py**

Append to the end of `backend/app/config.py` (after `settings = Settings()`):
```python

# --- Domain constants (centralized; never hardcode these in logic) ---
# USD per 1 INR. Env-overridable because the rate drifts; default ≈ ₹84/USD.
USD_PER_INR: float = float(os.getenv("SARTHI_USD_PER_INR", 1 / 84))

# ROI Predictor (F3) — all tunables live here, never inline in roi.py.
ROI_DEFAULT_INTEREST_RATE: float = 10.5  # annual %, typical Indian education loan
ROI_DEFAULT_TENURE_YEARS: int = 8        # loan repayment tenure
ROI_DEFAULT_LOAN_FRACTION: float = 0.70  # fallback loan = 70% of total cost
ROI_DEFAULT_YEARS: int = 2               # degree length in years
ROI_LIST_LIMIT: int = 6                  # max universities in a base-case list
ROI_SENSITIVITY_RATES: tuple[float, ...] = (9.0, 10.5, 12.0)   # grid columns (%)
ROI_SENSITIVITY_TENURES: tuple[int, ...] = (5, 8, 10)          # grid rows (years)
ROI_PRESTIGE_BASE: float = 0.9   # salary multiplier at competitiveness 1
ROI_PRESTIGE_STEP: float = 0.05  # +per competitiveness point (→ 1.1 at comp 5)
```

- [ ] **Step 8: Point shortlist.py at the shared FX constant**

In `backend/app/tools/shortlist.py`, replace line 24:
```python
USD_PER_INR = 1 / 84  # MVP fixed rate (see CLAUDE.md D7)
```
with:
```python
from ..config import USD_PER_INR  # shared FX constant (see CLAUDE.md D7)
```
Place this import with the other imports near the top (after `from langchain_core.tools import tool`), and delete the old assignment line. The name `USD_PER_INR` stays usable unchanged in the rest of the module.

- [ ] **Step 9: Run the tests to verify they pass**

Run: `cd backend && ./.venv/Scripts/python -m pytest tests/test_config.py -v`
Expected: PASS (3 passed)

- [ ] **Step 10: Sanity-check shortlist still works**

Run: `cd backend && ./.venv/Scripts/python -c "import sys; sys.path.insert(0,'.'); from app.tools.shortlist import shortlist; print(shortlist('Robotics', country='US')['count'])"`
Expected: prints a positive integer (e.g. `6`)

- [ ] **Step 11: Commit**

```bash
git add backend/pytest.ini backend/requirements-dev.txt backend/tests/__init__.py backend/tests/test_config.py backend/app/config.py backend/app/tools/shortlist.py
git commit -m "F3: add pytest + ROI config constants, share USD_PER_INR"
```

---

### Task 2: Salary priors data file

**Files:**
- Create: `backend/data/salary_priors.json`
- Test: `backend/tests/test_salary_data.py`

**Interfaces:**
- Produces: `salary_priors.json` with keys `data_note`, `currency`, `living_cost_usd_per_year` (US, Canada), `starting_salary_usd[country][field]` for all 8 fields in `universities.json`'s `fields_taxonomy`, both countries.

- [ ] **Step 1: (Honor "real figures") Quick-verify anchor salaries**

Do a quick web check on 2-3 anchors (US CS/SWE new-grad H1B median on levels.fyi or h1bdata.info; Canada CS new-grad). If a figure below is materially off (>~15%), adjust it in Step 3. This keeps the numbers defensibly "real public figures," not invented. Do not block on this — the values below are reasonable approximations.

- [ ] **Step 2: Write the failing data-integrity test**

Create `backend/tests/test_salary_data.py`:
```python
import json

from app import config


def _load(name):
    return json.loads((config.BACKEND_DIR / "data" / name).read_text(encoding="utf-8"))


def test_salary_priors_cover_every_field_and_country():
    salary = _load("salary_priors.json")
    taxonomy = _load("universities.json")["fields_taxonomy"]
    for country in ("US", "Canada"):
        assert salary["living_cost_usd_per_year"][country] > 0
        for field in taxonomy:
            assert salary["starting_salary_usd"][country][field] > 0


def test_salary_priors_has_data_note():
    salary = _load("salary_priors.json")
    assert salary["data_note"].strip()
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `cd backend && ./.venv/Scripts/python -m pytest tests/test_salary_data.py -v`
Expected: FAIL — `FileNotFoundError` for `salary_priors.json`

- [ ] **Step 4: Create the data file**

Create `backend/data/salary_priors.json`:
```json
{
  "data_note": "Approximate median new-grad (master's) salaries for guidance only — NOT a guarantee. Sources: US H1B LCA disclosure medians + levels.fyi entry-level figures (USD/yr); Canada figures converted from CAD market medians. Living costs are rough annual estimates (tuition is separate, from universities.json). Always verify against current data.",
  "currency": "USD",
  "living_cost_usd_per_year": {
    "US": 18000,
    "Canada": 15000
  },
  "starting_salary_usd": {
    "US": {
      "Computer Science": 120000,
      "AI/ML": 135000,
      "Data Science": 115000,
      "Robotics": 115000,
      "Electrical Engineering": 100000,
      "Mechanical Engineering": 85000,
      "Civil Engineering": 72000,
      "Business/MBA": 110000
    },
    "Canada": {
      "Computer Science": 75000,
      "AI/ML": 85000,
      "Data Science": 72000,
      "Robotics": 72000,
      "Electrical Engineering": 68000,
      "Mechanical Engineering": 62000,
      "Civil Engineering": 58000,
      "Business/MBA": 70000
    }
  }
}
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `cd backend && ./.venv/Scripts/python -m pytest tests/test_salary_data.py -v`
Expected: PASS (2 passed)

- [ ] **Step 6: Commit**

```bash
git add backend/data/salary_priors.json backend/tests/test_salary_data.py
git commit -m "F3: add field x country salary priors data"
```

---

### Task 3: ROI pure functions (`_emi`, `_prestige_multiplier`, `roi_for_university`, `roi`)

**Files:**
- Create: `backend/app/tools/roi.py`
- Test: `backend/tests/test_roi.py`

**Interfaces:**
- Consumes: `config.*` constants (Task 1), `salary_priors.json` (Task 2), and from `shortlist.py`: `UNIVERSITIES: list[dict]`, `_normalize_field(str)->str|None`, `_normalize_country(str|None)->str|None`.
- Produces:
  - `_emi(principal_inr: float, annual_rate_pct: float, years: int) -> float`
  - `_prestige_multiplier(competitiveness: int) -> float`
  - `roi_for_university(uni: dict, field: str, loan_inr_lakh: float|None, interest_rate: float, tenure_years: int, years: int) -> dict | None`
  - `roi(field, country=None, universities=None, loan_inr_lakh=None, interest_rate=config.ROI_DEFAULT_INTEREST_RATE, tenure_years=config.ROI_DEFAULT_TENURE_YEARS, years=config.ROI_DEFAULT_YEARS, limit=config.ROI_LIST_LIMIT) -> dict` — dict with `note`, `assumptions`, `count`, `results` (each row has: `name, country, city, qs_rank, total_cost_inr_lakh, expected_salary_inr_lakh_per_year, loan_inr_lakh, monthly_emi_inr, emi_to_income_pct, payback_years`).

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_roi.py`:
```python
from app import config
from app.tools import roi as roi_mod


def test_emi_known_value():
    # ₹10,00,000 @ 10% for 10 years ≈ ₹13,215/month
    assert abs(roi_mod._emi(1_000_000, 10.0, 10) - 13215) < 5


def test_emi_zero_rate_is_principal_over_months():
    assert roi_mod._emi(1_200_000, 0, 10) == 1_200_000 / 120


def test_emi_higher_rate_costs_more():
    assert roi_mod._emi(1_000_000, 12, 8) > roi_mod._emi(1_000_000, 9, 8)


def test_prestige_multiplier_endpoints():
    assert roi_mod._prestige_multiplier(1) == config.ROI_PRESTIGE_BASE
    assert abs(roi_mod._prestige_multiplier(5) - 1.1) < 1e-9


def test_roi_rows_have_expected_keys_and_positive_numbers():
    out = roi_mod.roi("Computer Science", country="US")
    assert out["count"] > 0
    row = out["results"][0]
    for key in (
        "name", "country", "city", "qs_rank", "total_cost_inr_lakh",
        "expected_salary_inr_lakh_per_year", "loan_inr_lakh",
        "monthly_emi_inr", "emi_to_income_pct", "payback_years",
    ):
        assert key in row
    assert row["total_cost_inr_lakh"] > 0
    assert row["monthly_emi_inr"] > 0
    assert row["payback_years"] > 0


def test_roi_sorted_by_payback_ascending():
    out = roi_mod.roi("Computer Science", country="US")
    paybacks = [r["payback_years"] for r in out["results"]]
    assert paybacks == sorted(paybacks)


def test_roi_default_loan_is_fraction_of_cost():
    out = roi_mod.roi("Computer Science", universities=["Arizona State University"])
    row = out["results"][0]
    expected = round(row["total_cost_inr_lakh"] * config.ROI_DEFAULT_LOAN_FRACTION, 1)
    assert row["loan_inr_lakh"] == expected


def test_roi_explicit_universities_filter():
    out = roi_mod.roi("Computer Science", universities=["Arizona State University"])
    assert out["count"] == 1
    assert out["results"][0]["name"] == "Arizona State University"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && ./.venv/Scripts/python -m pytest tests/test_roi.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.tools.roi'`

- [ ] **Step 3: Implement the pure functions**

Create `backend/app/tools/roi.py`:
```python
"""F3 — ROI Predictor.

Given a field/country (or an explicit list of universities), estimates the
financial return of a degree: total cost, expected starting salary, monthly
loan EMI, EMI-to-income ratio, and payback years. All figures are approximate,
for guidance only.

Two tools are exposed to the agent (see bottom of file):
- estimate_roi:  base-case ROI for each matching university (a scannable list).
- roi_breakdown: one named university + a rate x tenure EMI sensitivity grid.

The pure functions are independently testable. Every tunable number lives in
app.config — nothing is hardcoded here.
"""

import json

from langchain_core.tools import tool

from .. import config
from .shortlist import UNIVERSITIES, _normalize_country, _normalize_field

_SALARY = json.loads(
    (config.BACKEND_DIR / "data" / "salary_priors.json").read_text(encoding="utf-8")
)
SALARY_NOTE = _SALARY["data_note"]
STARTING_SALARY_USD = _SALARY["starting_salary_usd"]
LIVING_COST_USD = _SALARY["living_cost_usd_per_year"]


def _usd_to_inr_lakh(usd: float) -> float:
    """Convert USD to INR lakh using the shared FX constant."""
    return usd / config.USD_PER_INR / 100_000


def _emi(principal_inr: float, annual_rate_pct: float, years: int) -> float:
    """Monthly EMI via standard amortization. Zero/negative rate -> P / months."""
    months = max(int(years) * 12, 1)
    if annual_rate_pct <= 0:
        return principal_inr / months
    r = annual_rate_pct / 100 / 12
    growth = (1 + r) ** months
    return principal_inr * r * growth / (growth - 1)


def _prestige_multiplier(competitiveness: int) -> float:
    """Mild salary nudge by selectivity: 0.9 (comp 1) ... 1.1 (comp 5)."""
    return config.ROI_PRESTIGE_BASE + config.ROI_PRESTIGE_STEP * (competitiveness - 1)


def roi_for_university(
    uni: dict,
    field: str,
    loan_inr_lakh: float | None,
    interest_rate: float,
    tenure_years: int,
    years: int,
) -> dict | None:
    """ROI for one university. Returns None if no salary prior for its country/field."""
    country = uni["country"]
    salary_usd = STARTING_SALARY_USD.get(country, {}).get(field)
    if salary_usd is None:
        return None
    salary_usd *= _prestige_multiplier(uni["competitiveness"])

    living = LIVING_COST_USD.get(country, 0)
    total_cost_inr_lakh = _usd_to_inr_lakh((uni["tuition_usd"] + living) * years)
    salary_inr_lakh = _usd_to_inr_lakh(salary_usd)
    salary_inr_per_year = salary_inr_lakh * 100_000

    loan_lakh = (
        loan_inr_lakh
        if loan_inr_lakh is not None
        else total_cost_inr_lakh * config.ROI_DEFAULT_LOAN_FRACTION
    )
    emi = _emi(loan_lakh * 100_000, interest_rate, tenure_years)
    total_repayment = emi * tenure_years * 12
    payback_years = total_repayment / salary_inr_per_year
    emi_to_income_pct = emi / (salary_inr_per_year / 12) * 100

    return {
        "name": uni["name"],
        "country": country,
        "city": uni["city"],
        "qs_rank": uni["qs_rank"],
        "total_cost_inr_lakh": round(total_cost_inr_lakh, 1),
        "expected_salary_inr_lakh_per_year": round(salary_inr_lakh, 1),
        "loan_inr_lakh": round(loan_lakh, 1),
        "monthly_emi_inr": round(emi),
        "emi_to_income_pct": round(emi_to_income_pct, 1),
        "payback_years": round(payback_years, 1),
    }


def roi(
    field: str,
    country: str | None = None,
    universities: list[str] | None = None,
    loan_inr_lakh: float | None = None,
    interest_rate: float = config.ROI_DEFAULT_INTEREST_RATE,
    tenure_years: int = config.ROI_DEFAULT_TENURE_YEARS,
    years: int = config.ROI_DEFAULT_YEARS,
    limit: int = config.ROI_LIST_LIMIT,
) -> dict:
    """Per-university base-case ROI list, sorted by fewest payback years."""
    canon_field = _normalize_field(field)
    canon_country = _normalize_country(country)
    field_for_salary = canon_field or field

    if universities:
        wanted = {u.strip().lower() for u in universities}
        pool = [u for u in UNIVERSITIES if u["name"].strip().lower() in wanted]
    else:
        pool = [
            u
            for u in UNIVERSITIES
            if (not canon_field or canon_field in u["fields"])
            and (not canon_country or u["country"] == canon_country)
        ]

    rows = []
    for u in pool:
        row = roi_for_university(
            u, field_for_salary, loan_inr_lakh, interest_rate, tenure_years, years
        )
        if row:
            rows.append(row)
    rows.sort(key=lambda r: r["payback_years"])
    rows = rows[:limit]

    return {
        "note": SALARY_NOTE,
        "assumptions": {
            "interest_rate_pct": interest_rate,
            "tenure_years": tenure_years,
            "degree_years": years,
            "loan_inr_lakh": loan_inr_lakh,
            "loan_default_fraction_of_cost": (
                None if loan_inr_lakh is not None else config.ROI_DEFAULT_LOAN_FRACTION
            ),
        },
        "count": len(rows),
        "results": rows,
    }
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && ./.venv/Scripts/python -m pytest tests/test_roi.py -v`
Expected: PASS (8 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/tools/roi.py backend/tests/test_roi.py
git commit -m "F3: ROI pure functions (EMI, salary, payback) + tests"
```

---

### Task 4: Sensitivity-grid function (`breakdown`)

**Files:**
- Modify: `backend/app/tools/roi.py` (add `breakdown`)
- Test: `backend/tests/test_roi.py` (add grid tests)

**Interfaces:**
- Consumes: `roi_for_university` (Task 3), `_emi` (Task 3), `config.ROI_SENSITIVITY_RATES`, `config.ROI_SENSITIVITY_TENURES`, `UNIVERSITIES`, `_normalize_field`.
- Produces: `breakdown(university: str, field: str, loan_inr_lakh: float|None = None, years: int = config.ROI_DEFAULT_YEARS) -> dict` — on success: `note`, `university`, `base_case` (a `roi_for_university` row), `sensitivity_grid` with `rates_pct`, `tenures_years`, and `monthly_emi_inr` (list of `{tenure_years, emi_by_rate: {"<rate>%": emi}}`). On failure: `{"error": str, "note": str}`.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_roi.py`:
```python
def test_breakdown_full_grid_shape():
    out = roi_mod.breakdown("Arizona State University", "Computer Science")
    grid = out["sensitivity_grid"]["monthly_emi_inr"]
    assert len(grid) == len(config.ROI_SENSITIVITY_TENURES)
    for row in grid:
        assert len(row["emi_by_rate"]) == len(config.ROI_SENSITIVITY_RATES)
    assert "base_case" in out
    assert out["university"] == "Arizona State University"


def test_breakdown_emi_rises_with_rate_within_a_tenure():
    out = roi_mod.breakdown("Arizona State University", "Computer Science")
    first_row = out["sensitivity_grid"]["monthly_emi_inr"][0]
    emis = list(first_row["emi_by_rate"].values())
    assert emis == sorted(emis)


def test_breakdown_substring_match():
    out = roi_mod.breakdown("Arizona State", "Computer Science")
    assert out["university"] == "Arizona State University"


def test_breakdown_unknown_university_returns_error():
    out = roi_mod.breakdown("Hogwarts", "Computer Science")
    assert "error" in out
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && ./.venv/Scripts/python -m pytest tests/test_roi.py -k breakdown -v`
Expected: FAIL — `AttributeError: module 'app.tools.roi' has no attribute 'breakdown'`

- [ ] **Step 3: Implement `breakdown`**

In `backend/app/tools/roi.py`, add after the `roi(...)` function (before any `@tool` definitions, which arrive in Task 5):
```python
def breakdown(
    university: str,
    field: str,
    loan_inr_lakh: float | None = None,
    years: int = config.ROI_DEFAULT_YEARS,
) -> dict:
    """One university's base-case ROI plus a rate x tenure EMI sensitivity grid."""
    canon_field = _normalize_field(field) or field
    target = university.strip().lower()
    uni = next((u for u in UNIVERSITIES if u["name"].strip().lower() == target), None)
    if uni is None:
        uni = next((u for u in UNIVERSITIES if target in u["name"].lower()), None)
    if uni is None:
        return {"error": f"University '{university}' not found in dataset.", "note": SALARY_NOTE}

    base = roi_for_university(
        uni,
        canon_field,
        loan_inr_lakh,
        config.ROI_DEFAULT_INTEREST_RATE,
        config.ROI_DEFAULT_TENURE_YEARS,
        years,
    )
    if base is None:
        return {
            "error": f"No salary data for {canon_field} in {uni['country']}.",
            "note": SALARY_NOTE,
        }

    loan_inr = base["loan_inr_lakh"] * 100_000
    grid = []
    for tenure in config.ROI_SENSITIVITY_TENURES:
        grid.append(
            {
                "tenure_years": tenure,
                "emi_by_rate": {
                    f"{rate}%": round(_emi(loan_inr, rate, tenure))
                    for rate in config.ROI_SENSITIVITY_RATES
                },
            }
        )

    return {
        "note": SALARY_NOTE,
        "university": uni["name"],
        "base_case": base,
        "sensitivity_grid": {
            "rates_pct": list(config.ROI_SENSITIVITY_RATES),
            "tenures_years": list(config.ROI_SENSITIVITY_TENURES),
            "monthly_emi_inr": grid,
        },
    }
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && ./.venv/Scripts/python -m pytest tests/test_roi.py -v`
Expected: PASS (12 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/tools/roi.py backend/tests/test_roi.py
git commit -m "F3: rate x tenure EMI sensitivity breakdown + tests"
```

---

### Task 5: `@tool` wrappers, export, and agent registration

**Files:**
- Modify: `backend/app/tools/roi.py` (add two `@tool` wrappers at the bottom)
- Modify: `backend/app/tools/__init__.py` (export the tools)
- Modify: `backend/app/agent.py:25,27` (import + add to `TOOLS`)
- Test: `backend/tests/test_roi_tools.py`

**Interfaces:**
- Consumes: `roi(...)` and `breakdown(...)` (Tasks 3-4).
- Produces: `estimate_roi` and `roi_breakdown` LangChain tools (call with `.invoke({...})`, return JSON strings). Exported from `app.tools`.

- [ ] **Step 1: Write the failing tool tests**

Create `backend/tests/test_roi_tools.py`:
```python
import json

from app.tools import estimate_roi, roi_breakdown


def test_estimate_roi_tool_returns_json_list():
    out = estimate_roi.invoke({"field": "Computer Science", "country": "US"})
    data = json.loads(out)
    assert data["count"] > 0
    assert "monthly_emi_inr" in data["results"][0]


def test_estimate_roi_tool_accepts_university_list():
    out = estimate_roi.invoke(
        {"field": "Robotics", "universities": ["Carnegie Mellon University"]}
    )
    data = json.loads(out)
    assert data["count"] == 1
    assert data["results"][0]["name"] == "Carnegie Mellon University"


def test_roi_breakdown_tool_returns_grid():
    out = roi_breakdown.invoke(
        {"university": "Arizona State University", "field": "Computer Science"}
    )
    data = json.loads(out)
    assert "sensitivity_grid" in data
    assert data["university"] == "Arizona State University"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && ./.venv/Scripts/python -m pytest tests/test_roi_tools.py -v`
Expected: FAIL — `ImportError: cannot import name 'estimate_roi' from 'app.tools'`

- [ ] **Step 3: Add the `@tool` wrappers**

Append to the bottom of `backend/app/tools/roi.py`:
```python
@tool
def estimate_roi(
    field: str,
    country: str | None = None,
    universities: list[str] | None = None,
    loan_inr_lakh: float | None = None,
    interest_rate: float | None = None,
    tenure_years: int | None = None,
) -> str:
    """Estimate the financial ROI (cost vs salary vs EMI) of a degree, per university.

    Call this when the student asks whether a degree is "worth it", about cost,
    expected salary, or loan EMI — or right after shortlisting, to attach ROI to
    the same schools (pass their names in `universities`).

    Args:
        field: Field of study, e.g. "Robotics", "Computer Science", "MBA".
        country: "US" or "Canada". Omit if open to any.
        universities: Optional list of university names to score (e.g. the ones you
            just shortlisted). If omitted, matches by field/country.
        loan_inr_lakh: Loan amount in INR lakh. Omit to assume 70% of total cost.
        interest_rate: Annual loan interest %. Omit for the default (~10.5%).
        tenure_years: Loan tenure in years. Omit for the default (8).

    Returns a JSON string: per-university total cost, expected salary, monthly EMI,
    EMI-to-income %, and payback years. All figures approximate — present as
    guidance and say they are worth verifying.
    """
    return json.dumps(
        roi(
            field,
            country=country,
            universities=universities,
            loan_inr_lakh=loan_inr_lakh,
            interest_rate=(
                interest_rate if interest_rate is not None else config.ROI_DEFAULT_INTEREST_RATE
            ),
            tenure_years=(
                tenure_years if tenure_years is not None else config.ROI_DEFAULT_TENURE_YEARS
            ),
        )
    )


@tool
def roi_breakdown(
    university: str,
    field: str,
    loan_inr_lakh: float | None = None,
) -> str:
    """Detailed ROI for ONE university, with a loan rate x tenure EMI grid.

    Call this when the student zooms into a single university and wants to see how
    the monthly EMI changes across interest rates and repayment tenures.

    Args:
        university: The university name (e.g. "Arizona State University").
        field: Field of study, e.g. "Computer Science".
        loan_inr_lakh: Loan amount in INR lakh. Omit to assume 70% of total cost.

    Returns a JSON string with the base-case ROI plus a sensitivity grid of
    monthly EMIs across rates and tenures. All figures approximate.
    """
    return json.dumps(breakdown(university, field, loan_inr_lakh=loan_inr_lakh))
```

- [ ] **Step 4: Export the tools**

Replace the contents of `backend/app/tools/__init__.py` with:
```python
"""Agent tools (F2+)."""

from .roi import estimate_roi, roi_breakdown
from .shortlist import shortlist_universities

__all__ = ["shortlist_universities", "estimate_roi", "roi_breakdown"]
```

- [ ] **Step 5: Register the tools in the agent graph**

In `backend/app/agent.py`, change the tools import (line 25):
```python
from .tools import estimate_roi, roi_breakdown, shortlist_universities
```
and the `TOOLS` list (line 27):
```python
TOOLS = [shortlist_universities, estimate_roi, roi_breakdown]
```
(No other change needed — `ToolNode(TOOLS)` and `bind_tools(TOOLS)` already consume the list.)

- [ ] **Step 6: Run the full test suite to verify everything passes**

Run: `cd backend && ./.venv/Scripts/python -m pytest -v`
Expected: PASS (all tests across config, salary data, roi, roi_tools)

- [ ] **Step 7: Verify the graph imports cleanly**

Run: `cd backend && ./.venv/Scripts/python -c "import sys; sys.path.insert(0,'.'); from app.agent import TOOLS; print([t.name for t in TOOLS])"`
Expected: `['shortlist_universities', 'estimate_roi', 'roi_breakdown']`

- [ ] **Step 8: Commit**

```bash
git add backend/app/tools/roi.py backend/app/tools/__init__.py backend/app/agent.py backend/tests/test_roi_tools.py
git commit -m "F3: expose estimate_roi + roi_breakdown tools, register in agent"
```

---

### Task 6: System prompt update + manual end-to-end check

**Files:**
- Modify: `backend/app/prompts.py` (extend the "YOUR TOOLS" section)
- Test: `backend/tests/test_prompt.py`

**Interfaces:**
- Consumes: nothing new. Produces: updated `SYSTEM_PROMPT` mentioning both ROI tools and how to render their output.

- [ ] **Step 1: Write the failing prompt test**

Create `backend/tests/test_prompt.py`:
```python
from app.prompts import SYSTEM_PROMPT


def test_prompt_mentions_roi_tools():
    assert "estimate_roi" in SYSTEM_PROMPT
    assert "roi_breakdown" in SYSTEM_PROMPT
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && ./.venv/Scripts/python -m pytest tests/test_prompt.py -v`
Expected: FAIL — `assert 'estimate_roi' in SYSTEM_PROMPT`

- [ ] **Step 3: Extend the prompt's "YOUR TOOLS" section**

In `backend/app/prompts.py`, the `SYSTEM_PROMPT` is one triple-quoted string. The `shortlist_universities` tool paragraph ends `...Suggest a healthy mix, not only Reach \` then a final continuation line that is just:
```python
schools.
```
Directly **after** that `schools.` line and **before** the blank line preceding `BOUNDARIES:`, paste these lines *inside the same triple-quoted string* (do not add new quotes — match the existing `\`-continuation style):
```python
- estimate_roi: call this when the student asks if a degree is "worth it", or \
about cost, expected salary, or loan EMI — and especially right after a \
shortlist, passing the same school names in `universities` so cost meets fit. \
Present results as a short markdown table (University | Cost | Salary/yr | \
EMI/mo | Payback yrs), then one line of plain-language guidance (e.g. what the \
EMI-to-income ratio implies). Always say figures are approximate.
- roi_breakdown: call this when the student zooms into ONE university and wants \
to see how the monthly EMI shifts across interest rates and tenures. Present the \
sensitivity grid as a small markdown table (tenure rows x rate columns).
```
The lines above become part of the existing `SYSTEM_PROMPT` string; the file's trailing `BOUNDARIES: ...` content stays after them, still inside the same triple quotes.

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd backend && ./.venv/Scripts/python -m pytest tests/test_prompt.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Run the full suite**

Run: `cd backend && ./.venv/Scripts/python -m pytest -v`
Expected: PASS (all tests)

- [ ] **Step 6: Manual end-to-end check (real agent, rate-limit-safe model)**

Start the backend in one terminal:
```bash
cd backend && SARTHI_MODEL_DEFAULT=meta/llama-3.3-70b-instruct ./.venv/Scripts/python -m uvicorn app.server:app --port 8000
```
Then exercise the agent (new terminal, or the web UI at :3000). Confirm:
- Asking "MS in Robotics in the US — is it worth it financially?" triggers `estimate_roi` and renders a cost/salary/EMI/payback table.
- A follow-up "show me the EMI breakdown for Carnegie Mellon" triggers `roi_breakdown` and renders a rate×tenure grid.
- The reply includes an "approximate / verify" caveat.

(If the model doesn't call the tool, nudge the prompt wording; tool-calling is confirmed on llama-3.3-70b per CLAUDE.md §0.)

- [ ] **Step 7: Commit**

```bash
git add backend/app/prompts.py backend/tests/test_prompt.py
git commit -m "F3: teach the agent the ROI tools + rendering; finish F3"
```

---

## Post-implementation

- Update `CLAUDE.md` §0 "Next up" (F3 → done; note F3 shipped) and §14 checklist (`[x] F3 ROI`). The salary-priors open item in §14 is now satisfied by `salary_priors.json`.
- Consider merging `f3-roi-predictor` → `main` (see superpowers:finishing-a-development-branch).
```
