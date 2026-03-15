# AgentGraphRAG

面向航空质量问题溯因分析的多 Agent GraphRAG 项目。当前版本按 `Project.md` 和 `补充.md` 的业务流程做了重构，重点落在以下几件事：

- 配置中心支持按角色配置模型，不把 `bge-m3`、`Qwen2.5-3B-Instruct`、`Qwen2.5-Coder-3B-Instruct`、Milvus、Neo4j、MySQL 写死在代码里。
- 在线链路改成 Query Router Agent、Retrieval Agent、Graph Reasoning Agent、Verification Agent、Answer Synthesis Agent 的角色化编排。
- 离线链路保留结构化与非结构化双通道，chunk、图谱装载、案例记忆装载分开处理。
- Milvus 拆成 `knowledge_chunks` 和 `case_memory` 两套 collection，和 `Project.md` 的设计对齐。
- 前端工作台支持本地文件上传、知识库更新、文档预览、chunk 浏览、问答、trace 查看和图谱快照查看。
- Prompt Registry 提供 prompt 版本登记与查询接口。

## 1. 入口

启动服务后可直接使用：

- `http://127.0.0.1:8000/workspace`：工作台，上传文件、入库、问答、预览 chunk、查看 trace、查看 graph snapshot
- `http://127.0.0.1:8000/settings`：配置中心
- `http://127.0.0.1:8000/health`：健康检查
- `http://127.0.0.1:8000/api/v1/prompts`：Prompt Registry

## 2. 当前架构

### 离线阶段

- 结构化记录：清洗 -> 标准化 -> chunk -> Milvus -> Neo4j
- 非结构化文档：解析 -> 文档分类 -> 语义分块 -> 实体关系抽取 -> Milvus / Neo4j -> case memory
- 案例记忆：单独写入 MySQL 和 Milvus `case_memory`

### 在线阶段

- Query Router Agent：问题解析、实体识别、检索策略判断
- Retrieval Agent：构建 query plan，执行 graph / vector / hybrid 检索
- Graph Reasoning Agent：整理 reasoning path 和证据链
- Verification Agent：做证据充分性、冲突检查、fallback 判断
- Answer Synthesis Agent：基于证据输出最终答案

### 存储层

- MySQL：系统管理数据、文档元数据、审计日志、case 元数据
- Milvus：`knowledge_chunks` + `case_memory`
- Neo4j：Issue / Phenomenon / Component / Cause / Action 等图谱关系

## 3. 你要的推荐配置方式

你提到的组合可以直接通过 `/settings` 页面配置，不需要改代码：

- Embedding：`bge-m3`
- 问答模型：`Qwen/Qwen2.5-3B-Instruct`
- 推理模型：`Qwen/Qwen2.5-Coder-3B-Instruct`
- 向量库：Milvus
- 图库：Neo4j
- 管理库：MySQL

推荐做法：

1. 用一个 OpenAI-compatible 网关承载两个 Qwen 模型。
2. 问答模型填到 `answer_llm_model`。
3. 推理模型填到 `reasoning_llm_model`。
4. 如果两个模型走不同服务，把 `answer_llm_base_url`、`reasoning_llm_base_url` 分开填。
5. `embedding_provider=local` 且填写 `embedding_base_url` 时，会优先按 OpenAI-compatible embedding 接口走真实服务；不填时退回本地测试占位向量。

## 4. 配置页面

配置 API：

- `GET /api/v1/settings/schema`
- `GET /api/v1/settings/state`
- `GET /api/v1/settings/test-connections`
- `POST /api/v1/settings`

配置页会把值写回项目根目录 `.env`，并按 provider 自动补齐常见官方默认值。

## 5. 一套可直接照填的示例

```env
AGENTGRAPHRAG_LLM_PROVIDER="openai-compatible"
AGENTGRAPHRAG_LLM_BASE_URL="http://127.0.0.1:8000/v1"
AGENTGRAPHRAG_ANSWER_LLM_MODEL="Qwen/Qwen2.5-3B-Instruct"
AGENTGRAPHRAG_REASONING_LLM_MODEL="Qwen/Qwen2.5-Coder-3B-Instruct"

AGENTGRAPHRAG_EMBEDDING_PROVIDER="local"
AGENTGRAPHRAG_EMBEDDING_MODEL="bge-m3"
AGENTGRAPHRAG_EMBEDDING_BASE_URL="http://127.0.0.1:9997/v1"
AGENTGRAPHRAG_EMBEDDING_DIMENSIONS="1024"

AGENTGRAPHRAG_MYSQL_URL="mysql+pymysql://root:password@127.0.0.1:3306/agentgraphrag?charset=utf8mb4"

AGENTGRAPHRAG_MILVUS_MODE="self-hosted"
AGENTGRAPHRAG_MILVUS_URI="http://127.0.0.1:19530"
AGENTGRAPHRAG_MILVUS_DATABASE="default"
AGENTGRAPHRAG_MILVUS_COLLECTION="knowledge_chunks"
AGENTGRAPHRAG_MILVUS_CASE_COLLECTION="case_memory"

AGENTGRAPHRAG_NEO4J_MODE="custom"
AGENTGRAPHRAG_NEO4J_URI="bolt://127.0.0.1:7687"
AGENTGRAPHRAG_NEO4J_USER="neo4j"
AGENTGRAPHRAG_NEO4J_PASSWORD="password"
AGENTGRAPHRAG_NEO4J_DATABASE="neo4j"
```

## 6. 工作台支持的能力

`/workspace` 页面可以直接完成：

- 本地非结构化文件上传
- 上传后自动发起入库
- 浏览文档详情和 chunk 预览
- 问答提交
- 展示答案、证据、推理路径
- 展示完整 trace 与 agent traces
- 展示最近文档、最近入库任务、最近审计日志
- 展示图谱快照

## 7. Prompt Registry

接口：

- `GET /api/v1/prompts`

当前会返回每个 prompt 的：

- `name`
- `file`
- `version`
- `purpose`
- `path`

## 8. 运行

```bash
conda create -n AgentGraphRAG python=3.12 -y
conda activate AgentGraphRAG
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## 9. 初始化示例数据

```bash
python scripts/seed_demo.py
```

## 10. 架构文档

额外的完整架构说明见：

- [docs/项目架构说明.md](D:/Project/AgentGraphRAG/docs/项目架构说明.md)

## 11. 我对外部服务可行性的结论

当前方案按官方资料是成立的：

- `bge-m3`：适合 1024 维 embedding，可作为统一 query / chunk / case summary 向量模型
- `Qwen2.5-3B-Instruct`：适合做最终问答输出
- `Qwen2.5-Coder-3B-Instruct`：更适合结构化任务、Cypher 规划、路由与校验
- Milvus / Zilliz：都支持通过 endpoint + token 或本地 URI 接入
- Neo4j Aura / 自建 Neo4j：都支持 URI + 用户名 + 密码直连
- MySQL：继续作为管理数据和审计数据承载层没有问题，不参与主推理

## 12. 当前限制

- 当前 shell 环境里缺少 `pytest`、`sqlalchemy` 等依赖，所以我只能完成 `compileall` 级别的静态验证，无法在这里跑完整动态测试。
- 文档分类、Cypher 规划、证据校验目前保留规则回退，生产环境建议一定接上真实推理模型。
- 图谱快照当前是节点和关系列表视图，还不是交互式可视化画布。

## 13. 参考资料

- Qwen2.5-3B-Instruct: https://huggingface.co/Qwen/Qwen2.5-3B-Instruct
- Qwen2.5-Coder-3B-Instruct: https://huggingface.co/Qwen/Qwen2.5-Coder-3B-Instruct
- bge-m3: https://huggingface.co/BAAI/bge-m3
- vLLM OpenAI-compatible serving: https://docs.vllm.ai/en/latest/serving/openai_compatible_server.html
- Ollama OpenAI compatibility: https://docs.ollama.com/openai
- Milvus connect: https://milvus.io/docs/connect-to-milvus-server.md
- Zilliz connect: https://docs.zilliz.com/docs/connect-to-cluster
- Neo4j Aura connect: https://neo4j.com/docs/aura/getting-started/connect-instance/
- MySQL Connector/Python docs: https://dev.mysql.com/doc/connector-python/en/
