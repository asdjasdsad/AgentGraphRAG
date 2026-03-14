from __future__ import annotations

from app.core.db_mysql import audit_logs_table


class EpisodicMemory:
    def recent(self, user_id: str) -> list[dict]:
        rows = [row for row in audit_logs_table.all() if row["user_id"] == user_id]
        return sorted(rows, key=lambda item: item["created_at"], reverse=True)[:10]


episodic_memory = EpisodicMemory()
