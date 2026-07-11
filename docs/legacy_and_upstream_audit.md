# Legacy and upstream audit

## 本地仓库原始状态

检查时项目根目录仅有空的 `.agents/`、`.codex/` 和 `.git/` 目录，没有旧版源代码或说明文件。因此本项目从零开始，没有可直接迁移的本地 legacy 实现。系统 PATH 没有 Git；恢复任务时确认 Codex 工作区运行时提供 Git 2.53.0，并已用该明确路径真实初始化本地 `main` 仓库。没有安装系统 Git，也没有修改 PATH。

## 上游结论

### jihe520/MathModelAgent

固定提交 `be9c59c1aaa13c3dcb74452ea5cae11dada27589`。实际主线包含分阶段 Skills、结果报告驱动写作、Typst/LaTeX 模板和验收 Skill。可参考阶段边界、图表规划、结果门禁和模板选择。README 同时列出 benchmark、HIL、feedback、RAG 等未完成项，不能按功能清单默认已实现。

许可证不是 OSI 标准许可证；`docs/md/License.md` 限定个人免费、禁止商业用途、禁止闭源分发和在其上提供商业服务。因此本项目不复制其代码、模板或 Skill 文本，只记录设计启发。

### op7418/Humanizer-zh

固定提交 `91f3d394db8419c20d67ebe22a96cf8fee0a404b`，MIT。其 SKILL 定义了 24 类常见 AI 写作模式。删除空泛意义、宣传语言、模糊归因和机械排比适合学术适配；“增加个人声音、第一人称、情绪、允许混乱”等规则不适合 CUMCM 论文。当前 `academic-humanizer-zh` 为重新设计，不复制原 Skill 全文。

### leaf-hsiao/cumcmthesis

固定提交 `aceadc56666d75a80081694c1538512dbc53cc18`。README 明确它是 2016 模板、基于 2015 格式、使用 XeLaTeX。类文件包含学校、队员和指导教师等旧式字段，且根目录未发现许可证。仅作为历史证据，不作为 2026 官方规范或可复用模板。

## 复用分类

- 可保留：无本地 legacy 内容。
- 可适配：阶段化产物、结果驱动写作、有限验收循环、学术表达清理原则。
- 不可直接复用：限制性或无许可证上游内容、旧年份模板、声称未完成的功能、面向博客的“个人化”写法。

详细来源与风险见 `references/upstream_repositories.yaml`。
