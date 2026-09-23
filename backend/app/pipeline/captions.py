"""Build big, punchy word-by-word captions as an ASS subtitle file for libass."""

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Word:
    text: str
    start: float
    end: float


MAX_WORDS_PER_CAPTION = 3
# Captions longer than this get their own chunk, so they stay on one line.
MAX_CHARS_PER_CAPTION = 18
FONT_NAME = "Anton"
FALLBACK_FONT = "Liberation Sans"

# Pop-in: start at 70% size and grow to 100% over 90ms.
POP = r"{\fscx70\fscy70\t(0,90,\fscx100\fscy100)}"


def chunk_words(words: list[Word]) -> list[Word]:
    """Group words into 1-3 word captions, breaking after punctuation."""
    chunks: list[Word] = []
    current: list[Word] = []
    for word in words:
        if current:
            joined = " ".join(w.text for w in current + [word])
            if len(current) >= MAX_WORDS_PER_CAPTION or len(joined) > MAX_CHARS_PER_CAPTION:
                chunks.append(_merge(current))
                current = []
        current.append(word)
        if re.search(r"[.!?,;:]$", word.text):
            chunks.append(_merge(current))
            current = []
    if current:
        chunks.append(_merge(current))

    # Hold each caption until the next one starts, so the screen never goes blank mid-sentence.
    for this, nxt in zip(chunks, chunks[1:]):
        if nxt.start - this.end < 0.6:
            this.end = nxt.start
    return chunks


def _merge(words: list[Word]) -> Word:
    return Word(" ".join(w.text for w in words), words[0].start, words[-1].end)


def build_ass(words: list[Word], font: str = FONT_NAME) -> str:
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,{font},165,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,2,0,1,12,5,5,60,60,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [
        f"Dialogue: 0,{_ts(c.start)},{_ts(c.end)},Caption,,0,0,0,,{POP}{_escape(c.text.upper())}"
        for c in chunk_words(words)
        if c.end > c.start
    ]
    return header + "\n".join(lines) + "\n"


def write_ass(words: list[Word], path: Path, font: str = FONT_NAME) -> None:
    path.write_text(build_ass(words, font), encoding="utf-8")


def _ts(seconds: float) -> str:
    """ASS timestamps are H:MM:SS.cc (centiseconds)."""
    cs = max(0, round(seconds * 100))
    h, cs = divmod(cs, 360_000)
    m, cs = divmod(cs, 6_000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _escape(text: str) -> str:
    # Braces start override blocks and backslashes start escapes in ASS.
    return text.replace("\\", "").replace("{", "(").replace("}", ")")
