from __future__ import annotations

import re
from collections.abc import Iterable


def clean_text(text: str) -> str:
    text = text.replace("\u3000", " ").replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_sentences(text: str) -> list[str]:
    chunks = re.split(r"[。！？；;\n]+", text)
    return [part.strip() for part in chunks if part.strip()]


def keyword_hit_count(text: str, keywords: Iterable[str]) -> int:
    return sum(1 for keyword in keywords if keyword and keyword in text)
