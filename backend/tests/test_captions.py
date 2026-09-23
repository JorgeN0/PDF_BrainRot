from app.pipeline.captions import Word, _ts, build_ass, chunk_words


def words(*items):
    return [Word(t, s, e) for t, s, e in items]


def test_groups_at_most_three_words():
    chunks = chunk_words(
        words(("a", 0, 0.1), ("b", 0.1, 0.2), ("c", 0.2, 0.3), ("d", 0.3, 0.4))
    )
    assert [c.text for c in chunks] == ["a b c", "d"]


def test_breaks_after_punctuation():
    chunks = chunk_words(words(("bro,", 0, 0.3), ("listen", 0.3, 0.6), ("up.", 0.6, 0.9)))
    assert [c.text for c in chunks] == ["bro,", "listen up."]


def test_long_words_get_their_own_caption():
    chunks = chunk_words(words(("photosynthesis", 0, 0.5), ("literally", 0.5, 0.9)))
    assert [c.text for c in chunks] == ["photosynthesis", "literally"]


def test_caption_holds_until_next_one_starts():
    chunks = chunk_words(words(("hi.", 0, 0.3), ("yo.", 0.5, 0.8)))
    assert chunks[0].end == 0.5
    # A long pause is left as a gap.
    chunks = chunk_words(words(("hi.", 0, 0.3), ("yo.", 2.0, 2.3)))
    assert chunks[0].end == 0.3


def test_ass_output_is_uppercase_and_escaped():
    ass = build_ass(words(("{evil}\\n", 0, 0.5), ("ok", 0.5, 1.0)))
    dialogue = [line for line in ass.splitlines() if line.startswith("Dialogue:")]
    assert len(dialogue) == 1
    text = dialogue[0].split(",,", 1)[1]
    assert "(EVIL)N OK" in text
    assert "{evil}" not in text.lower()
    assert "PlayResX: 1080" in ass


def test_timestamp_format():
    assert _ts(0) == "0:00:00.00"
    assert _ts(61.234) == "0:01:01.23"
    assert _ts(3725.5) == "1:02:05.50"
