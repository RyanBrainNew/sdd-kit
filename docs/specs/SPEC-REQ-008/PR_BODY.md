# SPEC-REQ-008 固定预设升级 upgrade-workflow

## Spec 文件

- `docs/specs/SPEC-REQ-008/spec.md`
- Issue: `https://github.com/RyanBrainNew/sdd-kit/issues/3`

## Spec Item 列表

- AC-001-1
- AC-001-2
- AC-001-3
- AC-001-4
- AC-001-5
- AC-002-1
- AC-002-2
- AC-002-3
- AC-003-1
- AC-003-2
- AC-003-3
- AC-004-1
- AC-004-2
- AC-004-3
- T-001 实现 `upgrade-workflow` 状态机命令、Workspace/CLI 入口、历史与原子写入
- T-002 实现升级后的 Gate 重校验、pending_gates 与 inbox 展示
- T-003 同步 README、执行手册、Agent 契约、版本与 manifest

## 变更说明

- 高层方案：在 `sdd/scripts/sdd.py` 新增 `command_upgrade_workflow`。它解析
  `--to <name>@<version>`，校验人工身份、reason、版本方向与目标预设，然后
  备份旧快照、原子写入新快照，追加 `state.workflow_history` 与 `history`，
  最后调用 `save_state()` 写入 state 并追加事件；失败时恢复旧快照与旧 state。
- 关键决策：
  1. 目标预设必须已存在于 `sdd/workflows/`，`@version` 与预设 version 严格一致。
  2. 同预设同版本拒绝；降级仅允许 `--allow-downgrade` + `--design-change`。
  3. 跨预设允许，但 reason 必填并记录来源/目标 name。
  4. 升级后用目标预设的 `required_gates[当前状态]` 复核 Gate，未 PASS 的 Gate
     写入 `workflow_history[-1].pending_gates`，不写报告、不推进状态。
  5. `inbox` 动态复核 pending gates：仍缺失则展示，已有 PASS 报告则自动消失。
  6. `Workspace.upgrade_workflow()` 通过子进程调用状态机；CLI 再强制 `--human`。
  7. 旧工件只读；升级仅改 `workflow.json`、`state.json`、`events.jsonl`。
- 方案对比：
  - 直接改 `state.workflow` 不换快照：`resolve_workflow()` 会报 digest 不一致，放弃。
  - 创建新 Spec：丢失原 Spec 的审批、任务和证据链，放弃。
  - 在 MCP 暴露升级：违反人工动作边界，放弃。

## AC 验证清单

| AC | Task | Evidence |
| --- | --- | --- |
| AC-001-1 | T-001 | 见 `docs/specs/SPEC-REQ-008/verification.md` |
| AC-001-2 | T-001 | 见 `docs/specs/SPEC-REQ-008/verification.md` |
| AC-001-3 | T-001 | 见 `docs/specs/SPEC-REQ-008/verification.md` |
| AC-001-4 | T-001 | 见 `docs/specs/SPEC-REQ-008/verification.md` |
| AC-001-5 | T-001 | 见 `docs/specs/SPEC-REQ-008/verification.md` |
| AC-002-1 | T-001 | 见 `docs/specs/SPEC-REQ-008/verification.md` |
| AC-002-2 | T-001 | 见 `docs/specs/SPEC-REQ-008/verification.md` |
| AC-002-3 | T-001 | 见 `docs/specs/SPEC-REQ-008/verification.md` |
| AC-003-1 | T-002 | 见 `docs/specs/SPEC-REQ-008/verification.md` |
| AC-003-2 | T-002 | 见 `docs/specs/SPEC-REQ-008/verification.md` |
| AC-003-3 | T-002 | 见 `docs/specs/SPEC-REQ-008/verification.md` |
| AC-004-1 | T-001 | 见 `docs/specs/SPEC-REQ-008/verification.md` |
| AC-004-2 | T-003 | 见 `docs/specs/SPEC-REQ-008/verification.md` |
| AC-004-3 | T-001 | 见 `docs/specs/SPEC-REQ-008/verification.md` |

## 命令与结果

- 全量测试命令：`python -m unittest discover -s tests -v`
- 升级定向测试：`python -m unittest tests.test_upgrade_workflow -v`
- 核心与 Agent 校验：`python -m sdd verify-core`、`python -m sdd verify-agent`
- 结构化证据：`docs/specs/SPEC-REQ-008/verification-evidence.jsonl`

- Evidence recorded: Command: python -m unittest discover -s tests -v

## 未运行 / Not run

None。未执行批量升级、任意 DAG 编辑或 MCP 写工具，均不在本 Spec 范围。

## 风险与回滚

| 风险 | 影响 | 缓解 | 负责人 |
|---|---|---|---|
| 预设 version 与内容不同步 | 升级后 digest 混乱 | 强制 version 匹配并校验 digest | 平台维护者 |
| 写 state 失败 | 快照与 state 不一致 | 备份+恢复旧快照/state | 平台维护者 |
| pending gate 记录过期 | inbox 误导 | 每次动态复核报告状态 | 平台维护者 |
| 跨预设门禁收紧 | 当前阶段突然阻断 | 升级提示 pending gates，人工补 Gate | 平台维护者 |
| 误用降级 | 门禁被放宽 | 强制 design-change 并写历史 | 平台维护者 |

## Gate 记录

# Gate 记录

| Gate | State | Mode | Result | Evidence | At |
| --- | --- | --- | --- | --- | --- |
| G0 | SPEC_READY | manual | PASS | 需求已确认 | 2026-11-24T17:45:22+08:00 |
| G1 | SPEC_READY | auto | PASS | spec check passed | 2026-11-24T17:45:22+08:00 |
| G2 | DESIGN_READY | auto | PASS | design.md submitted via CLI and checked | 2026-11-24T17:48:12+08:00 |
| G3 | TASKS_READY | auto | PASS | tasks.md submitted via CLI and checked | 2026-11-24T17:50:01+08:00 |
| G4 | VERIFYING | auto | PASS | all tasks completed | 2026-11-24T17:58:34+08:00 |
| G5 | PR_READY | auto | PASS | verification.md submitted via CLI and checked | 2026-11-24T18:19:25+08:00 |

## 证据

- `docs/specs/SPEC-REQ-008/verification.md`
- `docs/specs/SPEC-REQ-008/gates.md`
- `sdd/reports/SPEC-REQ-008/gate1-report.md`
- `sdd/reports/SPEC-REQ-008/gate2-report.md`
- `sdd/reports/SPEC-REQ-008/gate3-report.md`
- `sdd/reports/SPEC-REQ-008/gate4-report.md`
- `sdd/reports/SPEC-REQ-008/gate5-report.md`
