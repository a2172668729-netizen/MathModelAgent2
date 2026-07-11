# Benchmark 与回归体系

## 目标与边界

Benchmark 用于判断本地工程流水线在代码修改后是否退化。它真实执行 Python、独立数值检查、图表与表格生成、XeLaTeX、PDF 自动检查、隔离 Reviewer 和重复运行。案例使用预先审阅的参考实现，因此验证的是可复现工程闭环和明确数值任务，不代表系统已能自主阅读任意竞赛题并选择模型。

## 目录与契约

```text
benchmarks/
  cases/<case-id>/
    case.yaml          # 元数据、步骤、门禁、范围、超时和错误清单
    problem.md         # 原始题面
    generate_data.py   # 固定种子的可复现数据生成器
  baseline/            # 当前基线摘要，不保存大型 attempt 产物
  runtime/             # 公共可执行入口
  known_issues.yaml
benchmark_results/     # 每次本地运行，已 gitignore
```

每次 suite 创建独立时间戳目录，每个案例和每次重复都使用独立 attempt。attempt 保存 `case.json`、输入、输出、图表、表格、论文、完整日志、状态机、oracle 验证、PDF 预览和 Reviewer 报告。失败会终止在 `FAILED` 并生成 `diagnostic.json`，不会静默跳过。

## 指标

硬性项包括任务完成、真实 Python PID/退出码、结构化结果来源、独立范围验证、有效图表、完整 CSV/LaTeX 表、真实 LaTeX 编译、PDF 结构、引用文件、重复一致性、Reviewer 隔离、终态和失败诊断。

质量项总分 100：页数范围、无自动识别空白页、无缺失图片源、无替换字符或必要中文缺失、无 overfull box，各 20 分。警告不改变硬性结论，例如 smoke 只跑一次或最终人工逐页视觉验收仍待完成。

## 运行

```powershell
# 列表、单例、标签
python -m mmagent benchmark list
python -m mmagent benchmark run --case ode_logistic_growth
python -m mmagent benchmark run --tag optimization

# 快速、全部单次、完整双次
python -m mmagent benchmark run --smoke
python -m mmagent benchmark run --all
python -m mmagent benchmark run --full

# 显式重复次数和输出根
python -m mmagent benchmark run --case forecasting_seasonal --repeat 2 --output benchmark_results

# 比较两个版本的 summary
python -m mmagent benchmark compare benchmark_results/<old>/summary.json benchmark_results/<new>/summary.json
```

命令退出码：suite 无意外回归为 0，正常案例硬失败或负向案例意外通过为 1。`--full` 不包含故意失败夹具；负向验证需显式 `--case intentional_failure_diagnostic`。

## 如何新增案例

1. 复制一个现有 `cases/<id>/`，使用小型自建或许可明确的数据。
2. 在 `case.yaml` 声明唯一 ID、难度、标签、超时、固定种子、完整建模步骤、硬性检查、窄而合理的数值范围、产物结构、典型错误与歧义。
3. 编写接受 `--run-root` 和 `--seed` 的生成器；不得访问网络或个人绝对路径。
4. 在 `benchmark_cases.py` 加入实际数值实现和结构化结果，不得使用常量伪造 solver 输出。
5. 先运行单例两次，核对 oracle、PDF 页面和复现，再运行完整测试。若实际证据与预期冲突，判断是案例设计、环境还是代码缺陷，不能直接放宽范围。

## 如何阅读报告

`summary.json` 供机器处理，`summary.md` 供人工浏览。每个 `case_report.json` 列出 hard failures、质量分和警告。进一步查看 attempt 的：

- `logs/*_execution.json`：命令、PID、时间、超时、退出码和清理方式；
- `oracle_validation.json`：逐个数值范围和实际值；
- `validation_report.json` 与 `paper/preview/all/`：PDF 结构和逐页 PNG；
- `review/isolation.json`：Reviewer 副本策略和主 workspace 前后哈希；
- `diagnostic.json`：失败阶段、错误类型和完整日志位置。

## 回归排查

1. 先看 suite 与 case 的 hard failure ID，不以总分替代硬门禁。
2. `python_really_executed`：检查 solver stderr、exit code、timeout 与 cleanup。
3. `independent_numeric_validation`：比较实际值和 case 中的范围；确认是错误 oracle 还是算法变化。
4. `latex_compiled`/PDF：查看 `latexmk.log`、`xelatex.log` 和全部页面预览。
5. `reproduction_consistent`：比较两次输入种子、依赖、代码树哈希和 details 表。
6. 只有证据证明断言错误时才改 benchmark；代码缺陷应修代码，环境缺失应记录 blocked/known issue。

## 已知限制

自动 PDF 检查不能替代最终人工逐页验收；空白页和乱码判断是保守启发式。Reviewer 是进程与落盘副本隔离，不是敌对代码的 OS 沙箱。当前合成案例不能衡量联网研究、RAG、API、多 Agent 或任意真实赛题的自主建模能力，这些能力仍未获授权。
