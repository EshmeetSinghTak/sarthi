from app.tools.sop import analyze_sop


def test_empty_string_is_safe():
    out = analyze_sop("")
    assert out["word_count"] == 0
    assert out["paragraph_count"] == 0
    assert out["length_flag"] == "short"
    assert out["cliche_hits"] == []
    assert out["long_sentences"] == []


def test_length_flag_bands():
    assert analyze_sop("word " * 500)["length_flag"] == "short"
    assert analyze_sop("word " * 800)["length_flag"] == "ok"
    assert analyze_sop("word " * 1200)["length_flag"] == "long"


def test_word_and_paragraph_counts():
    out = analyze_sop("one two three\n\nfour five")
    assert out["word_count"] == 5
    assert out["paragraph_count"] == 2


def test_cliche_detection_case_insensitive_and_counts():
    out = analyze_sop("Since Childhood I loved robots. Since childhood, again.")
    hits = {h["phrase"]: h["count"] for h in out["cliche_hits"]}
    assert hits.get("since childhood") == 2


def test_long_sentence_flagged():
    long_one = "I " + "really " * 45 + "want this."
    assert len(analyze_sop(long_one)["long_sentences"]) == 1
    assert analyze_sop("I want this. It is short.")["long_sentences"] == []


def test_structure_signals():
    text = "I want to join this Master's program because my goal is a research career."
    sig = analyze_sop(text)["structure_signals"]
    assert sig["mentions_program"] and sig["mentions_goal"] and sig["gives_reasons"]
    assert not any(analyze_sop("Hello there.")["structure_signals"].values())
