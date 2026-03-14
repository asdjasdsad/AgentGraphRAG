from __future__ import annotations


def table_rows_to_text(rows: list[dict[str, str]]) -> list[str]:
    rendered = []
    for row in rows:
        parts = [f"{key}：{value}" for key, value in row.items() if value]
        if parts:
            rendered.append("；".join(parts) + "。")
    return rendered
