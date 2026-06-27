# F5 — Loan Eligibility + Personalized Offer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** An indicative education-loan eligibility + offer engine, surfaced both as an agent tool (chat offer card) and a `/loan` page, with an explainable reason chain and advisory framing.

**Architecture:** A pure `app/loan.py` engine (single `assess_eligibility()` entry point = ML-ready seam) reads real, sourced figures from `data/loan_policy.json` and shared math from a new `app/finance.py`. Two thin consumers call it: a `loan_offer` agent tool and a `POST /loan/offer` REST endpoint. Stateless (no DB).

**Tech Stack:** Python 3.14, LangChain `@tool`, FastAPI + Pydantic, pytest (sync); Next.js 16 + React 19 + Tailwind v4 + framer-motion.

## Global Constraints

- **No paid LLMs / no Claude.** Not relevant to F5's compute (deterministic), but no new model calls are added.
- **Never hardcode tunables.** Policy *numbers* live in `backend/data/loan_policy.json`; engine *behavior* tunables live in `backend/app/config.py`. Nothing numeric hardcoded in `loan.py`.
- **Honesty:** no fabricated ML model; `loan_policy.json` holds real, **cited** published figures with an as-of date.
- **Compliance (non-negotiable):** every offer carries an advisory disclaimer; SARTHI is advisory, the lender underwrites. The engine itself populates `disclaimers`, so no surface can omit it.
- **`user_id` from the signed cookie**, never the body (REST endpoint follows the existing `auth.resolve_user` + `_with_cookie` pattern).
- **Stateless v1:** offers are recomputed on demand; no persistence.
- Tests: plain `pytest`, no new deps. Backend: `cd backend && ./.venv/Scripts/python -m pytest -q`. Frontend: `cd sarthi-web && npx tsc --noEmit` and `npm run build`.
- Windows: scripts printing model/unicode output need `sys.stdout.reconfigure(encoding="utf-8")`.

---

## File Structure

**New files:**
- `backend/app/finance.py` — shared loan math: `emi`, `max_principal_for_emi` (pure, no app imports).
- `backend/data/loan_policy.json` — real, cited lender-policy figures.
- `backend/app/loan.py` — the eligibility engine: `assess_eligibility` + internal `_rule_engine`.
- `backend/app/tools/loan.py` — `@tool loan_offer`.
- `backend/tests/test_finance.py`, `test_loan.py`, `test_loan_tool.py`, `test_loan_api.py`.
- `sarthi-web/src/lib/loan.ts` — typed client for the offer endpoint.
- `sarthi-web/src/app/(app)/loan/page.tsx` — the loan workspace.

**Modified files:**
- `backend/app/config.py` — loan behavior tunables.
- `backend/app/tools/roi.py` — use `finance.emi` (keep `_emi` alias for its tests).
- `backend/app/tools/__init__.py` — export `loan_offer`.
- `backend/app/agent.py` — register `loan_offer` in `TOOLS`.
- `backend/app/prompts.py` — describe the tool.
- `backend/app/server.py` — `POST /loan/offer`.
- `sarthi-web/src/lib/nav.ts` — add the Loan nav item.
- `sarthi-web/src/components/AppShell.tsx` — add `wallet` to the icon map.
- `backend/tests/test_config.py` — assert new tunables.
- `CLAUDE.md` — record F5.

---

## Task 1: Policy data + config tunables

**Files:**
- Create: `backend/data/loan_policy.json`
- Modify: `backend/app/config.py`
- Test: `backend/tests/test_config.py`

**Interfaces:**
- Produces: `config.LOAN_DEFAULT_TENURE_YEARS: int`, `config.LOAN_STRENGTH_STRONG_EMI_PCT: float`, `config.LOAN_STRENGTH_MODERATE_EMI_PCT: float`, `config.LOAN_POLICY_PATH: Path`; the JSON file with keys listed below.

- [ ] **Step 1: Research and write `loan_policy.json`**

Research current publicly published Indian education-loan figures (HDFC Credila, Avanse, SBI Global Ed-Vantage, Bank of Baroda rate cards / eligibility pages). Create `backend/data/loan_policy.json` with the values you confirm and cite the URLs + capture month in `data_note`. The values below are realistic starting points — **verify and adjust each against a live source, and replace the `data_note` with real cited URLs**:

```json
{
  "data_note": "Indicative figures compiled from publicly published Indian education-loan rate cards and eligibility pages (HDFC Credila, Avanse, SBI Global Ed-Vantage, Bank of Baroda), captured June 2026. Sources: <add the exact URLs you used>. Lenders set actual terms after assessment; these are for guidance only.",
  "currency": "INR",
  "unsecured_cap_inr_lakh": 50,
  "secured_ltv_pct": 90,
  "secured_max_inr_lakh": 150,
  "foir_pct": 55,
  "rate_bands": {
    "secured": { "low": 9.5, "high": 11.5 },
    "unsecured": { "low": 11.0, "high": 14.5 }
  },
  "country_rate_adjustment_pct": { "US": 0.0, "Canada": 0.0, "default": 0.5 },
  "moratorium_months_default": 12,
  "processing_fee_pct": 1.0
}
```

- [ ] **Step 2: Write the failing test**

Add to `backend/tests/test_config.py`:

```python
def test_loan_tunables_present():
    assert config.LOAN_DEFAULT_TENURE_YEARS > 0
    assert 0 < config.LOAN_STRENGTH_STRONG_EMI_PCT < config.LOAN_STRENGTH_MODERATE_EMI_PCT <= 100
    assert config.LOAN_POLICY_PATH.exists()


def test_loan_policy_file_shape():
    import json
    policy = json.loads(config.LOAN_POLICY_PATH.read_text(encoding="utf-8"))
    for key in (
        "data_note", "unsecured_cap_inr_lakh", "secured_ltv_pct",
        "secured_max_inr_lakh", "foir_pct", "rate_bands",
        "country_rate_adjustment_pct", "moratorium_months_default",
    ):
        assert key in policy, key
    assert policy["rate_bands"]["secured"]["low"] < policy["rate_bands"]["unsecured"]["high"]
    assert "default" in policy["country_rate_adjustment_pct"]
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd backend && ./.venv/Scripts/python -m pytest tests/test_config.py -q`
Expected: FAIL — `AttributeError: ... 'LOAN_DEFAULT_TENURE_YEARS'`.

- [ ] **Step 4: Add the config tunables**

In `backend/app/config.py`, append after the SOP constants block:

```python
# --- F5 Loan Eligibility + Offer (behavior tunables; policy numbers live in
# data/loan_policy.json, never here) ---
LOAN_DEFAULT_TENURE_YEARS: int = 10            # typical education-loan tenure
LOAN_STRENGTH_STRONG_EMI_PCT: float = 40.0     # EMI <= this % of income -> Strong
LOAN_STRENGTH_MODERATE_EMI_PCT: float = 60.0   # <= this -> Moderate, else Limited
LOAN_POLICY_PATH = BACKEND_DIR / "data" / "loan_policy.json"
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && ./.venv/Scripts/python -m pytest tests/test_config.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/data/loan_policy.json backend/app/config.py backend/tests/test_config.py
git commit -m "feat(loan): real sourced loan_policy.json + engine config tunables"
```

---

## Task 2: Shared finance helpers

**Files:**
- Create: `backend/app/finance.py`
- Modify: `backend/app/tools/roi.py`
- Test: `backend/tests/test_finance.py`

**Interfaces:**
- Produces: `finance.emi(principal_inr: float, annual_rate_pct: float, years: int) -> float`; `finance.max_principal_for_emi(monthly_emi: float, annual_rate_pct: float, years: int) -> float`.
- Consumed by: `roi.py` (Task 2 refactor) and `loan.py` (Task 3).

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_finance.py`:

```python
from app import finance


def test_emi_known_value():
    # Rs 10,00,000 @ 10% for 10 years ~ Rs 13,215/month
    assert abs(finance.emi(1_000_000, 10.0, 10) - 13215) < 5


def test_emi_zero_rate_is_principal_over_months():
    assert finance.emi(1_200_000, 0, 10) == 1_200_000 / 120


def test_max_principal_inverts_emi():
    # Round-trip: principal -> EMI -> principal.
    principal = 2_500_000
    e = finance.emi(principal, 11.0, 8)
    assert abs(finance.max_principal_for_emi(e, 11.0, 8) - principal) < 1.0


def test_max_principal_zero_rate():
    assert finance.max_principal_for_emi(10_000, 0, 10) == 10_000 * 120


def test_max_principal_nonpositive_emi_is_zero():
    assert finance.max_principal_for_emi(0, 11.0, 8) == 0
    assert finance.max_principal_for_emi(-5, 11.0, 8) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && ./.venv/Scripts/python -m pytest tests/test_finance.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.finance'`.

- [ ] **Step 3: Create `finance.py`**

Create `backend/app/finance.py`:

```python
"""Shared loan math — pure functions, no app imports (avoids import cycles).

Used by the ROI predictor (F3) and the loan eligibility engine (F5).
"""


def emi(principal_inr: float, annual_rate_pct: float, years: int) -> float:
    """Monthly EMI via standard amortization. Zero/negative rate -> P / months."""
    months = max(int(years) * 12, 1)
    if annual_rate_pct <= 0:
        return principal_inr / months
    r = annual_rate_pct / 100 / 12
    growth = (1 + r) ** months
    return principal_inr * r * growth / (growth - 1)


def max_principal_for_emi(monthly_emi: float, annual_rate_pct: float, years: int) -> float:
    """Largest principal whose EMI fits `monthly_emi`. Inverts emi(). <=0 -> 0."""
    if monthly_emi <= 0:
        return 0.0
    months = max(int(years) * 12, 1)
    if annual_rate_pct <= 0:
        return monthly_emi * months
    r = annual_rate_pct / 100 / 12
    growth = (1 + r) ** months
    return monthly_emi * (growth - 1) / (r * growth)
```

- [ ] **Step 4: Refactor `roi.py` to use it (DRY)**

In `backend/app/tools/roi.py`, replace the local `_emi` definition:

```python
def _emi(principal_inr: float, annual_rate_pct: float, years: int) -> float:
    """Monthly EMI via standard amortization. Zero/negative rate -> P / months."""
    months = max(int(years) * 12, 1)
    if annual_rate_pct <= 0:
        return principal_inr / months
    r = annual_rate_pct / 100 / 12
    growth = (1 + r) ** months
    return principal_inr * r * growth / (growth - 1)
```

with an import-and-alias (keeps `roi_mod._emi` working for `test_roi.py`). Add to the imports near the top (after `from .. import config`):

```python
from ..finance import emi as _emi
```

and delete the local `def _emi(...)` block shown above.

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && ./.venv/Scripts/python -m pytest tests/test_finance.py tests/test_roi.py tests/test_roi_tools.py -q`
Expected: PASS (finance tests + existing ROI tests still green).

- [ ] **Step 6: Commit**

```bash
git add backend/app/finance.py backend/app/tools/roi.py backend/tests/test_finance.py
git commit -m "refactor(finance): shared emi + max_principal_for_emi; ROI reuses it"
```

---

## Task 3: The eligibility engine

**Files:**
- Create: `backend/app/loan.py`
- Test: `backend/tests/test_loan.py`

**Interfaces:**
- Consumes: `finance.emi`, `finance.max_principal_for_emi` (Task 2); `config.LOAN_*` + `config.USD_PER_INR` (not needed); the policy file.
- Produces: `assess_eligibility(loan_amount_inr_lakh: float, co_applicant_income_inr_lakh_per_year: float, collateral_value_inr_lakh: float = 0.0, country: str | None = None, tenure_years: int | None = None, existing_emi_inr_per_month: float = 0.0) -> dict`.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_loan.py`:

```python
from app import loan

REQUIRED_KEYS = {
    "requested_inr_lakh", "eligible_inr_lakh", "secured",
    "collateral_value_inr_lakh", "indicative_rate_low_pct",
    "indicative_rate_high_pct", "tenure_years", "moratorium_months",
    "representative_emi_inr", "emi_to_income_pct", "eligibility_strength",
    "reasons", "shortfall_inr_lakh", "disclaimers", "policy_note",
}


def test_output_has_all_keys_and_disclaimer():
    offer = loan.assess_eligibility(40, 18, collateral_value_inr_lakh=0)
    assert REQUIRED_KEYS <= set(offer)
    assert offer["disclaimers"] and all(isinstance(d, str) for d in offer["disclaimers"])
    assert offer["reasons"]  # explainability always present


def test_low_income_serviceability_binds():
    # Tiny co-applicant income -> serviceability is the binding cap.
    offer = loan.assess_eligibility(50, 3, collateral_value_inr_lakh=0)
    assert offer["eligible_inr_lakh"] < 50
    assert offer["shortfall_inr_lakh"] > 0
    assert offer["eligibility_strength"] in {"limited", "moderate"}
    assert any("income" in (r["factor"] + r["detail"]).lower() for r in offer["reasons"])


def test_zero_income_is_limited():
    offer = loan.assess_eligibility(40, 0, collateral_value_inr_lakh=0)
    assert offer["eligibility_strength"] == "limited"
    assert offer["eligible_inr_lakh"] == 0


def test_unsecured_cap_binds_for_high_income_no_collateral():
    # Huge income removes the serviceability cap; unsecured product cap binds.
    offer = loan.assess_eligibility(200, 500, collateral_value_inr_lakh=0)
    assert offer["secured"] is False
    assert offer["eligible_inr_lakh"] == loan.POLICY["unsecured_cap_inr_lakh"]
    assert any("unsecured" in (r["factor"] + r["detail"]).lower() for r in offer["reasons"])


def test_collateral_makes_offer_secured_with_lower_rate():
    secured = loan.assess_eligibility(60, 500, collateral_value_inr_lakh=100)
    unsecured = loan.assess_eligibility(60, 500, collateral_value_inr_lakh=0)
    assert secured["secured"] is True
    assert secured["indicative_rate_low_pct"] < unsecured["indicative_rate_low_pct"]


def test_comfortable_request_is_strong_no_shortfall():
    offer = loan.assess_eligibility(20, 50, collateral_value_inr_lakh=0)
    assert offer["shortfall_inr_lakh"] == 0
    assert offer["eligibility_strength"] == "strong"


def test_country_rate_adjustment_applied():
    us = loan.assess_eligibility(30, 50, country="US")
    other = loan.assess_eligibility(30, 50, country="Germany")
    adj = loan.POLICY["country_rate_adjustment_pct"]
    expected = adj.get("default") - adj.get("US", 0.0)
    assert abs((other["indicative_rate_low_pct"] - us["indicative_rate_low_pct"]) - expected) < 1e-6
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && ./.venv/Scripts/python -m pytest tests/test_loan.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.loan'`.

- [ ] **Step 3: Write the engine**

Create `backend/app/loan.py`:

```python
"""F5 — Loan eligibility + personalized offer engine.

assess_eligibility() is the single public entry point (the ML-ready seam): all
callers go through it; the rule logic lives in _rule_engine, which a real model
could later replace without changing any caller. Indicative only — SARTHI guides,
the lender underwrites. Policy numbers come from data/loan_policy.json; behavior
tunables from config. Nothing numeric is hardcoded here.
"""

import json

from . import config
from .finance import emi, max_principal_for_emi

POLICY = json.loads(config.LOAN_POLICY_PATH.read_text(encoding="utf-8"))

DISCLAIMERS = [
    "Indicative estimate by SARTHI, not a loan sanction.",
    "Final amount, interest rate, and approval rest with the lender after "
    "verification of income, collateral, and academics.",
]


def _rate_band(secured: bool, country: str | None) -> tuple[float, float, float]:
    band = POLICY["rate_bands"]["secured" if secured else "unsecured"]
    adj_map = POLICY["country_rate_adjustment_pct"]
    adj = adj_map.get(country, adj_map["default"]) if country else adj_map["default"]
    low = band["low"] + adj
    high = band["high"] + adj
    return low, high, (low + high) / 2


def _strength(emi_to_income_pct: float, shortfall: float, income_lakh: float) -> str:
    if income_lakh <= 0 or emi_to_income_pct > config.LOAN_STRENGTH_MODERATE_EMI_PCT:
        return "limited"
    if emi_to_income_pct <= config.LOAN_STRENGTH_STRONG_EMI_PCT and shortfall == 0:
        return "strong"
    return "moderate"


def _rule_engine(
    loan_amount_inr_lakh: float,
    co_applicant_income_inr_lakh_per_year: float,
    collateral_value_inr_lakh: float,
    country: str | None,
    tenure_years: int,
    existing_emi_inr_per_month: float,
) -> dict:
    requested = max(0.0, loan_amount_inr_lakh)
    income_lakh = max(0.0, co_applicant_income_inr_lakh_per_year)
    collateral = max(0.0, collateral_value_inr_lakh)

    ltv = POLICY["secured_ltv_pct"] / 100
    covered = collateral * ltv
    secured = collateral > 0 and covered >= requested

    if secured:
        product_cap = min(covered, POLICY["secured_max_inr_lakh"])
    else:
        product_cap = POLICY["unsecured_cap_inr_lakh"]

    low, high, mid = _rate_band(secured, country)

    monthly_income = income_lakh * 100_000 / 12
    max_emi = max(0.0, POLICY["foir_pct"] / 100 * monthly_income - max(0.0, existing_emi_inr_per_month))
    serviceability_cap = max_principal_for_emi(max_emi, mid, tenure_years) / 100_000

    eligible = round(max(0.0, min(requested, product_cap, serviceability_cap)), 1)
    shortfall = round(max(0.0, requested - eligible), 1)

    rep_emi = round(emi(eligible * 100_000, mid, tenure_years))
    emi_to_income_pct = round(rep_emi / monthly_income * 100, 1) if monthly_income > 0 else 100.0

    reasons: list[dict] = []
    if income_lakh <= 0:
        reasons.append({"factor": "Co-applicant income", "impact": "blocks offer",
                        "detail": "No co-applicant income provided to service an EMI."})
    elif serviceability_cap <= product_cap and serviceability_cap < requested:
        reasons.append({"factor": "Co-applicant income", "impact": "limits amount",
                        "detail": f"EMI is capped at {POLICY['foir_pct']}% of monthly income, "
                                  f"which supports about Rs {round(serviceability_cap, 1)} lakh."})
    if not secured and product_cap <= requested and product_cap <= serviceability_cap:
        reasons.append({"factor": "Unsecured cap", "impact": "limits amount",
                        "detail": f"Without collateral, the indicative cap is "
                                  f"Rs {POLICY['unsecured_cap_inr_lakh']} lakh."})
    if secured:
        reasons.append({"factor": "Collateral", "impact": "improves terms",
                        "detail": "Collateral backs the loan, enabling a higher amount "
                                  "and a lower rate band."})
    if shortfall == 0 and eligible > 0:
        reasons.append({"factor": "Requested amount", "impact": "fits",
                        "detail": "The requested amount fits within indicative eligibility."})
    if not reasons:
        reasons.append({"factor": "Assessment", "impact": "indicative",
                        "detail": "Estimate based on income, collateral, and published norms."})

    return {
        "requested_inr_lakh": round(requested, 1),
        "eligible_inr_lakh": eligible,
        "secured": secured,
        "collateral_value_inr_lakh": round(collateral, 1),
        "indicative_rate_low_pct": round(low, 2),
        "indicative_rate_high_pct": round(high, 2),
        "tenure_years": tenure_years,
        "moratorium_months": POLICY["moratorium_months_default"],
        "representative_emi_inr": rep_emi,
        "emi_to_income_pct": emi_to_income_pct,
        "eligibility_strength": _strength(emi_to_income_pct, shortfall, income_lakh),
        "reasons": reasons,
        "shortfall_inr_lakh": shortfall,
        "disclaimers": list(DISCLAIMERS),
        "policy_note": POLICY["data_note"],
    }


def assess_eligibility(
    loan_amount_inr_lakh: float,
    co_applicant_income_inr_lakh_per_year: float,
    collateral_value_inr_lakh: float = 0.0,
    country: str | None = None,
    tenure_years: int | None = None,
    existing_emi_inr_per_month: float = 0.0,
) -> dict:
    """Indicative education-loan offer. The single seam all callers go through."""
    return _rule_engine(
        loan_amount_inr_lakh,
        co_applicant_income_inr_lakh_per_year,
        collateral_value_inr_lakh,
        country,
        tenure_years if tenure_years is not None else config.LOAN_DEFAULT_TENURE_YEARS,
        existing_emi_inr_per_month,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && ./.venv/Scripts/python -m pytest tests/test_loan.py -q`
Expected: PASS (7 tests). If `test_country_rate_adjustment_applied` fails because your policy sets US and default equal, adjust the policy so `default` differs from `US` (the spec intends a small premium for less-common destinations).

- [ ] **Step 5: Commit**

```bash
git add backend/app/loan.py backend/tests/test_loan.py
git commit -m "feat(loan): rule-based eligibility engine with reason chain"
```

---

## Task 4: The `loan_offer` agent tool

**Files:**
- Create: `backend/app/tools/loan.py`
- Modify: `backend/app/tools/__init__.py`, `backend/app/agent.py`, `backend/app/prompts.py`
- Test: `backend/tests/test_loan_tool.py`

**Interfaces:**
- Consumes: `assess_eligibility` (Task 3).
- Produces: `loan_offer` LangChain tool (callable via `.invoke({...})`, returns a JSON string).

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_loan_tool.py`:

```python
import json

from app.tools import loan_offer


def test_loan_offer_tool_returns_json_with_keys():
    out = loan_offer.invoke({
        "loan_amount_inr_lakh": 40,
        "co_applicant_income_inr_lakh_per_year": 18,
    })
    data = json.loads(out)
    assert "eligible_inr_lakh" in data
    assert "eligibility_strength" in data
    assert data["disclaimers"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && ./.venv/Scripts/python -m pytest tests/test_loan_tool.py -q`
Expected: FAIL — `ImportError: cannot import name 'loan_offer'`.

- [ ] **Step 3: Write the tool**

Create `backend/app/tools/loan.py`:

```python
"""F5 — loan offer agent tool. Thin wrapper over the eligibility engine."""

import json

from langchain_core.tools import tool

from ..loan import assess_eligibility


@tool
def loan_offer(
    loan_amount_inr_lakh: float,
    co_applicant_income_inr_lakh_per_year: float,
    collateral_value_inr_lakh: float = 0.0,
    country: str | None = None,
    tenure_years: int | None = None,
    existing_emi_inr_per_month: float = 0.0,
) -> str:
    """Estimate an INDICATIVE education-loan offer for the student.

    Call this when the student asks how much loan they can get, whether they'd
    qualify, what their EMI would be, or about loan rates. Gather the inputs
    conversationally from what you already know about them (you remember their
    target cost, family income, etc.) — don't interrogate; pass what you have and
    assume sensible defaults for the rest.

    Args:
        loan_amount_inr_lakh: Loan amount the student needs, in INR lakh.
        co_applicant_income_inr_lakh_per_year: Co-applicant (usually a parent)
            gross annual income, in INR lakh. The primary eligibility driver.
        collateral_value_inr_lakh: Value of property/FD offered as security, in
            INR lakh. Omit/0 if none (unsecured).
        country: Destination country (e.g. "US", "Canada"). Omit if unknown.
        tenure_years: Repayment tenure in years. Omit for the default.
        existing_emi_inr_per_month: Any existing monthly EMIs. Omit if none.

    Returns a JSON string: eligible amount, indicative rate band, tenure,
    representative EMI, eligibility strength (strong/moderate/limited), a reason
    chain, and disclaimers. Present it as an INDICATIVE offer with the eligibility
    strength and the top reasons — NEVER as a guaranteed approval. Always show the
    disclaimer that final terms rest with the lender.
    """
    return json.dumps(
        assess_eligibility(
            loan_amount_inr_lakh=loan_amount_inr_lakh,
            co_applicant_income_inr_lakh_per_year=co_applicant_income_inr_lakh_per_year,
            collateral_value_inr_lakh=collateral_value_inr_lakh,
            country=country,
            tenure_years=tenure_years,
            existing_emi_inr_per_month=existing_emi_inr_per_month,
        )
    )
```

- [ ] **Step 4: Register the tool**

In `backend/app/tools/__init__.py`, add the import and `__all__` entry:

```python
from .loan import loan_offer
```

and add `"loan_offer"` to the `__all__` list.

In `backend/app/agent.py`, update the tools import and the `TOOLS` list. Change:

```python
from .tools import estimate_roi, list_my_sops, review_sop, roi_breakdown, shortlist_universities

TOOLS = [shortlist_universities, estimate_roi, roi_breakdown, review_sop, list_my_sops]
```

to:

```python
from .tools import (
    estimate_roi,
    list_my_sops,
    loan_offer,
    review_sop,
    roi_breakdown,
    shortlist_universities,
)

TOOLS = [shortlist_universities, estimate_roi, roi_breakdown, review_sop, list_my_sops, loan_offer]
```

- [ ] **Step 5: Describe the tool in the system prompt**

In `backend/app/prompts.py`, inside the `YOUR TOOLS:` block, after the `review_sop / list_my_sops` bullet (before the closing `BOUNDARIES:` line), add:

```python
- loan_offer: call this when the student asks how much education loan they can \
get, whether they'd qualify, what their EMI would be, or about loan rates. Pass \
what you remember (loan amount needed, co-applicant/family income, any \
collateral, destination). Present the result as an INDICATIVE offer — the \
eligibility strength (Strong/Moderate/Limited), the indicative amount and rate \
band, the monthly EMI, and the top one or two reasons. NEVER call it a \
guaranteed approval, and always include that final terms rest with the lender.
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && ./.venv/Scripts/python -m pytest tests/test_loan_tool.py tests/test_prompt.py -q`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/tools/loan.py backend/app/tools/__init__.py backend/app/agent.py backend/app/prompts.py backend/tests/test_loan_tool.py
git commit -m "feat(loan): loan_offer agent tool, registered and prompted"
```

---

## Task 5: REST endpoint `POST /loan/offer`

**Files:**
- Modify: `backend/app/server.py`
- Test: `backend/tests/test_loan_api.py`

**Interfaces:**
- Consumes: `assess_eligibility` (Task 3); `auth.resolve_user`, `_with_cookie` (existing).
- Produces: `POST /loan/offer` returning `{"offer": <offer dict>}`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_loan_api.py`:

```python
from fastapi.testclient import TestClient

from app.server import app


def test_loan_offer_endpoint_returns_offer():
    with TestClient(app) as client:
        res = client.post(
            "/loan/offer",
            json={"loan_amount_inr_lakh": 40, "co_applicant_income_inr_lakh_per_year": 18},
        )
        assert res.status_code == 200
        offer = res.json()["offer"]
        assert "eligible_inr_lakh" in offer
        assert offer["disclaimers"]


def test_loan_offer_endpoint_defaults_collateral():
    with TestClient(app) as client:
        res = client.post(
            "/loan/offer",
            json={"loan_amount_inr_lakh": 30, "co_applicant_income_inr_lakh_per_year": 25},
        )
        assert res.status_code == 200
        assert res.json()["offer"]["secured"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && ./.venv/Scripts/python -m pytest tests/test_loan_api.py -q`
Expected: FAIL — 404 (route not defined).

- [ ] **Step 3: Add the endpoint**

In `backend/app/server.py`, add the import near the other app imports (after `from .config import settings`):

```python
from .loan import assess_eligibility
```

Add the request model near the other Pydantic models (after `SaveVersionRequest`):

```python
class LoanOfferRequest(BaseModel):
    loan_amount_inr_lakh: float
    co_applicant_income_inr_lakh_per_year: float
    collateral_value_inr_lakh: float = 0.0
    country: str | None = None
    tenure_years: int | None = None
    existing_emi_inr_per_month: float = 0.0
```

Add the route at the end of the file:

```python
# ---------------------------------------------------------------------------
# F5 — Loan eligibility + offer
# ---------------------------------------------------------------------------


@app.post("/loan/offer")
def loan_offer_endpoint(req: LoanOfferRequest, request: Request):
    user_id, is_new = auth.resolve_user(request)
    offer = assess_eligibility(**req.model_dump())
    return _with_cookie({"offer": offer}, user_id, is_new)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && ./.venv/Scripts/python -m pytest tests/test_loan_api.py -q`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/server.py backend/tests/test_loan_api.py
git commit -m "feat(loan): POST /loan/offer endpoint (cookie-scoped)"
```

---

## Task 6: Frontend `/loan` page

**Files:**
- Create: `sarthi-web/src/lib/loan.ts`, `sarthi-web/src/app/(app)/loan/page.tsx`
- Modify: `sarthi-web/src/lib/nav.ts`, `sarthi-web/src/components/AppShell.tsx`

**Interfaces:**
- Consumes: `POST /api/agent/loan/offer` → `{ offer: LoanOffer }`.
- Produces: the `/loan` route + nav entry.

- [ ] **Step 1: Add the typed client**

Create `sarthi-web/src/lib/loan.ts`:

```ts
const BASE = "/api/agent";

export type LoanInputs = {
  loan_amount_inr_lakh: number;
  co_applicant_income_inr_lakh_per_year: number;
  collateral_value_inr_lakh: number;
  country: string | null;
  tenure_years: number;
};

export type Reason = { factor: string; impact: string; detail: string };

export type LoanOffer = {
  requested_inr_lakh: number;
  eligible_inr_lakh: number;
  secured: boolean;
  collateral_value_inr_lakh: number;
  indicative_rate_low_pct: number;
  indicative_rate_high_pct: number;
  tenure_years: number;
  moratorium_months: number;
  representative_emi_inr: number;
  emi_to_income_pct: number;
  eligibility_strength: "strong" | "moderate" | "limited";
  reasons: Reason[];
  shortfall_inr_lakh: number;
  disclaimers: string[];
  policy_note: string;
};

export const getOffer = (inputs: LoanInputs) =>
  fetch(`${BASE}/loan/offer`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(inputs),
  }).then(async (res) => {
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return (await res.json()).offer as LoanOffer;
  });
```

- [ ] **Step 2: Add the nav item**

Replace `sarthi-web/src/lib/nav.ts` with:

```ts
export type NavItem = {
  href: "/chat" | "/sop" | "/loan";
  label: string;
  icon: "chat" | "doc" | "wallet";
};

export const APP_NAV: NavItem[] = [
  { href: "/chat", label: "Chat", icon: "chat" },
  { href: "/sop", label: "SOP", icon: "doc" },
  { href: "/loan", label: "Loan", icon: "wallet" },
];
```

- [ ] **Step 3: Add the icon to the shell map**

In `sarthi-web/src/components/AppShell.tsx`, change:

```tsx
import { IconChat, IconDoc } from "./icons";
```

to:

```tsx
import { IconChat, IconDoc, IconWallet } from "./icons";
```

and change:

```tsx
const ICONS = { chat: IconChat, doc: IconDoc } as const;
```

to:

```tsx
const ICONS = { chat: IconChat, doc: IconDoc, wallet: IconWallet } as const;
```

- [ ] **Step 4: Create the page**

Create `sarthi-web/src/app/(app)/loan/page.tsx`:

```tsx
"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useCallback, useEffect, useRef, useState } from "react";

import { Chakra } from "../../../components/Chakra";
import { IconWallet } from "../../../components/icons";
import { container, item } from "../../../lib/motion";
import { type LoanInputs, type LoanOffer, getOffer } from "../../../lib/loan";

const STRENGTH: Record<LoanOffer["eligibility_strength"], { label: string; cls: string }> = {
  strong: { label: "Strong", cls: "bg-saffron/15 text-saffron" },
  moderate: { label: "Moderate", cls: "bg-saffron-deep/15 text-saffron-deep" },
  limited: { label: "Limited", cls: "bg-ink-3 text-muted" },
};

const lakh = (n: number) => `₹${n.toLocaleString("en-IN")} L`;
const inr = (n: number) => `₹${n.toLocaleString("en-IN")}`;

function Field({
  label, value, onChange, min = 0, step = 1, suffix,
}: {
  label: string; value: number; onChange: (v: number) => void;
  min?: number; step?: number; suffix?: string;
}) {
  return (
    <label className="block">
      <span className="text-sm text-muted">{label}</span>
      <div className="mt-1 flex items-center gap-2 rounded-xl border border-ink-3 bg-ink-2 px-3 focus-within:border-saffron/60">
        <input
          type="number"
          value={Number.isNaN(value) ? "" : value}
          min={min}
          step={step}
          onChange={(e) => onChange(parseFloat(e.target.value))}
          className="min-w-0 flex-1 bg-transparent py-2.5 text-cream outline-none"
        />
        {suffix && <span className="shrink-0 text-xs text-muted">{suffix}</span>}
      </div>
    </label>
  );
}

function OfferCard({ offer }: { offer: LoanOffer }) {
  const s = STRENGTH[offer.eligibility_strength];
  return (
    <motion.div
      key={`${offer.eligible_inr_lakh}-${offer.tenure_years}-${offer.indicative_rate_low_pct}`}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: "spring", stiffness: 260, damping: 26 }}
      className="rounded-2xl border border-ink-3 bg-ink-2 p-5 sm:p-6"
    >
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="flex items-baseline gap-2">
            <span className="font-display text-5xl font-semibold leading-none tabular-nums">
              {lakh(offer.eligible_inr_lakh)}
            </span>
          </div>
          <p className="mt-1 text-xs text-muted">
            indicative eligibility {offer.secured ? "· secured" : "· unsecured"}
          </p>
        </div>
        <span className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-medium ${s.cls}`}>
          {s.label}
        </span>
      </div>

      <dl className="mt-5 grid grid-cols-2 gap-4 sm:grid-cols-4">
        {[
          ["Rate band", `${offer.indicative_rate_low_pct}–${offer.indicative_rate_high_pct}%`],
          ["EMI / month", inr(offer.representative_emi_inr)],
          ["Tenure", `${offer.tenure_years} yrs`],
          ["Moratorium", `${offer.moratorium_months} mo`],
        ].map(([k, v]) => (
          <div key={k}>
            <dt className="text-xs text-muted">{k}</dt>
            <dd className="mt-0.5 font-display text-lg tabular-nums">{v}</dd>
          </div>
        ))}
      </dl>

      {offer.shortfall_inr_lakh > 0 && (
        <p className="mt-4 text-sm text-saffron-deep">
          {lakh(offer.shortfall_inr_lakh)} short of the {lakh(offer.requested_inr_lakh)} requested.
        </p>
      )}

      <div className="mt-5">
        <p className="text-xs text-muted">Why this estimate</p>
        <ul className="mt-2 space-y-2">
          {offer.reasons.map((r, i) => (
            <li key={i} className="flex gap-2 text-sm">
              <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-saffron/60" />
              <span><span className="text-cream">{r.factor}</span> — <span className="text-muted">{r.detail}</span></span>
            </li>
          ))}
        </ul>
      </div>

      <p className="mt-5 border-t border-ink-3 pt-4 text-[11px] leading-relaxed text-muted">
        {offer.disclaimers.join(" ")}
      </p>
    </motion.div>
  );
}

export default function LoanWorkspace() {
  const [inputs, setInputs] = useState<LoanInputs>({
    loan_amount_inr_lakh: 40,
    co_applicant_income_inr_lakh_per_year: 12,
    collateral_value_inr_lakh: 0,
    country: "US",
    tenure_years: 10,
  });
  const [offer, setOffer] = useState<LoanOffer | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const debounce = useRef<ReturnType<typeof setTimeout>>(undefined);

  useEffect(() => {
    fetch("/api/agent/session", { credentials: "include" }).catch(() => {});
  }, []);

  const compute = useCallback(async (i: LoanInputs) => {
    setLoading(true);
    setError(null);
    try {
      setOffer(await getOffer(i));
    } catch {
      setError("Couldn't compute an offer. Is the agent running?");
    } finally {
      setLoading(false);
    }
  }, []);

  const set = (patch: Partial<LoanInputs>) => {
    const next = { ...inputs, ...patch };
    setInputs(next);
    if (offer) {
      // Live recompute once an offer exists, debounced.
      if (debounce.current) clearTimeout(debounce.current);
      debounce.current = setTimeout(() => compute(next), 300);
    }
  };

  const valid =
    inputs.loan_amount_inr_lakh > 0 && inputs.co_applicant_income_inr_lakh_per_year >= 0;

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-6 px-5 py-6">
      <motion.div variants={container} initial="hidden" animate="show">
        <motion.h1 variants={item} className="font-display text-3xl font-semibold">
          What could you qualify for?
        </motion.h1>
        <motion.p variants={item} className="mt-2 text-balance text-muted">
          An indicative education-loan estimate based on co-applicant income and collateral.
          SARTHI guides; the lender decides.
        </motion.p>
      </motion.div>

      <div className="grid gap-4 rounded-2xl border border-ink-3 bg-ink-2/40 p-5 sm:grid-cols-2">
        <Field label="Loan needed" value={inputs.loan_amount_inr_lakh} suffix="₹ lakh"
          onChange={(v) => set({ loan_amount_inr_lakh: v })} />
        <Field label="Co-applicant income / year" value={inputs.co_applicant_income_inr_lakh_per_year} suffix="₹ lakh"
          onChange={(v) => set({ co_applicant_income_inr_lakh_per_year: v })} />
        <Field label="Collateral value (0 if none)" value={inputs.collateral_value_inr_lakh} suffix="₹ lakh"
          onChange={(v) => set({ collateral_value_inr_lakh: v })} />
        <label className="block">
          <span className="text-sm text-muted">Destination</span>
          <select
            value={inputs.country ?? ""}
            onChange={(e) => set({ country: e.target.value || null })}
            className="mt-1 w-full rounded-xl border border-ink-3 bg-ink-2 px-3 py-2.5 text-cream outline-none focus:border-saffron/60"
          >
            <option value="US">US</option>
            <option value="Canada">Canada</option>
            <option value="">Other</option>
          </select>
        </label>
        <label className="block sm:col-span-2">
          <span className="flex items-center justify-between text-sm text-muted">
            <span>Tenure</span>
            <span className="tabular-nums text-cream">{inputs.tenure_years} years</span>
          </span>
          <input
            type="range" min={5} max={15} step={1} value={inputs.tenure_years}
            onChange={(e) => set({ tenure_years: parseInt(e.target.value, 10) })}
            className="mt-2 w-full accent-saffron"
          />
        </label>
      </div>

      <button
        onClick={() => compute(inputs)}
        disabled={!valid || loading}
        className="inline-flex min-h-11 items-center justify-center gap-2 self-start rounded-full bg-saffron px-5 py-2.5 text-sm font-medium text-ink transition-colors hover:bg-saffron-deep focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-saffron/70 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {loading ? <Chakra rolling size={18} /> : <IconWallet className="size-4" />}
        {offer ? "Recalculate" : "See my offer"}
      </button>

      <AnimatePresence>
        {error && (
          <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            role="alert" className="text-sm text-saffron-deep">
            {error}
          </motion.p>
        )}
      </AnimatePresence>

      {offer ? (
        <OfferCard offer={offer} />
      ) : (
        <div className="aura-saffron grid place-items-center rounded-2xl border border-dashed border-ink-3 bg-ink-2/40 p-10 text-center">
          <Chakra size={36} />
          <p className="mt-4 max-w-sm text-sm text-muted">
            Enter your details and SARTHI will show an indicative amount, rate band, and EMI —
            with the reasons behind it.
          </p>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 5: Type-check and build**

Run: `cd sarthi-web && npx tsc --noEmit`
Expected: exit 0.

Run: `cd sarthi-web && npm run build`
Expected: succeeds; route `/loan` listed.

- [ ] **Step 6: Manual verification (both servers running)**

Restart the backend (it must pick up the new tool/endpoint):
`cd backend && ./.venv/Scripts/python -m uvicorn app.server:app --port 8000`
Frontend: `cd sarthi-web && npm run dev`
- Visit `/loan`. Default inputs → "See my offer" → offer card with amount, rate band, EMI, strength badge, reason chain, disclaimer.
- Low income (e.g. 3) → eligible amount drops, strength Limited, an income reason appears.
- Set collateral above the loan amount → badge/secured flips, lower rate band.
- Move the tenure slider → EMI updates (debounced).
- In `/chat`: "How much loan can I get? I need 40 lakh, my dad earns 12 lakh a year" → agent calls `loan_offer` and presents an indicative offer with the disclaimer.

- [ ] **Step 7: Commit**

```bash
git add sarthi-web/src/lib/loan.ts sarthi-web/src/lib/nav.ts sarthi-web/src/components/AppShell.tsx "sarthi-web/src/app/(app)/loan/page.tsx"
git commit -m "feat(loan): /loan workspace page, nav entry, typed client"
```

---

## Task 7: Document F5 and verify the whole suite

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Record F5 in `CLAUDE.md`**

In `§0`, immediately before the `**Next up:**` line, add:

```markdown
- **F5 — Loan Eligibility + Personalized Offer:** done. Indicative education-loan engine (`backend/app/loan.py`, single `assess_eligibility` seam = ML-ready) over real **sourced** figures in `backend/data/loan_policy.json` (caps, LTV, FOIR, rate bands — cited, as-of dated) and shared math in new `backend/app/finance.py` (ROI now reuses it). Computes eligible amount (min of requested / product cap / serviceability cap), indicative rate band, EMI, qualitative eligibility strength (Strong/Moderate/Limited) + an explainable reason chain; engine always emits advisory `disclaimers` (RBI-aligned — SARTHI guides, lender underwrites). Two surfaces: `loan_offer` agent tool (chat offer card) + cookie-scoped `POST /loan/offer` → new `/loan` page (form + live sliders). Stateless (no DB). New pytest suites (finance/loan/tool/api). **Honesty note:** no ML model — real labeled loan-approval data isn't public, so a trained model would be fabricated; we use real *policy* data in a transparent rules engine, ML-ready for later.
```

Then update the `**Next up:**` line to point at F6:

```markdown
**Next up:** F6 — Document Auto-Fill into loan application (from past conversations).
```

- [ ] **Step 2: Run the full backend suite**

Run: `cd backend && ./.venv/Scripts/python -m pytest -q`
Expected: all pass (existing + new finance/loan/tool/api/config tests).

- [ ] **Step 3: Final frontend checks**

Run: `cd sarthi-web && npx tsc --noEmit && npm run build`
Expected: both clean.

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: record F5 loan eligibility + offer in CLAUDE.md"
```

---

## Self-Review Notes

- **Spec coverage:** engine + seam (Task 3) · real sourced policy data (Task 1) · shared math/no-dup (Task 2) · qualitative strength + reason chain + disclaimers always present (Task 3) · agent tool (Task 4) · REST endpoint (Task 5) · `/loan` page with form + live sliders + nav (Task 6) · compliance framing baked into engine output (Task 3, surfaced Tasks 4/6) · tests for finance/engine/tool/api (Tasks 2–5) · docs + honesty note (Task 7). The import-cycle risk (loan ↔ tools) is pre-empted by `finance.py` (Task 2).
- **Type consistency:** `assess_eligibility(...)` signature identical across engine (T3), tool (T4), endpoint (T5); offer dict keys match `LoanOffer` TS type (T6) and `REQUIRED_KEYS` test (T3); `eligibility_strength` values `strong|moderate|limited` consistent backend↔frontend; nav `icon: "wallet"` matches the `ICONS` map entry (T6).
- **No placeholders:** every code step shows complete code; the only research step (T1) ships concrete starting values plus an explicit instruction to verify and cite real sources.
