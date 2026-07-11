# Core pipeline audit

审计时间：2026-07-10（Asia/Shanghai）  
审计范围：修改前的 `D:/Projects/MathModelAgent2` 工作树、两个现有 workspace、CLI、状态机、测试和本机工具链。

## 结论

现有 Phase 1～3 架构和确定性 Phase 2 最小闭环均可读取，两个 workspace 通过结构校验，基线测试为 **27 collected / 27 passed**。当前实现已经用 `subprocess.run(..., shell=False)` 真实执行 workspace 内的 Python 包装脚本并保存 stdout/stderr、输入哈希和 YAML run manifest，但尚未满足本轮完整闭环：科学计算依赖未安装，没有绘图、CSV/JSON 结果、LaTeX 表格、完整论文、latexmk、PDF 页数/预览/匿名检查、完整 provenance 或第二次复现比较。

本机 PATH 中没有可用的 Git、XeLaTeX、latexmk、kpsewhich 或 pdftotext；`pdftoppm` 来自 Codex bundled runtime。仓库 `.venv` 可用，Python 为 3.12.13。

## 项目结构与依赖

- 构建/依赖：`pyproject.toml` + setuptools，开发依赖只有 pytest。
- 运行依赖：pydantic、PyYAML。
- 可执行入口：`mmagent = mmagent.cli:main`。
- Python：`D:/Projects/MathModelAgent2/.venv/Scripts/python.exe`，3.12.13。
- 已安装包不含 numpy、pandas、scipy、matplotlib、pypdf 或 PyMuPDF。
- 主要源码：`src/mmagent/{cli,models,workspace,pipeline,demo_solver,agent}.py`。
- 测试：5 个测试文件，共 27 项。
- 现有 demo：`workspaces/phase2_demo`；另有初始 workspace `workspaces/example_problem`。

## Git 状态

工作区存在 `.git/`，但当前 PATH 中 `git` 命令不可用，因此首次审计命令不能读取分支、提交历史或工作树差异。没有修改全局 Git 配置。修改前观察到的项目文件清单由本审计前的递归只读目录扫描保留在当前 Codex 命令记录中。

审计后依据仓库 `docs/decision_log.md` 的既有记录，定位到 Codex bundled runtime 的 Git 2.53.0。该仓库是无提交的 unborn `main`，全部文件均为 untracked，无法补造“修改前提交”。为不污染 `main`，随后创建了未提交分支 `feature/core-python-pdf-pipeline`；没有覆盖文件或创建虚假基线提交。

## 基线命令与结果

```text
.venv/Scripts/python.exe -m pytest --collect-only -q
27 tests collected in 0.11s

.venv/Scripts/python.exe -m pytest -ra
27 passed in 1.93s

.venv/Scripts/python.exe -m mmagent validate-workspace workspaces/example_problem
PASS

.venv/Scripts/python.exe -m mmagent validate-workspace workspaces/phase2_demo
PASS
```

`mmagent doctor` 结果摘要：Python、pydantic、PyYAML、当前目录可写均通过；Git、XeLaTeX、pdftotext 缺失；pdftoppm 与微软雅黑/黑体/宋体被检测到。

## CLI 审计

现有命令：

- `init`
- `status`
- `validate-workspace`
- `demo`
- `validate-results`
- `render-report`
- `compile-report`
- `resume`
- `run-solver`
- `agent-doctor`
- `doctor`

缺口：没有本轮要求的独立 `validate <run>`、`reproduce <run>` 语义；`demo` 只运行旧 Phase 2 fixture；`compile-report` 直接调用 xelatex 两次而不是 latexmk。

## Workspace 数据模型与状态机

结构化模型集中在 `src/mmagent/models.py`，使用 Pydantic 严格 schema 和相对路径校验。现有主要模型包含 ProblemSpec、AssumptionsFile、DatasetMetadata、ModelCandidate、ModelSelection、Experiment、ValidationReportFile、RunManifest、ReportManifest、PdfAcceptance 和 WorkspaceState。

现有状态链：

`CREATED -> INGESTED -> ANALYZED -> DATA_READY -> MODELS_PROPOSED -> MODEL_SELECTED -> IMPLEMENTED -> VALIDATED -> PAPER_DRAFTED -> PAPER_HUMANIZED -> FACT_CHECKED -> PDF_COMPILED -> FORMAT_CHECKED -> REVIEWED -> FINALIZED`

失败状态为 `FAILED` 并记录 `failed_stage`。现有链未直接表达本轮所需的 `CODE_READY`、`CODE_EXECUTED`、`FIGURES_GENERATED`、`TABLES_GENERATED`、`PDF_VALIDATED`、`REPRODUCIBILITY_VALIDATED` 和 `AWAITING_HUMAN_APPROVAL`。增量实现需要保持旧链兼容，同时为 core run 建立更细门禁；自动流程不得进入 FINAL/FINALIZED。

落盘状态：

- `workspaces/example_problem`：`CREATED`，校验通过。
- `workspaces/phase2_demo`：`PAPER_DRAFTED`，校验通过；此前因缺少 XeLaTeX 被阻断。

## 现有核心能力与缺口

### Python 执行

已实现：真实子进程、`shell=False`、超时、非零退出码、stdout/stderr 分离、失败状态、输入和 solver SHA-256、失败后重跑。

缺口：workspace 内 solver 只是 `mmagent.demo_solver` 包装入口；执行 manifest 没有完整 executable/version/time/duration/exit-code/env 摘要/output inventory；没有默认网络隔离或输出路径审计；结果只有 YAML；没有 numpy/pandas/scipy/matplotlib 流程。

### 绘图与表格

未实现可复用绘图模块。没有折线图、散点图、柱状图、热力图、PNG/SVG 产物或中文字体处理。未实现 DataFrame 到 CSV/LaTeX booktabs 表格的可追溯链。

### LaTeX 与 PDF

已实现最小 `ctexart` 源文件和在 PATH 中寻找 xelatex 后执行两次的编译门禁。结构检查仅验证文件头和极小尺寸；视觉和身份检查固定为 `not_run`。

缺口：本机 TeX 工具链缺失；没有 latexmk、完整中文论文、日志分层、页数、SHA-256、警告审计、预览页或逐页视觉验收。

### 复现与 provenance

现有 run manifest 记录部分环境、依赖、随机种子、输入哈希和产物路径。没有第二次清理派生输出后的真实重跑，也没有 JSON reproducibility report、图表源数据对比或二进制内容等价分类。

## Roadmap 与 Reviewer 开放问题

路线图实际位于 `docs/roadmap.md`（仓库根目录没有 `roadmap.md`）。Phase 1 标为完成，Phase 2 标为已实现但 PDF 依赖本机 XeLaTeX，Phase 3 是 assisted Skill 契约，真实赛题能力仍待评测。

`workspaces/phase2_demo/review/review_report.yaml` 尚有以下与本轮直接相关的开放问题：

1. PDF 编译、结构、逐页视觉和身份验收被阻断。
2. 模型选择的人工检查点未完成。
3. 独立 validator 代码、命令、哈希和单独运行清单未落盘。
4. workspace solver 只有包入口包装，公式到代码的审计链不足。

合成数据的泛化限制已标为 accepted risk，必须继续明确披露。

## 实施边界

本轮在现有架构中新增 Python-only core pipeline，不引入 Web UI、数据库、联网研究、RAG、多语言执行器或并行 Agent。环境和自动化验收可以推进到 `AWAITING_HUMAN_APPROVAL`；逐页视觉结论和最终定稿保留人工门禁。

## 2026-07-11 恢复后的完成审计

本节记录实施后的真实状态，不改写上面的修改前基线。

- Python：项目 `.venv` 为 3.12.13；numpy、pandas、scipy、matplotlib、pypdf、PyMuPDF 均由 `mmagent doctor` 检出。
- TeX：TeX Live 2026 full scheme 安装于 `D:/texlive/2026`；XeTeX `3.141592653-2.6-0.999998`、Latexmk 4.88，`ctexart`、`booktabs`、`graphicx`、`amsmath` 均可定位。中文环境验收 PDF 为 109,232 bytes，验收状态 `passed`。
- CLI：已新增并真实运行 `demo curve-fitting`、`run`、`compile`、`validate`、`reproduce`、core `status` 语义；旧 Phase 2 CLI 保持兼容。
- 执行：solver 与独立 validator 均以 `subprocess.run(..., shell=False)` 在 run-local 受控环境执行，保存命令、时间、退出码、stdout/stderr、输入/源码哈希和输出清单。
- 图表与表格：真实生成拟合图、残差图的 PNG/SVG，以及参数和误差指标的 CSV/LaTeX booktabs 表格。
- PDF：最新第二次 run 的 `paper/main.pdf` 为 4 页、315,529 bytes，PDF 头、页数、日志、缺图、引用、身份和绝对路径检查通过；overfull/underfull 警告均为 0，逐页预览未见裁切、重叠、黑块或缺字。
- 复现：首次 run `run-20260711t010935048946z` 与第二次 run `run-20260711t010942206919z` 的输入、源码、参数、指标、预测、图表源数据、生成文件集合和退出码条件全部通过；PDF 为二进制不同但内容等价。
- 测试：最终 `.venv/Scripts/python.exe -m pytest -ra` 实际收集 42 项，结果 `42 passed in 24.31s`，包含真实 XeLaTeX 集成、完整 demo 和第二次复现测试。
- Agent 与 workspace：`mmagent agent-doctor` 通过；`example_problem` 与 `phase2_demo` 的 `validate-workspace` 均通过；标准 core demo 状态为 `AWAITING_HUMAN_APPROVAL`，未进入 `FINAL`。
- Git：bundled Git 可读取工作树；当前仍是无提交的 `feature/core-python-pdf-pipeline`，全部项目文件为 untracked，没有可伪造的历史基线或提交级 diff。

仍未完成：用户最终批准、真实赛题前向评测、真实外部研究、CUMCM 2026 官方规则核验，以及 Phase 4 的受控自动化能力。
