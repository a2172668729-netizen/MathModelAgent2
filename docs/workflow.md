# Workflow

第一阶段提供 workspace 生命周期操作和环境诊断。第二阶段加入受控执行闭环：准备好的模型与求解程序从 `MODEL_SELECTED` 开始，依次经过 `IMPLEMENTED`、`VALIDATED`、`PAPER_DRAFTED` 和 `PDF_COMPILED`。长期流水线仍依次为 ingest、analyze、data audit、model proposal、selection、implementation、validation、evidence writing、academic editing、fact check、LaTeX compile、format check、review 和 finalization。

每阶段必须声明输入文件、输出文件、成功标准、失败状态和重跑策略。人工确认记录时间、选择、理由和受影响产物。自动修订最多三轮，超过上限保留当前产物并输出未解决问题，不得无限循环。

`resume` 每次只根据落盘状态选择下一阶段，最多推进四步并停在编译门禁。求解失败记录 `FAILED/IMPLEMENTED`；验证失败记录 `FAILED/VALIDATED`；编译失败记录 `FAILED/PDF_COMPILED`。缺少 XeLaTeX 属于 `blocked` 验收结果，保留 `PAPER_DRAFTED`，方便环境修复后恢复。

## Python core 状态机

新增 core run 使用更细的真实产物门禁，同时保留旧 Phase 2/3 状态链：

```text
CREATED
-> INPUT_READY
-> CODE_READY
-> CODE_EXECUTED
-> RESULTS_VALIDATED
-> FIGURES_GENERATED
-> TABLES_GENERATED
-> PAPER_DRAFTED
-> PDF_COMPILED
-> PDF_VALIDATED
-> REPRODUCIBILITY_VALIDATED
-> AWAITING_HUMAN_APPROVAL
-> FINAL（仅显式人工批准）
```

任何阶段失败都记录 `FAILED` 和失败原因。状态函数只允许下一相邻门禁，禁止 Python 失败后进入 `CODE_EXECUTED`、PDF 失败后进入 `PDF_COMPILED`、未做第二次真实运行就进入 `REPRODUCIBILITY_VALIDATED`，也禁止自动进入 `FINAL`。
