# 未决问题

- P1/P2 的排期与负责人不在本 Spec 内；本 Spec 只保证 P0 完成后，P1 的检查项注册表
  可以直接复用 P0 的稳定检查 ID，不需要重写 G0/G1 报告格式。
- 中高风险 Spec 的“独立 review 证据”沿用现有 `sdd/prompts/review.md` 与
  `verification.md` 的“独立审查”章节，不新增第二套 review 工件；如果后续 P1-3 引入
  技术栈 overlay，只需在现有 findings 结构上扩展，不改 G5 的阻断语义。
- `context_bundle` 的 `allowed_paths` 不新增必填文档：从 design 的“影响范围”和当前
  Task 的测试/命令派生；派生为空时返回空数组和范围提示，不静默扩大到其他 Spec。
- issue #7 的 epic 编号没有单独的工作项系统 ID，本 Spec 以 `SDD-EPIC-007` 作为
  可追溯工作项；P1/P2 另立 Spec 时会使用不同的工作项 ID。
