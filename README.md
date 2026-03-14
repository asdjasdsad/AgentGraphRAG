# AgentGraphRAG

面向航空质量问题溯因分析的 GraphRAG Agent 项目，按 `D:\Project\Project.md` 的架构落地为可运行版本。

## 当前实现

- FastAPI 接口：文档上传、导入、问答、案例查询、审计查询、配置中心
- 离线链路：文档解析、规则分类、chunk、实体关系抽取、向量/图双写
- 在线链路：问题解析、graph/vector/hybrid 路由、检索、重排、证据校验、保守回答
- 真实存储接入：
  - `MySQL` 通过 SQLAlchemy 连接
  - `Milvus` 通过 `pymilvus.MilvusClient` 连接
  - `Neo4j` 通过官方 `neo4j` driver 连接
- 测试环境：`app_env=test` 时保留本地 mock 分支，避免单测依赖外部服务

## 运行

```bash
conda create -n AgentGraphRAG python=3.12 -y
conda activate AgentGraphRAG
pip install -r requirements.txt
uvicorn app.main:app --reload
```

启动后打开：

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/settings`
- `http://127.0.0.1:8000/health`

## 推荐配置

### DashScope Embedding

- `AGENTGRAPHRAG_EMBEDDING_PROVIDER=dashscope`
- `AGENTGRAPHRAG_EMBEDDING_MODEL=text-embedding-v4`
- `AGENTGRAPHRAG_EMBEDDING_BASE_URL=https://dashscope.aliyuncs.com/api/v1/services/embeddings/text-embedding/text-embedding`
- `AGENTGRAPHRAG_EMBEDDING_DIMENSIONS=1024`
- `AGENTGRAPHRAG_EMBEDDING_QUERY_INSTRUCTION=为航空质量问题检索最相关的原因、措施、案例和证据`
- `AGENTGRAPHRAG_EMBEDDING_API_KEY=你的 DashScope Key`

### MySQL

- `AGENTGRAPHRAG_MYSQL_URL=mysql+pymysql://root:password@127.0.0.1:3306/agentgraphrag?charset=utf8mb4`

### Milvus

- `AGENTGRAPHRAG_MILVUS_MODE=self-hosted`
- `AGENTGRAPHRAG_MILVUS_URI=http://127.0.0.1:19530`
- `AGENTGRAPHRAG_MILVUS_TOKEN=`
- `AGENTGRAPHRAG_MILVUS_DATABASE=default`
- `AGENTGRAPHRAG_MILVUS_COLLECTION=chunks`

### Neo4j

- `AGENTGRAPHRAG_NEO4J_MODE=custom`
- `AGENTGRAPHRAG_NEO4J_URI=bolt://127.0.0.1:7687`
- `AGENTGRAPHRAG_NEO4J_USER=neo4j`
- `AGENTGRAPHRAG_NEO4J_PASSWORD=你的密码`
- `AGENTGRAPHRAG_NEO4J_DATABASE=neo4j`

## 配置方式

推荐直接打开 `/settings` 页面保存配置。页面会把值写入项目根目录的 `.env`。

配置 API：

- `GET /api/v1/settings/schema`
- `GET /api/v1/settings/state`
- `POST /api/v1/settings`

## 验证方式

启动服务后访问 `/health`，返回里会包含：

- `mysql`
- `milvus`
- `neo4j`

如果三者都连通，`status` 会是 `ok`；否则会返回 `degraded` 和对应错误信息。

## 初始化数据

如果你已经从本地 mock embedding 切到 DashScope，建议重新导入一次数据：

```bash
python scripts/seed_demo.py
```

这样新的 chunk 会重新生成真实 embedding，并写入 MySQL、Milvus、Neo4j。
