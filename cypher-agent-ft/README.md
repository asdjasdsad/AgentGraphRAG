# cypher-agent-ft

面向 GraphRAG 图查询 Agent 的 Cypher 生成模型优化子项目。这个子项目按 `second_project_design.md` 的要求提供一条可运行的真实训练闭环：

1. 导出和裁剪图谱 schema
2. 任务模板实例化与 prompt pool 构造
3. teacher/mock 候选生成
4. 四层校验与 synthetic SFT / DPO 数据集构建
5. 基于 `Qwen/Qwen2.5-Coder-3B-Instruct` 的 QLoRA SFT / DPO
6. 基于 adapter 的离线评测与 replay 验证

## 目录

```text
cypher-agent-ft/
├── configs/
├── data/
├── outputs/
├── scripts/
└── src/cypher_agent_ft/
```

## 准备

建议在服务器上的独立环境中安装：

```bash
bash cypher-agent-ft/scripts/bootstrap_server.sh
source .venv-cypher-agent-ft/bin/activate
python cypher-agent-ft/scripts/check_environment.py
```

默认本地 teacher:

```text
Qwen/Qwen3-Coder-30B-A3B-Instruct (4bit, bitsandbytes)
```

如果要走真实 teacher 数据生成，还需要额外配置：

```bash
export OPENAI_API_KEY=...
```

## 数据流水线

在仓库根目录执行：

```bash
python cypher-agent-ft/scripts/export_schema.py
python cypher-agent-ft/scripts/build_prompt_pool.py --limit 12
python cypher-agent-ft/scripts/generate_candidates_gpt4o.py --mode mock
python cypher-agent-ft/scripts/validate_candidates.py
python cypher-agent-ft/scripts/build_sft_dataset.py
python cypher-agent-ft/scripts/generate_sft_outputs.py --mode sft_mock
python cypher-agent-ft/scripts/build_dpo_dataset.py
python cypher-agent-ft/scripts/eval_offline.py --stage sft
python cypher-agent-ft/scripts/eval_offline.py --stage dpo
python cypher-agent-ft/scripts/replay_eval.py
```

## 真实训练

如果要迁移到另一台服务器，建议按这个顺序：

```bash
git pull
bash cypher-agent-ft/scripts/bootstrap_server.sh
source .venv-cypher-agent-ft/bin/activate
python cypher-agent-ft/scripts/check_environment.py
python cypher-agent-ft/scripts/prefetch_models.py
GPU_ID=0 PROMPT_LIMIT=500 bash cypher-agent-ft/scripts/run_data_pipeline.sh
GPU_ID=0 bash cypher-agent-ft/scripts/run_training_pipeline.sh
bash cypher-agent-ft/scripts/run_eval_pipeline.sh
```

SFT:

```bash
python cypher-agent-ft/scripts/train_real.py --stage sft
```

DPO:

```bash
python cypher-agent-ft/scripts/train_real.py --stage dpo
```

真实 adapter 推理:

```bash
python cypher-agent-ft/scripts/generate_real_outputs.py \
  --dataset cypher-agent-ft/data/sft/test.jsonl \
  --adapter-path cypher-agent-ft/outputs/adapters/sft-real
```

## 说明

- 默认数据构造仍使用本地 mock teacher，避免依赖 OpenAI 才能起步。
- 配置文件使用“JSON 兼容 YAML”格式，便于在不额外引入 YAML 依赖的情况下执行本地流程。
- 训练与推理链路已切到真实 `Transformers + PEFT + TRL`，可直接在本机 GPU 上跑 QLoRA / DPO。
- git 中会带上脚本、配置和已生成的小样本数据，但不会带大模型权重缓存；新服务器首次运行 `prefetch_models.py` 时仍需要下载模型。
