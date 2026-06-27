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
