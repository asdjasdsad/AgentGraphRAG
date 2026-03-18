from __future__ import annotations

from pathlib import Path

from app.utils.text_utils import clean_text


def parse_pdf(path: Path) -> dict:
    try:
        import fitz  # type: ignore

        document = fitz.open(path)
        pages = []
        headings: list[str] = []
        for index, page in enumerate(document):
            text = clean_text(page.get_text("text"))
            pages.append({"page_no": index + 1, "raw_text": text, "text_blocks": [text]})
            headings.extend([line for line in text.splitlines()[:5] if len(line) < 40])
        raw_text = "\n".join(page["raw_text"] for page in pages)
        return {"pages": pages, "headings": headings, "table_headers": [], "raw_text": raw_text}
    except Exception:
        text = clean_text(path.read_text(encoding="utf-8", errors="ignore"))
        return {
            "pages": [{"page_no": 1, "raw_text": text, "text_blocks": [text]}],
            "headings": text.splitlines()[:5],
            "table_headers": [],
            "raw_text": text,
        }
