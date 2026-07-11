# Benchmark framework

`cases/<case-id>/` 是可执行、可扩展的回归数据集。每个目录必须包含 `case.yaml`、`problem.md` 和 `generate_data.py`。`case.yaml` 记录难度、标签、超时、固定种子、预期建模步骤、硬性检查、数值范围、结构要求、典型错误与已知歧义。

当前正常基线包含七类项目：预测、评价、优化、聚类、微分方程、缺失/异常数据处理和多图多表中文综合题。`intentional_failure_diagnostic` 是负向夹具，不进入正常 full 基线。

统一入口：

```powershell
mmagent benchmark list
mmagent benchmark run --case forecasting_seasonal
mmagent benchmark run --tag data-quality
mmagent benchmark run --smoke
mmagent benchmark run --all
mmagent benchmark run --full
mmagent benchmark compare <old-summary.json> <new-summary.json>
```

`--all` 每个正常案例运行一次；`--full` 默认每个正常案例运行两次并执行容差内复现比较。详细架构、扩展步骤与排障见 [`docs/benchmark_system.md`](../docs/benchmark_system.md)。原有人工主观评分卡保留在 `mmagent benchmark-scorecard <workspace>`。

当前经实际运行的基线见 [`baseline/current.md`](baseline/current.md) 和机器可读的 [`baseline/current.json`](baseline/current.json)。
