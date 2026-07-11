# curve_fitting_demo 人工终审清单

## 审查对象与当前状态

- 当前状态：`AWAITING_HUMAN_APPROVAL`
- 本清单关联运行 ID：`run-20260711t010942206919z`
- 来源运行 ID：`run-20260711t010935048946z`
- 最终 PDF（仓库相对路径）：`workspaces/curve_fitting_demo/runs/run-20260711t010942206919z/paper/main.pdf`
- 最终 PDF（本机准确路径）：`D:\Projects\MathModelAgent2\workspaces\curve_fitting_demo\runs\run-20260711t010942206919z\paper\main.pdf`
- PDF 页数：4
- Manifest：`workspaces/curve_fitting_demo/runs/run-20260711t010942206919z/manifest.json`
- PDF 验证报告：`workspaces/curve_fitting_demo/runs/run-20260711t010942206919z/validation_report.json`
- 隔离 Reviewer 报告：`workspaces/curve_fitting_demo/review/review_report.yaml`
- 技术评估：`passed`
- 复现状态：`passed`，分类为 `numerically_reproducible`
- 人工审批记录：`workspaces/curve_fitting_demo/runs/run-20260711t010942206919z/human_approval.json`
- 人工决定及理由的追加记录：`workspaces/curve_fitting_demo/decisions.md`

> 自动结构检查和隔离 Reviewer 不能替代人工逐页验收。以下项目默认均未由人工确认；完成勾选并记录明确决定前，不得将 workspace 标记为 `FINAL` 或 `REVIEWED`。

## 匿名性与信息泄露人工检查

- [ ] PDF 可见正文、页眉、页脚、图表及附录中没有真实姓名、学校、单位、学号、邮箱或联系方式。
- [ ] PDF 文档属性中的 Author、Creator、Producer、Title 等字段符合匿名提交要求。
- [ ] PDF 和正文中没有本机绝对路径、用户名、临时目录、内部项目路径或其他环境信息。
- [ ] 图表、截图、文件名和引用中没有间接身份线索。
- [ ] 如目标竞赛另有匿名规则，已逐项对照；当前报告只声明为内部工程格式，不冒充官方模板。

## 四页逐页排版人工检查

预览目录：`workspaces/curve_fitting_demo/runs/run-20260711t010942206919z/paper/preview/all/`

- [ ] 第 1 页：标题、匿名作者、摘要、公式、正文边界、字体和页码均清晰，无裁切、重叠、黑块或缺字。
- [ ] 第 2 页：公式、参数表、指标表、交叉引用和段落分页均正确，无越界或异常空白。
- [ ] 第 3 页：拟合图、残差图、图题、坐标轴、图例和正文解释均可读，颜色及线型可区分。
- [ ] 第 4 页：结论、局限性、复现说明、末页留白和页码均符合提交要求。
- [ ] 以实际 PDF 阅读器逐页检查，而不只查看 PNG 预览。

## 正文数值与程序输出一致性人工抽查

程序证据：

- `runs/run-20260711t010942206919z/outputs/metrics.json`
- `runs/run-20260711t010942206919z/outputs/predictions.csv`
- `runs/run-20260711t010942206919z/outputs/validation.json`
- `runs/run-20260711t010942206919z/tables/parameters.csv`
- `runs/run-20260711t010942206919z/tables/metrics.csv`
- `runs/run-20260711t010942206919z/paper/main.tex`

以下路径均相对于 `workspaces/curve_fitting_demo/`。

- [ ] 样本数、斜率、截距与 `outputs/metrics.json` 一致，正文仅做声明过的舍入。
- [ ] RMSE、MAE、R²、最大绝对误差与结构化结果和表格一致。
- [ ] 残差定义、RSS 目标、RMSE、MAE 和 R² 公式与 `src/solve.py`、`src/validate.py` 一致。
- [ ] 图表数据来自 `outputs/figure_data.csv` / `outputs/predictions.csv`，没有手工改数。
- [ ] 独立验证结论与正文表述一致；`sample-out-validation` 和 `sensitivity-analysis` 仍如实标为 `not_run`。
- [ ] 正文没有把合成工程样例推广为真实竞赛数据或现实泛化结论。

## 人工决定

当前记录必须保持：`human_approval.json -> status: pending`。

### 批准时

- [ ] 在实际 PDF 阅读器中完成上述全部适用检查。
- [ ] 由人工在 `human_approval.json` 记录明确批准、审批人/角色、时间、审查 PDF 的 SHA-256 和备注。
- [ ] 在 `decisions.md` 追加批准理由及受影响产物。
- [ ] 再由获准流程决定是否推进状态；本清单本身不推进状态。

### 拒绝时

- [ ] 在 `human_approval.json` 记录 `rejected`、拒绝时间、具体问题和需要重做的产物。
- [ ] 在 `decisions.md` 追加拒绝理由和返工范围。
- [ ] 保持非 FINAL 状态，只重做失败或被拒绝的阶段。

## 本轮准备结论

本清单只汇总已落盘技术证据并提供人工检查入口。当前仍为 `AWAITING_HUMAN_APPROVAL`；视觉检查、最终提交适用性和人工批准均未由本轮自动代替或宣称完成。
