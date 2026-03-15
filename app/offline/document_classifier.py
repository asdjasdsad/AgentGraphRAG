from __future__ import annotations

from app.domain.enums import DocumentType
from app.prompts import render_prompt
from app.utils.text_utils import keyword_hit_count


ISSUE_RECORD_KEYWORDS = ["问题编号", "故障现象", "责任单位", "发现时间", "影响范围", "闭环"]
ANALYSIS_REPORT_KEYWORDS = ["原因分析", "根因", "问题分析", "结论", "评估", "失效机理"]
ACTION_REPORT_KEYWORDS = ["整改措施", "维修方案", "处理建议", "验证结果", "复测", "实施步骤"]


def classify_document(file_name: str, first_page_text: str, headings: list[str], table_headers: list[str]) -> dict:
    prompt_blueprint = render_prompt("classify_doc", file_name=file_name, first_page_text=first_page_text, headings=headings, table_headers=table_headers)
    text = "\n".join([file_name, first_page_text, *headings, *table_headers])
    scores = {
        DocumentType.ISSUE_RECORD: keyword_hit_count(text, ISSUE_RECORD_KEYWORDS),
        DocumentType.ANALYSIS_REPORT: keyword_hit_count(text, ANALYSIS_REPORT_KEYWORDS),
        DocumentType.ACTION_REPORT: keyword_hit_count(text, ACTION_REPORT_KEYWORDS),
    }
    doc_type, score = max(scores.items(), key=lambda item: item[1])
    if score == 0:
        if any(keyword in file_name for keyword in ("整改", "维修", "方案")):
            return {"doc_type": DocumentType.ACTION_REPORT, "confidence": 0.55, "source": "filename", "reason": f"文件名更像 action_report；prompt_length={len(prompt_blueprint)}"}
        if any(keyword in file_name for keyword in ("分析", "报告", "根因")):
            return {"doc_type": DocumentType.ANALYSIS_REPORT, "confidence": 0.55, "source": "filename", "reason": f"文件名更像 analysis_report；prompt_length={len(prompt_blueprint)}"}
        return {"doc_type": DocumentType.UNKNOWN, "confidence": 0.2, "source": "fallback", "reason": f"规则命中不足；prompt_length={len(prompt_blueprint)}"}
    confidence = min(0.99, 0.5 + score * 0.12)
    return {"doc_type": doc_type, "confidence": confidence, "source": "rule", "reason": f"规则命中 {score} 项；prompt_length={len(prompt_blueprint)}"}
