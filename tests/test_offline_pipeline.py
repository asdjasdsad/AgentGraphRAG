from app.domain.enums import DocumentType
from app.domain.schemas import ParsedDocument, ParsedSection
from app.offline.chunking import build_chunks
from app.offline.document_classifier import classify_document
from app.offline.extraction import extract_entities_relations


def test_document_classifier_analysis_report() -> None:
    result = classify_document("液压泵分析报告.docx", "原因分析\n结论", ["原因分析"], [])
    assert result["doc_type"] == DocumentType.ANALYSIS_REPORT


def test_chunking_and_extraction() -> None:
    parsed = ParsedDocument(
        document_id="doc_001",
        file_name="demo.docx",
        doc_type=DocumentType.ANALYSIS_REPORT,
        sections=[ParsedSection(section_path="3.原因分析", content="液压泵泄漏的原因是密封圈老化。", page_no=1)],
    )
    chunks = build_chunks(parsed)
    assert chunks
    extraction = extract_entities_relations(chunks[0].content, parsed.doc_type.value)
    assert extraction["entities"]
