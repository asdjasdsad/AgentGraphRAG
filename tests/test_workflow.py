from app.domain.schemas import AskRequest
from app.offline.ingest_structured import ingest_structured_records
from app.online.workflow import workflow


def test_workflow_answer() -> None:
    ingest_structured_records(
        [
            {
                "issue_id": "Q2025-010",
                "phenomenon": "液压泵泄漏",
                "component": ["液压泵"],
                "cause": ["密封圈老化"],
                "action": ["更换密封圈"],
            }
        ],
        load_batch_id="test_batch",
    )
    response = workflow.run(
        AskRequest(question="液压泵泄漏的原因有哪些？", conversation_id="conv_001", user_id="u001")
    )
    assert response.answer
    assert response.evidence
    assert response.reasoning_path
