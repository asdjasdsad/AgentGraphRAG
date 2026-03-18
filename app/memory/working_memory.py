from __future__ import annotations

from collections import defaultdict


class WorkingMemory:
    def __init__(self) -> None:
        self._messages: dict[str, list[dict]] = defaultdict(list)

    def append(self, conversation_id: str, payload: dict) -> None:
        self._messages[conversation_id].append(payload)

    def get(self, conversation_id: str) -> list[dict]:
        return self._messages.get(conversation_id, [])


working_memory = WorkingMemory()
