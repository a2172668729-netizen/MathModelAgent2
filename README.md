# MathModelAgent 2.0

面向全国大学生数学建模竞赛（CUMCM）的可复现建模工作台。长期目标是从赛题与附件出发，执行分析、建模、代码求解、验证、证据驱动写作和 PDF 验收；当前保留 Phase 1～3 架构，并新增 Python-only 的曲线拟合真实闭环。

## 当前可用能力

- `mmagent new <problem_id>`：创建独立的真实历史题 workspace；接入流程见 [`docs/real_problem_readiness.md`](docs/real_problem_readiness.md)。
- `mmagent audit-input / advance / results-macros / benchmark`：盘点原始材料、执行证据门禁、生成可追溯论文宏并维护人工评分表。
- `mmagent init <workspace>`：安全创建标准 workspace，不覆盖已有文件。
- `mmagent status <workspace>`：只读显示阶段、已完成阶段和缺失产物。
- `mmagent validate-workspace <workspace>`：校验目录、YAML 数据模型和相对引用路径。
- `mmagent doctor`：只读检查 Python、Git、XeLaTeX、PDF 工具、字体、依赖和目录可写性。
- `mmagent demo <workspace>`：创建明确标记为 synthetic 的工程示例并运行到 PDF 编译门禁。
- `mmagent run-solver / validate-results / render-report / compile-report`：逐阶段运行已有求解程序、独立验证、生成证据报告并尝试真实编译。
- `mmagent resume <workspace>`：从落盘状态恢复下一步，重试范围有界。
- `mmagent agent-doctor`：验证 Agent 状态链、九个 Skill、UI 元数据、能力开关、选型策略和 final 门禁。
- `mmagent demo curve-fitting --workspace <path>`：真实执行 Python、独立验证、生成 PNG/SVG、CSV/LaTeX 表格、中文论文、PDF 和第二次复现报告。
- `mmagent run / compile / validate / reproduce / status`：操作 Python-only core run；自动流程最多停在 `AWAITING_HUMAN_APPROVAL`。
- Pydantic 结构化模型、CUMCM 2026 临时规范层、benchmark 评分框架。

第二阶段不会生成模型代码，也不会把合成示例当作竞赛结果。尚未实现自动读题、模型推荐、联网研究、完整论文生成和多 Agent。见 [路线图](docs/roadmap.md)。

Phase 3 已提供一个 assisted Orchestrator、七个阶段 Skill、Academic Humanizer 和隔离 Reviewer 契约。使用方式见 [Agent 使用说明](docs/agent_usage.md)。这些 Skills 由 Codex 对本地 artifacts 执行，不接 OpenAI API。

## Python 到 PDF 完整 demo

在已激活 `.venv` 且 XeLaTeX/latexmk 位于 PATH 时运行：

```powershell
mmagent doctor
mmagent demo curve-fitting --workspace workspaces/curve_fitting_demo
mmagent status workspaces/curve_fitting_demo
mmagent validate workspaces/curve_fitting_demo
```

`demo curve-fitting` 会连续创建第一次真实 run 和第二次真实复现 run。输入数据与正式源码保存在 workspace 根目录并复制进每个隔离 run；第二次运行不会复制第一次的派生结果。成功状态为 `AWAITING_HUMAN_APPROVAL`，程序没有自动进入 `FINAL`。

单步命令：

```powershell
mmagent run workspaces/curve_fitting_demo
mmagent compile workspaces/curve_fitting_demo --run-id <run_id>
mmagent validate workspaces/curve_fitting_demo --run-id <run_id>
mmagent reproduce workspaces/curve_fitting_demo --run-id <run_id>
```

详细产物和门禁见 [完整 demo 说明](docs/core_pipeline_demo.md) 与 [复现说明](docs/reproducibility.md)。

当前仓库已在 Windows 11 上真实完成一次标准 workspace 验收：两次隔离 run 均生成数值结果、PNG/SVG、CSV/LaTeX 表格和 4 页中文 PDF，第二次 run 停在 `AWAITING_HUMAN_APPROVAL`；完整测试为 42/42 通过。TeX Live 安装与中文编译证据见 [TeX 环境验收报告](docs/tex_environment_report.md)。该结果只证明 synthetic 工程闭环，不代表真实竞赛建模能力。

## Phase 2 最小闭环

```powershell
mmagent demo workspaces/phase2_demo
mmagent status workspaces/phase2_demo
```

`demo` 实际执行 workspace 内的 `code/solve.py`，保存输入哈希、环境、日志、实验结果和验证记录。若 PATH 中没有 XeLaTeX，命令以退出码 `2` 停在 `PAPER_DRAFTED`，并写入 `reports/pdf_acceptance.yaml` 的 `blocked` 状态；不会伪造 PDF 或标记 final。详细契约见 [Phase 2 说明](docs/phase2_contract.md)。

## Windows 开发

要求 Python 3.11 或以上。不要把系统 Python、Git 或 TeX 路径写入业务代码。

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest
mmagent doctor
```

TeX Live 2026 安装到 `D:\texlive\2026` 且不持久修改 PATH 时，可在当前 PowerShell 会话执行：

```powershell
$env:MMAGENT_TEX_BIN = 'D:\texlive\2026\bin\windows'
$env:Path = "$env:MMAGENT_TEX_BIN;$env:Path"
where.exe xelatex
where.exe latexmk
mmagent doctor
```

完整 Windows 与 TeX 步骤见 [Windows setup](docs/windows_setup.md)。`doctor` 本身不会安装软件或修改环境变量。

## macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -m pytest
mmagent doctor
```

所有 workspace 路径均通过 `pathlib.Path` 相对解析。虚拟环境、大型数据、缓存、私密信息和实验大文件不进入 Git。

## 竞赛规范边界

本仓库区分三层：年度官方规范、模板实现、赛题内容。`competition_profiles/cumcm/2026/official_spec.yaml` 当前明确标记为 `provisional`；在官方来源核实前，任何社区模板都不得声称符合 2026 官方要求。
