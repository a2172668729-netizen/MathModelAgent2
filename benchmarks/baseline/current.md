# Current benchmark baseline

基线来源：`benchmark-20260711t132624924206z`，代码树 SHA-256 为 `6666c6ecb0f27a0c8548d892d826b4a9d38b7fe364df3c0bc720ed381c86eba1`。

- 完整测试：69 passed，23.40 秒。
- smoke：2/2 passed，18.35 秒。
- full：7/7 passed，每例 2 次，共 14 个独立 attempt，115.06 秒。
- 重复一致性：7/7 在声明容差内一致。
- 故意失败：`expected_failure_observed`，2.80 秒，保留非零退出、stderr、失败状态和 diagnostic。
- PDF：full 每个案例第二次 attempt 共 16 页已逐页查看；未见裁切、重叠、黑块、缺图或乱码，图表顺序正确。该检查不等同于用户对未来竞赛提交的最终批准。
- 版本比较：`no_regression`。

| 案例 | 类型 | 状态 | 质量分 | 关键结果 |
|---|---|---:|---:|---|
| `forecasting_seasonal` | 预测 | passed | 100 | holdout RMSE 0.485918；下一期 43.947179 |
| `evaluation_resilience` | 评价 | passed | 100 | top score 0.705833；winner index 1 |
| `optimization_production` | 优化 | passed | 100 | objective 1800；人工 80；材料 75 |
| `clustering_regions` | 聚类 | passed | 100 | 3 簇；inertia 14.125059；最小簇 18 |
| `ode_logistic_growth` | 微分方程 | passed | 100 | growth 0.262164；capacity 98.500917；RMSE 0.669394 |
| `data_quality_regression` | 缺失/异常 | passed | 100 | 缺失 4；异常 3；斜率 3.000558 |
| `comprehensive_city_planning` | 中文综合、多图多表 | passed | 100 | 5 城市；2024；top score 0.6；趋势 1.383743 |

开放限制详见 [`benchmarks/known_issues.yaml`](../known_issues.yaml)，完整本地产物位于 `benchmark_results/benchmark-20260711t132624924206z/`（该目录被 Git 忽略）。
