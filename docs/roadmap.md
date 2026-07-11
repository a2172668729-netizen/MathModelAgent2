# Roadmap

## Phase 1 — foundation（已完成）

规格、上游审计、数据模型、workspace、benchmark、四个 CLI 和测试。

## Phase 2 — 最小闭环（已实现，PDF 编译依赖本机 XeLaTeX）

读取明确标记的 synthetic 示例；运行现成 Python 求解程序；保存输入哈希、环境和日志；独立重算结果；生成证据 Markdown 与最小 LaTeX；尝试 XeLaTeX 编译；输出验收记录。缺少编译器时状态为 `blocked`，不生成或冒充 PDF。

## Phase 3 — 分阶段能力（Agent 契约已实现，真实赛题能力待逐项评测）

已建立题意结构化、数据审计、候选模型、baseline、实现、验证、证据写作、学术审校和隔离 Reviewer Skills；默认 assisted，并由 `config/agent.yaml` 约束路由。下一步必须用获授权的真实赛题逐项前向评测，不能把 Skill 契约等同于已验证的竞赛解题能力。

## Python core 闭环（已实现并真实验证）

Windows 11 环境已安装并验证 TeX Live 2026 full scheme。`mmagent demo curve-fitting --workspace workspaces/curve_fitting_demo` 已真实完成两次隔离运行，生成 JSON/CSV、PNG/SVG、LaTeX 表格、完整中文论文、4 页 PDF、预览、manifest、独立验证和复现报告；关键数值在容差 `1e-10` 内一致，状态停在 `AWAITING_HUMAN_APPROVAL`。完整测试为 42/42 通过。

该里程碑仅验证 synthetic 曲线拟合工程链。真实赛题的自动读题、模型推荐、外部证据研究和竞赛质量论文仍未实现；最终人工审批仍未执行。

## Phase 4 — 自动化与评测（尚未实现）

引入有限 subagents、真实文献检索、benchmark 回归、失败恢复和受控 auto/research 模式。Web UI、RAG 和高级部署只有在 benchmark 证明必要时评估。
