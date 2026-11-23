# 未决问题

- 是否把现有 `l2-standard`、`l2-hotfix`、`l2-strict` 升级为 schema 2？
  本 Spec 保持它们为 schema 1，避免既有 Spec 的 digest 与快照语义漂移；
  新能力通过新增 `l2-refactor` 示范，后续如需统一升级另立 Spec。
- `artifacts` 是否允许重命名 `spec.md` 等产物？本 Spec 不允许；检查函数、
  Gate 报告和模板都绑定固定产物名，重命名会扩大 diff 并破坏审计可读性。
- `gate_checks` 是否允许关闭 required 检查？不允许；只允许裁剪 advisory 检查，
  以免 profile 成为绕过强制检查的入口。
- `human_checkpoints` 是否允许移除 `approve`/`merge`？不允许；v2 只允许增加
  `complete_gate` 类型的人工确认，保持正常流程两个计划内检查点。
- 阶段跳过是否允许跨过已声明 Gate？不允许；校验阶段要求被跳过阶段对应的强制
  Gate 折叠到下一个已声明阶段，否则拒绝 profile。
