from app.router import Tier, choose_tier, is_weak_reply


def test_trivial_greeting_is_light():
    assert choose_tier("hi") is Tier.LIGHT
    assert choose_tier("thanks!") is Tier.LIGHT
    assert choose_tier("ok cool") is Tier.LIGHT


def test_greeting_with_question_is_not_light():
    # A question is never trivial — fall back to the safe default.
    assert choose_tier("hello, which university?") is Tier.MID


def test_comparative_keywords_are_reasoning():
    assert choose_tier("US vs Canada for robotics?") is Tier.REASONING
    assert choose_tier("should I do an MS or an MBA") is Tier.REASONING
    assert choose_tier("compare CMU and MIT for me") is Tier.REASONING


def test_long_message_is_reasoning():
    long_msg = " ".join(["word"] * 45)
    assert choose_tier(long_msg) is Tier.REASONING


def test_deep_tool_forces_reasoning_regardless_of_text():
    assert choose_tier("hi", just_ran_deep_tool=True) is Tier.REASONING


def test_ordinary_turn_is_mid_safe_default():
    # The central misroute defense: uncertain -> MID, never light.
    assert choose_tier("what's the deadline for fall intake") is Tier.MID
    assert choose_tier("tell me about the GRE") is Tier.MID
    assert choose_tier("") is Tier.MID


def test_is_weak_reply():
    assert is_weak_reply("") is True
    assert is_weak_reply("   ") is True
    assert is_weak_reply("ok") is True  # below min chars
    assert is_weak_reply("I can't help with that.") is True  # refusal
    assert is_weak_reply("Here is a detailed, useful answer for you.") is False
