# 需求上下文

- Work item: `SDD-PROFILE-001`
- Issue: https://github.com/RyanBrainNew/sdd-kit/issues/7

## 原始需求

issue #7 的 P1-1：把工作流预设扩展为可声明、可校验的 Profile v2，让使用者只新增
一个 profile 文件即可定义新流程，不改核心状态机；同时提供 `workflow validate`，
未知字段、未知检查 ID、非法阶段和非法人工动作必须显式失败。

## 调研事实

- `sdd/scripts/sdd.py` 的 `WORKFLOW_SCHEMA` 当前为 `1`；`validate_workflow_preset`
  要求 `stages` 必须等于固定 `STAGE_ORDER`，且 `required_gates` 必须等于
  `workflow_defaults()`，因此当前无法声明阶段子序列或自定义 Gate 组合。
- 当前校验只检查已知字段的取值，未拒绝未知顶层字段；未知嵌套字段也不会报错。
- `load_workflow_preset` 校验 name 与文件名一致；`create_workflow_snapshot`
  把完整 profile 写入 `docs/specs/<Spec>/workflow.json`；
  `resolve_workflow` 用快照 digest/version 与 `state.json.workflow` 比对。
- 现有 `l2-standard`、`l2-hotfix`、`l2-strict` 都是 schema 1；旧 Spec
  `SPEC-DEVTOOLS-002`、`SPEC-REQ-001` 的快照也是 schema 1，必须继续通过校验。
- 检查项注册表位于 `CHECK_REGISTRY`，由 `validate_check_registry` 校验；
  `run_gate_checks(gate, ctx)` 当前会执行该 Gate 的全部注册检查。
- `context_bundle` 的 `allowed_paths` 从 design 的“影响范围”和当前 Task 派生；
  默认排除其他 Spec，未提供 profile 级 include/exclude 规则。
- CLI 由 `sdd/cli.py` 提供 `python -m sdd`；当前没有 `workflow` 子命令。
- 相关测试：`tests/test_sdd.py` 的 workflow 快照、hotfix、strict 与检查项注册表用例；
  `tests/test_cli.py` 覆盖 CLI 参数与错误码；`tests/test_ci_contract.py` 覆盖 CI 门禁。
- 项目只允许 Python 标准库；核心变更必须同步测试、README、`sdd/README.md`、
  `sdd/agent-contract.md`、版本和 manifest。

## 影响范围

- 核心：`sdd/scripts/sdd.py` 的 profile 校验、阶段推进、Gate 检查选择、
  人工检查点、风险标签和 context bundle 规则。
- CLI：`sdd/cli.py` 新增 `workflow validate`。
- 预设：新增 `sdd/workflows/l2-refactor.json`；现有三个预设保持不变。
- 测试：新增 schema v2、非法 profile、阶段跳过、gate_checks、human_checkpoints、
  context_rules 与旧快照兼容用例。
- 文档：`README.md`、`docs/GUIDE.md`、`sdd/README.md`、`sdd/agent-contract.md`。
- 发布：`sdd/VERSION`、`sdd/__init__.py`、`sdd/manifest.json`。

## 约束与排除

- 不支持任意 DAG、脚本化状态机、服务端或第三方依赖。
- 不重命名现有产物文件；不实现 `upgrade-workflow`。
- 不实现 P1-2 的 warn/waiver、P1-3 的 Review overlay、P2 的知识索引与 BAR。
- 不手改 `state.json`、`events.jsonl` 或 profile 快照。
- 旧 Spec 的快照、digest 和 Gate 结果不得因新增 profile 而变化。
