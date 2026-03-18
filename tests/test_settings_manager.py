from types import SimpleNamespace

from app.core.settings_manager import build_settings_snapshot, render_settings_page, save_managed_settings


def _build_defaults() -> dict[str, str]:
    return {
        "app_name": "AgentGraphRAG",
        "app_env": "dev",
        "debug": "true",
        "api_prefix": "/api/v1",
        "llm_provider": "",
        "llm_model": "",
        "llm_base_url": "",
        "llm_api_key": "",
        "llm_api_version": "",
        "embedding_provider": "local",
        "embedding_model": "bge-m3",
        "embedding_base_url": "",
        "embedding_api_key": "",
        "embedding_api_version": "",
        "embedding_dimensions": "1024",
        "embedding_query_instruction": "为航空质量问题检索最相关的原因、措施、案例和证据",
        "document_parse_provider": "local",
        "document_parse_base_url": "",
        "document_parse_api_key": "",
        "mysql_url": "sqlite:///local.db",
        "neo4j_mode": "local",
        "neo4j_uri": "bolt://localhost:7687",
        "neo4j_user": "neo4j",
        "neo4j_password": "password",
        "neo4j_database": "neo4j",
        "milvus_mode": "local",
        "milvus_uri": "http://localhost:19530",
        "milvus_token": "",
        "milvus_database": "default",
        "milvus_collection": "chunks",
    }


def test_save_managed_settings_keeps_existing_secret_and_applies_provider_defaults(monkeypatch, tmp_path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        '\n'.join(
            [
                '# existing config',
                'AGENTGRAPHRAG_LLM_API_KEY="old-secret"',
                'CUSTOM_FLAG="keep-me"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    defaults = _build_defaults()
    monkeypatch.setattr("app.core.settings_manager.ENV_FILE", env_file)
    monkeypatch.setattr("app.core.settings_manager.get_settings", lambda: SimpleNamespace(**defaults))

    submitted = defaults | {"llm_provider": "openai", "llm_model": "gpt-4.1-mini", "llm_api_key": ""}
    save_managed_settings(submitted)

    content = env_file.read_text(encoding="utf-8")
    assert 'AGENTGRAPHRAG_LLM_PROVIDER="openai"' in content
    assert 'AGENTGRAPHRAG_LLM_BASE_URL="https://api.openai.com/v1"' in content
    assert 'AGENTGRAPHRAG_LLM_API_KEY="old-secret"' in content
    assert 'CUSTOM_FLAG="keep-me"' in content


def test_build_settings_snapshot_flags_missing_zilliz_token(monkeypatch) -> None:
    values = _build_defaults() | {
        "milvus_mode": "zilliz-cloud",
        "milvus_uri": "https://in01-xxx.serverless.gcp-us-west1.zillizcloud.com",
        "milvus_token": "",
    }
    monkeypatch.setattr("app.core.settings_manager.current_settings_values", lambda settings=None: values)

    snapshot = build_settings_snapshot()

    assert snapshot["summary"]["errors"] >= 1
    assert any(check["title"] == "Zilliz Cloud 缺少 Token" for check in snapshot["checks"])


def test_render_settings_page_masks_secret_values_and_shows_presets(monkeypatch) -> None:
    values = _build_defaults() | {"llm_api_key": "top-secret", "llm_provider": "deepseek", "llm_model": "deepseek-chat"}
    monkeypatch.setattr("app.core.settings_manager.current_settings_values", lambda settings=None: values)

    html = render_settings_page("saved")

    assert "DeepSeek" in html
    assert "AGENTGRAPHRAG_LLM_API_KEY" in html
    assert "top-secret" not in html
    assert "saved" in html


def test_dashscope_embedding_defaults_are_applied(monkeypatch, tmp_path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("", encoding="utf-8")

    defaults = _build_defaults()
    monkeypatch.setattr("app.core.settings_manager.ENV_FILE", env_file)
    monkeypatch.setattr("app.core.settings_manager.get_settings", lambda: SimpleNamespace(**defaults))

    submitted = defaults | {
        "embedding_provider": "dashscope",
        "embedding_model": "text-embedding-v4",
        "embedding_base_url": "",
        "embedding_api_key": "dashscope-secret",
        "embedding_dimensions": "",
        "embedding_query_instruction": "",
    }
    normalized = save_managed_settings(submitted)

    assert normalized["embedding_model"] == "text-embedding-v4"
    assert normalized["embedding_base_url"].endswith("/api/v1/services/embeddings/text-embedding/text-embedding")
    assert normalized["embedding_dimensions"] == "1024"
