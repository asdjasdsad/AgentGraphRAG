from __future__ import annotations

from pathlib import Path

from app.core.db_mysql import chunks_table, documents_table
from app.domain.enums import DocumentType
from app.domain.schemas import CaseSummary, DocumentMetadata, ParsedDocument, ParsedSection, ParsedStep
from app.offline.chunking import build_chunks
from app.offline.document_classifier import classify_document
from app.offline.extraction import extract_entities_relations
from app.offline.loaders.case_loader import persist_case_memory
from app.offline.loaders.milvus_loader import load_chunks_to_milvus
from app.offline.loaders.neo4j_loader import load_graph_data
from app.offline.parsers.ocr_parser import parse_image_with_ocr
from app.offline.parsers.pdf_parser import parse_pdf
from app.offline.parsers.word_parser import parse_docx
from app.utils.text_utils import clean_text


def _parse_by_suffix(path: Path) -> dict:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return parse_pdf(path)
    if suffix == ".docx":
        return parse_docx(path)
    return parse_image_with_ocr(path)


def _build_parsed_document(metadata: DocumentMetadata, parsed: dict) -> ParsedDocument:
    classification = classify_document(metadata.file_name, parsed["raw_text"][:1000], parsed["headings"], parsed["table_headers"])
    doc_type = classification["doc_type"]
    sections: list[ParsedSection] = []
    steps: list[ParsedStep] = []
    records: list[dict] = []
    if doc_type == DocumentType.ANALYSIS_REPORT:
        for page in parsed["pages"]:
            sections.append(ParsedSection(section_path=f"page_{page['page_no']}", content=page["raw_text"], page_no=page["page_no"]))
    elif doc_type == DocumentType.ACTION_REPORT:
        for index, line in enumerate(clean_text(parsed["raw_text"]).splitlines(), start=1):
            if line:
                steps.append(ParsedStep(step_no=index, content=line))
    else:
        records.append({"issue_id": metadata.document_id, "phenomenon": clean_text(parsed["raw_text"][:80]), "component": [], "cause": [], "action": []})
    return ParsedDocument(document_id=metadata.document_id, file_name=metadata.file_name, doc_type=doc_type, pages=parsed["pages"], records=records, sections=sections, steps=steps, headings=parsed["headings"], table_headers=parsed["table_headers"], raw_text=parsed["raw_text"])


def ingest_document(metadata: DocumentMetadata | dict, load_batch_id: str | None = None) -> dict:
    metadata_obj = metadata if isinstance(metadata, DocumentMetadata) else DocumentMetadata(**metadata)
    parsed = _parse_by_suffix(Path(metadata_obj.storage_path or ""))
    parsed_doc = _build_parsed_document(metadata_obj, parsed)
    chunks = build_chunks(parsed_doc)
    for chunk in chunks:
        chunk.load_batch_id = load_batch_id
    load_chunks_to_milvus(chunks)
    entities: list[dict] = []
    relations: list[dict] = []
    for chunk in chunks:
        extraction = extract_entities_relations(chunk.content, parsed_doc.doc_type.value)
        entities.extend(extraction["entities"])
        relations.extend(extraction["relations"])
        chunks_table.upsert(chunk, "chunk_id")
    load_graph_data(entities, relations)
    if chunks:
        case = CaseSummary(issue_type=parsed_doc.doc_type.value, summary=chunks[0].content[:240], root_cause_chain_json=[entity["name"] for entity in entities if entity["type"] == "Cause"], actions_json=[entity["name"] for entity in entities if entity["type"] == "Action"], source_docs_json=[metadata_obj.document_id])
        persist_case_memory(case)
    metadata_obj.doc_type = parsed_doc.doc_type
    metadata_obj.parse_status = "success"
    documents_table.upsert(metadata_obj, "document_id")
    return {"document_id": metadata_obj.document_id, "doc_type": parsed_doc.doc_type.value, "chunks": len(chunks), "entities": len(entities), "relations": len(relations)}
