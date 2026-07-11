# Agent 使用方式

MathModelAgent 2.0 当前是 Codex 驱动的本地 artifact workflow，不是需要 API Key 的独立在线服务。根目录 `AGENTS.md` 保存仓库级永久规则；`skills/` 保存可复用阶段工作流；`config/agent.yaml` 保存状态、路由、检查点和能力开关。

OpenAI 的 Codex 用例将重复工作流保存为 Skills；本仓库据此把阶段知识从巨型提示词拆成独立 Skill。官方入口：[Codex use cases](https://developers.openai.com/codex/use-cases)。

## 启动

在 Codex 中打开仓库后使用：

```text
读取 AGENTS.md 和 skills/modeling-orchestrator/SKILL.md，
以 assisted 模式检查 workspaces/<name>，只推进下一个可验证阶段。
```

若当前 Codex 环境已发现项目 Skills，也可显式调用：

```text
Use $modeling-orchestrator to inspect workspaces/<name> and advance only the next verified stage.
```

## 人工检查点

- `ANALYZED`：确认题意、子问题和关键假设。
- `MODEL_SELECTED`：确认 baseline、候选比较和选型理由。
- `VALIDATED`：确认验证范围、失败项和限制。
- `FINALIZED` 前：确认 PDF、匿名、格式和 Reviewer 问题全部闭环。

每次确认必须写入 workspace 的 `decisions.md`。未确认时保持当前状态，不用聊天中的默认同意代替落盘记录。

## Reviewer 隔离

Reviewer 必须使用新上下文，仅读取落盘产物，并将写权限限制在 `review/`。当前仓库定义了隔离契约，但没有自动启动并行 Reviewer；这符合默认禁用多 Agent 的能力配置。

