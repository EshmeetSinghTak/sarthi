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
    total_cost_inr_lakh = round(_usd_to_inr_lakh((uni["tuition_usd"] + living) * years), 1)
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
        "total_cost_inr_lakh": total_cost_inr_lakh,
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
