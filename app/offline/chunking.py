from __future__ import annotations

from app.core.config import get_settings
from app.domain.enums import ChunkType, DocumentType
from app.domain.schemas import Chunk, ParsedDocument
from app.utils.text_utils import clean_text, split_sentences


def _guess_chunk_type(section_path: str, content: str) -> ChunkType:
    text = f"{section_path} {content}"
    if "原因" in text or "根因" in text:
        return ChunkType.CAUSE_ANALYSIS
    if "措施" in text or "建议" in text or "整改" in text:
        return ChunkType.ACTION
    if "验证" in text or "复测" in text:
        return ChunkType.VALIDATION
    if "现象" in text or "故障" in text or "泄漏" in text:
        return ChunkType.PHENOMENON
    if "部件" in text or "组件" in text or "泵" in text:
        return ChunkType.COMPONENT
    return ChunkType.GENERAL


def _split_long_text(content: str) -> list[str]:
    max_chars = get_settings().max_chunk_chars
    if len(content) <= max_chars:
        return [content]
    parts: list[str] = []
    buffer = ""
    for sentence in split_sentences(content):
        if len(buffer) + len(sentence) + 1 > max_chars and buffer:
            parts.append(buffer.strip())
            buffer = sentence
        else:
            buffer = f"{buffer} {sentence}".strip()
    if buffer:
        parts.append(buffer)
    return parts


def build_chunks(parsed_doc: ParsedDocument) -> list[Chunk]:
    chunks: list[Chunk] = []
    if parsed_doc.doc_type == DocumentType.ISSUE_RECORD:
        for record in parsed_doc.records:
            content = clean_text(
                f"问题编号：{record.get('issue_id', '')}；现象：{record.get('phenomenon', '')}；"
                f"部件：{'、'.join(record.get('component', []))}；"
                f"原因：{'、'.join(record.get('cause', []))}；"
                f"措施：{'、'.join(record.get('action', []))}"
            )
            chunks.append(
                Chunk(
                    document_id=parsed_doc.document_id,
                    doc_type=parsed_doc.doc_type,
                    chunk_type=ChunkType.GENERAL,
                    section_path="issue_record",
                    content=content,
                    issue_id=record.get("issue_id"),
                    component=record.get("component", []),
                    metadata={"record": record},
                )
            )
        return chunks

    sections = parsed_doc.sections or []
    if parsed_doc.steps:
        sections = [
            {"section_path": f"step_{step.step_no}", "content": step.content, "page_no": 1}
            for step in parsed_doc.steps
        ]
    for section in sections:
        section_path = section.section_path if hasattr(section, "section_path") else section["section_path"]
        content = section.content if hasattr(section, "content") else section["content"]
        page_no = section.page_no if hasattr(section, "page_no") else section.get("page_no")
        for piece in _split_long_text(clean_text(content)):
            chunks.append(
                Chunk(
                    document_id=parsed_doc.document_id,
                    doc_type=parsed_doc.doc_type,
                    chunk_type=_guess_chunk_type(section_path, piece),
                    section_path=section_path,
                    content=piece,
                    page_no=page_no,
                    metadata={"file_name": parsed_doc.file_name},
                )
            )
    return chunks
