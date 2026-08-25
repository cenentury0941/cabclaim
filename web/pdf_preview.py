"""Render PDF pages for the web UI."""

from __future__ import annotations

from pathlib import Path

import pymupdf


def list_pdfs(folder: str | Path) -> list[Path]:
    path = Path(folder)
    if not path.is_dir():
        return []
    return sorted(path.glob("*.pdf"), key=lambda p: p.name.lower())


def render_pdf_pages(pdf_path: str | Path, *, dpi: int = 130) -> list[bytes]:
    """Return PNG bytes for each page of the PDF."""
    images: list[bytes] = []
    with pymupdf.open(pdf_path) as doc:
        for page in doc:
            pix = page.get_pixmap(dpi=dpi)
            images.append(pix.tobytes("png"))
    return images
