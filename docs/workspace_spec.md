# Workspace specification

标准目录见 `workspaces/example_problem/`。关键文件：

- `problem_spec.yaml`：题目、子问题、目标、约束和变量。
- `assumptions.yaml`：假设、依据、影响和验证状态的结构化事实源。
- `assumptions.md`：供人工说明和检查点讨论使用，不替代结构化事实源。
- `state.yaml`：当前阶段、完成阶段、失败信息、产物相对路径。
- `run_manifest.yaml`：运行身份、环境、命令、输入哈希、参数和产物。
- `decisions.md`：人工确认和关键工程选择。

`input/` 保存原始题目；`data/raw` 与 `data/processed` 分离；模型候选和最终选择分离；结果、图表、表格、报告、论文、审稿和最终提交包各有独立目录。所有记录路径均相对 workspace，禁止绝对路径和 `..`。

## Python core run

曲线拟合闭环在不破坏上述模型的前提下使用隔离运行目录：

```text
workspaces/curve_fitting_demo/
  input/problem.md
  input/data.csv
  src/solve.py
  src/validate.py
  demo_config.json
  decisions.md
  latest_run.json
  reproducibility_report.json
  runs/<run_id>/
    input/
    src/{solve.py,validate.py,pipeline/*.py}
    outputs/{metrics.json,predictions.csv,figure_data.csv,validation.json}
    figures/{fit_curve,residuals}.{png,svg}
    tables/{parameters,metrics}.{csv,tex}
    paper/main.tex
    paper/main.pdf
    paper/preview/
    logs/
    manifest.json
    validation_report.json
    reproducibility_report.json
    human_approval.json
```

base input/source 是复现事实源；每个 run 保留实际执行副本和哈希。派生输出不会在两个 run 之间复制。
