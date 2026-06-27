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
