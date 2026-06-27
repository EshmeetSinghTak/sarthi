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
