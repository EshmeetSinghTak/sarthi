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
