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


def test_tier_models_present():
    assert config.settings.model_light == "meta/llama-3.1-8b-instruct"
    assert config.settings.model_mid  # defaults to the standard chat model
    assert config.settings.model_reasoning == "nvidia/llama-3.3-nemotron-super-49b-v1.5"
    assert config.settings.reasoning_max_tokens >= 2048


def test_router_tunables_present():
    assert config.ROUTER_TRIVIAL_MAX_WORDS > 0
    assert isinstance(config.ROUTER_TRIVIAL_PATTERNS, tuple) and config.ROUTER_TRIVIAL_PATTERNS
    assert config.ROUTER_COMPLEX_MIN_WORDS > config.ROUTER_TRIVIAL_MAX_WORDS
    assert "vs" in config.ROUTER_COMPLEX_KEYWORDS
    assert "review_sop" in config.ROUTER_DEEP_TOOLS
    assert config.ROUTER_WEAK_REPLY_MIN_CHARS > 0
    assert any("can't" in p or "cannot" in p for p in config.ROUTER_REFUSAL_PATTERNS)


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
