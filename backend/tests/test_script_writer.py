import json

import pytest

from app.pipeline import script_writer
from app.pipeline.script_writer import (
    ModelOutputError,
    ScriptError,
    clean_script,
    fit_length,
    split_chunks,
    target_words,
    write_script,
)


def test_clean_script_strips_unspeakable_stuff():
    raw = "**Bro** 💀 check https://x.com [upbeat music] #StudyTok\n- 50% & rising"
    assert clean_script(raw) == "Bro check 50 percent and rising"


def test_fit_length_leaves_reasonable_scripts_alone():
    script = "One two three. Four five six."
    assert fit_length(script, 6) == script


def test_fit_length_cuts_at_sentence_boundary():
    script = " ".join(["This is five words."] * 20)  # 80 words
    cut = fit_length(script, 20)
    assert cut.endswith(".")
    assert len(cut.split()) <= 26


def test_split_chunks_respects_limit():
    text = "\n\n".join(["x" * 400] * 10) + "\n\n" + "y" * 2500
    chunks = split_chunks(text, 1000)
    assert all(len(c) <= 1000 for c in chunks)
    assert "".join(chunks).replace("\n", "") == text.replace("\n", "")


def test_target_words_scales_with_length():
    assert target_words(30) < target_words(60) < target_words(180)


def test_write_script_parses_model_json(monkeypatch):
    calls = []

    def fake_chat(messages, schema=None, keep_alive="5m"):
        calls.append((messages, schema, keep_alive))
        return json.dumps(
            {"title": "Mitochondria 💀", "script": "Bro. " + "The mitochondria is the powerhouse. " * 5}
        )

    monkeypatch.setattr(script_writer, "_chat", fake_chat)
    result = write_script("Some document text about cells.", 30)
    assert result["title"] == "Mitochondria"
    assert result["script"].startswith("Bro.")
    assert len(calls) == 1
    _, schema, keep_alive = calls[0]
    assert schema == script_writer.SCRIPT_SCHEMA
    assert keep_alive == 0


def test_long_documents_are_condensed_first(monkeypatch):
    calls = []

    def fake_chat(messages, schema=None, keep_alive="5m"):
        calls.append(schema)
        if schema is None:
            return "- a note"
        return json.dumps({"title": "T", "script": "word " * 40})

    monkeypatch.setattr(script_writer, "_chat", fake_chat)
    long_text = "\n\n".join(["lorem ipsum " * 400] * 10)  # ~48k chars
    write_script(long_text, 60)
    notes_calls = [c for c in calls if c is None]
    assert len(notes_calls) >= 2
    assert calls[-1] == script_writer.SCRIPT_SCHEMA


def test_retries_bad_output_and_drops_schema_last(monkeypatch):
    schemas = []
    good = json.dumps({"title": "T", "script": "word " * 40})

    def flaky_chat(messages, schema=None, keep_alive="5m"):
        schemas.append(schema)
        if len(schemas) == 1:
            raise ModelOutputError("Ollama error 500: token repeat limit reached")
        if len(schemas) == 2:
            return "not json at all"
        return f"Sure! Here you go:\n{good}\nHope that helps"

    monkeypatch.setattr(script_writer, "_chat", flaky_chat)
    assert write_script("doc", 30)["title"] == "T"
    assert schemas == [script_writer.SCRIPT_SCHEMA, script_writer.SCRIPT_SCHEMA, None]


def test_config_errors_are_not_retried(monkeypatch):
    calls = []

    def missing_model(*args, **kwargs):
        calls.append(1)
        raise ScriptError("model isn't installed")

    monkeypatch.setattr(script_writer, "_chat", missing_model)
    with pytest.raises(ScriptError, match="isn't installed"):
        write_script("doc", 30)
    assert len(calls) == 1


def test_empty_script_is_an_error(monkeypatch):
    monkeypatch.setattr(
        script_writer, "_chat", lambda *a, **k: json.dumps({"title": "x", "script": "🔥🔥"})
    )
    with pytest.raises(ScriptError):
        write_script("doc", 30)
