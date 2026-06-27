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
