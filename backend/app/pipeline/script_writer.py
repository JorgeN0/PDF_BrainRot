"""Turn document text into a brainrot narration script using a local Ollama model."""

import json
import re
from typing import Callable

import httpx

from app.config import settings

# Measured Kokoro pace at speed 1.1 (pauses between sentences included).
WORDS_PER_SECOND = 2.4
# Above this, the text is condensed into notes first so it fits the model's context.
MAX_DIRECT_CHARS = 20_000
CHUNK_CHARS = 6_000
NUM_CTX = 8192

SCRIPT_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "script": {"type": "string"},
    },
    "required": ["title", "script"],
}

SYSTEM_PROMPT = """You write narration scripts for viral "brainrot" short-form videos \
(TikTok, Reels, Shorts) that explain a document while Minecraft parkour or Subway Surfers \
gameplay plays in the background.

Rules:
- The first sentence is a scroll-stopping hook written fresh for this topic (a "POV:" \
line, a wild claim, a direct callout of the viewer). Never reuse a generic opener.
- Stay under the word limit. The video is timed, and every extra word gets cut.
- Short, punchy sentences. Talk like a chronically online Gen-Z narrator: slang like \
"no cap", "lowkey", "bro", "fr", "it's giving", "cooked", "W", "L", "aura", used naturally, \
never so much that it hides the meaning.
- Explain the document's actual key ideas, facts and numbers correctly. Never invent facts.
- Output only the words the narrator says out loud: no emojis, hashtags, markdown, bullet \
points, stage directions, sound effects, or URLs. Write symbols and units as words \
("percent", "and", "cubic kilometers").
- End with a punchy one-line closer.
- The title is a short clickbait title, at most 8 words."""

NOTES_PROMPT = """Summarize this part of a document as compact bullet notes. Keep every key \
idea, definition, name, number and conclusion. No intro, no outro, just the notes."""


class ScriptError(Exception):
    pass


class ModelOutputError(ScriptError):
    """The model produced unusable output. Worth retrying, unlike a missing model."""


ProgressFn = Callable[[str], None]

ATTEMPTS = 3


def target_words(length_seconds: int) -> int:
    return round(length_seconds * WORDS_PER_SECOND)


def write_script(text: str, length_seconds: int, on_progress: ProgressFn | None = None) -> dict:
    """Return {"title": ..., "script": ...} for the given document text."""
    notes = condense(text, on_progress)
    words = target_words(length_seconds)
    user_prompt = (
        f"Write a script of {round(words * 0.85)} to {words} words (it has to fill about "
        f"{length_seconds} seconds of speech, no more) about this document. Reply with JSON: "
        f'{{"title": "...", "script": "..."}}\n\nDocument:\n"""\n{notes}\n"""'
    )
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
    if on_progress:
        on_progress("Writing the script")

    # Schema-constrained decoding occasionally makes small models loop until Ollama aborts
    # ("token repeat limit reached"), so retry, and drop the schema on the last try.
    for attempt in range(1, ATTEMPTS + 1):
        try:
            raw = _chat(
                messages,
                schema=SCRIPT_SCHEMA if attempt < ATTEMPTS else None,
                # Unload right away so the TTS model gets the GPU memory.
                keep_alive=0,
            )
            data = _parse_json(raw)
            break
        except ModelOutputError:
            if attempt == ATTEMPTS:
                raise

    script = fit_length(clean_script(str(data.get("script", ""))), words)
    title = clean_script(str(data.get("title", ""))) or "Your PDF, but brainrot"
    if len(script.split()) < 10:
        raise ScriptError("The model returned an empty script. Try again or use a different model.")
    return {"title": title, "script": script}


def condense(text: str, on_progress: ProgressFn | None = None) -> str:
    """Summarize long text chunk by chunk until it fits the model's context."""
    while len(text) > MAX_DIRECT_CHARS:
        chunks = split_chunks(text, CHUNK_CHARS)
        notes = []
        for i, chunk in enumerate(chunks, 1):
            if on_progress:
                on_progress(f"Reading the PDF ({i}/{len(chunks)})")
            notes.append(
                _chat(
                    [
                        {"role": "system", "content": NOTES_PROMPT},
                        {"role": "user", "content": chunk},
                    ]
                )
            )
        text = "\n\n".join(notes)
    return text


def split_chunks(text: str, max_chars: int) -> list[str]:
    """Split on paragraph boundaries into chunks of at most max_chars (hard-cut if needed)."""
    chunks: list[str] = []
    current = ""
    for para in text.split("\n\n"):
        while len(para) > max_chars:
            if current:
                chunks.append(current)
                current = ""
            chunks.append(para[:max_chars])
            para = para[max_chars:]
        if current and len(current) + len(para) + 2 > max_chars:
            chunks.append(current)
            current = para
        else:
            current = f"{current}\n\n{para}" if current else para
    if current:
        chunks.append(current)
    return chunks


_URL = re.compile(r"https?://\S+|www\.\S+")
_BRACKETED = re.compile(r"\[[^\]]*\]")
_HASHTAG = re.compile(r"(?<!\w)#\w+")
_MARKDOWN = re.compile(r"[*_`#>~|]")
# Emoji, pictographs, dingbats, flags, variation selectors, zero-width joiners.
_EMOJI = re.compile(
    "[\U0001f000-\U0001faff\U00002600-\U000027bf\U0001f1e6-\U0001f1ff\ufe0f\u200d\u2b50\u2b55]"
)


def clean_script(text: str) -> str:
    """Strip everything that would sound wrong when read aloud."""
    text = _URL.sub("", text)
    text = _BRACKETED.sub("", text)
    text = _HASHTAG.sub("", text)
    text = _EMOJI.sub("", text)
    text = _MARKDOWN.sub("", text)
    text = re.sub(r"^\s*[-•]\s+", "", text, flags=re.MULTILINE)
    text = text.replace("&", " and ").replace("%", " percent")
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([,.!?;:])", r"\1", text)
    return text.strip()


def fit_length(script: str, target: int) -> str:
    """If the model overshot, cut at a sentence boundary near the target length.

    Local models routinely overshoot word counts, and a "30s" video that runs 45s
    defeats the length picker.
    """
    words = script.split()
    if len(words) <= target * 1.2:
        return script
    limit = round(target * 1.1)
    sentences = re.split(r"(?<=[.!?])\s+", script)
    kept: list[str] = []
    count = 0
    for sentence in sentences:
        n = len(sentence.split())
        if kept and count + n > limit:
            break
        kept.append(sentence)
        count += n
    return " ".join(kept)


def _chat(messages: list[dict], schema: dict | None = None, keep_alive: int | str = "5m") -> str:
    payload: dict = {
        "model": settings.ollama_model,
        "messages": messages,
        "stream": False,
        "keep_alive": keep_alive,
        "options": {"num_ctx": NUM_CTX, "temperature": 0.8},
    }
    if schema:
        payload["format"] = schema
    try:
        resp = httpx.post(f"{settings.ollama_url}/api/chat", json=payload, timeout=600)
    except httpx.HTTPError as exc:
        raise ScriptError(f"Couldn't reach Ollama at {settings.ollama_url}. Is it running?") from exc
    if resp.status_code == 404:
        raise ScriptError(
            f"Ollama model '{settings.ollama_model}' isn't installed. "
            f"Run: ollama pull {settings.ollama_model}"
        )
    if resp.status_code >= 500:
        raise ModelOutputError(f"Ollama error {resp.status_code}: {resp.text[:300]}")
    if resp.status_code >= 400:
        raise ScriptError(f"Ollama error {resp.status_code}: {resp.text[:300]}")
    return resp.json()["message"]["content"]


def _parse_json(raw: str) -> dict:
    """Parse the model's JSON reply, tolerating chatter around the object."""
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    try:
        data = json.loads(match.group(0) if match else raw)
    except json.JSONDecodeError as exc:
        raise ModelOutputError(f"The model returned invalid JSON: {raw[:200]}") from exc
    if not isinstance(data, dict):
        raise ModelOutputError(f"The model returned unexpected JSON: {raw[:200]}")
    return data


def check_ollama() -> tuple[bool, str]:
    """Health check: is Ollama up and is the configured model pulled?"""
    try:
        resp = httpx.get(f"{settings.ollama_url}/api/tags", timeout=3)
        resp.raise_for_status()
    except httpx.HTTPError:
        return False, f"Ollama isn't reachable at {settings.ollama_url}. Start it with: ollama serve"
    names = {m.get("name", "") for m in resp.json().get("models", [])}
    model = settings.ollama_model
    if model in names or f"{model}:latest" in names:
        return True, f"Ollama is ready with {model}"
    return False, f"Model '{model}' isn't installed. Run: ollama pull {model}"
