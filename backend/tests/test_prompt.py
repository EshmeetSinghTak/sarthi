from app.prompts import SYSTEM_PROMPT


def test_prompt_mentions_roi_tools():
    assert "estimate_roi" in SYSTEM_PROMPT
    assert "roi_breakdown" in SYSTEM_PROMPT


def test_prompt_mentions_sop_tools():
    assert "review_sop" in SYSTEM_PROMPT
    assert "list_my_sops" in SYSTEM_PROMPT


def test_prompt_has_never_write_rule():
    assert "NEVER write or rewrite" in SYSTEM_PROMPT
