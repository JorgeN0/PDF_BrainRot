import pymupdf
import pytest

from app.pipeline.pdf_extract import PdfError, clean_text, extract_text


def make_pdf(path, text):
    doc = pymupdf.open()
    page = doc.new_page()
    if text:
        page.insert_textbox(pymupdf.Rect(50, 50, 550, 800), text, fontsize=11)
    doc.save(path)
    doc.close()
    return path


def test_extracts_text(tmp_path):
    pdf = make_pdf(
        tmp_path / "a.pdf",
        "Photosynthesis turns sunlight into chemical energy.\nPlants are goated at it.",
    )
    text = extract_text(pdf)
    assert "Photosynthesis turns sunlight" in text
    assert "goated" in text


def test_scanned_or_empty_pdf_is_rejected(tmp_path):
    with pytest.raises(PdfError, match="No selectable text"):
        extract_text(make_pdf(tmp_path / "empty.pdf", ""))


def test_garbage_file_is_rejected(tmp_path):
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"not a pdf at all")
    with pytest.raises(PdfError):
        extract_text(bad)


def test_clean_text_rejoins_lines_and_hyphens():
    assert clean_text("impor-\ntant stuff\nhere\n\n\n\nnext") == "important stuff here\n\nnext"
