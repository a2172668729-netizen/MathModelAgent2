# 隔离 Reviewer 复审报告

## 结论

本次从当前 `latest_run.json` 重新读取证据，审阅对象是 `run-20260711t010942206919z`，关联 source run 为 `run-20260711t010935048946z`。技术审查通过；此前 RV-002、RV-003、RV-004 均已由最新落盘产物关闭。

当前仍不能标记为 `FINAL` 或 `REVIEWED`。唯一开放的 critical blocker 是 RV-001：`human_approval.json` 和 manifest 仍为 `pending`，PDF 验证记录仍为 `awaiting_human_approval`。本次 AI Reviewer 的四页视觉检查不能替代仓库要求的人工最终批准。

## 当前证据核验

- 从 `latest_run.json` 重新确定 latest/source 两次 run，没有采用 writer 概述作为证据。
- source run 的 40 条、latest run 的 41 条 manifest 记录均重新核对文件大小与 SHA-256，全部匹配。
- 两次 run 的 2 个输入、10 个 Python 源文件、5 个结构化数值输出、4 个图文件、4 个表文件和 `main.tex` 一致；两份 PDF 哈希不同，但均通过验证，复现报告将其记录为内容等价。
- 只读闭式 OLS 复算得到：样本数 36，斜率约 2.5572047130，截距约 3.1335039111，RMSE 约 0.8199391781，MAE 约 0.6476007559，R² 约 0.9884643818，最大绝对误差约 1.8165114726。与 solver 输出在 `1e-8` 容差内一致。
- 预测值、残差、`figure_data.csv`、CSV/LaTeX 表格、摘要、结果、误差分析与结论中的数字均一致。
- 论文公式与实现一致：带截距线性模型、残差方向、RSS、RMSE、MAE 与 R² 定义匹配。solver 使用 SciPy `curve_fit`，独立 validator 使用闭式 OLS，且两者落盘退出码均为 0。
- 样本内均值基线 RMSE 约为 7.634159，高于线性模型 RMSE。样本外验证和敏感性分析仍为 `not_run`，论文没有越界作现实或样本外泛化声明。
- 最新 PDF 的编译退出码为 0，共 4 页；无缺失文件、未定义引用、未定义引用文献、overfull 或 underfull box。
- 逐页查看 4 张最新预览：中文、公式、表格、两张图、页眉与页码均清晰，无裁切、重叠、黑块或缺字。
- 可见作者为“匿名”，PDF Author 元数据为 `Anonymous`；论文中未发现 workspace 绝对路径或用户身份泄漏。
- 格式明确为内部 `ctexart` 工程报告，没有冒充官方竞赛模板。

## 此前问题的关闭状态

### RV-002 — Closed

最新 validator 已把残差均值和总体标准差写入 `outputs/validation.json`；`claim_evidence.json` 追踪残差均值来源；论文误差分析报告残差均值 `-2.060e-15`，对图中趋势作有限解释，并明确说明该视觉判断不构成同方差、独立性或样本外泛化检验。残差分析不再只是展示图形。

### RV-003 — Closed

最新论文不再声称可由固定种子重建原始观测，而是明确表述为“固定保存并进行哈希跟踪的 synthetic fixture”，且正式运行不重新生成数据。该措辞与当前可验证的输入文件和 manifest 证据一致。

### RV-004 — Closed

最新 XeLaTeX 日志和 `validation_report.json` 中 overfull、underfull box 均为 0；四页预览未见排版缺陷。

## 唯一开放问题

### RV-001 — Critical / Blocking：人工最终批准待完成

证据：`latest_run.json` 状态为 `AWAITING_HUMAN_APPROVAL`；latest run 的 manifest 与 `human_approval.json` 都记录 `pending`；`validation_report.json` 的 `visual_check` 为 `awaiting_human_approval`。

补救：由人工逐页检查当前 4 页 PDF，确认匿名性和提交适用性，并通过仓库规定流程显式记录最终批准。在此之前不得标记 `FINAL` 或 `REVIEWED`。

## 未执行或被阻断

- 未重新运行 solver、validator 或 LaTeX 编译；本复审只读取当前落盘证据，并额外执行不写文件的独立数值复算。
- 样本外验证：`not_run`，论文未作样本外声明。
- 敏感性分析：`not_run`，当前无依赖该检查的模型选择、因果或稳健性结论。
- 官方竞赛模板核验：`not_run`，报告只声称内部工程格式。
- 人工最终批准：`blocked`，必须由人工完成。

本次只覆盖 `workspaces/curve_fitting_demo/review/review_report.yaml` 与 `review.md`，未修改其他文件。
