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
    max_emi = max(
        0.0, POLICY["foir_pct"] / 100 * monthly_income - max(0.0, existing_emi_inr_per_month)
    )
    serviceability_cap = max_principal_for_emi(max_emi, mid, tenure_years) / 100_000

    eligible = round(max(0.0, min(requested, product_cap, serviceability_cap)), 1)
    shortfall = round(max(0.0, requested - eligible), 1)

    rep_emi = round(emi(eligible * 100_000, mid, tenure_years))
    emi_to_income_pct = round(rep_emi / monthly_income * 100, 1) if monthly_income > 0 else 100.0

    reasons: list[dict] = []
    if income_lakh <= 0:
        reasons.append({
            "factor": "Co-applicant income",
            "impact": "blocks offer",
            "detail": "No co-applicant income provided to service an EMI.",
        })
    elif serviceability_cap <= product_cap and serviceability_cap < requested:
        reasons.append({
            "factor": "Co-applicant income",
            "impact": "limits amount",
            "detail": f"EMI is capped at {POLICY['foir_pct']}% of monthly income, "
                      f"which supports about Rs {round(serviceability_cap, 1)} lakh.",
        })
    if not secured and product_cap <= requested and product_cap <= serviceability_cap:
        reasons.append({
            "factor": "Unsecured cap",
            "impact": "limits amount",
            "detail": f"Without collateral, the indicative cap is "
                      f"Rs {POLICY['unsecured_cap_inr_lakh']} lakh.",
        })
    if secured:
        reasons.append({
            "factor": "Collateral",
            "impact": "improves terms",
            "detail": "Collateral backs the loan, enabling a higher amount and a lower rate band.",
        })
    if shortfall == 0 and eligible > 0:
        reasons.append({
            "factor": "Requested amount",
            "impact": "fits",
            "detail": "The requested amount fits within indicative eligibility.",
        })
    if not reasons:
        reasons.append({
            "factor": "Assessment",
            "impact": "indicative",
            "detail": "Estimate based on income, collateral, and published norms.",
        })

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
