# 工作流 Profile v2：可声明扩展与 workflow validate验证报告

## 1. 元数据

| 项 | 内容 |
|---|---|
| Spec ID | SPEC-REQ-002 |
| 工作项 ID | SDD-PROFILE-001 |
| 作者 | SDD Agent |
| 创建日期 | 2026-11-23T14:33:04+08:00 |
| 验证时间 | 2026-11-23T15:40:00+08:00 |

## 2. 命令

- 结构化命令证据由 `sdd verify` 追加；每条证据包含 Command/CWD/Exit/Head/Plan-Hash/At。

## 3. 结果

- schema 2 校验、阶段子序列、运行时规则、CLI 与 l2-refactor 预设的单元测试全部通过。
- 全量单元测试见第 2 节 `sdd verify` 的退出码与输出。
- `python -m sdd verify-core`、`python -m sdd verify-agent`、
  `python -m sdd check --all --stage ci --check-git` 在 LF 工作区通过。
- 历史 `SPEC-DEVTOOLS-002`、`SPEC-REQ-001` 的 workflow 快照 digest 未变化。

## 4. 未运行

- 本地未安装 `mcp` SDK 时，2 个 MCP 相关用例会跳过；GitHub Actions 安装
  `sdd/mcp/requirements.txt` 后执行。
- 未执行 `upgrade-workflow`；本 Spec Out-of-Scope。
- 未实现 warn/waiver、Review overlay、知识索引和 BAR/Fix Pattern；属于 issue #7
  的后续 P1/P2 工作。

## 5. AC 覆盖

| AC | 测试/证据 | 结果 |
|---|---|---|
| AC-001-1 | `WorkflowProfileTests#test_valid_v2_profile`：合法 v2 profile 校验通过并返回稳定 digest | PASS |
| AC-001-2 | `WorkflowProfileTests#test_unknown_fields_report_paths`、`WorkflowCliTests#test_workflow_validate_errors`：未知字段带路径报错 | PASS |
| AC-001-3 | `WorkflowProfileTests#test_schema1_snapshot_unchanged`、`test_old_specs_stay_stable`：schema 1 校验与 digest 不变 | PASS |
| AC-002-1 | `WorkflowStageTests#test_skip_design_stage`：省略 `DESIGN_READY` 后直接进入 `TASKS_READY` | PASS |
| AC-002-2 | `WorkflowStageTests#test_gate_or_checkpoint_conflict_rejected`：删除强制 Gate 或 approve/merge 被拒绝 | PASS |
| AC-002-3 | `WorkflowStageTests#test_invalid_stage_order_rejected`：重复、逆序、缺首尾阶段带索引报错 | PASS |
| AC-003-1 | `WorkflowRuntimeTests#test_gate_checks_filter_advisory`：裁剪 advisory、保留 required | PASS |
| AC-003-2 | `WorkflowRuntimeTests#test_extra_human_checkpoint`：额外 G3 人工检查点阻止自动完成 | PASS |
| AC-003-3 | `WorkflowRuntimeTests#test_risk_and_context_rules`：risk_stop 并集与 context_rules 裁剪/越界拒绝 | PASS |
| AC-004-1 | `WorkflowCliTests#test_workflow_validate_json`：合法 profile 返回 0 与 name/version/digest | PASS |
| AC-004-2 | `WorkflowCliTests#test_workflow_validate_errors`：缺失/非 JSON/未知字段返回非 0 且不写状态 | PASS |
| AC-005-1 | `WorkflowProfileTests#test_l2_refactor_flow`：l2-refactor 快照正确并可到 `PR_READY` | PASS |
| AC-005-2 | `WorkflowProfileTests#test_old_specs_stay_stable` + `check --all`：旧 Spec 快照与 Gate 结果不变 | PASS |
| AC-005-3 | `CiWorkflowTests#test_ci_workflow_runs_sdd_checks` + LF 工作区三项门禁 | PASS |

## 6. Gate 5 结论

PASS。schema 2 能力、CLI 和 l2-refactor 预设均有可复验测试；旧 schema 1 快照
保持兼容。残余风险是 `upgrade-workflow` 与 warn/waiver 等后续能力尚未实现，
已明确排除在本 Spec 范围外。

## 7. 独立审查

| 项 | 内容 |
|---|---|
| Reviewer | 独立审查会话（只读复核，非实现会话） |
| Session | review-spec-req-002 |
| Model | Codex 独立会话 |
| Findings | 复核 schema 2 校验、阶段跳过、gate_checks、human_checkpoints、risk_stop 与 context_rules。发现并修复三处问题：全量测试与站点版本徽章仍停留在 0.9.3、验证报告残留一次失败命令证据、`sdd/scripts/sdd.py` 的 `VERSION` 常量落后于 `sdd/VERSION`。修复后重新执行全量验证，未发现新的阻断项。 |
| Blocking issues | none |
