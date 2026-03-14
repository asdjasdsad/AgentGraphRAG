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
    ConfigField(
        "app_env",
        "运行环境",
        "app",
        "推荐使用 dev / test / prod。",
        required=True,
        options=(ConfigOption("dev", "dev"), ConfigOption("test", "test"), ConfigOption("prod", "prod")),
    ),
    ConfigField(
        "debug",
        "调试模式",
        "app",
        "FastAPI 调试开关。",
        required=True,
        options=(ConfigOption("true", "true"), ConfigOption("false", "false")),
    ),
    ConfigField("api_prefix", "API 前缀", "app", "默认保留为 /api/v1。", required=True, placeholder="/api/v1"),
    ConfigField(
        "llm_provider",
        "LLM 提供方",
        "llm",
        "按官方接入方式选择 provider；空值表示当前问答链路不启用外部 LLM。",
        options=(
            ConfigOption("", "未启用"),
            ConfigOption("openai", "OpenAI"),
            ConfigOption("azure-openai", "Azure OpenAI"),
            ConfigOption("deepseek", "DeepSeek"),
            ConfigOption("dashscope", "DashScope / 通义千问"),
            ConfigOption("openai-compatible", "OpenAI Compatible"),
        ),
    ),
    ConfigField("llm_model", "LLM 模型名", "llm", "模型名；Azure OpenAI 场景下这里填 deployment name。", placeholder="gpt-4.1-mini"),
    ConfigField("llm_base_url", "LLM Base URL", "llm", "官方或代理网关地址。", placeholder="https://api.example.com/v1"),
    ConfigField(
        "llm_api_key",
        "LLM API Key",
        "llm",
        "外部问答模型统一读取这个名字。",
        input_type="password",
        placeholder="sk-...",
        secret=True,
    ),
    ConfigField(
        "llm_api_version",
        "LLM API Version",
        "llm",
        "仅在少数 Azure 或兼容层需要时填写；官方 v1 路径可留空。",
        placeholder="2024-10-21",
    ),
    ConfigField(
        "embedding_provider",
        "Embedding 提供方",
        "embedding",
        "local 表示继续使用本地占位 embedding；外部向量服务按 provider 选择。",
        required=True,
        options=(
            ConfigOption("local", "Local / bge-m3"),
            ConfigOption("openai", "OpenAI"),
            ConfigOption("azure-openai", "Azure OpenAI"),
            ConfigOption("dashscope", "DashScope / 通义千问"),
            ConfigOption("openai-compatible", "OpenAI Compatible"),
        ),
    ),
    ConfigField("embedding_model", "Embedding 模型名", "embedding", "本地默认 bge-m3；Azure 场景下这里填 deployment name。", required=True, placeholder="bge-m3"),
    ConfigField("embedding_base_url", "Embedding Base URL", "embedding", "外部向量服务地址。", placeholder="https://api.example.com/v1"),
    ConfigField(
        "embedding_api_key",
        "Embedding API Key",
        "embedding",
        "外部 embedding 服务统一读取这个名字。",
        input_type="password",
        placeholder="emb-...",
        secret=True,
    ),
    ConfigField(
        "embedding_api_version",
        "Embedding API Version",
        "embedding",
        "仅在 Azure 或兼容层要求额外版本参数时填写。",
        placeholder="2024-10-21",
    ),
    ConfigField(
        "embedding_dimensions",
        "Embedding Dimension",
        "embedding",
        "DashScope text-embedding-v4 官方支持 1024 / 768 / 512 / 256；本地 mock 也会按这个维度生成向量。",
        required=True,
        placeholder="1024",
    ),
    ConfigField(
        "embedding_query_instruction",
        "Embedding Query Instruction",
        "embedding",
        "仅在 DashScope query embedding 时作为 instruct 传入，用来强化航空质量问题检索意图。",
        placeholder="为航空质量问题检索最相关的原因、措施、案例和证据",
    ),
    ConfigField(
        "document_parse_provider",
        "文档解析服务",
        "document",
        "按 Project.md，默认本地解析即可；若改成外部解析网关，再补 Base URL 和 Key。",
        required=True,
        options=(ConfigOption("local", "Local Parser"), ConfigOption("dify", "Dify / Gateway")),
    ),
    ConfigField("document_parse_base_url", "解析服务 Base URL", "document", "Dify 或其他解析网关地址。", placeholder="https://your-dify.example.com/v1"),
    ConfigField(
        "document_parse_api_key",
        "解析服务 API Key",
        "document",
        "外部文档解析服务统一读取这个名字。",
        input_type="password",
        placeholder="app-...",
        secret=True,
    ),
    ConfigField(
        "neo4j_mode",
        "Neo4j 模式",
        "graph",
        "Project.md 设计里图谱层由 Neo4j 承担；Aura 和本地都走 URI + 用户名 + 密码。",
        required=True,
        options=(
            ConfigOption("local", "Local Neo4j"),
            ConfigOption("aura", "Neo4j Aura"),
            ConfigOption("custom", "Custom Neo4j"),
        ),
    ),
    ConfigField("neo4j_uri", "Neo4j URI", "graph", "本地常见为 bolt://localhost:7687；Aura 常见为 neo4j+s://xxxx.databases.neo4j.io。", required=True, placeholder="bolt://localhost:7687"),
    ConfigField("neo4j_user", "Neo4j 用户名", "graph", "Aura 和本地默认都是 neo4j 用户名起步。", required=True, placeholder="neo4j"),
    ConfigField(
        "neo4j_password",
        "Neo4j 密码",
        "graph",
        "图数据库连接密码。",
        input_type="password",
        placeholder="password",
        secret=True,
    ),
    ConfigField("neo4j_database", "Neo4j Database", "graph", "AuraDB Free 默认一般是 neo4j。", required=True, placeholder="neo4j"),
    ConfigField(
        "milvus_mode",
        "Milvus 模式",
        "vector",
        "本地 / 自建 Milvus 主要看 URI；Zilliz Cloud 还需要 token。",
        required=True,
        options=(
            ConfigOption("local", "Local Milvus"),
            ConfigOption("self-hosted", "Self-hosted Milvus"),
            ConfigOption("zilliz-cloud", "Zilliz Cloud"),
        ),
    ),
    ConfigField("milvus_uri", "Milvus URI / Endpoint", "vector", "本地例如 http://localhost:19530；Zilliz Cloud 填集群 endpoint。", required=True, placeholder="http://localhost:19530"),
    ConfigField(
        "milvus_token",
        "Milvus Token",
        "vector",
        "Zilliz Cloud 或启用鉴权的 Milvus 统一使用这个字段。",
        input_type="password",
        placeholder="token",
        secret=True,
    ),
    ConfigField("milvus_database", "Milvus Database", "vector", "Milvus / Zilliz 使用的数据库名。", required=True, placeholder="default"),
    ConfigField("milvus_collection", "Milvus Collection", "vector", "向量集合名，默认 chunks。", required=True, placeholder="chunks"),
    ConfigField("mysql_url", "MySQL URL", "database", "Project.md 设计里管理数据最终应落 MySQL；本地 MVP 可暂时保留 sqlite 风格连接串。", required=True, placeholder="mysql+pymysql://user:password@host:3306/dbname"),
)

SECTION_ORDER = ("app", "llm", "embedding", "document", "graph", "vector", "database")
SECTION_META: dict[str, tuple[str, str]] = {
    "app": ("应用基础", "这组配置影响服务标题、调试模式和 API 路由。"),
    "llm": ("LLM 配置", "这里统一管理问答模型 provider、网关地址和密钥。"),
    "embedding": ("Embedding 配置", "Project.md 里的向量召回层需要 embedding；本地 MVP 也可以先保持 local。"),
    "document": ("文档解析", "Project.md 里默认本地解析即可；如果未来切到 Dify 或其他网关，这组字段直接复用。"),
    "graph": ("图谱存储", "Neo4j 本地、自建、Aura 统一收敛到这里。"),
    "vector": ("向量存储", "Milvus 本地、自建、Zilliz Cloud 统一收敛到这里。"),
    "database": ("管理库", "结构化管理数据和审计配置最终应落 MySQL；当前项目仍兼容本地模式。"),
}

PRESET_GROUP_ORDER = ("llm_provider", "embedding_provider", "neo4j_mode", "milvus_mode", "document_parse_provider")
PRESET_GROUP_META: dict[str, tuple[str, str]] = {
    "llm_provider": ("LLM 官方方案", "按当前官方接入方式选择 provider；按钮会帮你填入安全默认值。"),
    "embedding_provider": ("Embedding 官方方案", "向量模型沿用与 LLM 分离的配置，方便后续切换供应商。"),
    "neo4j_mode": ("Neo4j 部署方案", "Aura 和本地都使用 URI + 用户名 + 密码；Aura API 凭证不是当前项目所需。"),
    "milvus_mode": ("Milvus / Zilliz 方案", "Zilliz Cloud 额外要求 token；本地或自建 Milvus 可只配 URI。"),
    "document_parse_provider": ("文档解析方案", "Project.md 保留了本地解析和外部网关两种路线。"),
}

PRESETS: tuple[ProviderPreset, ...] = (
    ProviderPreset(
        key="openai",
        label="OpenAI",
        group="llm_provider",
        summary="官方平台 API Key + /v1 基础路径。",
        docs_url="https://platform.openai.com/docs/api-reference/authentication",
        defaults={"llm_provider": "openai", "llm_base_url": "https://api.openai.com/v1"},
        required_fields=("llm_model", "llm_api_key"),
        notes=("OpenAI 官方认证文档使用 Bearer API key。",),
    ),
    ProviderPreset(
        key="azure-openai",
        label="Azure OpenAI",
        group="llm_provider",
        summary="官方推荐用 /openai/v1/ 路径；模型字段填 deployment name。",
        docs_url="https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/responses",
        required_fields=("llm_model", "llm_api_key", "llm_base_url"),
        notes=("Base URL 形如 https://YOUR-RESOURCE-NAME.openai.azure.com/openai/v1/。", "如果沿用旧 SDK/旧接口，可能还需要 api-version。"),
    ),
    ProviderPreset(
        key="deepseek",
        label="DeepSeek",
        group="llm_provider",
        summary="官方 OpenAI-compatible 方案；统一走 API Key + 基础网关。",
        docs_url="https://api-docs.deepseek.com/",
        defaults={"llm_provider": "deepseek", "llm_base_url": "https://api.deepseek.com/v1"},
        required_fields=("llm_model", "llm_api_key"),
        notes=("DeepSeek 官方文档同时给出 OpenAI SDK 兼容接法。",),
    ),
    ProviderPreset(
        key="dashscope",
        label="DashScope / 通义千问",
        group="llm_provider",
        summary="官方 OpenAI 兼容模式；不同地域使用不同 compatible-mode 域名。",
        docs_url="https://help.aliyun.com/zh/model-studio/compatibility-of-openai-with-dashscope",
        required_fields=("llm_model", "llm_api_key", "llm_base_url"),
        notes=("北京地域常用 https://dashscope.aliyuncs.com/compatible-mode/v1。", "国际/美东地域需改成对应 dashscope-intl / dashscope-us 域名。"),
    ),
    ProviderPreset(
        key="openai-compatible",
        label="OpenAI Compatible",
        group="llm_provider",
        summary="适合自建代理网关或其他兼容 OpenAI 协议的服务。",
        docs_url="https://platform.openai.com/docs/api-reference/authentication",
        required_fields=("llm_model", "llm_api_key", "llm_base_url"),
        notes=("只有接口兼容时才建议直接复用这组字段。",),
    ),
    ProviderPreset(
        key="local",
        label="Local / bge-m3",
        group="embedding_provider",
        summary="沿用项目当前本地占位 embedding 方案，不需要外部 Key。",
        docs_url="https://platform.openai.com/docs/guides/embeddings",
        defaults={"embedding_provider": "local", "embedding_model": "bge-m3", "embedding_dimensions": "1024"},
        required_fields=("embedding_model", "embedding_dimensions"),
        notes=("local provider 只把 embedding 生成留在本地，不依赖外部 API Key。",),
    ),
    ProviderPreset(
        key="openai",
        label="OpenAI Embeddings",
        group="embedding_provider",
        summary="官方 API Key + /v1；模型名按 OpenAI embedding 模型填写。",
        docs_url="https://platform.openai.com/docs/guides/embeddings",
        defaults={"embedding_provider": "openai", "embedding_base_url": "https://api.openai.com/v1", "embedding_dimensions": "1024"},
        required_fields=("embedding_model", "embedding_api_key", "embedding_dimensions"),
    ),
    ProviderPreset(
        key="azure-openai",
        label="Azure OpenAI Embeddings",
        group="embedding_provider",
        summary="与 LLM 一样走 Azure 资源 endpoint；模型字段填 embedding deployment。",
        docs_url="https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/responses",
        required_fields=("embedding_model", "embedding_api_key", "embedding_base_url", "embedding_dimensions"),
        notes=("如果仍走旧接口，可能还要带 api-version。",),
    ),
    ProviderPreset(
        key="dashscope",
        label="DashScope Embeddings",
        group="embedding_provider",
        summary="按 DashScope 官方 text-embedding-v4 原生接口接入，支持 document/query 区分、instruct 和多档维度。",
        docs_url="https://help.aliyun.com/zh/model-studio/text-embedding-api-reference",
        defaults={
            "embedding_provider": "dashscope",
            "embedding_model": "text-embedding-v4",
            "embedding_base_url": "https://dashscope.aliyuncs.com/api/v1/services/embeddings/text-embedding/text-embedding",
            "embedding_dimensions": "1024",
            "embedding_query_instruction": "为航空质量问题检索最相关的原因、措施、案例和证据",
        },
        required_fields=("embedding_model", "embedding_api_key", "embedding_base_url", "embedding_dimensions"),
        notes=(
            "text-embedding-v4 官方支持 1024 / 768 / 512 / 256 四档维度。",
            "项目会在 query embedding 时把 embedding_query_instruction 作为 instruct 传入。",
        ),
    ),
    ProviderPreset(
        key="openai-compatible",
        label="Compatible Embeddings",
        group="embedding_provider",
        summary="适合自建或三方兼容 OpenAI embedding 协议的服务。",
        docs_url="https://platform.openai.com/docs/guides/embeddings",
        required_fields=("embedding_model", "embedding_api_key", "embedding_base_url", "embedding_dimensions"),
    ),
    ProviderPreset(
        key="local",
        label="Local Neo4j",
        group="neo4j_mode",
        summary="本地开发常见 bolt://localhost:7687 + neo4j 用户名。",
        docs_url="https://neo4j.com/docs/aura/getting-started/connect-instance/",
        defaults={"neo4j_mode": "local", "neo4j_uri": "bolt://localhost:7687", "neo4j_user": "neo4j", "neo4j_database": "neo4j"},
        required_fields=("neo4j_uri", "neo4j_user", "neo4j_password", "neo4j_database"),
    ),
    ProviderPreset(
        key="aura",
        label="Neo4j Aura",
        group="neo4j_mode",
        summary="AuraDB 连接仍是 URI + 用户名 + 密码；推荐 neo4j+s://。",
        docs_url="https://neo4j.com/docs/aura/getting-started/connect-instance/",
        defaults={"neo4j_mode": "aura", "neo4j_user": "neo4j", "neo4j_database": "neo4j"},
        required_fields=("neo4j_uri", "neo4j_user", "neo4j_password", "neo4j_database"),
        notes=("Aura API 的 OAuth 凭证用于控制面 API，不是这个项目连图库必须要配的。",),
    ),
    ProviderPreset(
        key="custom",
        label="Custom Neo4j",
        group="neo4j_mode",
        summary="适合已有企业内部 Neo4j 集群。",
        docs_url="https://neo4j.com/docs/aura/getting-started/connect-instance/",
        required_fields=("neo4j_uri", "neo4j_user", "neo4j_password", "neo4j_database"),
    ),
    ProviderPreset(
        key="local",
        label="Local Milvus",
        group="milvus_mode",
        summary="本地开发常见 http://localhost:19530。",
        docs_url="https://milvus.io/docs/connect-to-milvus-server.md",
        defaults={"milvus_mode": "local", "milvus_uri": "http://localhost:19530", "milvus_database": "default", "milvus_collection": "chunks"},
        required_fields=("milvus_uri", "milvus_database", "milvus_collection"),
    ),
    ProviderPreset(
        key="self-hosted",
        label="Self-hosted Milvus",
        group="milvus_mode",
        summary="自建 Milvus 以 URI 为主，开启鉴权时可额外填 token。",
        docs_url="https://milvus.io/docs/connect-to-milvus-server.md",
        defaults={"milvus_mode": "self-hosted", "milvus_database": "default", "milvus_collection": "chunks"},
        required_fields=("milvus_uri", "milvus_database", "milvus_collection"),
    ),
    ProviderPreset(
        key="zilliz-cloud",
        label="Zilliz Cloud",
        group="milvus_mode",
        summary="官方方案是 endpoint + token；没有 token 不能连数据面。",
        docs_url="https://docs.zilliz.com/docs/connect-to-cluster",
        defaults={"milvus_mode": "zilliz-cloud", "milvus_database": "default", "milvus_collection": "chunks"},
        required_fields=("milvus_uri", "milvus_token", "milvus_database", "milvus_collection"),
        notes=("Zilliz Cloud 的 endpoint 和 token 都来自集群控制台。",),
    ),
    ProviderPreset(
        key="local",
        label="Local Parser",
        group="document_parse_provider",
        summary="继续使用仓库内 PDF / DOCX / OCR 解析链路。",
        defaults={"document_parse_provider": "local"},
        notes=("这条路线不需要额外 API Key。",),
    ),
    ProviderPreset(
        key="dify",
        label="Dify / Gateway",
        group="document_parse_provider",
        summary="如果把文档解析委托给外部网关，再填 Base URL 和 API Key。",
        docs_url="https://docs.dify.ai/api-reference/introduction",
        required_fields=("document_parse_base_url", "document_parse_api_key"),
        notes=("Dify 常见是实例级 Base URL + 应用或服务 API Key。",),
    ),
)

FIELD_MAP = {field.name: field for field in CONFIG_FIELDS}
SECRET_FIELD_NAMES = {field.name for field in CONFIG_FIELDS if field.secret}
PRESET_GROUPS: dict[str, tuple[ProviderPreset, ...]] = {
    group: tuple(preset for preset in PRESETS if preset.group == group) for group in PRESET_GROUP_ORDER
}
PRESET_INDEX: dict[str, dict[str, ProviderPreset]] = {
    group: {preset.key: preset for preset in presets} for group, presets in PRESET_GROUPS.items()
}
SEVERITY_ORDER = {"error": 0, "warning": 1, "info": 2, "success": 3}


def serialize_option(option: ConfigOption) -> dict[str, str]:
    return {"value": option.value, "label": option.label}


def serialize_field(field: ConfigField) -> dict[str, Any]:
    return {
        "name": field.name,
        "label": field.label,
        "section": field.section,
        "description": field.description,
        "input_type": field.input_type,
        "placeholder": field.placeholder,
        "secret": field.secret,
        "required": field.required,
        "options": [serialize_option(option) for option in field.options],
    }


def serialize_preset(preset: ProviderPreset) -> dict[str, Any]:
    return {
        "key": preset.key,
        "label": preset.label,
        "group": preset.group,
        "summary": preset.summary,
        "docs_url": preset.docs_url,
        "docs_label": preset.docs_label,
        "defaults": dict(preset.defaults),
        "required_fields": list(preset.required_fields),
        "notes": list(preset.notes),
    }


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
    return {
        "fields": [serialize_field(field) for field in CONFIG_FIELDS],
        "sections": [
            {"key": section, "title": SECTION_META[section][0], "description": SECTION_META[section][1]}
            for section in SECTION_ORDER
        ],
        "preset_groups": {
            group: {
                "title": PRESET_GROUP_META[group][0],
                "description": PRESET_GROUP_META[group][1],
                "presets": [serialize_preset(preset) for preset in PRESET_GROUPS[group]],
            }
            for group in PRESET_GROUP_ORDER
        },
    }


def _field_labels(field_names: tuple[str, ...] | list[str]) -> str:
    labels = [FIELD_MAP[name].label for name in field_names if name in FIELD_MAP]
    return "、".join(labels)


def _check(level: str, title: str, message: str, field_names: tuple[str, ...] | list[str] = ()) -> dict[str, Any]:
    return {
        "level": level,
        "title": title,
        "message": message,
        "fields": list(field_names),
        "field_labels": _field_labels(field_names),
    }


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
        checks.append(_check("info", "当前未启用外部 LLM", "问答链路仍会按仓库现状走本地规则/模拟流程。"))
    elif llm_provider == "azure-openai":
        if "/openai/v1/" not in resolved.get("llm_base_url", ""):
            checks.append(_check("warning", "Azure OpenAI Base URL 形态可疑", "Azure 官方新路径通常包含 /openai/v1/，请确认不是旧 endpoint 或代理路径。", ("llm_base_url",)))
        checks.append(_check("info", "Azure OpenAI 模型字段说明", "Azure OpenAI 的 model 字段通常填写 deployment name，而不是裸模型名。", ("llm_model",)))
    elif llm_provider == "dashscope" and "compatible-mode" not in resolved.get("llm_base_url", ""):
        checks.append(_check("warning", "DashScope Base URL 形态可疑", "百炼 OpenAI 兼容模式的官方路径通常包含 compatible-mode/v1。", ("llm_base_url",)))
    elif llm_provider == "openai-compatible":
        checks.append(_check("info", "兼容层责任边界", "只有目标服务真正兼容 OpenAI 协议时，才建议直接复用这组字段。"))

    embedding_provider = resolved.get("embedding_provider", "")
    if embedding_provider == "local":
        checks.append(_check("info", "Embedding 仍处于本地模式", "当前只把 embedding 生成留在本地，不需要额外 API Key。", ("embedding_model",)))
    elif embedding_provider == "azure-openai":
        checks.append(_check("info", "Azure Embedding 模型字段说明", "Azure OpenAI embedding 场景下，embedding_model 通常填写 deployment name。", ("embedding_model",)))
    elif embedding_provider == "dashscope" and "compatible-mode" not in resolved.get("embedding_base_url", "") and "text-embedding" not in resolved.get("embedding_base_url", ""):
        checks.append(_check("warning", "DashScope Embedding Base URL 形态可疑", "DashScope text-embedding-v4 官方原生接口通常包含 /api/v1/services/embeddings/text-embedding/text-embedding。", ("embedding_base_url",)))

    if embedding_provider == "dashscope":
        if resolved.get("embedding_dimensions", "") not in {"1024", "768", "512", "256"}:
            checks.append(_check("warning", "DashScope Embedding Dimension 可疑", "text-embedding-v4 官方推荐维度为 1024 / 768 / 512 / 256。", ("embedding_dimensions",)))
        checks.append(_check("info", "DashScope Query Instruction 已启用", "项目会在 query embedding 请求里自动带上 embedding_query_instruction，便于检索原因、措施和案例。", ("embedding_query_instruction",)))

    parse_provider = resolved.get("document_parse_provider", "local")
    if parse_provider == "local":
        checks.append(_check("info", "文档解析沿用本地链路", "这与 Project.md 当前 MVP 阶段的本地解析设计一致。"))

    neo4j_mode = resolved.get("neo4j_mode", "local")
    if neo4j_mode == "aura" and not resolved.get("neo4j_uri", "").startswith("neo4j+s://"):
        checks.append(_check("warning", "Aura URI 形态可疑", "Neo4j Aura 官方示例通常使用 neo4j+s:// 开头的加密连接。", ("neo4j_uri",)))

    milvus_mode = resolved.get("milvus_mode", "local")
    if milvus_mode == "zilliz-cloud" and not resolved.get("milvus_token", ""):
        checks.append(_check("error", "Zilliz Cloud 缺少 Token", "Zilliz Cloud 的真实接入方案是 endpoint + token，没有 token 无法连数据面。", ("milvus_token",)))
    elif milvus_mode in {"local", "self-hosted"} and resolved.get("milvus_token", ""):
        checks.append(_check("info", "Milvus Token 已配置", "如果你的 Milvus 开启了鉴权，这个 token 会被保留；未开启时可忽略。", ("milvus_token",)))

    mysql_url = resolved.get("mysql_url", "")
    if mysql_url.startswith("sqlite"):
        checks.append(_check("info", "当前仍是本地兼容数据库配置", "Project.md 的长期方案是 MySQL，但仓库当前实现仍允许用本地连接串跑通 MVP。", ("mysql_url",)))

    checks.sort(key=lambda item: (SEVERITY_ORDER[item["level"]], item["title"]))
    return checks

