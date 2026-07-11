# 故意失败诊断夹具

该案例不是能力基准，而是验证 Runner 在求解器真实非零退出时能否终止状态机、保留 stdout/stderr、退出码和 diagnostic.json。它不得进入正常 full 基线。
