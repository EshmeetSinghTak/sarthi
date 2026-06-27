from app import llm
from app.config import settings


def test_three_tier_instances_have_correct_models():
    assert llm.llm_light.model_name == settings.model_light
    assert llm.llm_mid.model_name == settings.model_mid
    assert llm.llm_reasoning.model_name == settings.model_reasoning


def test_reasoning_has_larger_token_budget_than_light():
    assert llm.llm_reasoning.max_tokens > llm.llm_light.max_tokens


def test_distill_facts_still_exported():
    assert callable(llm.distill_facts)
