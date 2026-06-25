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
