# 真实历史赛题接入与评测 v1

本流程只证明项目可以接收、记录并评测第一道真实历史题，不代表已经具备真实竞赛能力。默认模式仍是 `assisted`，不启用联网搜索、模型 API、RAG、Web UI、数据库或并行 Agent。

## 职责边界

- 云端模型负责理解题意、提出候选模型、在人工检查点后编码、分析验证结果和撰写论文。
- 本地项目负责创建 workspace、只读盘点输入、执行代码、保存中间证据、验证 schema 和阶段门禁、登记结果、生成可追溯 LaTeX 宏并记录 benchmark。
- 本地门禁不会自动选择“最优模型”、给主观项打分、批准论文或进入 `REVIEWED` / `FINALIZED`。

## 1. 创建并放入材料

```powershell
mmagent new cumcm-2020-a
```

命令默认创建 `workspaces/cumcm-2020-a/`。`problem_id` 必须以小写字母开头，只含小写字母、数字、`_` 或 `-`。把原始题目 PDF、说明 TXT/Markdown、CSV、XLSX、JSON、图片及其他附件原样放进 `input/`；不要改写原文件，也不要把 OCR 文本冒充原文。

随后运行：

```powershell
mmagent audit-input workspaces/cumcm-2020-a
mmagent status workspaces/cumcm-2020-a
mmagent validate-workspace workspaces/cumcm-2020-a
```

输入审计生成 `input_inventory.json` 和 `input_inventory.md`，记录相对路径、大小、SHA-256、读取状态与解析错误。CSV/XLSX 还记录工作表、行列数和字段名。不支持的附件仍会被登记，并明确写出不支持原因；工具不使用 OCR。

空白 workspace 的 `validate-workspace` 结构检查应通过，同时以 warning 报告当前为 `CREATED`、下一阶段缺少输入材料。这是预期的未完成状态，不是系统错误。

## 2. Assisted workflow 的结构化证据

Codex 必须按仓库 `skills/modeling-orchestrator/SKILL.md` 每次只处理下一阶段，并落盘以下文件：

- `problem_analysis.yaml`：`subproblems`、`known_conditions`、`objectives`、`constraints`、`problem_facts`、`model_assumptions`、`ambiguities_and_risks`。题目事实和已知条件必须带 `source_refs`。
- `data_audit.yaml`：逐数据集记录 `fields`（类型、单位、缺失、重复、异常）、`cleaning_operations` 和 `data_risks`。
- `model_candidates.yaml`：至少两个候选模型，逐项记录适用条件、优点、风险、验证方法、采用/放弃决定和理由；进入选择阶段前必须人工批准且恰有一个 `adopt`。
- `experiment_plan.yaml`：基线、实验方案、评价指标、随机种子、训练/验证方式、敏感性或稳健性计划。

所有文件由严格 schema 校验。缺文件或字段时，`mmagent advance <workspace> <STAGE>` 返回 `BLOCKED` 和具体路径/字段，不能跳阶段。例如：

```powershell
mmagent advance workspaces/cumcm-2020-a INGESTED
mmagent advance workspaces/cumcm-2020-a ANALYZED
```

完整顺序为：

`CREATED → INGESTED → ANALYZED → DATA_READY → MODELS_PROPOSED → MODEL_SELECTED → IMPLEMENTED → VALIDATED → PAPER_DRAFTED → AWAITING_HUMAN_APPROVAL`

其中输入审计、题目分析、候选比较及人工选择、实验计划、真实运行清单、结果注册和验证必须按顺序存在。`REVIEWED` 和 `FINALIZED` 永远不是自动转移。

## 3. 结果注册与论文数字

真实程序输出登记在 `results/results.json`。每项结果包含类型（标量、参数、表格、图表）、模型名、数据版本、实验 ID、来源脚本、生成时间和验证状态；表格/图表还必须指向真实文件。每个实验还需有通过的 `runs/<experiment_id>.yaml`，并把 `results/results.json` 登记为运行产物。

一个最小的已验证标量条目如下：

```json
{
  "schema_version": "1.0",
  "results": [{
    "id": "rmse-result",
    "kind": "scalar",
    "name": "RMSE",
    "value": 0.125,
    "unit": "m",
    "latex_macro": "ModelRMSE",
    "model_name": "Linear model",
    "data_version": "sha256:<dataset digest>",
    "experiment_id": "baseline-run",
    "source_script": "code/solve.py",
    "generated_at": "2026-07-11T00:00:00Z",
    "validation_status": "passed"
  }]
}
```

运行 `mmagent results-macros <workspace>` 后，仅对已验证且具有通过运行清单的标量/参数生成 `paper/generated/results_macros.tex`。论文使用 `\ModelRMSE`，不要手工复制关键数字。

## 4. Benchmark 与人工审批

创建 workspace 时会生成 `benchmark_scorecard.yaml` 和 `.md`。题目理解、数据审计、模型选择依据、验证、可追溯性、论文完整度和可复现性均标为 `requires_human_score: true`，默认分数为空。代码执行成功率、人工介入次数、严重错误数和总运行时间只记录真实统计。修改 YAML 后运行：

```powershell
mmagent benchmark workspaces/cumcm-2020-a
```

该命令校验评分表并重建 Markdown，不会自动填写主观分数。验证通过、论文草稿存在后，流程最多进入 `AWAITING_HUMAN_APPROVAL`；用户仍需检查模型选择、关键假设、验证结论、PDF 逐页视觉结果和 reviewer 证据，才能另行决定是否批准。

## 第一份历史题需要提供的文件

至少提供原始题目 PDF。若题目发布了数据表、图片、附件说明、官方补充或勘误，也应一并提供原文件；若希望对照历史表现，可另附获奖论文或公开评语，但必须标明来源，且不能把参考解答当作模型运行结果。
