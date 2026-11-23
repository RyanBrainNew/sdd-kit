# 需求上下文

- Work item: `SDD-GATE-002`
- Issue: https://github.com/RyanBrainNew/sdd-kit/issues/7

## 原始需求

issue #7 的 P1-2：Gate 检查项注册表与 `pass/warn/block`。要求每项检查有稳定
ID、所属 Gate、触发方式、级别、可豁免性、证据要求和责任角色；建议项失败只告警，
强制项失败阻断，安全红线不可降级；新增人工豁免并记录范围、原因、审批人、
到期时间和证据；Gate 报告、`inbox` 与 `metrics` 能按检查 ID 追溯。

## 调研事实

- `CHECK_REGISTRY` 当前只有 G0/G1 的 11 个检查，字段为 id/gate/name/level/
  trigger/waivable/evidence/owner，没有 `redline` 和触发方式枚举校验。
- `run_gate_checks()` 当前只把结果分为 `pass` 和 `block`，并把所有失败都
  汇总为错误；`check_gates()` 要求报告总体结果严格等于 `PASS`。
- G2–G5 仍由 `command_complete()` 内的手工检查驱动，尚未进入注册表；
  对应 `record_gate()` 调用使用临时检查元组，没有稳定检查 ID。
- `build_inbox_item()` 每个 Spec 最多返回一个人工事项；Gate 告警目前不可见。
- `compute_spec_metrics()` 按事件统计 lead time、rewind、人工介入和 Gate
  失败次数，没有按检查 ID 的 pass/warn/block/waived 维度。
- `command_merge()` 会再次执行 CI 检查；任何 block 都必须在这里继续阻断。
- `sdd/cli.py` 暴露 CLI，MCP 适配器不包含状态机规则；人工动作通过
  `--human` 强制，且 MCP 不注册 `approve/merge/unblock/rewind`。
- `start-work` 当前会把工作项行错误追加到 `docs/prd-index.md` 的 FEAT 映射表
  末尾，这是已知工具缺陷；本 Spec 需要修正当前数据行，但不扩大为工具重构。
- 当前测试基线：`tests/test_sdd.py` 的 CheckRegistryTests、MetricsTests、
  InboxTests、GateEvidenceTests；`tests/test_cli.py`；`tests/test_ci_contract.py`。

## 影响范围

- 核心：`sdd/scripts/sdd.py` 的注册表、Gate 检查执行、报告、inbox、metrics
  和人工豁免命令。
- CLI：`sdd/cli.py` 新增 `waive` 参数和输出。
- 状态：`state.json` 增加 CLI 写入的 waiver 审批记录；不手改。
- 文档：README、`sdd/README.md`、`sdd/agent-contract.md`、相关 prompts。
- 发布：`sdd/VERSION`、`sdd/__init__.py`、`sdd/manifest.json`。

## 约束与排除

- 不新增服务端、数据库、常驻进程或第三方依赖。
- 不实现 Review overlay、知识索引、BAR/Fix Pattern 或 P1/P2 其他范围。
- 不迁移历史 Gate 报告，不改变既有 Spec 的 Gate 结果和 digest。
- 不允许 Agent 调用 `waive`，也不允许 MCP 暴露该动作。
