# 写 Spec

目标：把工作项需求变成一份可验收、可拆任务、可测试的 `spec.md`，并满足公司 Gate 0/G1 的工件要求。

1. 读工作项/原始需求、仓库 `AGENTS.md`、`docs/prd-index.md`、相关领域文档和代码。
2. 使用项目术语，不要发明同义词；需求有歧义时不要猜，标记 `[NEEDS CLARIFICATION]` 并停下问一个阻塞问题。
3. 元数据中的 Spec ID 必须与目录名一致，工作项 ID 不带前导 `%`。
4. 每条 FR 用 `FR-001`，每条 AC 用 `AC-001-1`；AC 编号前缀必须对应 FR 编号。
5. 每条 AC 必须是可观察行为，并在同一条定义中写 `Given ... When ... Then ...` 和【执行路径：本地单元测试/人工评审/...】。
6. In-Scope / Out-of-Scope 都必须有可判定边界，禁止“等、尽量、合理、酌情”等模糊表述。
7. 不在 spec 里写具体文件路径和代码片段；这些属于 design。
8. 填完删除本文件的 TODO 注释，运行 `python sdd/scripts/sdd.py check --stage spec`。
9. 不要运行 `sdd approve`；这是人类的确认动作。
