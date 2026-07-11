# Decision log

## 2026-07-11 — executable benchmark and regression system

- Benchmark 正常基线使用七个仓库自建合成案例，负向故障夹具单独运行；不复制历史赛题，也不把参考实现冒充自动读题建模能力。
- `--all` 表示全部正常案例单次执行，`--full` 表示全部正常案例默认双次执行并比较数值和结构结果；smoke 单次未做复现明确记录为 `not_run` warning。
- Reviewer 通过独立子进程读取 attempt 的落盘副本，并用主 attempt 前后哈希证明未写回；这是工作流隔离而不是 OS 级安全沙箱。
- PDF 自动质量分检查页数、启发式空白页、图片源、必要中文/替换字符和 overfull box；最终人工逐页视觉验收继续是 warning/人工门禁。
- 首次全案例运行发现生产优化的预期目标区间错误：真实 `scipy.optimize.linprog` 结果为 1800 且两项资源均满足上界。该问题归类为 benchmark 设计错误，oracle 改为围绕 1800 的窄容差，没有放宽代码或安全门禁。

## 2026-07-11 — real-problem readiness v1

- Real historical problems use a dedicated `workspace_kind: real_problem` and do not copy the curve-fitting demo solver.
- An incomplete blank workspace is structurally valid but reports its next evidence gate as blocked; missing competition material is not treated as a framework failure.
- Subjective benchmark dimensions remain unset until a human supplies both a score and rationale. `REVIEWED` and `FINALIZED` are not automated transitions.

## 2026-07-10

- Windows 11 为主开发环境，代码必须兼容 macOS。
- Python 3.11+、Pydantic、PyYAML、pytest；CLI 使用标准库 argparse，减少第一阶段依赖。
- CUMCM 默认 LaTeX + XeLaTeX；Typst 暂不实现。
- 2026 CUMCM 规范保持 provisional，直到官方来源完成核验。
- 上游只做证据化设计参考；许可证不清或限制性内容不复制。
- 第一阶段只创建 `academic-humanizer-zh` 可发现 Skill 骨架，其余阶段先在架构文档定义边界。
- 系统 PATH 没有 Git，且最初 `.git` 为空目录。恢复任务时发现 Codex 工作区运行时提供 Git 2.53.0，已用其明确路径真实初始化 `main`；不安装系统 Git、不修改 PATH，`doctor` 仍按用户 PATH 如实报告。
- 系统 PATH 的 Python 是 Windows Store 占位符；本轮验证使用 Codex 随附 Python 3.12 和项目内 `.venv`。
- Phase 2 使用项目自建并明确标记的 synthetic 线性数据，只验证工程闭环，不作为竞赛或现实证据。
- Phase 2 只执行 workspace 已有求解程序，不生成模型代码；模型选择由示例契约固定，`approved_by_human` 保持 false，不冒充真实人工检查点。
- 证据报告读取通过独立重算的结构化结果；LaTeX 是内部技术草稿，不冒充 CUMCM 2026 官方模板。
- XeLaTeX 缺失时写 `blocked` 验收记录并保留 `PAPER_DRAFTED`；不安装系统工具、不伪造 PDF、不推进 final。
- Phase 3 采用仓库 `AGENTS.md` + `skills/` + `config/agent.yaml` 的 Codex-assisted 结构，不接 OpenAI API；技能契约与真实赛题能力分开验收。
- Agent 默认单写者、最多三次阶段重试；外部研究、API、RAG、Web UI、数据库和并行 Agent 继续禁用。
- Reviewer 只读落盘产物且只写 `review/`；独立前向测试使用无前序对话继承的上下文，不开启并行建模写入。
- 本轮首次 Git 审计只使用 PATH，因而报告不可用；随后按本文件既有证据定位 bundled Git 2.53.0。仓库仍是无提交的 unborn 分支，故不伪造修改前 checkpoint，只创建 `feature/core-python-pdf-pipeline` 承载本轮未提交工作树。
- TeX Live 2026 使用 TUG 官方安装器的 `scheme-full` profile 安装到 `D:/texlive/2026`。自动 CTAN 路由落到北美慢速镜像后，保留失败日志并改用 CTAN 官方列表中状态正常的 USTC 镜像；不改用 MiKTeX。
- 安装 profile 不持久修改 PATH、文件关联或桌面集成；验收和 demo 通过当前进程的 `MMAGENT_TEX_BIN`/PATH 定位工具，避免覆盖无关环境变量。
- Python solver 的默认网络限制通过 run-local `sitecustomize.py` 阻断 socket 与外部子进程，并限制入口、cwd 和声明输出根；这是可信 solver 的受控执行，不声称为可承载敌对代码的操作系统级沙箱。
- 新 core demo 的用户请求明确允许“线性或非线性”拟合，工程 fixture 选择线性模型。该许可只覆盖 demo，不替代真实竞赛的模型选择与最终人工门禁。

## 2026-07-11

- 恢复中止任务后，发现端到端测试把成功运行时合法的空 `logs/python_stderr.log` 误判为失败。验收改为 stderr 文件必须存在且由 `execution.json` 引用；语法错误和运行时异常用例仍要求非空 stderr，显式 `SystemExit(7)` 以非零退出码和 `failure_reason` 作为失败证据。
- TeX 环境验收脚本在 Windows 上应调用实际存在的 `tlmgr.bat`，并使用 `info --only-installed scheme-full` 避免把远程仓库可用性混入本地安装完整性检查。
- 标准 workspace demo 的首次 run 为 `run-20260711t005740670249z`，第二次复现 run 为 `run-20260711t005748179659z`；两次均真实执行 Python、validator、Matplotlib 和 latexmk，复现通过并停在 `AWAITING_HUMAN_APPROVAL`。
- Codex 已逐页查看第二次 run 的 4 张 PDF 预览，未见裁切、重叠、黑块或缺字；这不是用户的最终批准，`human_approval_status` 继续保持 `pending`。
- 隔离 Reviewer 指出残差段落缺少结构化解释后，validator 新增残差均值与总体标准差诊断，论文引用残差均值并明确限制视觉判断；同时缩窄 synthetic 输入措辞并拆分复现段落，消除 0.23064pt overfull warning。
- 修订后的首次 run 为 `run-20260711t010935048946z`，第二次复现 run 为 `run-20260711t010942206919z`；最新 PDF 4 页、315,529 bytes，overfull/underfull 均为 0，状态仍为 `AWAITING_HUMAN_APPROVAL`。
