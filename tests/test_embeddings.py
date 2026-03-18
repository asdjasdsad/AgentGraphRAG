from types import SimpleNamespace

from app.core.embeddings import DashScopeEmbeddingProvider, LocalEmbeddingProvider, build_embedding_provider
from app.prompts import render_prompt


def test_local_embedding_provider_respects_dimensions() -> None:
    settings = SimpleNamespace(embedding_dimensions=32)
    provider = LocalEmbeddingProvider(settings)

    vector = provider.embed_query("液压泵泄漏")

    assert len(vector) == 32
    assert round(sum(item * item for item in vector), 6) == 1.0


def test_dashscope_embedding_provider_uses_native_payload(monkeypatch) -> None:
    requests: list[dict] = []

    class FakeResponse:
        status_code = 200
        text = "ok"

        def json(self) -> dict:
            return {"output": {"embeddings": [{"text_index": 0, "embedding": [3.0, 4.0, 0.0]}]}}

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

        def post(self, url: str, headers: dict, json: dict) -> FakeResponse:
            requests.append({"url": url, "headers": headers, "json": json})
            return FakeResponse()

    monkeypatch.setattr("app.core.embeddings.httpx.Client", FakeClient)
    settings = SimpleNamespace(
        embedding_provider="dashscope",
        embedding_base_url="https://dashscope.aliyuncs.com/api/v1/services/embeddings/text-embedding/text-embedding",
        embedding_api_key="dashscope-secret",
        embedding_model="text-embedding-v4",
        embedding_dimensions=512,
        embedding_query_instruction="检索航空质量问题的原因和措施",
    )
    provider = DashScopeEmbeddingProvider(settings)

    vector = provider.embed_query("液压泵泄漏的原因是什么")

    assert vector == [0.6, 0.8, 0.0]
    assert requests[0]["json"]["parameters"]["text_type"] == "query"
    assert requests[0]["json"]["parameters"]["dimension"] == 512
    assert requests[0]["json"]["parameters"]["instruct"] == "检索航空质量问题的原因和措施"


def test_build_embedding_provider_selects_dashscope() -> None:
    settings = SimpleNamespace(
        embedding_provider="dashscope",
        embedding_base_url="https://dashscope.aliyuncs.com/api/v1/services/embeddings/text-embedding/text-embedding",
        embedding_api_key="secret",
        embedding_model="text-embedding-v4",
        embedding_dimensions=1024,
        embedding_query_instruction="检索航空质量问题的原因和措施",
    )

    provider = build_embedding_provider(settings)

    assert isinstance(provider, DashScopeEmbeddingProvider)


def test_prompt_template_can_render_context() -> None:
    prompt = render_prompt("parse_question", question="液压泵泄漏的原因是什么", allowed_scope=["documents", "graph"])

    assert "液压泵泄漏的原因是什么" in prompt
    assert "documents" in prompt
