# Reproducibility contract

曲线拟合 fixture 使用固定种子 `20260710` 生成一次 `input/data.csv`。base input/source 已存在时，后续 run 只复制并读取这些文件，不重新生成随机观测。

复现命令创建新的隔离 run，重新执行 solver、独立 validator、Matplotlib、表格生成、论文组装、latexmk 和 PDF 验证。它不会复制第一次 run 的 `outputs/`、`figures/`、`tables/`、`paper/` 或 `logs/`。

`reproducibility_report.json` 比较：

- input 与 solver/validator SHA-256；
- 参数、RMSE、MAE、R² 与最大绝对误差；
- `predictions.csv` 与 `figure_data.csv`，默认相对/绝对容差均为 `1e-10`；
- 关键生成文件集合；
- Python、validator 和 latexmk 退出码；
- 两个 PDF 的结构验证状态；
- PNG、SVG、PDF 的二进制 SHA-256 分类。

数值与图表源数据一致且两个 PDF 均有效时，二进制文件因时间戳或工具元数据不同可记为 `binary_diff_content_equivalent`，不会误报为数值不可复现。任何输入、源码、关键数值、预测或图表源数据差异都会使复现失败。

2026-07-11 的最新标准 workspace 实测使用 `run-20260711t010935048946z` 作为首次运行、`run-20260711t010942206919z` 作为复现运行。`workspaces/curve_fitting_demo/reproducibility_report.json` 的全部条件均为 `true`，参数与四项指标、预测和图表源数据均在 `1e-10` 容差内一致；两次 PDF 均通过结构验证，PDF 二进制差异被记录为内容等价而非数值失败。
