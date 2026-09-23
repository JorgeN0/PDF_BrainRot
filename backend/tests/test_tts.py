from types import SimpleNamespace

from app.pipeline.tts import estimate_word_times, words_from_tokens


def tok(text, start=None, end=None, ws=" "):
    return SimpleNamespace(text=text, start_ts=start, end_ts=end, whitespace=ws)


def test_tokens_merge_punctuation_and_apply_offset():
    tokens = [
        tok("Bro", 0.0, 0.3, ""),
        tok(",", ws=" "),
        tok("listen", 0.4, 0.8, ""),
        tok("!", ws=""),
    ]
    words = words_from_tokens(tokens, offset=10.0)
    assert [(w.text, w.start, w.end) for w in words] == [
        ("Bro,", 10.0, 10.3),
        ("listen!", 10.4, 10.8),
    ]


def test_missing_timestamps_trigger_fallback():
    assert words_from_tokens([tok("hello"), tok("world")], 0) == []


def test_estimate_spreads_words_over_the_whole_chunk():
    words = estimate_word_times("a bb ccc", 1.0, 3.0)
    assert [w.text for w in words] == ["a", "bb", "ccc"]
    assert words[0].start == 1.0
    assert abs(words[-1].end - 3.0) < 1e-9
    durations = [w.end - w.start for w in words]
    assert durations[0] < durations[1] < durations[2]
