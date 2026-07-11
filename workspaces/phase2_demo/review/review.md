# 独立 Reviewer 报告

## 结论

状态：`blocked`。当前产物不能进入 `REVIEWED` 或 `final`。存在三个开放的 critical 问题：PDF 未编译及未完成结构/逐页视觉验收、身份检查未执行、模型选择的人工检查点未完成。

本次审阅仅依据 `workspaces/phase2_demo` 的落盘产物，不采用前序 writer 的对话理由。结构化问题清单见 `review/review_report.yaml`。

## 阻断问题

1. **PDF 验收被阻断。** `reports/pdf_acceptance.yaml` 记录 `status: blocked`、`attempts: 0`，且 `structural_check` 与 `visual_check` 均为 `not_run`。当前没有可接受的 PDF，也没有逐页视觉验收证据。
2. **身份检查未执行。** 同一验收记录将 `identity_check` 标为 `not_run`。虽然 LaTeX 源文件使用“匿名工程示例”，但这不能替代对编译文件、元数据和逐页内容的身份泄漏检查。
3. **人工模型选择检查点未完成。** `models/selected/selection.yaml` 中 `approved_by_human: false`，`decisions.md` 也明确未声称竞赛检查点。

## 主要开放问题

- `results/validation.yaml` 声称完成独立重算，但 workspace 内没有独立验证程序、验证命令、验证器哈希或单独的验证运行清单；目前无法从落盘证据复核其独立性。
- `code/solve.py` 仅调用 `mmagent.demo_solver.main`。实际公式和指标实现未落盘在 workspace 中，因此无法在隔离 Reviewer 上下文内完成公式—代码逐项核对。

## 已核对且未发现矛盾的项目

- `input/observations.csv` 的五个点严格满足 `y = 2x + 1`。由这些点重算得到斜率 2、截距 1、线性样本内 RMSE 0；均值基线 RMSE 为 `sqrt(8) = 2.828427124746...`，与 `results/experiment.yaml`、证据报告和论文中的数值一致（论文做了十进制舍入）。
- `run_manifest.yaml` 中对输入 CSV 和 solver 包装文件记录的 SHA-256 与本次只读复核结果一致。
- 报告与论文均明确将数据限定为项目自带合成示例，没有把结果表述为真实竞赛或现实结论。

## 泛化边界

该数据只有五个项目构造点，并且精确满足预设线性关系。`results/validation.yaml` 将样本外验证标为 `not_run`。因此，零样本内 RMSE 只能证明这个工程 fixture 的闭环一致性，不能证明现实规律、竞赛性能或样本外泛化能力。当前披露充分，故在结构化报告中记为 `accepted_risk`；一旦扩大结论范围，必须重新打开为阻断问题并补充真实或竞赛授权数据及样本外验证。

## 解除阻断所需动作

1. 持久化人工对模型选择和关键假设的明确批准。
2. 落盘可审阅的实际 solver 实现，以及独立 validator 的代码和运行清单。
3. 使用可用的 XeLaTeX 工具链真实编译 PDF，完成结构检查、逐页视觉检查和身份检查，并持久化验收结果。
