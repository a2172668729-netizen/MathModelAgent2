# Phase 2 最小闭环契约

## 范围

Phase 2 证明 artifact-first 流程可以真实执行和恢复，不证明系统已经能自动解决竞赛题。项目示例数据由仓库明确构造并标记为 synthetic，不得作为现实或竞赛结论引用。

## 求解程序接口

- 入口固定为 workspace 内的 `code/solve.py`。
- 执行器使用当前 Python、参数列表和 `shell=False`，默认超时 120 秒。
- 输入来自 `problem_spec.yaml.source_files`；每个输入及求解入口记录 SHA-256。
- 求解器必须原子写入 `results/experiment.yaml`，并通过 `Experiment` schema。
- stdout、stderr、最新 `run_manifest.yaml` 和不可覆盖的 `runs/<run-id>.yaml` 均落盘。
- 非零退出码、超时、缺失/陈旧结果或 schema 错误都进入 `FAILED/IMPLEMENTED`。

## 验证与报告

`validate-results` 独立读取 CSV 并重算斜率、截距、线性 RMSE 和均值基线 RMSE。验证结果写入 `results/validation.yaml`；报告生成只接受 `passed` 验证，并从结构化产物读取数字。

生成物：

- `reports/evidence_report.md`
- `paper/main.tex`
- `reports/report_manifest.yaml`

LaTeX 是内部技术草稿，不是官方 CUMCM 模板。

## PDF 门禁

`compile-report` 必须实际找到 XeLaTeX 并运行两次。缺失编译器时退出码为 `2`，写入 `reports/pdf_acceptance.yaml` 的 `blocked` 状态并保持 `PAPER_DRAFTED`。即便编译成功，视觉和身份检查仍为 `not_run`，因此 Phase 2 不推进 `FINALIZED`。

## 恢复

`resume` 依据 `state.yaml` 恢复 `IMPLEMENTED`、`VALIDATED` 或 `PDF_COMPILED` 的失败步骤。每次调用最多推进四步，禁止无限重试。已有失败日志和 run manifest 保留不变。

