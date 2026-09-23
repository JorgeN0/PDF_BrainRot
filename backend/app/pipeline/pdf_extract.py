"""Pull readable text out of a PDF."""

import re
from pathlib import Path

import pymupdf


class PdfError(Exception):
    pass


def extract_text(pdf_path: Path) -> str:
    try:
        doc = pymupdf.open(pdf_path)
    except Exception as exc:
        raise PdfError(f"Could not open PDF: {exc}") from exc

    with doc:
        if doc.needs_pass:
            raise PdfError("This PDF is password protected.")
        pages = [page.get_text("text") for page in doc]

    text = clean_text("\n".join(pages))
    if len(text) < 40:
        raise PdfError(
            "No selectable text found. This looks like a scanned PDF, and OCR isn't supported yet."
        )
    return text


def clean_text(text: str) -> str:
    # Re-join words hyphenated across line breaks: "impor-\ntant" -> "important".
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    # Single newlines inside a paragraph become spaces; blank lines stay paragraph breaks.
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)
    text = re.sub(r"[ \t ]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()
