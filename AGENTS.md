# Repository operating rules

1. 修改前先读取相关文件，并保持变更范围与当前任务一致。
2. 不得声称未执行的代码、测试、编译或检查已经执行。
3. 不得伪造数据、运行结果、论文、文献或引用。
4. 不得用空模板、空函数或大量 TODO 冒充完成能力。
5. 论文中的数字只能来自可追溯的结构化结果或真实来源。
6. Academic Humanizer 只能改变表达，不得改变事实、公式、数值、变量、引用、图表编号或实验结论。
7. 社区模板不得冒充当年官方竞赛模板；未核实规则必须标为 provisional。
8. 需求或证据冲突写入 `docs/decision_log.md`。
9. 每次代码变更运行相应测试；未能运行时如实记录原因。
10. 避免无关重构，不覆盖用户已有文件，不执行危险删除。
11. 使用 `pathlib.Path`，不得硬编码 Windows、macOS 或个人目录。
12. 不提交 API Key、个人身份信息、虚拟环境、大型数据、模型和缓存。
13. 自动生成的 PDF 必须经过真实编译、结构检查和逐页视觉验收后才能标为 final。
14. Reviewer 必须与前序 writer 的上下文和写权限隔离；审阅证据来自落盘产物。
15. 无法完成的检查标记为 `not_run` 或 `blocked`，不得降格为通过。

第一阶段不得实现完整自动建模、联网研究、API 接入、RAG、Web UI、数据库服务、多 Agent 并行或论文生成。

## MathModelAgent routing

第一阶段已经完成。后续默认仍采用 `assisted`，不因进入 Phase 2/3 自动获得联网、API、RAG、Web UI、数据库或并行 Agent 权限。

当用户要求开始、继续或恢复完整数模 workspace 时：

1. 先读取 `skills/modeling-orchestrator/SKILL.md`。
2. 根据落盘状态只调用下一阶段 Skill：`problem-analysis`、`data-audit`、`model-design`、`implementation`、`validation`、`report-writing`、`academic-humanizer-zh`。
3. 模型选择、关键假设、验证结论和定稿必须经过人工检查点。
4. Reviewer 使用 `skills/reviewer/SKILL.md`，必须从隔离上下文读取落盘产物，且只能写 `review/`。
5. Skill 指令不得覆盖本文件的证据、测试、路径、PDF 和安全规则。

