# Python-to-PDF core demo

## 一条命令

```powershell
mmagent demo curve-fitting --workspace workspaces/curve_fitting_demo
```

该命令在同一 workspace 中创建两个隔离 run：第一次完整执行和第二次完整复现。每个 run 都真实执行落盘的 `src/solve.py` 与 `src/validate.py`，真实生成图、表、LaTeX 和 PDF，不使用 mock 代替集成步骤。

## 产物链

```text
input/problem.md + input/data.csv
  -> src/solve.py
  -> outputs/metrics.json + predictions.csv + figure_data.csv
  -> src/validate.py -> outputs/validation.json
  -> figures/*.png + figures/*.svg
  -> tables/*.csv + tables/*.tex
  -> outputs/claim_evidence.json + paper/report_manifest.json
  -> paper/main.tex
  -> latexmk -xelatex -> paper/main.pdf
  -> validation_report.json + paper/preview/
  -> reproducibility_report.json
  -> AWAITING_HUMAN_APPROVAL
```

关键数值来自 `metrics.json` 和 `predictions.csv`。`claim_evidence.json` 将论文声明映射回结构化证据，`report_manifest.json` 列出写作输入；LaTeX 表格由结构化结果生成，论文不维护第二份手工数值源。

## CLI

- `mmagent doctor`：检查 Python、依赖、Git、XeLaTeX、latexmk、kpsewhich、PDF 工具和中文字体。
- `mmagent run <workspace>`：从固定 base input/source 创建一个新 run 并运行到 `PDF_VALIDATED`。
- `mmagent compile <workspace> [--run-id ID]`：对选定 run 重新执行 latexmk 和 PDF 验证。
- `mmagent validate <workspace> [--run-id ID]`：校验数值、PDF 与 manifest 哈希。
- `mmagent reproduce <workspace> [--run-id ID]`：隔离前次派生输出，创建第二个 run，并比较数值与内容等价性。
- `mmagent status <workspace>`：显示 latest run、当前状态和人工审批状态。

## 安全边界

执行器只接受 run workspace 内的脚本，使用参数数组和 `shell=False`，设置超时，分离 stdout/stderr，并使用 run-local `sitecustomize.py` 阻断 Python socket 连接以及 solver 再启动外部进程。该措施是针对本项目可信 Python solver 的受控执行策略，不是用来执行任意敌对代码的操作系统级沙箱。

自动流程不能进入 `FINAL`。PDF 结构、日志、页数、哈希、缺图、未定义引用、匿名信息和绝对路径由程序检查；预览图会生成，但最终逐页视觉接受和定稿必须由人确认。

## 当前真实验收

2026-07-11 在 `workspaces/curve_fitting_demo` 运行一条命令 demo：

- 首次 run：`run-20260711t010935048946z`；
- 第二次复现 run：`run-20260711t010942206919z`；
- 复现分类：`numerically_reproducible`；
- 第二次 PDF：4 页、315,529 bytes，结构检查通过，overfull/underfull 警告均为 0；
- 全部 4 页预览已逐页查看，未见裁切、重叠、黑块或缺字；
- `human_approval_status` 仍为 `pending`，当前状态为 `AWAITING_HUMAN_APPROVAL`。

这组证据是 synthetic 工程 fixture，不得作为竞赛结论或真实数据证据。
