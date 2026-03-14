from __future__ import annotations

from app.core.db_mysql import chunks_table
from app.domain.enums import ChunkType, DocumentType
from app.domain.schemas import Chunk, StructuredRecord
from app.offline.extraction import extract_entities_relations
from app.offline.loaders.milvus_loader import load_chunks_to_milvus
from app.offline.loaders.neo4j_loader import load_graph_data
from app.offline.normalization import normalize_record


def ingest_structured_records(records: list[dict], load_batch_id: str | None = None) -> dict:
    normalized_records = [normalize_record({**record, "load_batch_id": load_batch_id}) for record in records]
    chunks: list[Chunk] = []
    entities: list[dict] = []
    relations: list[dict] = []
    for record in normalized_records:
        text = (
            f"问题编号：{record.issue_id}；现象：{record.phenomenon}；"
            f"部件：{'、'.join(record.component)}；原因：{'、'.join(record.cause)}；"
            f"措施：{'、'.join(record.action)}"
        )
        chunk = Chunk(
            document_id=record.issue_id,
            doc_type=DocumentType.ISSUE_RECORD,
            chunk_type=ChunkType.GENERAL,
            section_path="structured_record",
            content=text,
            issue_id=record.issue_id,
            component=record.component,
            source_type="structured",
            load_batch_id=load_batch_id,
            metadata=record.model_dump(mode="json"),
        )
        chunks.append(chunk)
        extraction = extract_entities_relations(text, "issue_record")
        entities.extend(extraction["entities"])
        relations.extend(extraction["relations"])
    load_chunks_to_milvus(chunks)
    load_graph_data(entities, relations)
    for chunk in chunks:
        chunks_table.upsert(chunk, "chunk_id")
    return {"records": len(normalized_records), "chunks": len(chunks), "entities": len(entities), "relations": len(relations)}
