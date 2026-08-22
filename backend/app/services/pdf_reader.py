"""Reads PDFs. Returns text, or an image if the PDF is a scan."""
import base64

import fitz  # PyMuPDF
import pdfplumber


def extract_text(file_path: str) -> tuple[str, bool]:
    """
    Returns (text, was_scanned).

    A digital PDF has a text layer we can read directly.
    A scanned PDF is just a photo - almost no text comes out,
    so we fall back to sending an image to the AI instead.
    """
    parts = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            parts.append(page.extract_text() or "")

    text = "\n".join(parts).strip()
    was_scanned = len(text) < 50   # under 50 chars = no real text layer

    return text, was_scanned


def page_to_base64(file_path: str, page_num: int = 0) -> str:
    """Converts a PDF page into a PNG image, encoded for sending to the AI."""
    doc = fitz.open(file_path)
    page = doc[page_num]
    pix = page.get_pixmap(dpi=200)   # 200 dpi is readable without being huge
    doc.close()
    return base64.standard_b64encode(pix.tobytes("png")).decode()