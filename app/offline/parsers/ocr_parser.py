from __future__ import annotations

from pathlib import Path

from app.utils.text_utils import clean_text


def parse_image_with_ocr(path: Path) -> dict:
    text = clean_text(path.read_text(encoding="utf-8", errors="ignore")) if path.suffix.lower() == ".txt" else ""
    return {
        "pages": [{"page_no": 1, "raw_text": text, "text_blocks": [text]}],
        "headings": [],
        "table_headers": [],
        "raw_text": text,
    }
