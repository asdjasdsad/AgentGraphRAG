# 图查询 Agent 的 Cypher 生成模型微调项目设计文档

> 版本：v1.0  
> 面向对象：Codex / 开发同学  
> 目标：基于本设计文档，落地一个可运行的“数据构造 → SFT(QLoRA) → DPO → 离线评测 → replay 验证”的完整项目，用于优化 GraphRAG 系统中 Graph Reasoning Agent 的 Cypher 生成能力。

---

## 1. 项目背景与目标

### 1.1 背景

在“面向航空质量问题溯因分析的智能问答系统”中，在线链路的 Graph Reasoning Agent 负责根据结构化问题对象生成 `query_plan + Cypher`，再调用 Neo4j 检索图谱证据。当前通用基座模型在该节点存在如下问题：

1. **Cypher 语法不稳定**：生成结果存在语法错误，`Neo4j EXPLAIN` 无法通过。
2. **Schema 幻觉**：容易使用不存在的 label / relation / property。
3. **关系方向错误**：如把 `(:Cause)-[:CAUSES]->(:Phenomenon)` 反写。
4. **约束丢失**：漏掉组件过滤、返回字段约束、hop 约束等。
5. **多跳路径规划不稳**：在 `cause_trace`、`source_trace` 等任务中，路径长度和关系选择不合理。
6. **结果不利于后续链路消费**：返回字段不规范，影响 graph hits、reasoning path、source link 回显。

### 1.2 目标

本项目目标不是做通用问答微调，而是训练一个**面向图查询 Agent 的 Cypher 生成专用模型**，使其在给定：

- `user_query`（辅助）
- `parsed_question`（核心）
- `schema_context`（核心）
- `constraints`（核心）

的条件下，稳定输出：

- `query_plan`
- `cypher`

并在离线评测与系统 replay 中带来可量化收益。

### 1.3 成果目标（建议验收指标）

> 下面是建议目标值，不要求一次达到，但代码结构与评测逻辑必须支持这些指标。

- `Cypher syntax pass rate >= 90%`
- `Schema compliance >= 85%`
- `Execution success rate >= 80%`
- `Business logic accuracy >= 80%`
- `Graph retrieval hit rate` 相比基座模型明显提升
- `fallback trigger rate` 相比基座模型明显下降

---

## 2. 项目范围与非目标

### 2.1 范围

本项目只实现以下内容：

1. 从业务图谱 schema、规则表、任务模板出发，自动构造训练数据。
2. 基于 `Qwen2.5-Coder-3B-Instruct` 做 QLoRA 监督微调。
3. 基于 chosen/rejected preference pairs 做 DPO 偏好对齐。
4. 实现离线评测脚本。
5. 实现将微调模型挂回 Graph Reasoning Agent 的 replay 验证脚本。

### 2.2 非目标

1. 不实现完整问答系统前端。
2. 不实现项目一完整后端，只需要提供 replay 所需的最小集成。
3. 不要求接入真实业务文档正文；只需要图谱 schema、任务模板、规则表、实体词表即可。
4. 不要求训练 reward model，不做 PPO/RLHF。

---

## 3. 任务定义

### 3.1 模型输入

模型训练与推理输入统一为结构化任务对象：

```json
{
  "user_query": "液压泵泄漏的可能原因有哪些？",
  "parsed_question": {
    "question_type": "cause_trace",
    "entities": ["液压泵", "泄漏"],
    "relation_type": "possible_causes",
    "constraints": [],
    "need_multihop": true
  },
  "schema_context": {
    "node_types": {
      "Issue": ["issue_id"],
      "Phenomenon": ["canonical_name"],
      "Component": ["canonical_name"],
      "Cause": ["canonical_name"],
      "Action": ["canonical_name"],
      "Document": ["document_id"],
      "Chunk": ["chunk_id", "page_no", "section_path"]
    },
    "relation_types": [
      "(:Issue)-[:INVOLVES_COMPONENT]->(:Component)",
      "(:Cause)-[:CAUSES]->(:Phenomenon)",
      "(:Action)-[:MITIGATES]->(:Cause)",
      "(:Document)-[:CONTAINS]->(:Chunk)",
      "(:Chunk)-[:MENTIONS]->(:Cause)"
    ]
  },
  "constraints": {
    "max_hops": 2,
    "must_filter_component": true,
    "must_return": ["cause_name", "source_doc_ids"],
    "forbidden_patterns": ["unbounded_match", "full_graph_scan"]
  }
}
```

### 3.2 模型输出

```json
{
  "query_plan": {
    "target_nodes": ["Cause"],
    "required_relations": ["INVOLVES_COMPONENT", "CAUSES"],
    "filters": [
      "Component.canonical_name = 液压泵",
      "Phenomenon.canonical_name CONTAINS 泄漏"
    ],
    "max_hops": 2
  },
  "cypher": "MATCH ..."
}
```

### 3.3 任务类型（至少覆盖）

1. `cause_trace`：根因追溯
2. `action_lookup`：措施查询
3. `source_trace`：来源追溯
4. `multi_hop_root_cause`：多跳根因链
5. `validation_check`：验证/闭环查询

---

## 4. 技术选型

### 4.1 主技术栈

- Python 3.10+
- Neo4j（schema、EXPLAIN、执行验证）
- GPT-4o（teacher 数据生成）
- Hugging Face Datasets（数据集管理）
- Pydantic（结构化校验）
- Transformers（模型、tokenizer、generate）
- PEFT（LoRA/QLoRA adapter）
- bitsandbytes（4bit 量化）
- LLaMA-Factory（SFT / DPO 训练）
- FlashAttention-2（可选训练加速）

### 4.2 基座模型

- `Qwen2.5-Coder-3B-Instruct`

原因：

1. 偏代码/结构化生成，适合 Cypher。
2. 3B 对企业内部任务更合理，成本和延迟比 7B 更好。
3. 在强约束任务下，3B 配合 QLoRA 足够做能力验证。

### 4.3 Teacher 模型

- `GPT-4o`

原因：

1. Structured Outputs 稳定。
2. 长上下文支持较好，能吃 schema/context/rules/few-shot。
3. 可通过 Batch API 降低成本。

---

## 5. 目录结构建议

```text
cypher-agent-ft/
├── README.md
├── requirements.txt
├── .env.example
├── configs/
│   ├── schema.yaml
│   ├── rules.yaml
│   ├── task_templates.yaml
│   ├── sft.yaml
│   └── dpo.yaml
├── data/
│   ├── raw/
│   ├── intermediate/
│   ├── processed/
│   ├── sft/
│   └── dpo/
├── scripts/
│   ├── export_schema.py
│   ├── build_prompt_pool.py
│   ├── generate_candidates_gpt4o.py
│   ├── validate_candidates.py
│   ├── build_sft_dataset.py
│   ├── generate_sft_outputs.py
│   ├── build_dpo_dataset.py
│   ├── eval_offline.py
│   └── replay_eval.py
├── src/
│   ├── common/
│   │   ├── io.py
│   │   ├── logger.py
│   │   ├── utils.py
│   │   └── types.py
│   ├── schema/
│   │   ├── loader.py
│   │   ├── cutter.py
│   │   └── checker.py
│   ├── templates/
│   │   ├── task_sampler.py
│   │   └── instantiator.py
│   ├── teacher/
│   │   ├── prompt_builder.py
│   │   ├── client_openai.py
│   │   └── parser.py
│   ├── validation/
│   │   ├── pydantic_validator.py
│   │   ├── neo4j_validator.py
│   │   ├── schema_validator.py
│   │   └── business_validator.py
│   ├── datasets/
│   │   ├── sft_builder.py
│   │   ├── dpo_builder.py
│   │   └── formatter.py
│   ├── training/
│   │   ├── sft_runner.py
│   │   ├── dpo_runner.py
│   │   └── tokenizer_utils.py
│   ├── inference/
│   │   ├── generate.py
│   │   └── postprocess.py
│   └── eval/
│       ├── metrics.py
│       ├── offline_eval.py
│       └── replay_eval.py
└── outputs/
    ├── adapters/
    ├── merged/
    ├── logs/
    └── reports/
```

---

## 6. 数据构造阶段设计

### 6.1 输入资源来源

本项目假设没有真实业务文件正文，但有以下资源：

1. **全局业务图谱 Schema**
   - 节点类型、关系类型、属性名、关系方向
   - 来源：已有 Neo4j 图谱 / 手工维护 schema 配置
2. **任务模板**
   - 例如 cause_trace、source_trace 等任务定义
   - 来源：项目一在线链路中的 Graph 查询场景沉淀
3. **实体词表 / alias_map**
   - 例如“油泵 -> 液压泵”、“漏油 -> 泄漏”
4. **查询约束 / 风险规则**
   - 如 `max_hops`、必须过滤组件、必须返回来源字段、禁止全图扫描

### 6.2 导出全局 Schema

脚本：`scripts/export_schema.py`

输出建议：
- `configs/schema.yaml`
- `data/intermediate/global_schema.json`

内容至少包括：
- node types
- relation types
- property keys
- allowed directions

如可访问 Neo4j，可通过 APOC 或 meta 查询导出；如不可访问，允许直接维护静态 schema YAML。

### 6.3 任务模板定义

文件：`configs/task_templates.yaml`

```yaml
- task_type: cause_trace_with_component
  question_type: cause_trace
  relation_type: possible_causes
  need_multihop: true
  must_include_component: true
  required_relations:
    - INVOLVES_COMPONENT
    - CAUSES
  max_hops: 2

- task_type: source_trace
  question_type: source_trace
  relation_type: evidence_trace
  need_multihop: true
  required_relations:
    - CONTAINS
    - MENTIONS
  max_hops: 3
```

### 6.4 实例化训练输入

脚本：`scripts/build_prompt_pool.py`

流程：
1. 读取任务模板。
2. 从实体词表抽取实体实例。
3. 构造：
   - `user_query`
   - `parsed_question`
   - `constraints`
4. 从全局 schema 裁剪 task-specific `schema_context`。

说明：
- `user_query` 不依赖真实业务问题，可通过模板自然语言生成。
- 核心仍是 `parsed_question + schema_context + constraints`。

### 6.5 Teacher 生成候选样本

脚本：`scripts/generate_candidates_gpt4o.py`

输入：
- prompt pool
- GPT-4o API key

输出：
- 每个 prompt 生成 `2~3` 条候选 `query_plan + cypher`

建议：
- 使用 Batch API
- 输出格式强制为 JSON schema

### 6.6 候选样本校验

脚本：`scripts/validate_candidates.py`

四层校验：
1. **Pydantic 结构校验**：字段和类型是否正确
2. **Neo4j 语法校验**：`EXPLAIN <cypher>` 是否通过
3. **Schema 一致性检查**：label / relation / property / direction 是否合法
4. **业务规则回测**：是否命中 required relations、满足 hop 和返回字段约束

### 6.7 构建 synthetic SFT dataset

脚本：`scripts/build_sft_dataset.py`

对于每个 prompt：
1. 收集通过校验的候选
2. 按规则打综合分
3. 选出 **1 个最优候选** 作为 gold output

输出：
- `data/sft/train.jsonl`
- `data/sft/val.jsonl`
- `data/sft/test.jsonl`

### 6.8 构建 preference dataset

脚本：`scripts/build_dpo_dataset.py`

#### prompt 来源
- 与 SFT 同分布但独立于 SFT train split 的 held-out prompt pool
- 少量额外实例化 prompt

#### chosen 来源
- 该 prompt 对应的高质量 gold output
- 即 synthetic SFT dataset 中该 prompt 的最优答案

#### rejected 候选池来源
1. teacher 次优候选
2. SFT 模型真实错误输出
3. 规则扰动生成的 hard negatives

#### 注意
- 不是每个 prompt 固定保留 3 个 rejected
- 正确做法是：
  - 先构建 rejected 候选池
  - 再为每个 prompt 筛选 `1~2` 个最有代表性的 hard negatives

筛选规则：
- 优先保留“近似正确但业务上偏差明显”的 hard negatives
- 丢弃完全崩坏、无训练价值的垃圾输出

输出：
- `data/dpo/train.jsonl`
- `data/dpo/val.jsonl`
- `data/dpo/test.jsonl`

---

## 7. SFT 实现方案

### 7.1 目标

让模型学会在结构化图查询任务输入下，稳定生成：
- `query_plan`
- `cypher`

### 7.2 数据格式

将样本转换为 instruction tuning 格式：

```json
{
  "instruction": "根据给定的结构化问题、图谱 Schema 上下文和查询约束，生成 query_plan 和可执行的 Cypher。",
  "input": {...},
  "output": {...}
}
```

### 7.3 为什么这里不需要文本嵌入模型

SFT 训练阶段不需要 `bge-m3` 这类 embedding model。这里所谓“编码”是 tokenizer 将文本转成 token ids，不是将文本编码成检索向量。

### 7.4 预处理与 tokenization

脚本：`src/training/tokenizer_utils.py`

输出：
- `input_ids`
- `attention_mask`
- `labels`

### 7.5 QLoRA 说明

- **LoRA**：在关键线性层旁挂低秩 adapter，只训练新增参数
- **QLoRA**：将基座模型以 4bit 量化加载，再训练 LoRA adapter

一句话描述：
> 采用 QLoRA 方案，以 4bit 量化方式加载基座模型以降低显存占用，并在冻结主模型参数的基础上挂载 LoRA adapter 进行参数高效微调。

### 7.6 训练参数建议

基座模型：
- `Qwen2.5-Coder-3B-Instruct`

LoRA：
- `r = 64`
- `alpha = 128`
- `dropout = 0.05`
- target modules:
  - `q_proj`
  - `k_proj`
  - `v_proj`
  - `o_proj`
  - `gate_proj`
  - `up_proj`
  - `down_proj`

QLoRA：
- `load_in_4bit = true`
- `bnb_4bit_quant_type = nf4`
- `bnb_4bit_compute_dtype = bf16`

训练：
- `per_device_train_batch_size = 4`
- `gradient_accumulation_steps = 8`
- `global_batch_size = 32`
- `num_train_epochs = 3`
- `learning_rate = 2e-4`
- `lr_scheduler_type = cosine`
- `warmup_ratio = 0.03`
- `max_seq_length = 4096`
- `bf16 = true`
- `gradient_checkpointing = true`
- `eval_steps = 20`

### 7.7 为什么 `eval_steps = 20`

若 train set 为 1440 条、global batch size 为 32，则每个 epoch 约 45 个 optimizer steps。设成 `20` 可保证每个 epoch 评估约 2 次，既能及时观察 `val_loss` 与任务指标，又不会过于频繁。

### 7.8 SFT 训练流程

脚本：`src/training/sft_runner.py`

流程：
1. 加载 tokenizer
2. 加载 4bit 量化基座模型
3. 挂载 LoRA adapter
4. 读取 SFT dataset
5. 调用 LLaMA-Factory 执行 SFT
6. 每 `eval_steps=20` 在验证集上评估
7. 保存 checkpoint
8. 选择最优 checkpoint

### 7.9 SFT 阶段监控指标

框架自带：
- `train_loss`
- `val_loss`

任务指标（通过独立脚本在 val/test 上评测）：
- `Cypher syntax pass rate`
- `Schema compliance`
- `Execution success rate`
- `Business logic accuracy`

### 7.10 指标定义

- **Cypher syntax pass rate**：使用 `Neo4j EXPLAIN` 统计语法通过率
- **Schema compliance**：label/relation/property/direction 与 schema 一致的比例
- **Execution success rate**：在验证图快照上成功执行并返回结构正确结果的比例
- **Business logic accuracy**：基于任务模板规则和少量人工抽查判断是否满足业务逻辑

---

## 8. DPO 实现方案

### 8.1 目标

在 SFT 已让模型“会生成”的基础上，让模型进一步偏向：
- 更完整的过滤条件
- 更正确的关系方向
- 更合理的 hop 规划
- 更规范的返回字段
- 更适合后续 graph hits / source link / reasoning path 消费的结果

### 8.2 为什么 SFT 后还需要 DPO

SFT 只能让模型学习 gold output 的模式，但不会显式优化“两个都像样的结果里哪个更优”。DPO 解决的是偏好排序问题。

### 8.3 DPO 数据集来源

#### prompt
- 与 SFT 同分布的结构化 prompt
- 优先来自 held-out prompt pool 和额外实例化 prompt

#### chosen
- 该 prompt 对应的高质量 gold output
- 来自数据构造阶段最优样本

#### rejected 候选池
1. teacher 次优候选
2. SFT 模型真实错误输出
3. 规则扰动后的 hard negatives

### 8.4 如何获得 SFT 模型真实错误输出

脚本：`scripts/generate_sft_outputs.py`

技术：
- `Transformers.generate()` 或 `vLLM`

建议采样参数：
- `temperature = 0.7`
- `top_p = 0.9`
- `num_return_sequences = 2`

然后再跑：
- Pydantic 结构校验
- `Neo4j EXPLAIN`
- schema checker
- business validator

保留“近似正确但不够优”的输出作为 rejected 候选。

### 8.5 规则扰动 hard negatives

脚本：`src/datasets/dpo_builder.py`

扰动策略：
- 删除关键过滤条件
- 反转关系方向
- 改坏属性名
- 缩短 / 拉长 hop
- 改坏返回字段

### 8.6 rejected 最终筛选原则

- 不是每个 prompt 保留 3 个 rejected
- 每个 prompt 最多保留 `1~2` 个最有代表性的 hard negatives
- 优先保留：
  - 语法对
  - schema 大体对
  - 但业务逻辑明显差于 chosen

### 8.7 DPO 训练对象

继续沿用 QLoRA 路线：
- 4bit 量化加载基座模型
- 冻结基座模型参数
- 只更新 LoRA adapter 权重

### 8.8 policy / reference model

- `policy model`：SFT 后可训练模型
- `reference model`：SFT checkpoint 的冻结副本

### 8.9 DPO 原理（够实现即可）

对于每条 preference pair：
- 计算 `prompt + chosen`
- 计算 `prompt + rejected`
- 让当前 policy model 相比 reference model 更偏向 chosen

通俗解释：
- SFT 教“会做”
- DPO 教“更偏向哪个结果”

### 8.10 DPO 训练参数建议

- `per_device_train_batch_size = 2`
- `gradient_accumulation_steps = 8`
- `global_batch_size = 16`
- `num_train_epochs = 1`
- `learning_rate = 5e-7`
- `beta = 0.1`
- `max_seq_length = 4096`
- `bf16 = true`

### 8.11 DPO 训练流程

脚本：`src/training/dpo_runner.py`

流程：
1. 加载 SFT checkpoint 作为 policy model
2. 复制冻结 reference model
3. 加载 preference dataset
4. tokenize `prompt + chosen/rejected`
5. 计算 DPO loss
6. 反向传播
7. 只更新 LoRA adapter 参数
8. 保存最优 checkpoint

### 8.12 DPO 评测指标

- `preference accuracy`
- `Schema compliance`
- `Execution success rate`
- `Business logic accuracy`
- `Missing-filter ratio`
- `Over-broad query ratio`

---

## 9. 离线评测

脚本：`scripts/eval_offline.py`

输入：
- SFT / DPO 后模型
- held-out test set
- 图谱验证快照

输出：
- `outputs/reports/sft_eval.json`
- `outputs/reports/dpo_eval.json`

指标：
- syntax pass
- schema compliance
- execution success
- business logic accuracy
- preference accuracy（仅 DPO）

---

## 10. Replay 验证

### 10.1 目标

将微调后的模型挂回项目一中的 Graph Reasoning Agent，观察系统级收益。

### 10.2 replay query 来源

- 从项目一真实场景中抽样的 query 模板
- 或基于真实场景改写的 replay queries

建议数量：
- 50 条左右

### 10.3 replay 方式

脚本：`scripts/replay_eval.py`

流程：
1. Query Router 正常输出 `parsed_question`
2. 微调模型替换原 Graph Reasoning Agent，生成 `query_plan + cypher`
3. Neo4j 执行
4. 系统继续做 graph/vector/hybrid 检索、评估、回退
5. 统计系统级指标

### 10.4 系统级指标

- `Graph retrieval hit rate`
- `fallback trigger rate`
- `constraint violation rate`

---

## 11. 实现优先级

### Phase 1：最小可运行版本
1. 导出 schema
2. 任务模板实例化
3. GPT-4o 生成候选
4. 校验并构造 synthetic SFT dataset
5. 跑通 QLoRA SFT
6. 输出离线评测

### Phase 2：DPO
1. 生成 SFT 模型错误输出
2. 构建 rejected 候选池
3. 构建 preference dataset
4. 跑通 DPO
5. 输出离线评测

### Phase 3：replay
1. 将模型挂回 Graph Reasoning Agent
2. 跑 replay query
3. 输出系统级指标

---

## 12. Codex 实现要求

1. 所有脚本需可单独运行。
2. 每个阶段都输出中间产物，便于人工检查。
3. 数据文件统一用 JSONL。
4. 每个评测脚本都输出可读 report。
5. 对外部依赖（Neo4j、OpenAI API）提供 mock/本地替代接口抽象。
6. 所有关键逻辑都写清楚 docstring。
7. 不要把真实业务数据写死在代码里。

---

## 13. 交付物清单

最终至少应交付：

1. `README.md`
2. 数据构造脚本
3. SFT 训练脚本与配置
4. DPO 训练脚本与配置
5. 离线评测脚本
6. replay 验证脚本
7. 示例数据与示例报告

---

## 14. 一句话项目说明（给 Codex 的摘要）

请实现一个面向 GraphRAG 图查询 Agent 的 Cypher 生成模型优化项目：从业务图谱 Schema、任务模板和查询规则出发，自动构造 synthetic SFT dataset 与 preference dataset，基于 Qwen2.5-Coder-3B-Instruct 使用 QLoRA 完成 SFT，再用 DPO 完成偏好对齐，并通过离线评测和 replay 验证模型对图查询正确性、稳定性和系统级检索效果的提升。
