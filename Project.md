# GraphRAG Agent 系统设计文档（Codex 直用版）

## 1. 文档目标

本文档用于指导工程开发人员或 Codex 从 0 到 1 实现一个**面向航空质量问题溯因分析**的 GraphRAG Agent 系统。

本文档强调：

- 可直接落地的工程设计
- 清晰的模块边界
- 离线与在线阶段拆分
- 多智能体协作
- 记忆管理
- MCP 协议接入
- 风险控制与审计
- 可解释输出与证据追溯

本文档默认使用以下技术栈：

- Python
- FastAPI
- LangChain
- LangGraph
- Neo4j
- Milvus
- bge-m3
- MySQL
- PyMuPDF
- python-docx
- PaddleOCR
- pdfplumber
- Dify（可选）
- MCP（作为标准化工具接入层，可逐步引入）

---

## 2. 项目背景与目标

### 2.1 业务背景

本系统面向**航空制造与运维中的质量问题分析**场景，业务数据同时包含两大类来源。

#### 结构化数据

来自现有业务系统 API / Java 后端 / MySQL 表，例如：

- 质量问题记录
- 故障现象字段
- 部件信息
- 原因字段
- 措施字段
- 任务状态 / 闭环信息
- 问题编号 / 责任单位 / 时间字段

#### 非结构化数据

来自上传文件或指定目录，例如：

- 故障分析报告
- 技术评估报告
- 维修经验总结
- 整改措施文档
- PDF / Word / 扫描件 / 表格

业务需求不是简单“问答”，而是：

- 自动识别质量问题中的关键实体
- 检索相关历史知识和案例
- 追溯可能原因
- 给出维修或整改措施
- 输出可解释推理路径
- 支持高敏感场景下的风险控制和审计

### 2.2 为什么不是纯 RAG

纯 RAG 更适合 **chunk 级语义召回**，但当前场景具有以下特点：

- 故障现象、部件、原因、措施之间存在**显式关系**
- 需要 **多跳追溯**
- 需要 **可解释路径**
- 需要 **证据回溯**
- 需要支持 **结构化查询与关系约束**

因此系统采用 **GraphRAG**：

- **Milvus** 负责非结构化知识的语义召回
- **Neo4j** 负责显式关系建模、多跳推理和路径解释
- 二者结合支撑“语义召回 + 结构化推理”

### 2.3 系统目标

设计并实现一个具有以下能力的系统：

- 双源知识接入：结构化 + 非结构化
- 离线知识构建：解析、切分、抽取、装载
- 在线智能问答：路由、检索、推理、答案生成
- 多智能体协作：路由、检索、图推理、校验
- 记忆模块：工作记忆、语义记忆、情景记忆
- 风险控制：检索前限制、生成前校验、审计日志
- 可逐步引入 MCP 作为标准化工具接入层

---

## 3. 总体架构

### 3.1 分层设计

系统分为三条主线。

#### 1）离线阶段

负责把知识准备好：

- 双源数据接入
- 文档解析与语义分块
- 归一化与 schema 映射
- 向量 / 图谱双路装载
- 案例记忆沉淀

#### 2）在线阶段

负责把知识用起来：

- 用户提问
- 问题解析
- 检索意图路由
- 查询构建
- 执行检索
- 证据重排
- 结果评估
- 回退 / 补检
- 推理与答案生成

#### 3）多智能体协作

负责让在线流程模块化、角色化：

- Query Router Agent
- Retrieval Agent
- Graph Reasoning Agent
- Verification Agent

### 3.2 横切能力层

以下能力不单独成为主阶段，而是横切于离线 / 在线 / 多智能体之上：

- Prompt Engineering
- Context Engineering
- Memory Management
- MCP Tool Layer
- Risk Control
- Audit & Trace

### 3.3 架构图（文字版）

```text
                    ┌─────────────────────────────┐
                    │       External Sources      │
                    │  API / Docs / Reports / DB  │
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │       Offline Pipeline       │
                    │  parse / classify / chunk    │
                    │ normalize / extract / load   │
                    └───────┬────────────┬────────┘
                            │            │
                ┌───────────▼───┐   ┌───▼───────────┐
                │    Milvus     │   │    Neo4j      │
                │ vector memory │   │ graph memory  │
                └───────────┬───┘   └───┬───────────┘
                            │           │
                    ┌───────▼───────────▼──────────┐
                    │     Online LangGraph Flow     │
                    │ parse -> route -> retrieve    │
                    │ rerank -> verify -> answer    │
                    └───────┬───────────┬──────────┘
                            │           │
                    ┌───────▼───┐   ┌──▼────────────┐
                    │ FastAPI   │   │ Audit / Risk  │
                    │ API Layer │   │ Control Layer │
                    └───────────┘   └───────────────┘
````markdown
## 4. 技术选型与理由

### 4.1 Python

作为主开发语言，适合：

- LLM 应用开发
- RAG / GraphRAG
- 数据处理
- LangChain / LangGraph
- FastAPI 服务开发

### 4.2 FastAPI

用于：

- 文档上传
- 数据源配置
- 装载任务触发
- 在线问答接口
- 任务状态查询
- 审计查询接口

### 4.3 LangChain

用于：

- Prompt 模板
- Structured Output
- LLM 调用封装
- Embedding 调用
- 工具调用 glue code
- 检索器封装

### 4.4 LangGraph

用于：

- Agent 工作流编排
- 多节点状态流转
- 路由与分支控制
- 回退机制
- 多智能体协作

### 4.5 Milvus

用于：

- chunk 向量存储
- 案例摘要向量存储
- 自然语言语义召回
- metadata filter

选择理由：

- 适合承载非结构化文档切分后的文本知识单元
- 支持根据问题语义召回历史分析文本、措施文本、案例摘要
- 可结合 metadata 过滤文档类型、问题编号、chunk 类型等字段

### 4.6 Neo4j

用于：

- 现象 / 部件 / 原因 / 措施图谱
- 显式关系建模
- Cypher 查询
- 多跳推理
- 路径可解释输出

选择理由：

- 当前业务天然是关系网络
- 需要“现象 -> 部件 -> 原因 -> 措施”的路径追溯
- 需要把推理链可视化给前端

### 4.7 MySQL

用于：

- 用户 / 角色 / 权限
- 数据源配置
- 装载任务状态
- 文件元数据
- 审计日志
- 风险规则表
- 案例元数据

注意：

- 不把 MySQL 作为主推理库
- MySQL 更适合承载系统管理数据和审计数据

### 4.8 bge-m3

用于：

- query embedding
- chunk embedding
- case summary embedding

### 4.9 文档解析工具

用于非结构化文档解析：

- **PyMuPDF**：文本型 PDF
- **pdfplumber / camelot**：PDF 表格
- **python-docx**：Word 文档
- **PaddleOCR**：扫描件 OCR
- **Dify**：可选的文档解析能力接入

### 4.10 MCP（可选增强）

作为标准化工具接入层，统一暴露：

- Milvus 检索
- Neo4j 查询
- 案例记忆查询
- 装载任务
- 风险规则读取

定位：

- MCP 不替代 LangGraph
- MCP 不替代 RAG / GraphRAG
- MCP 主要承担**标准化工具接入层**

---

## 5. 业务域建模

### 5.1 核心实体

- `Issue`：质量问题
- `Phenomenon`：故障现象
- `Component`：部件
- `Cause`：原因
- `Action`：措施
- `Case`：历史案例
- `Document`：来源文档
- `Chunk`：文本知识单元

### 5.2 核心关系

- `Issue` -[HAS_PHENOMENON]-> `Phenomenon`
- `Issue` -[INVOLVES_COMPONENT]-> `Component`
- `Issue` -[HAS_CAUSE]-> `Cause`
- `Issue` -[HAS_ACTION]-> `Action`
- `Cause` -[CAUSES]-> `Phenomenon`
- `Action` -[MITIGATES]-> `Cause`
- `Action` -[HANDLES]-> `Phenomenon`
- `Case` -[SIMILAR_TO]-> `Issue`
- `Chunk` -[MENTIONS]-> `Component/Cause/Phenomenon/Action`
- `Document` -[CONTAINS]-> `Chunk`

### 5.3 本体统一要求

所有离线抽取结果入图前，必须映射为标准实体类型与标准关系类型，避免“抽到什么存什么”。

例如：

- `Phenomenon`
- `Component`
- `Cause`
- `Action`

以及：

- `CAUSES`
- `MITIGATES`
- `INVOLVES_COMPONENT`
- `HAS_ACTION`

---

## 6. 离线阶段设计

### 6.1 离线阶段目标

将结构化记录和非结构化文档转换为：

- 可向量召回的知识单元（Milvus）
- 可图谱推理的结构化知识（Neo4j）
- 可追溯的来源证据
- 可复用的案例记忆

### 6.2 数据来源

#### 6.2.1 结构化数据来源

来自业务系统 API / Java 模块 / MySQL 表：

- 问题编号
- 故障现象
- 部件信息
- 原因字段
- 措施字段
- 状态字段
- 闭环信息

#### 6.2.2 非结构化数据来源

来自上传文件或指定目录：

- PDF 报告
- Word 分析文档
- 扫描件
- 表格
- 维修经验总结

### 6.3 结构化链路

#### 6.3.1 输入

通过 FastAPI 触发 API 同步任务或批量导入任务。

#### 6.3.2 处理流程

```text
API 拉取 -> 字段清洗 -> 码表转换 -> 字段标准化 -> schema 映射 -> 图谱/向量双路装载
```

#### 6.3.3 清洗规则

包括但不限于：

- 空值清洗
- 别名归一
- 同义词映射
- 编号规范化
- 日期与状态字段规范化
- 重复记录合并

#### 6.3.4 输出

统一转换为标准 record：

```json
{
  "issue_id": "Q2025-001",
  "phenomenon": "液压泄漏",
  "component": ["液压泵"],
  "cause": ["密封圈老化"],
  "action": ["更换密封圈"],
  "source_type": "structured",
  "source_system": "quality_api",
  "load_batch_id": "batch_001"
}
```

### 6.4 非结构化链路

#### 6.4.1 目标

对不同类型质量问题文档进行结构保持解析，并输出适合后续 chunk 和装载的中间结构。

#### 6.4.2 文档类型分类

先做三类文档分类：

- `issue_record`
- `analysis_report`
- `action_report`

分类目的不是单纯贴标签，而是决定：

- 解析时优先保留什么
- 最终输出什么中间结构
- 后续采用什么抽取模板和装载方式

#### 6.4.3 文档分类策略

采用：

1. 规则分类
2. LLM 兜底分类

规则分类输入：

- 文件名
- 首页文本
- 标题关键词
- 表格列名

示例关键词：

```python
ISSUE_RECORD_KEYWORDS = ["问题编号", "故障现象", "责任单位", "发现时间", "影响范围"]
ANALYSIS_REPORT_KEYWORDS = ["原因分析", "根因", "问题分析", "结论", "评估"]
ACTION_REPORT_KEYWORDS = ["整改措施", "维修方案", "处理建议", "验证结果", "闭环"]
```

LLM 兜底输出使用 LangChain + Structured Output：

```json
{
  "doc_type": "analysis_report",
  "confidence": 0.87,
  "reason": "包含原因分析、结论、风险评估章节"
}
```

#### 6.4.4 文档解析策略

##### A. PDF 文本型

工具：

- PyMuPDF
- pdfplumber

输出：

- `page_no`
- `raw_text`
- `text_blocks`

##### B. Word 文档

工具：

- python-docx

输出：

- `heading`
- `paragraph`
- `table`
- `list_item`

##### C. 扫描件

工具：

- PaddleOCR

输出：

- OCR 文本
- 页码
- 图片说明文本（如可获取）

##### D. 表格

工具：

- pdfplumber / camelot
- python-docx

策略：

- 不直接 flatten 成一坨文本
- 先抽成结构化行记录
- 再转成标准文本表示

例如：

```text
部件：液压泵；故障现象：泄漏；潜在原因：密封圈老化；措施：更换密封圈。
```

#### 6.4.5 分类后的 parse 输出目标

##### issue_record

优先输出字段化文本：

```json
{
  "doc_type": "issue_record",
  "records": [
    {
      "issue_id": "Q2025-001",
      "phenomenon": "液压泄漏",
      "component": "液压泵",
      "action": "更换密封圈"
    }
  ]
}
```

##### analysis_report

优先输出章节化文本：

```json
{
  "doc_type": "analysis_report",
  "sections": [
    {
      "section_path": "3.原因分析",
      "content": "经排查发现密封圈老化..."
    }
  ]
}
```

##### action_report

优先输出步骤化文本：

```json
{
  "doc_type": "action_report",
  "steps": [
    {
      "step_no": 1,
      "content": "拆卸液压泵并检查密封圈磨损情况"
    }
  ],
  "validation": "复测正常"
}
```

### 6.5 语义分块（Chunking）

#### 6.5.1 原则

本项目不采用简单固定长度切分，而采用：

1. 标题边界优先
2. 业务语义单元优先
3. 长度约束作为兜底

#### 6.5.2 业务语义单元类型

- `phenomenon`
- `component`
- `cause_analysis`
- `action`
- `validation`
- `case_process`

#### 6.5.3 分块流程

##### Step 1：按标题切

- 标题正则
- MarkdownHeaderTextSplitter（可选）

##### Step 2：按业务语义单元切

通过：

- 标题关键词规则
- LangChain Structured Output 标注 `chunk_type`

##### Step 3：长度约束

对过长块再用 RecursiveCharacterTextSplitter 细分。

### 6.6 chunk metadata

每个 chunk 必须带完整 metadata：

```json
{
  "chunk_id": "chunk_001",
  "document_id": "doc_001",
  "doc_type": "analysis_report",
  "section_path": "3.原因分析",
  "chunk_type": "cause_analysis",
  "page_no": 4,
  "issue_id": "Q2025-001",
  "component": ["液压泵", "密封圈"],
  "source_type": "unstructured",
  "load_batch_id": "batch_001"
}
```

这些 metadata 后续用于：

- Milvus 过滤
- Neo4j 来源追踪
- 在线证据回显
- 风控范围控制
- 审计追踪

### 6.7 装载（Loading）

#### 6.7.1 装载的定义

装载不是简单入库，而是将中间文本 / record 转换为：

- 可向量检索的知识对象
- 可图谱推理的知识对象
- 可追溯的来源对象

#### 6.7.2 双路装载

##### 路 1：Milvus

输入：

- chunk
- case summary
- record text

过程：

- 通过 bge-m3 生成 embedding
- 写入 Milvus
- 保留 metadata

##### 路 2：Neo4j

输入：

- record
- chunk

过程：

- 用 Structured Output 抽取：
  - entities
  - relations
  - attributes
- 入图：
  - node
  - edge
  - property
  - source link

#### 6.7.3 统一 schema 映射

所有抽取结果入图前必须先映射到统一领域 schema：

- 现象 -> `Phenomenon`
- 部件 -> `Component`
- 原因 -> `Cause`
- 措施 -> `Action`

关系映射例如：

- 导致 -> `CAUSES`
- 处理 -> `HANDLES`
- 缓解 -> `MITIGATES`

#### 6.7.4 归一化与去重

包括：

- 同义词归一：泄露 / 泄漏
- 名称规范化：部件简称 / 全称
- 单位统一：温度、时间、编号
- 重复实体合并
- 重复关系合并

#### 6.7.5 来源追溯

每条知识必须保留：

- source_type
- source_id
- document_id
- page_no
- section_path
- issue_id
- load_batch_id

#### 6.7.6 案例记忆沉淀

从高质量分析链中沉淀案例：

```json
{
  "case_id": "case_001",
  "issue_type": "液压泄漏",
  "entities": ["液压泵", "密封圈"],
  "root_cause_chain": ["密封圈老化", "材料耐温不足"],
  "actions": ["更换密封圈", "增加高温测试"],
  "source_docs": ["doc_001", "doc_003"]
}
```

### 6.8 离线任务管理

#### 6.8.1 任务类型

- API 同步任务
- 文档解析任务
- chunk 生成任务
- 向量装载任务
- 图谱装载任务
- 案例沉淀任务

#### 6.8.2 任务状态

- pending
- running
- success
- failed

#### 6.8.3 失败重试

支持：

- 单文档重试
- 单批次重试
- 指定阶段重跑（解析 / 切分 / 装载）

---

## 7. 在线阶段设计

### 7.1 在线阶段目标

当用户提问时，系统需要：

- 解析问题
- 识别实体与意图
- 选择合适检索策略
- 执行检索
- 进行证据重排
- 进行证据充分性评估
- 必要时回退补检
- 输出答案、证据和推理路径

### 7.2 在线阶段主链路

```text
用户提问
-> 问题解析
-> 检索策略路由
-> 查询构建
-> 执行检索
-> 检索重排
-> 结果评估
-> 质量回退/补检
-> 推理与答案生成
-> 可解释输出
```

### 7.3 问题解析

#### 7.3.1 技术

- LangChain PromptTemplate
- LangChain Structured Output
- LLM

#### 7.3.2 输出 schema

```json
{
  "question_type": "cause_trace",
  "entities": ["液压泵", "泄漏"],
  "relation_type": "possible_causes",
  "constraints": [],
  "need_multihop": true,
  "retrieval_strategy": "hybrid"
}
```

### 7.4 检索策略路由

#### 7.4.1 路由方式

采用：

- 规则 / 特征初筛
- LLM 结构化路由
- 结果不足时回退

#### 7.4.2 三类检索策略

##### A. graph

适用于：

- 实体明确
- 关系明确
- 目标清晰

例如：

- 某现象的原因有哪些？
- 某原因对应哪些措施？

##### B. vector

适用于：

- 经验类问题
- 模糊描述
- 找类似案例
- 找报告描述

##### C. hybrid

适用于：

- 既需要语义召回，又需要结构化关系
- 需要多跳追溯
- 需要图路径和文本证据同时支撑
````
### 7.5 查询构建

#### 7.5.1 graph 查询构建

根据结构化问题对象生成：

- Cypher 模板
- max_hops
- relation filters

#### 7.5.2 vector 查询构建

生成：

- query_text
- embedding query
- metadata_filter
- top_k
- target_chunk_type

#### 7.5.3 hybrid 查询构建

同时准备：

- 向量召回参数
- 图扩展约束
- 重排参数

### 7.6 执行检索

#### 7.6.1 Milvus 检索

检索对象：

- chunk
- case summary
- 可选实体描述

#### 7.6.2 Neo4j 检索

执行：

- Cypher 查询
- 邻接节点扩展
- 多跳关系路径查询

#### 7.6.3 混合检索

流程：

- 先从 Milvus 召回候选文本 / 候选实体
- 再以候选实体为中心在 Neo4j 中扩展
- 最后做统一重排

### 7.7 检索重排（Rerank）

#### 7.7.1 目的

统一比较不同来源证据：

- 文本 chunk
- 图路径
- 案例摘要

#### 7.7.2 打分项

建议综合：

- `semantic_score`
- `entity_coverage`
- `relation_match`
- `graph_confidence`
- `doc_type_bonus`
- `hop_penalty`

#### 7.7.3 示例公式

```text
final_score =
  semantic_score
+ entity_coverage
+ relation_match
+ graph_confidence
+ doc_type_bonus
- hop_penalty
```

### 7.8 结果评估

#### 7.8.1 评估目标

判断当前证据是否足以支持答案生成。

#### 7.8.2 规则检查

- evidence_count
- max_score
- path_count
- key_entity_covered
- target_relation_hit

#### 7.8.3 LLM 校验

可用 Structured Output 输出：

```json
{
  "is_sufficient": true,
  "conflict_detected": false,
  "missing_part": [],
  "fallback_mode": "none"
}
```

### 7.9 质量回退 / 补检

#### 7.9.1 回退规则

- graph 无结果 -> vector
- vector 证据过散 -> graph 扩展
- hybrid 证据不足 -> 放宽约束后补检
- 高风险且证据不足 -> 保守回答

### 7.10 推理与答案生成

#### 7.10.1 输入

- 文本证据
- 图路径
- 案例记忆（可选）
- 风控结果

#### 7.10.2 输出

- 最终答案
- 核心原因链
- 维修措施
- 推理路径
- 证据来源

### 7.11 可解释输出

返回结构建议：

```json
{
  "answer": "可能原因包括密封圈老化和材料耐温不足。",
  "reasoning_path": [
    "液压泄漏 -> 液压泵",
    "液压泵 -> 密封圈老化",
    "密封圈老化 -> 液压泄漏"
  ],
  "evidence": [
    {
      "document_id": "doc_001",
      "page_no": 4,
      "section_path": "3.原因分析",
      "chunk_id": "chunk_001"
    }
  ],
  "risk_level": "medium"
}
```

---

## 8. 多智能体设计

### 8.1 为什么要多智能体

将在线阶段拆成多角色协作，更利于：

- 边界清晰
- 调试方便
- 风险隔离
- 后续 MCP tool 接入

### 8.2 Agent 角色

#### 8.2.1 Query Router Agent

职责：

- 解析问题
- 提取实体与关系
- 判断 graph / vector / hybrid
- 风险初判

#### 8.2.2 Retrieval Agent

职责：

- 调用 Milvus / case memory
- 返回候选文本证据
- 做基础 metadata 过滤

#### 8.2.3 Graph Reasoning Agent

职责：

- 生成 Cypher
- 调用 Neo4j
- 做多跳路径扩展

#### 8.2.4 Verification Agent

职责：

- 证据融合
- 证据充分性判断
- 风险校验
- 决定正常输出 / 保守输出 / 回退

### 8.3 协作方式

通过 **LangGraph** 实现，不是 agent 自由闲聊，而是：

- 每个 agent 对应一个 node
- 共享同一个 state
- edge 决定下一个执行节点

---

## 9. 记忆管理设计

### 9.1 Working Memory

#### 作用

当前会话内的短期状态。

#### 存储方式

- LangGraph state

#### 内容

- question
- entities
- relation_type
- retrieval_strategy
- vector_hits
- graph_hits
- reasoning_path
- risk_level

### 9.2 Semantic Memory

#### 作用

长期领域知识。

#### 存储方式

- Neo4j：图谱
- Milvus：chunk 向量 / case 向量
- MySQL：规则表 / 词表 / schema 元信息

### 9.3 Episodic Memory

#### 作用

历史案例记忆。

#### 存储方式

- MySQL：案例元数据
- Milvus：案例摘要向量
- Neo4j：案例关系链

#### 用法

在线阶段先检索相似 case，再补充实时检索。

### 9.4 Perceptual Memory

#### 当前定位

非核心，可作为后续扩展。

当前项目中更适合作为：

- OCR / 图片说明文本化后的补充知识

而非独立主记忆模块。

### 9.5 记忆是否 tool 化

- Working Memory：不 tool 化，直接放在 LangGraph state
- Semantic / Episodic Memory：可封装为内部服务或 MCP tool

例如：

- `search_case_memory`
- `read_schema_resource`
- `lookup_component_alias`

---

## 10. MCP 协议接入设计（可选增强）

### 10.1 MCP 定位

MCP 不负责主流程编排，而负责：

**标准化工具接入层**

#### 边界

- LangGraph：编排
- LangChain：模型 / prompt / structured output
- MCP：工具与资源协议层

### 10.2 适合暴露为 MCP tools 的能力

- `search_vector_evidence`
- `query_graph`
- `expand_reasoning_path`
- `search_case_memory`
- `start_ingestion_job`
- `get_ingestion_status`
- `read_audit_trace`
- `load_risk_rules`

### 10.3 适合暴露为 MCP resources 的内容

- 图谱 schema
- 术语词表
- 风险规则
- 文档目录
- 案例索引

### 10.4 适合暴露为 MCP prompts 的内容

- 根因分析提示模板
- 措施建议生成模板
- 高风险问题保守输出模板

### 10.5 引入收益

- 减少各 agent 重复手写数据库适配器
- 将底层工具调用统一标准化
- 降低 agent 层与数据库层耦合
- 更易扩展到其他宿主 / 平台

---

## 11. Prompt Engineering 设计

### 11.1 典型 prompt 类型

#### 离线阶段

- 文档分类 prompt
- chunk 语义标注 prompt
- 实体关系抽取 prompt
- case summary 生成 prompt

#### 在线阶段

- 问题解析 prompt
- 逻辑形式生成 prompt
- 路由判断 prompt
- 证据校验 prompt
- 高风险保守输出 prompt

### 11.2 设计原则

- 统一输出 schema
- 尽量采用 Structured Output
- 不允许自由格式结果进入关键流程
- 对高风险问题使用专用保守 prompt

---

## 12. Context Engineering 设计

### 12.1 离线阶段体现

- 文档结构保持
- 业务语义分块
- 完整 metadata
- chunk 类型标注
- schema 映射

### 12.2 在线阶段体现

- 证据融合
- 统一重排
- 上下文裁剪
- 风险过滤
- 结构化 evidence packing

## 13. 风险控制设计

### 13.1 风险分类

#### 信息风险

- 检索越权
- 敏感文档泄露
- 不该看到的证据被召回

#### 推理风险

- 证据不足却输出确定性结论
- 图路径错误却输出看似合理的答案
- 混合检索把不相关证据拼成伪因果链

#### 决策风险

- 措施建议未 grounding
- 输出不可追溯
- 高风险问题给出过于确定的建议

### 13.2 检索前风控

#### 输入

- 用户问题
- 命中实体
- 用户权限
- 风险规则

#### 输出

```json
{
  "risk_level": "high",
  "allowed_scope": ["quality_reports_internal"],
  "need_human_review": false
}
```

#### 应用方式

- 限制 Milvus metadata filter
- 限制 Neo4j 查询范围
- 高敏问题只允许返回摘要
- 对部分问题限制图扩展跳数

### 13.3 生成前风控

#### 检查项

- 证据充分性
- grounding
- 冲突检测
- 允许返回粒度

#### 输出

```json
{
  "is_grounded": true,
  "confidence_level": "medium",
  "can_return_full_answer": false,
  "fallback_mode": "summary_only"
}
```

#### 应用方式

- 证据不足时输出保守答案
- 存在冲突时输出“可能原因集合”
- 高风险场景只输出经过证据支持的最小结论

### 13.4 审计日志

每次问答记录：

- question
- trace_id
- route
- evidence ids
- risk level
- final answer
- fallback mode
- reviewer status

---

## 14. 数据存储设计

### 14.1 MySQL 表设计（建议）

#### users

- id
- username
- role
- permission_scope

#### documents

- document_id
- file_name
- file_type
- doc_type
- upload_time
- source_type
- source_system
- parse_status

#### ingestion_jobs

- job_id
- source_type
- batch_id
- status
- created_at
- finished_at
- error_message

#### chunks

- chunk_id
- document_id
- doc_type
- chunk_type
- section_path
- page_no
- issue_id
- content
- load_batch_id

#### cases

- case_id
- issue_type
- summary
- root_cause_chain_json
- actions_json
- source_docs_json

#### audit_logs

- trace_id
- user_id
- question
- route
- risk_level
- final_answer
- created_at

#### risk_rules

- rule_id
- rule_type
- content
- level
- enabled

### 14.2 Neo4j 节点标签

- Issue
- Phenomenon
- Component
- Cause
- Action
- Case
- Document
- Chunk

### 14.3 Milvus collection 建议

#### knowledge_chunks

字段：

- id
- embedding
- content
- doc_type
- chunk_type
- issue_id
- document_id
- page_no
- section_path

#### case_memory

字段：

- id
- embedding
- summary
- issue_type
- entities
- source_case_id

---

## 15. FastAPI 接口设计

### 15.1 离线阶段接口

#### 上传文档

`POST /api/v1/documents/upload`

#### 创建装载任务

`POST /api/v1/ingestion/start`

#### 查询装载任务状态

`GET /api/v1/ingestion/{job_id}`

#### 重试装载任务

`POST /api/v1/ingestion/{job_id}/retry`

#### 同步结构化数据

`POST /api/v1/sync/structured`

### 15.2 在线问答接口

#### 问答

`POST /api/v1/qa/ask`

请求示例：

```json
{
  "question": "液压泵泄漏的可能原因有哪些？",
  "conversation_id": "conv_001",
  "user_id": "u001"
}
```

#### 查询问答 trace

`GET /api/v1/qa/trace/{trace_id}`

#### 查询审计记录

`GET /api/v1/audit/logs`

### 15.3 案例记忆接口

#### 查询相似案例

`POST /api/v1/cases/search`

#### 查看案例详情

`GET /api/v1/cases/{case_id}`

---

## 16. LangGraph 工作流设计

### 16.1 State 定义（示例）

```python
from typing import TypedDict, List, Dict, Any

class QAState(TypedDict, total=False):
    trace_id: str
    user_id: str
    conversation_id: str
    question: str

    question_type: str
    entities: List[str]
    relation_type: str
    constraints: List[str]
    need_multihop: bool
    retrieval_strategy: str

    risk_level: str
    allowed_scope: List[str]

    query_embedding: List[float]
    cypher_query: str

    vector_hits: List[Dict[str, Any]]
    graph_hits: List[Dict[str, Any]]
    retrieved_evidence: List[Dict[str, Any]]
    reranked_evidence: List[Dict[str, Any]]

    reasoning_path: List[Dict[str, Any]]
    is_sufficient: bool
    conflict_detected: bool
    fallback_mode: str

    final_answer: str
    answer_payload: Dict[str, Any]
```

### 16.2 节点设计

- `parse_question`
- `risk_precheck`
- `route_retrieval`
- `build_query`
- `retrieve_vector`
- `retrieve_graph`
- `retrieve_hybrid`
- `rerank_evidence`
- `verify_evidence`
- `fallback_retrieve`
- `generate_answer`
- `audit_trace`

### 16.3 条件边示例

- parse_question -> risk_precheck
- risk_precheck -> route_retrieval
- route_retrieval -> retrieve_vector / retrieve_graph / retrieve_hybrid
- retrieve_* -> rerank_evidence
- rerank_evidence -> verify_evidence
- verify_evidence -> generate_answer / fallback_retrieve
- generate_answer -> audit_trace

---

## 17. 多智能体 + MCP 组合方式

### 17.1 不引入 MCP 的实现方式

LangGraph node 内直接调用：

- Milvus client
- Neo4j driver
- MySQL DAO

优点：

- 快速开发
- 依赖简单

缺点：

- 工具层耦合高
- 不利于复用

### 17.2 引入 MCP 的实现方式

LangGraph node 不直接操作 SDK，而通过 MCP client 调：

- `search_vector_evidence`
- `query_graph`
- `search_case_memory`
- `load_risk_rules`

优点：

- 标准化工具层
- 更利于复用与扩展
- 更适合后续平台化

---

## 18. 目录结构建议

```text
graphrag-agent/
├── app/
│   ├── main.py
│   ├── api/
│   │   ├── routes_documents.py
│   │   ├── routes_ingestion.py
│   │   ├── routes_qa.py
│   │   ├── routes_cases.py
│   │   └── routes_audit.py
│   ├── core/
│   │   ├── config.py
│   │   ├── logging.py
│   │   ├── db_mysql.py
│   │   ├── db_neo4j.py
│   │   ├── db_milvus.py
│   │   └── security.py
│   ├── domain/
│   │   ├── schemas.py
│   │   ├── ontology.py
│   │   └── enums.py
│   ├── offline/
│   │   ├── ingest_structured.py
│   │   ├── ingest_unstructured.py
│   │   ├── document_classifier.py
│   │   ├── parsers/
│   │   │   ├── pdf_parser.py
│   │   │   ├── word_parser.py
│   │   │   ├── ocr_parser.py
│   │   │   └── table_parser.py
│   │   ├── chunking.py
│   │   ├── extraction.py
│   │   ├── normalization.py
│   │   ├── loaders/
│   │   │   ├── milvus_loader.py
│   │   │   ├── neo4j_loader.py
│   │   │   └── case_loader.py
│   │   └── tasks.py
│   ├── online/
│   │   ├── workflow.py
│   │   ├── router.py
│   │   ├── query_builder.py
│   │   ├── retrieve_vector.py
│   │   ├── retrieve_graph.py
│   │   ├── retrieve_hybrid.py
│   │   ├── rerank.py
│   │   ├── verifier.py
│   │   ├── reasoning.py
│   │   └── answer_generator.py
│   ├── memory/
│   │   ├── working_memory.py
│   │   ├── semantic_memory.py
│   │   ├── episodic_memory.py
│   │   └── case_memory.py
│   ├── risk/
│   │   ├── risk_classifier.py
│   │   ├── risk_rules.py
│   │   ├── grounding_checker.py
│   │   └── audit.py
│   ├── prompts/
│   │   ├── classify_doc.txt
│   │   ├── extract_entities.txt
│   │   ├── parse_question.txt
│   │   ├── route_retrieval.txt
│   │   ├── verify_evidence.txt
│   │   └── safe_answer.txt
│   ├── mcp/
│   │   ├── server.py
│   │   ├── tools_vector.py
│   │   ├── tools_graph.py
│   │   ├── tools_cases.py
│   │   ├── resources_schema.py
│   │   └── prompts_registry.py
│   └── utils/
│       ├── text_utils.py
│       ├── metadata_utils.py
│       ├── alias_map.py
│       └── retry.py
├── tests/
├── scripts/
├── docker/
├── requirements.txt
└── README.md
```
## 19. 实施优先级（建议分阶段开发）

### Phase 1：最小可运行版本

目标：先跑通主链路

- FastAPI 基础接口
- 文档上传
- PDF / Word 解析
- 基础 chunk
- bge-m3 + Milvus 入库
- Neo4j 基础入图
- LangChain 问题解析
- LangGraph 单流程问答链

### Phase 2：增强检索与可解释

- graph / vector / hybrid 路由
- 重排
- Cypher 模板
- 多跳路径查询
- 来源追溯返回

### Phase 3：多智能体与记忆

- Router Agent
- Retrieval Agent
- Graph Reasoning Agent
- Verification Agent
- 会话记忆
- 案例记忆

### Phase 4：风控与审计

- 风险规则
- 检索前风控
- 生成前校验
- 审计 trace
- 保守输出

### Phase 5：MCP 协议层与平台化

- 将 Milvus 检索、Neo4j 查询、案例记忆、风险规则查询封装为 MCP tools
- 暴露 schema、术语表、风险规则为 MCP resources
- 暴露分析模板、保守输出模板为 MCP prompts
- 支持 LangGraph 节点通过 MCP client 调用工具层
- 为后续多宿主接入（Web / IDE / 内部平台）预留能力

---

## 20. 非功能性要求

### 20.1 可解释性

系统输出必须能够回溯到：

- 原始文档
- 原始页码
- 原始 chunk
- 图谱路径
- 检索策略
- 风险等级

### 20.2 可审计性

每次问答必须记录：

- trace_id
- 问题内容
- 会话 ID
- 用户 ID / 角色
- 路由策略
- 检索证据 ID 列表
- 最终输出
- 风险等级
- 是否触发回退
- 是否需要人工复核

### 20.3 可维护性

- 模块边界清晰
- Prompt 与代码分离
- 风险规则表可配置
- schema / ontology 可扩展
- chunk 规则和抽取模板可版本化

### 20.4 安全性

- 敏感问题只允许在授权范围内检索
- 风险节点支持保守输出
- 不允许无证据的强结论直接透出
- 审计日志不可缺失

### 20.5 性能要求（建议目标）

- 单次问答响应时间：3~8 秒内（依赖模型和索引规模）
- 检索阶段尽量控制 Top-K 与图扩展范围
- 对高频 schema/resource 采用缓存
- 离线装载支持批量处理与重试

---

## 21. 验收标准

### 21.1 离线阶段验收

#### 文档接入

- 支持 PDF / DOCX 上传
- 支持结构化 API 同步
- 能正确保存 documents 元数据

#### 文档解析

- 文本型 PDF 能解析正文和页码
- DOCX 能保留标题和表格
- 扫描件可通过 OCR 输出可读文本

#### 文档分类

- 至少支持 issue_record / analysis_report / action_report 三类
- 支持规则分类
- 支持 LLM 兜底分类

#### chunk

- 至少支持现象 / 原因 / 措施三类 chunk_type
- chunk 能保留 document_id / page_no / section_path / issue_id 等 metadata

#### 装载

- chunk 能写入 Milvus
- 实体关系能写入 Neo4j
- 支持 case memory 生成与存储
- 装载任务有状态记录

### 21.2 在线阶段验收

#### 问题解析

- 能输出结构化问题对象
- 至少识别 question_type / entities / relation_type / retrieval_strategy

#### 路由

- 能在 graph / vector / hybrid 三类策略中切换
- 路由逻辑支持规则 + LLM 结合

#### 检索

- Milvus 检索链可用
- Neo4j 图查询链可用
- hybrid 检索链可用

#### 重排

- 能对不同来源证据统一打分
- 能输出 reranked_evidence

#### 评估与回退

- 能判断证据是否足够
- 图查为空时可回退到向量检索
- 向量召回不足时可补图扩展

#### 输出

- 返回答案
- 返回证据来源
- 返回推理路径
- 返回 risk_level / fallback_mode（如有）

### 21.3 多智能体验收

- LangGraph 中至少存在 4 个角色节点：
  - Query Router Agent
  - Retrieval Agent
  - Graph Reasoning Agent
  - Verification Agent
- 节点间通过共享 state 协作
- 能看到完整 trace

### 21.4 风控验收

- 检索前能做风险初判
- 检索范围可按规则过滤
- 生成前可做 grounding / conflict 检查
- 高风险问题可降级为摘要输出
- 审计日志完整

---

## 22. 关键模块实现建议

### 22.1 document_classifier.py

职责：

- 接收文件名、首页内容、标题、表格列名
- 先规则分类
- 再使用 LLM 兜底分类
- 输出 `doc_type`

建议函数：

```python
def classify_document(
    file_name: str,
    first_page_text: str,
    headings: list[str],
    table_headers: list[str]
) -> dict:
    ...
```

输出示例：

```json
{
  "doc_type": "analysis_report",
  "confidence": 0.87,
  "source": "rule+llm"
}
```

---

### 22.2 chunking.py

职责：

- 按标题切
- 按业务语义单元切
- 按长度约束做二次切分
- 输出标准 chunk 对象

建议函数：

```python
def build_chunks(parsed_doc: dict) -> list[dict]:
    ...
```

输出示例：

```json
{
  "chunk_id": "chunk_001",
  "doc_type": "analysis_report",
  "chunk_type": "cause_analysis",
  "section_path": "3.原因分析",
  "content": "经排查发现密封圈老化..."
}
```

---

### 22.3 extraction.py

职责：

- 使用 Structured Output 对 chunk / record 做实体关系抽取
- 输出统一 schema

建议函数：

```python
def extract_entities_relations(text: str, doc_type: str) -> dict:
    ...
```

输出示例：

```json
{
  "entities": [
    {"name": "液压泵", "type": "Component"},
    {"name": "密封圈老化", "type": "Cause"},
    {"name": "液压泄漏", "type": "Phenomenon"}
  ],
  "relations": [
    {"source": "密封圈老化", "type": "CAUSES", "target": "液压泄漏"},
    {"source": "液压泵", "type": "INVOLVES", "target": "液压泄漏"}
  ]
}
```

---

### 22.4 milvus_loader.py

职责：

- 对 chunk / case summary 生成 embedding
- 写入 Milvus
- 保留 metadata

建议函数：

```python
def load_chunks_to_milvus(chunks: list[dict]) -> None:
    ...
```

---

### 22.5 neo4j_loader.py

职责：

- 将抽取结果写入 Neo4j
- 做实体合并
- 做关系去重
- 绑定来源信息

建议函数：

```python
def load_graph_data(records: list[dict], relations: list[dict]) -> None:
    ...
```

---

### 22.6 router.py

职责：

- 接收问题解析结果
- 结合规则与 LLM 结构化输出
- 决定走 graph / vector / hybrid

建议函数：

```python
def route_retrieval(state: dict) -> dict:
    ...
```

输出示例：

```json
{
  "retrieval_strategy": "hybrid",
  "reason": "问题包含明确实体且需要多跳追溯"
}
```

---

### 22.7 query_builder.py

职责：

- 根据 state 生成具体检索参数
- graph：Cypher 模板 + 参数
- vector：query_text + filter + top_k
- hybrid：同时生成两类参数

建议函数：

```python
def build_query_plan(state: dict) -> dict:
    ...
```

---

### 22.8 retrieve_vector.py

职责：

- 生成 query embedding
- 调 Milvus
- 返回候选 chunk / case summary

建议函数：

```python
def retrieve_vector_evidence(state: dict) -> dict:
    ...
```

---

### 22.9 retrieve_graph.py

职责：

- 构建 Cypher
- 调 Neo4j
- 返回路径 / 节点 / 边

建议函数：

```python
def retrieve_graph_evidence(state: dict) -> dict:
    ...
```

---

### 22.10 rerank.py

职责：

- 对不同来源证据统一排序
- 支持 graph + vector + case 混合证据

建议函数：

```python
def rerank_evidence(state: dict) -> dict:
    ...
```

伪代码：

```python
score = (
    semantic_score
    + entity_coverage
    + relation_match
    + graph_confidence
    + doc_type_bonus
    - hop_penalty
)
```

---

### 22.11 verifier.py

职责：

- 判断证据是否充分
- 判断是否存在冲突
- 决定回退 / 保守输出 / 正常输出

建议函数：

```python
def verify_evidence(state: dict) -> dict:
    ...
```

输出示例：

```json
{
  "is_sufficient": false,
  "conflict_detected": true,
  "fallback_mode": "summary_only"
}
```

---

### 22.12 answer_generator.py

职责：

- 结合 reranked_evidence、reasoning_path、risk_level 生成最终回答
- 输出 answer + evidence + trace

建议函数：

```python
def generate_final_answer(state: dict) -> dict:
    ...
```

---

## 23. 示例 Prompt 设计

### 23.1 问题解析 Prompt

目标：

- 抽取实体
- 判断问题类型
- 判断关系类型
- 判断是否需要多跳
- 判断推荐检索策略

输出 schema：

```json
{
  "question_type": "cause_trace",
  "entities": [],
  "relation_type": "",
  "constraints": [],
  "need_multihop": false,
  "retrieval_strategy": "graph"
}
```

---

### 23.2 文档分类 Prompt

目标：

- 在规则分不清时判断文档类型
- 输出 doc_type + confidence + reason

输出 schema：

```json
{
  "doc_type": "analysis_report",
  "confidence": 0.87,
  "reason": ""
}
```

---

### 23.3 实体关系抽取 Prompt

目标：

- 从 chunk 中抽取实体、关系、属性
- 映射到统一 schema

输出 schema：

```json
{
  "entities": [],
  "relations": []
}
```

---

### 23.4 风险校验 Prompt

目标：

- 判断当前答案是否 grounding
- 判断证据是否充分
- 判断是否需要降级输出

输出 schema：

```json
{
  "is_grounded": true,
  "confidence_level": "medium",
  "can_return_full_answer": false,
  "fallback_mode": "summary_only"
}
```

---

## 24. 示例 Cypher 设计

### 24.1 根据现象查原因

```cypher
MATCH (p:Phenomenon {name: $phenomenon})<-[:CAUSES]-(c:Cause)
RETURN c.name
LIMIT 10
```

### 24.2 根据原因查措施

```cypher
MATCH (a:Action)-[:MITIGATES]->(c:Cause {name: $cause})
RETURN a.name
LIMIT 10
```

### 24.3 多跳根因路径查询

```cypher
MATCH path = (p:Phenomenon {name: $phenomenon})<-[:CAUSES*1..3]-(c:Cause)
RETURN path
LIMIT 20
```

---

## 25. 示例 MCP Tool 设计

### 25.1 search_vector_evidence

输入：

- query
- filters
- top_k

输出：

- candidate evidence list

### 25.2 query_graph

输入：

- cypher
- params

输出：

- graph result / path list

### 25.3 search_case_memory

输入：

- issue_type
- component
- top_k

输出：

- case summary list

### 25.4 start_ingestion_job

输入：

- source_type
- payload

输出：

- job_id
- initial status

---

## 26. 开发注意事项

### 26.1 不要把 chunk 直接等同于知识

chunk 只是离线中间结果，必须经过：

- embedding / Milvus 装载
- Structured Output / Neo4j 建图
- metadata 绑定
- 来源映射

之后才算知识对象。

### 26.2 不要把图谱当成全文检索引擎

Neo4j 主要负责：

- 显式关系
- 多跳路径
- 结构化查询

全文语义召回仍以 Milvus 为主。

### 26.3 不要把 MCP 当成主流程框架

MCP 只适合作为工具接入层，不负责：

- 主编排
- 长流程状态管理
- 多智能体边控制

这些仍然由 LangGraph 负责。

### 26.4 风控不要只做输出过滤

风控应该至少覆盖：

- 检索前范围控制
- 生成前 grounding / 冲突校验
- 审计 trace 记录

---

## 27. 第一阶段最小实现清单（建议）

如果需要先快速落地 MVP，建议只做以下内容：

### 离线 MVP

- PDF / DOCX 上传
- 文本解析
- 基础分类
- 基础 chunk
- bge-m3 embedding
- Milvus 入库
- 基础实体关系抽取
- Neo4j 入图

### 在线 MVP

- 问题解析
- graph / vector 二选一路由
- Milvus 检索
- Neo4j 查询
- 基础重排
- 答案生成
- evidence 回显

### 暂缓项

- 完整多智能体
- 案例记忆
- MCP
- 高级风控
- 全链路审计

---

## 28. 后续增强方向

- 引入更完整的案例记忆体系
- 增强风险规则与审计平台
- 引入 MCP 作为统一工具协议层
- 增加多模态解析能力
- 引入 reranker 或更强证据校验模块
- 增强多轮问答中的会话记忆
- 增加人工复核工作流

---

## 29. 总结

本系统不是一个普通 RAG 问答 demo，而是一个面向高敏质量问题分析场景的 **GraphRAG Agent 系统**。

它的核心设计思想包括：

- 用**离线阶段**把结构化和非结构化知识构建为可检索、可推理、可追溯的知识底座
- 用**在线阶段**实现路由、查询构建、检索、重排、评估、回退和答案生成
- 用**LangGraph** 组织多智能体协作
- 用**Working / Semantic / Episodic Memory** 支撑多轮分析与案例复用
- 用**MCP** 作为可选的标准化工具接入层
- 用**风险控制和审计日志**满足高敏业务场景的可靠性要求

本设计文档既可作为项目立项 / 代码生成输入，也可作为后续简历、答辩、面试时的系统设计依据。