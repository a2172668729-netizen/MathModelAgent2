# Risk register

| 风险 | 严重度 | 早期信号 | 缓解措施 |
|---|---:|---|---|
| 题意解析错误 | critical | 子问题或约束缺失 | assisted 检查点、benchmark 硬错误 |
| 数字或引用幻觉 | critical | 论文值无法映射到结果 | 结构化证据、事实一致性门禁 |
| 2026 格式未发布或变更 | high | 无官方来源 | provisional 标记、年度隔离 |
| 身份信息泄露 | critical | PDF 含学校/姓名 | 文本扫描、视觉复核、硬错误 |
| 上游许可证冲突 | high | 复制无清晰许可文件 | 固定 commit、许可台账、仅设计参考 |
| Windows/macOS 差异 | medium | 路径或字体失败 | pathlib、doctor、双平台 CI |
| 自动修订失控 | high | 重复改写或事实漂移 | 最多三轮、受保护字段 diff |
| 生成代码不安全 | critical | 非受控网络/文件访问 | 后续沙箱与资源策略；第一阶段不执行 |

