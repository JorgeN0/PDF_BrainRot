"""Offline narration with Kokoro, plus per-word timings for the captions."""

import re
import threading
from pathlib import Path

import numpy as np
import soundfile as sf

from app.config import settings
from app.pipeline.captions import Word

SAMPLE_RATE = 24_000

# Curated English voices. The first letter of the id picks the accent: a = American, b = British.
VOICES = [
    {"id": "am_michael", "name": "Michael (US male)"},
    {"id": "af_heart", "name": "Heart (US female)"},
    {"id": "am_adam", "name": "Adam (US male)"},
    {"id": "am_puck", "name": "Puck (US male, playful)"},
    {"id": "am_fenrir", "name": "Fenrir (US male, deep)"},
    {"id": "af_bella", "name": "Bella (US female)"},
    {"id": "af_nicole", "name": "Nicole (US female, soft)"},
    {"id": "bm_george", "name": "George (UK male)"},
    {"id": "bf_emma", "name": "Emma (UK female)"},
]
VOICE_IDS = {v["id"] for v in VOICES}
DEFAULT_VOICE = VOICES[0]["id"]

_lock = threading.Lock()
_model = None
_pipelines: dict = {}


def _pipeline(lang_code: str):
    """Load the Kokoro model once and share it between accent pipelines."""
    global _model
    from kokoro import KModel, KPipeline  # heavy import, only when needed

    with _lock:
        if _model is None:
            import torch

            device = settings.kokoro_device
            if device == "auto":
                device = "cuda" if torch.cuda.is_available() else "cpu"
            _model = KModel(repo_id="hexgrad/Kokoro-82M").to(device).eval()
        if lang_code not in _pipelines:
            _pipelines[lang_code] = KPipeline(
                lang_code=lang_code, repo_id="hexgrad/Kokoro-82M", model=_model
            )
        return _pipelines[lang_code]


def synthesize(text: str, voice: str, out_path: Path) -> tuple[list[Word], float]:
    """Speak `text`, write a WAV to out_path, and return (word timings, duration in seconds)."""
    if voice not in VOICE_IDS:
        raise ValueError(f"Unknown voice: {voice}")
    pipeline = _pipeline(voice[0])

    audio_parts: list[np.ndarray] = []
    words: list[Word] = []
    offset = 0.0
    for result in pipeline(text, voice=voice, speed=settings.kokoro_speed):
        if result.audio is None:
            continue
        audio = result.audio.detach().cpu().numpy().astype(np.float32)
        duration = len(audio) / SAMPLE_RATE
        chunk_words = words_from_tokens(result.tokens or [], offset)
        if not chunk_words:
            chunk_words = estimate_word_times(result.graphemes, offset, offset + duration)
        words.extend(chunk_words)
        audio_parts.append(audio)
        offset += duration

    if not audio_parts:
        raise RuntimeError("Kokoro produced no audio.")
    sf.write(out_path, np.concatenate(audio_parts), SAMPLE_RATE)
    return words, offset


def words_from_tokens(tokens, offset: float) -> list[Word]:
    """Merge Kokoro tokens into caption words.

    Punctuation arrives as separate tokens with no timestamps, so glue it onto the
    previous word. A token followed by whitespace ends a word. Returns [] if any real
    word is missing timings, so the caller falls back to estimates.
    """
    # Group tokens into whitespace-separated words: (text, start, end).
    groups: list[tuple[str, float | None, float | None]] = []
    text, start, end = "", None, None
    for tok in tokens:
        text += tok.text
        if start is None and tok.start_ts is not None:
            start = tok.start_ts
        if tok.end_ts is not None:
            end = tok.end_ts
        if tok.whitespace:
            groups.append((text, start, end))
            text, start, end = "", None, None
    groups.append((text, start, end))

    words: list[Word] = []
    for text, start, end in groups:
        text = text.strip()
        if not text:
            continue
        if start is None or end is None:
            if not re.search(r"\w", text):
                if words:
                    words[-1].text += text  # stray punctuation
                continue
            return []
        words.append(Word(text, offset + start, offset + end))
    return words


def estimate_word_times(text: str, start: float, end: float) -> list[Word]:
    """Fallback: spread words across the chunk in proportion to their length."""
    tokens = text.split()
    if not tokens:
        return []
    weights = [len(t) + 1 for t in tokens]
    total = sum(weights)
    words, t = [], start
    for token, weight in zip(tokens, weights):
        span = (end - start) * weight / total
        words.append(Word(token, t, t + span))
        t += span
    return words
