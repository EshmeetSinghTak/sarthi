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
