from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_settings_page_is_exposed() -> None:
    response = client.get("/settings")

    assert response.status_code == 200
    assert "AgentGraphRAG 真实接入配置中心" in response.text


def test_root_redirects_to_settings() -> None:
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/settings"


def test_settings_schema_exposes_real_provider_presets() -> None:
    response = client.get("/api/v1/settings/schema")
    data = response.json()

    llm_presets = data["preset_groups"]["llm_provider"]["presets"]
    embedding_presets = data["preset_groups"]["embedding_provider"]["presets"]
    milvus_presets = data["preset_groups"]["milvus_mode"]["presets"]
    embedding_fields = {item["name"] for item in data["fields"]}

    assert any(item["key"] == "openai" for item in llm_presets)
    assert any(item["key"] == "dashscope" for item in embedding_presets)
    assert any(item["key"] == "azure-openai" for item in llm_presets)
    assert any(item["key"] == "zilliz-cloud" for item in milvus_presets)
    assert "embedding_dimensions" in embedding_fields


def test_health_reports_service_status() -> None:
    response = client.get("/health")
    data = response.json()

    assert response.status_code == 200
    assert "services" in data
    assert {"mysql", "milvus", "neo4j"} <= set(data["services"])
