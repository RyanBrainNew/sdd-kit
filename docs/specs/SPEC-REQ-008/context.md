# 需求上下文

- Work item: `SDD-WORKFLOW-001`
- Issue: https://github.com/RyanBrainNew/sdd-kit/issues/3

## 原始需求

issue #3 要求新增人工命令：

```powershell
python -m sdd upgrade-workflow --spec SPEC-ORDER-001 `
  --to l2-standard@2 --reason "统一到新门禁" --human
```

- 只允许人执行，强制 `--human`；
- 默认只允许升到更高 version；跨预设必须写明 reason；
- 原子替换 `docs/specs/<spec>/workflow.json`，同步 `state.json.workflow`；
- `workflow_history` 保留旧 name/version/digest/审批人与原因；
- 升级后重新校验现有 Gate，缺失的 Gate 进入 `inbox`；
- MCP 不暴露该人工动作；
- 同版本升级拒绝、降级默认拒绝、旧工件不被重写；
- 同步 README、`sdd/README.md`、`sdd/agent-contract.md`、版本与 manifest。

## 调研事实

- `create_workflow_snapshot()` 在新建 Spec 时写入 `workflow.json`，并把
  name/version/digest/snapshot 存入 `state.workflow`。
- `resolve_workflow()` 优先读取快照；快照 digest/version 与 state 不一致时直接报错，
  因此升级必须同时更新两处。
- 预设位于 `sdd/workflows/*.json`，`load_workflow_preset()` 会校验 schema 与
  `required_gates`；当前有 `l2-standard@1`、`l2-hotfix@1`、`l2-strict@1`、
  `l2-refactor@1`。
- `required_gates[state]` 给出当前状态应满足的 Gate 列表；
  `gate_report_status(gate_report_path(...))` 返回 PASS/缺失等状态。
- `inbox` 已汇总人工检查点、warn 和豁免；新增的缺失 Gate 可以作为独立 item 追加。
- 人工动作在 CLI 与状态机双重强制 `--human`，MCP 不暴露。
- 当前版本 `0.9.8`，manifest 50 文件；`sdd/scripts/sdd.py`、`sdd/cli.py`、
  `sdd/core.py` 均为受保护文件。

## 影响范围

- 核心：`sdd/scripts/sdd.py` 新增 `upgrade-workflow` 子命令、历史记录与 Gate 重校验。
- 编排：`sdd/core.py` 增加 `Workspace.upgrade_workflow()`，仍通过子进程调用。
- CLI：`sdd/cli.py` 注册命令并强制 `--human`。
- Inbox：读取最近一次升级的 pending gates，动态复核后展示。
- 测试：新增 `tests/test_upgrade_workflow.py`。
- 文档：README、执行手册、Agent 契约、版本与 manifest。

## 约束与排除

- 不实现任意 DAG 编辑、批量升级或 MCP 写工具。
- 不重写历史 Spec 的 spec/design/tasks/verification/gates 工件。
- 不为升级自动批准或伪造 Gate；缺失 Gate 只进入 inbox。
