from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ConfigOption:
    value: str
    label: str


@dataclass(frozen=True)
class ConfigField:
    name: str
    label: str
    section: str
    description: str
    input_type: str = "text"
    placeholder: str = ""
    secret: bool = False
    required: bool = False
    options: tuple[ConfigOption, ...] = ()


@dataclass(frozen=True)
class ProviderPreset:
    key: str
    label: str
    group: str
    summary: str
    docs_url: str = ""
    docs_label: str = "官方文档"
    defaults: dict[str, str] = field(default_factory=dict)
    required_fields: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()


CONFIG_FIELDS: tuple[ConfigField, ...] = (
    ConfigField("app_name", "应用名称", "app", "页面标题和接口元信息。", required=True),
    ConfigField("app_env", "运行环境", "app", "建议使用 dev / test / prod。", required=True, options=(ConfigOption("dev", "dev"), ConfigOption("test", "test"), ConfigOption("prod", "prod"))),
    ConfigField("debug", "调试模式", "app", "FastAPI 调试开关。", required=True, options=(ConfigOption("true", "true"), ConfigOption("false", "false"))),
    ConfigField("api_prefix", "API 前缀", "app", "默认保留为 /api/v1。", required=True, placeholder="/api/v1"),
    ConfigField("llm_provider", "LLM 提供方", "llm_shared", "问答模型和推理模型默认共用同一类 provider，角色模型名单独配置。", options=(ConfigOption("", "未启用"), ConfigOption("openai", "OpenAI"), ConfigOption("azure-openai", "Azure OpenAI"), ConfigOption("deepseek", "DeepSeek"), ConfigOption("dashscope", "DashScope / 通义千问"), ConfigOption("openai-compatible", "OpenAI Compatible"), ConfigOption("ollama", "Ollama"))),
    ConfigField("llm_base_url", "共享 LLM Base URL", "llm_shared", "大多数情况下这里填统一网关地址。角色级 Base URL 留空时会回落到这里。", placeholder="https://api.example.com/v1"),
    ConfigField("llm_api_key", "共享 LLM API Key", "llm_shared", "角色级 API Key 留空时会回落到这里。", input_type="password", placeholder="sk-...", secret=True),
    ConfigField("llm_api_version", "共享 LLM API Version", "llm_shared", "Azure 或兼容层需要时填写。", placeholder="2024-10-21"),
    ConfigField("llm_timeout_seconds", "LLM 超时秒数", "llm_shared", "回答与推理模型共用的默认超时。", required=True, placeholder="60"),
    ConfigField("answer_llm_model", "问答模型", "llm_answer", "最终答案生成使用的模型，例如 Qwen2.5-3B-Instruct。", placeholder="Qwen/Qwen2.5-3B-Instruct"),
    ConfigField("answer_llm_base_url", "问答模型 Base URL", "llm_answer", "可选覆盖共享网关；留空时使用共享 LLM Base URL。", placeholder="http://127.0.0.1:8000/v1"),
    ConfigField("answer_llm_api_key", "问答模型 API Key", "llm_answer", "可选覆盖共享 Key；留空时沿用共享 Key。", input_type="password", placeholder="EMPTY", secret=True),
    ConfigField("answer_llm_api_version", "问答模型 API Version", "llm_answer", "可选覆盖共享 API Version。", placeholder="2024-10-21"),
    ConfigField("answer_llm_temperature", "问答温度", "llm_answer", "最终回答建议保持较低温度，减少高敏场景漂移。", required=True, placeholder="0.2"),
    ConfigField("answer_llm_max_tokens", "问答最大输出 Token", "llm_answer", "最终回答的最大输出长度。", required=True, placeholder="1024"),
    ConfigField("reasoning_llm_model", "推理模型", "llm_reasoning", "问题解析、Cypher 规划、检索路由和证据校验使用的模型，例如 Qwen2.5-Coder-3B-Instruct。", placeholder="Qwen/Qwen2.5-Coder-3B-Instruct"),
    ConfigField("reasoning_llm_base_url", "推理模型 Base URL", "llm_reasoning", "可选覆盖共享网关；留空时使用共享 LLM Base URL。", placeholder="http://127.0.0.1:8001/v1"),
    ConfigField("reasoning_llm_api_key", "推理模型 API Key", "llm_reasoning", "可选覆盖共享 Key；留空时沿用共享 Key。", input_type="password", placeholder="EMPTY", secret=True),
    ConfigField("reasoning_llm_api_version", "推理模型 API Version", "llm_reasoning", "可选覆盖共享 API Version。", placeholder="2024-10-21"),
    ConfigField("reasoning_llm_temperature", "推理温度", "llm_reasoning", "Cypher 规划和结构化推理建议用 0 或接近 0。", required=True, placeholder="0.0"),
    ConfigField("reasoning_llm_max_tokens", "推理最大输出 Token", "llm_reasoning", "结构化解析与校验的最大输出长度。", required=True, placeholder="768"),
    ConfigField("embedding_provider", "Embedding 提供方", "embedding", "local 可配本地 bge-m3 服务或占位向量；外部向量服务按 provider 选择。", required=True, options=(ConfigOption("local", "Local / bge-m3"), ConfigOption("openai", "OpenAI"), ConfigOption("azure-openai", "Azure OpenAI"), ConfigOption("dashscope", "DashScope / 通义千问"), ConfigOption("openai-compatible", "OpenAI Compatible"), ConfigOption("ollama", "Ollama"))),
    ConfigField("embedding_model", "Embedding 模型", "embedding", "例如 bge-m3 或 text-embedding-v4。", required=True, placeholder="bge-m3"),
    ConfigField("embedding_base_url", "Embedding Base URL", "embedding", "外部 embedding 服务地址。", placeholder="http://127.0.0.1:11434/v1"),
    ConfigField("embedding_api_key", "Embedding API Key", "embedding", "外部 embedding 服务密钥。", input_type="password", placeholder="emb-...", secret=True),
    ConfigField("embedding_api_version", "Embedding API Version", "embedding", "Azure 或兼容层需要时填写。", placeholder="2024-10-21"),
    ConfigField("embedding_dimensions", "Embedding 维度", "embedding", "bge-m3 和 DashScope text-embedding-v4 常见为 1024 维。", required=True, placeholder="1024"),
    ConfigField("embedding_query_instruction", "Embedding Query Instruction", "embedding", "用于 query embedding 的检索指令。", placeholder="为航空质量问题检索最相关的原因、措施、案例和证据"),
    ConfigField("document_parse_provider", "文档解析服务", "document", "Project.md 当前优先本地解析，必要时可切到 Dify 或网关。", required=True, options=(ConfigOption("local", "Local Parser"), ConfigOption("dify", "Dify / Gateway"))),
    ConfigField("document_parse_base_url", "解析服务 Base URL", "document", "外部文档解析网关地址。", placeholder="https://your-dify.example.com/v1"),
    ConfigField("document_parse_api_key", "解析服务 API Key", "document", "外部文档解析服务密钥。", input_type="password", placeholder="app-...", secret=True),
    ConfigField("neo4j_mode", "Neo4j 模式", "graph", "Aura 和本地都走 URI + 用户名 + 密码。", required=True, options=(ConfigOption("local", "Local Neo4j"), ConfigOption("aura", "Neo4j Aura"), ConfigOption("custom", "Custom Neo4j"))),
    ConfigField("neo4j_uri", "Neo4j URI", "graph", "本地常见为 bolt://localhost:7687，Aura 常见为 neo4j+s://xxxx.databases.neo4j.io。", required=True, placeholder="bolt://localhost:7687"),
    ConfigField("neo4j_user", "Neo4j 用户名", "graph", "Aura 和本地默认都可用 neo4j 用户名起步。", required=True, placeholder="neo4j"),
    ConfigField("neo4j_password", "Neo4j 密码", "graph", "图数据库连接密码。", input_type="password", placeholder="password", secret=True),
    ConfigField("neo4j_database", "Neo4j Database", "graph", "AuraDB Free 默认一般是 neo4j。", required=True, placeholder="neo4j"),
    ConfigField("milvus_mode", "Milvus 模式", "vector", "本地、自建、Zilliz Cloud 均可通过这里配置。", required=True, options=(ConfigOption("local", "Local Milvus"), ConfigOption("self-hosted", "Self-hosted Milvus"), ConfigOption("zilliz-cloud", "Zilliz Cloud"))),
    ConfigField("milvus_uri", "Milvus URI / Endpoint", "vector", "本地例如 http://localhost:19530，Zilliz Cloud 填集群 endpoint。", required=True, placeholder="http://localhost:19530"),
    ConfigField("milvus_token", "Milvus Token", "vector", "Zilliz Cloud 或开启鉴权的 Milvus 使用。", input_type="password", placeholder="token", secret=True),
    ConfigField("milvus_database", "Milvus Database", "vector", "Milvus / Zilliz 使用的数据库名。", required=True, placeholder="default"),
    ConfigField("milvus_collection", "Chunk Collection", "vector", "非结构化 chunk 的向量集合。", required=True, placeholder="knowledge_chunks"),
    ConfigField("milvus_case_collection", "Case Collection", "vector", "案例记忆的向量集合。", required=True, placeholder="case_memory"),
    ConfigField("mysql_url", "MySQL URL", "database", "管理数据和审计日志建议落 MySQL；本地 MVP 仍可用 sqlite。", required=True, placeholder="mysql+pymysql://user:password@host:3306/dbname?charset=utf8mb4"),
)

SECTION_ORDER = ("app", "llm_shared", "llm_answer", "llm_reasoning", "embedding", "document", "graph", "vector", "database")
SECTION_META: dict[str, tuple[str, str]] = {
    "app": ("应用基础", "服务标题、调试模式和 API 前缀。"),
    "llm_shared": ("共享 LLM 网关", "统一配置 provider、默认网关和默认密钥。"),
    "llm_answer": ("问答模型", "负责最终回答生成，建议配置 Qwen2.5-3B-Instruct 这类偏通用对话模型。"),
    "llm_reasoning": ("推理模型", "负责问题解析、Cypher 规划、检索路由和证据校验，建议配置 Qwen2.5-Coder-3B-Instruct 这类结构化推理更稳的模型。"),
    "embedding": ("Embedding 配置", "向量召回层配置，推荐 bge-m3。"),
    "document": ("文档解析", "本地解析和外部网关两条路共存。"),
    "graph": ("图谱存储", "Neo4j 本地、自建、Aura 统一收敛。"),
    "vector": ("向量存储", "Milvus 和 Zilliz Cloud 统一收敛。"),
    "database": ("管理库", "结构化管理数据、任务状态和审计日志。"),
}

PRESET_GROUP_ORDER = ("llm_provider", "embedding_provider", "neo4j_mode", "milvus_mode", "document_parse_provider")
PRESET_GROUP_META: dict[str, tuple[str, str]] = {
    "llm_provider": ("LLM 官方方案", "统一 provider，角色模型名单独填写。"),
    "embedding_provider": ("Embedding 官方方案", "向量模型与回答模型分离，便于独立切换。"),
    "neo4j_mode": ("Neo4j 部署方案", "Aura 和本地都使用 URI + 用户名 + 密码。"),
    "milvus_mode": ("Milvus / Zilliz 方案", "Zilliz Cloud 额外要求 token。"),
    "document_parse_provider": ("文档解析方案", "Project.md 保留了本地解析和外部网关两条路线。"),
}

PRESETS: tuple[ProviderPreset, ...] = (
    ProviderPreset("openai", "OpenAI", "llm_provider", "官方平台 API Key + /v1 基础路径。", "https://platform.openai.com/docs/api-reference/authentication", defaults={"llm_provider": "openai", "llm_base_url": "https://api.openai.com/v1"}, required_fields=("answer_llm_model", "reasoning_llm_model", "llm_api_key")),
    ProviderPreset("azure-openai", "Azure OpenAI", "llm_provider", "推荐使用 /openai/v1/ 路径；模型字段填 deployment name。", "https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/responses", required_fields=("answer_llm_model", "reasoning_llm_model", "llm_api_key", "llm_base_url"), notes=("Base URL 形如 https://YOUR-RESOURCE-NAME.openai.azure.com/openai/v1/。",)),
    ProviderPreset("deepseek", "DeepSeek", "llm_provider", "官方 OpenAI-compatible 方案。", "https://api-docs.deepseek.com/", defaults={"llm_provider": "deepseek", "llm_base_url": "https://api.deepseek.com/v1"}, required_fields=("answer_llm_model", "reasoning_llm_model", "llm_api_key")),
    ProviderPreset("dashscope", "DashScope / 通义千问", "llm_provider", "通义千问推荐通过 OpenAI 兼容模式接入。", "https://help.aliyun.com/zh/model-studio/compatibility-of-openai-with-dashscope", required_fields=("answer_llm_model", "reasoning_llm_model", "llm_api_key", "llm_base_url"), notes=("北京地域常用 https://dashscope.aliyuncs.com/compatible-mode/v1。",)),
    ProviderPreset("openai-compatible", "OpenAI Compatible", "llm_provider", "适合 vLLM、SGLang、OneAPI 等兼容层。", "https://docs.vllm.ai/en/latest/serving/openai_compatible_server.html", required_fields=("answer_llm_model", "reasoning_llm_model", "llm_base_url")),
    ProviderPreset("ollama", "Ollama", "llm_provider", "适合本地单机部署，推荐走 OpenAI 兼容入口。", "https://docs.ollama.com/openai", defaults={"llm_provider": "ollama", "llm_base_url": "http://127.0.0.1:11434/v1"}, required_fields=("answer_llm_model", "reasoning_llm_model", "llm_base_url")),
    ProviderPreset("local", "Local / bge-m3", "embedding_provider", "本地模式，适合先用本地 bge-m3 服务或测试占位向量。", defaults={"embedding_provider": "local", "embedding_model": "bge-m3", "embedding_dimensions": "1024"}, required_fields=("embedding_model", "embedding_dimensions")),
    ProviderPreset("openai", "OpenAI Embeddings", "embedding_provider", "OpenAI embedding 接口。", "https://platform.openai.com/docs/guides/embeddings", defaults={"embedding_provider": "openai", "embedding_base_url": "https://api.openai.com/v1", "embedding_dimensions": "1024"}, required_fields=("embedding_model", "embedding_api_key", "embedding_dimensions")),
    ProviderPreset("azure-openai", "Azure OpenAI Embeddings", "embedding_provider", "Azure embedding deployment。", "https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/responses", required_fields=("embedding_model", "embedding_api_key", "embedding_base_url", "embedding_dimensions")),
    ProviderPreset("dashscope", "DashScope Embeddings", "embedding_provider", "按 text-embedding-v4 原生接口接入。", "https://help.aliyun.com/zh/model-studio/text-embedding-api-reference", defaults={"embedding_provider": "dashscope", "embedding_model": "text-embedding-v4", "embedding_base_url": "https://dashscope.aliyuncs.com/api/v1/services/embeddings/text-embedding/text-embedding", "embedding_dimensions": "1024", "embedding_query_instruction": "为航空质量问题检索最相关的原因、措施、案例和证据"}, required_fields=("embedding_model", "embedding_api_key", "embedding_base_url", "embedding_dimensions")),
    ProviderPreset("openai-compatible", "Compatible Embeddings", "embedding_provider", "适合兼容 OpenAI embedding 协议的服务。", "https://platform.openai.com/docs/guides/embeddings", required_fields=("embedding_model", "embedding_base_url", "embedding_dimensions")),
    ProviderPreset("ollama", "Ollama Embeddings", "embedding_provider", "适合通过本地 Ollama 暴露 embedding 模型。", "https://docs.ollama.com/openai", defaults={"embedding_provider": "ollama", "embedding_base_url": "http://127.0.0.1:11434/v1", "embedding_dimensions": "1024"}, required_fields=("embedding_model", "embedding_base_url", "embedding_dimensions")),
    ProviderPreset("local", "Local Neo4j", "neo4j_mode", "本地开发常见 bolt://localhost:7687。", "https://neo4j.com/docs/aura/getting-started/connect-instance/", defaults={"neo4j_mode": "local", "neo4j_uri": "bolt://localhost:7687", "neo4j_user": "neo4j", "neo4j_database": "neo4j"}, required_fields=("neo4j_uri", "neo4j_user", "neo4j_password", "neo4j_database")),
    ProviderPreset("aura", "Neo4j Aura", "neo4j_mode", "AuraDB 推荐使用 neo4j+s://。", "https://neo4j.com/docs/aura/getting-started/connect-instance/", defaults={"neo4j_mode": "aura", "neo4j_user": "neo4j", "neo4j_database": "neo4j"}, required_fields=("neo4j_uri", "neo4j_user", "neo4j_password", "neo4j_database")),
    ProviderPreset("custom", "Custom Neo4j", "neo4j_mode", "适合企业内部 Neo4j 集群。", "https://neo4j.com/docs/aura/getting-started/connect-instance/", required_fields=("neo4j_uri", "neo4j_user", "neo4j_password", "neo4j_database")),
    ProviderPreset("local", "Local Milvus", "milvus_mode", "本地开发常见 http://localhost:19530。", "https://milvus.io/docs/connect-to-milvus-server.md", defaults={"milvus_mode": "local", "milvus_uri": "http://localhost:19530", "milvus_database": "default", "milvus_collection": "knowledge_chunks", "milvus_case_collection": "case_memory"}, required_fields=("milvus_uri", "milvus_database", "milvus_collection", "milvus_case_collection")),
    ProviderPreset("self-hosted", "Self-hosted Milvus", "milvus_mode", "自建 Milvus 以 URI 为主。", "https://milvus.io/docs/connect-to-milvus-server.md", defaults={"milvus_mode": "self-hosted", "milvus_database": "default", "milvus_collection": "knowledge_chunks", "milvus_case_collection": "case_memory"}, required_fields=("milvus_uri", "milvus_database", "milvus_collection", "milvus_case_collection")),
    ProviderPreset("zilliz-cloud", "Zilliz Cloud", "milvus_mode", "真实接入需要 endpoint + token。", "https://docs.zilliz.com/docs/connect-to-cluster", defaults={"milvus_mode": "zilliz-cloud", "milvus_database": "default", "milvus_collection": "knowledge_chunks", "milvus_case_collection": "case_memory"}, required_fields=("milvus_uri", "milvus_token", "milvus_database", "milvus_collection", "milvus_case_collection")),
    ProviderPreset("local", "Local Parser", "document_parse_provider", "继续使用仓库内 PDF / DOCX / OCR 解析链路。", defaults={"document_parse_provider": "local"}),
    ProviderPreset("dify", "Dify / Gateway", "document_parse_provider", "把文档解析委托给外部网关时使用。", "https://docs.dify.ai/api-reference/introduction", required_fields=("document_parse_base_url", "document_parse_api_key")),
)

FIELD_MAP = {field.name: field for field in CONFIG_FIELDS}
SECRET_FIELD_NAMES = {field.name for field in CONFIG_FIELDS if field.secret}
PRESET_GROUPS: dict[str, tuple[ProviderPreset, ...]] = {group: tuple(preset for preset in PRESETS if preset.group == group) for group in PRESET_GROUP_ORDER}
PRESET_INDEX: dict[str, dict[str, ProviderPreset]] = {group: {preset.key: preset for preset in presets} for group, presets in PRESET_GROUPS.items()}
SEVERITY_ORDER = {"error": 0, "warning": 1, "info": 2, "success": 3}


def serialize_option(option: ConfigOption) -> dict[str, str]:
    return {"value": option.value, "label": option.label}


def serialize_field(field: ConfigField) -> dict[str, Any]:
    return {"name": field.name, "label": field.label, "section": field.section, "description": field.description, "input_type": field.input_type, "placeholder": field.placeholder, "secret": field.secret, "required": field.required, "options": [serialize_option(option) for option in field.options]}


def serialize_preset(preset: ProviderPreset) -> dict[str, Any]:
    return {"key": preset.key, "label": preset.label, "group": preset.group, "summary": preset.summary, "docs_url": preset.docs_url, "docs_label": preset.docs_label, "defaults": dict(preset.defaults), "required_fields": list(preset.required_fields), "notes": list(preset.notes)}


def resolve_settings_values(values: dict[str, str]) -> dict[str, str]:
    resolved = dict(values)
    for group in PRESET_GROUP_ORDER:
        selected_key = resolved.get(group, "")
        preset = PRESET_INDEX.get(group, {}).get(selected_key)
        if not preset:
            continue
        for field_name, default_value in preset.defaults.items():
            if not resolved.get(field_name):
                resolved[field_name] = default_value
    return resolved


def get_active_presets(values: dict[str, str]) -> dict[str, ProviderPreset]:
    active: dict[str, ProviderPreset] = {}
    for group in PRESET_GROUP_ORDER:
        selected_key = values.get(group, "")
        preset = PRESET_INDEX.get(group, {}).get(selected_key)
        if preset:
            active[group] = preset
    return active


def build_settings_schema() -> dict[str, Any]:
    return {"fields": [serialize_field(field) for field in CONFIG_FIELDS], "sections": [{"key": section, "title": SECTION_META[section][0], "description": SECTION_META[section][1]} for section in SECTION_ORDER], "preset_groups": {group: {"title": PRESET_GROUP_META[group][0], "description": PRESET_GROUP_META[group][1], "presets": [serialize_preset(preset) for preset in PRESET_GROUPS[group]]} for group in PRESET_GROUP_ORDER}}


def _field_labels(field_names: tuple[str, ...] | list[str]) -> str:
    labels = [FIELD_MAP[name].label for name in field_names if name in FIELD_MAP]
    return "、".join(labels)


def _check(level: str, title: str, message: str, field_names: tuple[str, ...] | list[str] = ()) -> dict[str, Any]:
    return {"level": level, "title": title, "message": message, "fields": list(field_names), "field_labels": _field_labels(field_names)}


def build_config_checks(values: dict[str, str]) -> list[dict[str, Any]]:
    resolved = resolve_settings_values(values)
    checks: list[dict[str, Any]] = []
    for field in CONFIG_FIELDS:
        if field.required and not resolved.get(field.name):
            checks.append(_check("error", f"缺少 {field.label}", f"{field.label} 是当前配置页的基础必填项。", (field.name,)))

    active_presets = get_active_presets(resolved)
    for _, preset in active_presets.items():
        missing = [name for name in preset.required_fields if not resolved.get(name)]
        if missing:
            checks.append(_check("error", f"{preset.label} 配置不完整", f"按官方接入方案，{preset.label} 还需要补齐：{_field_labels(missing)}。", missing))
        else:
            checks.append(_check("success", f"{preset.label} 字段齐全", f"{preset.label} 所需的核心字段已经齐全。", preset.required_fields))

    llm_provider = resolved.get("llm_provider", "")
    if not llm_provider:
        checks.append(_check("warning", "当前未启用外部 LLM", "多智能体链路将退回到规则化解析和模板回答，适合测试但不适合生产。"))
    else:
        if not resolved.get("answer_llm_model"):
            checks.append(_check("error", "缺少问答模型", "请配置最终回答使用的 answer_llm_model。", ("answer_llm_model",)))
        if not resolved.get("reasoning_llm_model"):
            checks.append(_check("error", "缺少推理模型", "请配置问题解析和 Cypher 规划使用的 reasoning_llm_model。", ("reasoning_llm_model",)))
        if llm_provider == "azure-openai" and "/openai/v1/" not in resolved.get("llm_base_url", ""):
            checks.append(_check("warning", "Azure OpenAI Base URL 形态可疑", "Azure 官方新路径通常包含 /openai/v1/。", ("llm_base_url",)))
        if llm_provider == "dashscope" and "compatible-mode" not in resolved.get("llm_base_url", ""):
            checks.append(_check("warning", "DashScope Base URL 形态可疑", "百炼 OpenAI 兼容模式路径通常包含 compatible-mode/v1。", ("llm_base_url",)))
        if llm_provider == "ollama":
            checks.append(_check("info", "Ollama 兼容层说明", "如果你本地通过 Ollama 提供模型，模型名请填 Ollama 已拉取的 tag，例如 qwen2.5:3b-instruct。", ("llm_base_url", "answer_llm_model", "reasoning_llm_model")))

    embedding_provider = resolved.get("embedding_provider", "")
    if embedding_provider == "local":
        checks.append(_check("info", "Embedding 处于本地模式", "当前会优先走本地 bge-m3 或测试占位向量。", ("embedding_model",)))
    if embedding_provider == "dashscope":
        if resolved.get("embedding_dimensions", "") not in {"1024", "768", "512", "256"}:
            checks.append(_check("warning", "DashScope Embedding 维度可疑", "text-embedding-v4 官方推荐维度为 1024 / 768 / 512 / 256。", ("embedding_dimensions",)))
        checks.append(_check("info", "DashScope Query Instruction 已启用", "query embedding 请求会自动携带 embedding_query_instruction。", ("embedding_query_instruction",)))
    if embedding_provider == "ollama":
        checks.append(_check("info", "Ollama Embedding 说明", "请确认本地 Ollama 服务已加载 embedding 模型，并暴露 OpenAI 兼容接口。", ("embedding_model", "embedding_base_url")))

    if resolved.get("document_parse_provider", "local") == "local":
        checks.append(_check("info", "文档解析沿用本地链路", "这与 Project.md 当前阶段的本地解析设计一致。"))
    if resolved.get("neo4j_mode") == "aura" and not resolved.get("neo4j_uri", "").startswith("neo4j+s://"):
        checks.append(_check("warning", "Aura URI 形态可疑", "Neo4j Aura 官方示例通常使用 neo4j+s:// 开头。", ("neo4j_uri",)))
    if resolved.get("milvus_mode") == "zilliz-cloud" and not resolved.get("milvus_token", ""):
        checks.append(_check("error", "Zilliz Cloud 缺少 Token", "Zilliz Cloud 的真实接入方案是 endpoint + token。", ("milvus_token",)))

    mysql_url = resolved.get("mysql_url", "")
    if mysql_url.startswith("sqlite"):
        checks.append(_check("warning", "当前仍使用本地兼容数据库", "Project.md 的长期方案是 MySQL；sqlite 只建议用于本地开发或测试。", ("mysql_url",)))
    else:
        checks.append(_check("success", "管理库已指向外部数据库", "当前管理库配置已脱离本地 sqlite。", ("mysql_url",)))

    checks.sort(key=lambda item: (SEVERITY_ORDER[item["level"]], item["title"]))
    return checks
