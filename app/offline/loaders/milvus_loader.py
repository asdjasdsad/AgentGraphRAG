from __future__ import annotations

from app.core.db_milvus import milvus_store
from app.domain.schemas import Chunk


def load_chunks_to_milvus(chunks: list[Chunk]) -> None:
    milvus_store.insert_chunks(chunks)
