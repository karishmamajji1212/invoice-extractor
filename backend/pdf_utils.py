"""PDF text extraction utilities."""
from __future__ import annotations

import io

from pypdf import PdfReader


def extract_text_from_pdf(data: bytes) -> str:
    """Extract all text from a PDF byte stream. Raises ValueError if no text found."""
    reader = PdfReader(io.BytesIO(data), strict=False)
    pages: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        pages.append(text)
    full = "\n".join(pages).strip()
    if not full:
        raise ValueError(
            "No extractable text found in PDF. This may be a scanned image; OCR is not supported."
        )
    return full


def extract_text(data: bytes, filename: str) -> str:
    """Dispatch text extraction based on file extension."""
    name = filename.lower()
    if name.endswith(".pdf"):
        return extract_text_from_pdf(data)
    if name.endswith(".txt"):
        return data.decode("utf-8", errors="replace").strip()
    raise ValueError(f"Unsupported file type: {filename}. Supported: PDF, TXT.")
