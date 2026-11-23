# SPEC-REQ-003 SDD-GATE-002

## Spec 文件

- `docs/specs/SPEC-REQ-003/spec.md`
- Issue: `https://github.com/RyanBrainNew/sdd-kit/issues/7`

## Spec Item 列表

- AC-001-1
- AC-001-2
- AC-001-3
- AC-002-1
- AC-002-2
- AC-002-3
- AC-002-4
- AC-003-1
- AC-003-2
- AC-003-3
- AC-003-4
- AC-004-1
- AC-004-2
- AC-004-3
- AC-005-1
- AC-005-2
- T-001 扩展 G0–G5 检查项注册表，增加 redline、触发方式和严格元数据校验
- T-002 实现 pass/warn/block、红线优先和 Gate 报告分级渲染
- T-003 新增人类 `waive`，绑定检查、产物哈希与到期时间并自动重校验
- T-004 让 inbox 展示 Gate 告警，并让 metrics 按检查 ID 聚合结果
- T-005 同步 CLI/MCP 边界、文档、版本、manifest 和发布兼容验证

## 变更说明

- 高层方案：在 `sdd/scripts/sdd.py` 内把“检查定义、执行、结果分级、豁免判定、
  报告渲染、指标解析”收口为一条链路。注册表新增 `redline` 与允许触发方式；
  G2–G5 的现有校验函数转为注册检查；所有 Gate 都通过 `run_gate_checks()`
  得到结构化行。required 失败默认 `block`，advisory 失败默认 `warn`；
  redline 无条件 `block`；有效豁免只把指定 required 行降为 `warn`。
- 关键决策：
  1. 保留既有 G0/G1 ID 与检查含义，只补充字段；新增 G2–G5 使用同 Gate
     内稳定编号，避免历史报告失效。
  2. `redline` 是独立布尔字段，不依赖 `waivable` 推测；`waivable=true` 且
     `redline=true` 注册表校验直接失败。首批将 G5 可复验证据设为证据链红线。
  3. 豁免绑定 `check_id + gate + Spec + Gate 产物哈希 + expires_at`；
     产物变化或到期即失效，不提供 Spec 级豁免。
  4. Gate 总体结果仍是 `PASS/FAILED`：只有 block 使结果 `FAILED`；
     warn 保留在报告和指标中，避免改变 `gate_report_status()` 的历史语义。
  5. `metrics` 和 `inbox` 读取当前每个 Gate 的最新 Markdown 报告，兼容
     旧五列表格；不补写历史报告，不新增数据库。
  6. `waive` 是 CLI 人工动作，强制 `--human`；MCP 不新增工具，也不复制
     Gate 或状态规则。
- 方案对比：
  - 把 warn 写成 Gate 失败并靠人工忽略：仍会阻断流转，违反验收，放弃。
  - 用新的 `waivers.json` 独立存储：增加工件和哈希同步复杂度；复用
    `state.json.waivers` 并由 CLI 写入更符合唯一状态机，采用。
  - 为豁免做 Spec 级开关：范围过大且容易绕过多项检查，放弃。
  - 只在报告文本中记录豁免：无法自动判断到期和产物变化，放弃。

## AC 验证清单

| AC | Task | Evidence |
| --- | --- | --- |
| AC-001-1 | T-001 | 见 `docs/specs/SPEC-REQ-003/verification.md` |
| AC-001-2 | T-001 | 见 `docs/specs/SPEC-REQ-003/verification.md` |
| AC-001-3 | T-001 | 见 `docs/specs/SPEC-REQ-003/verification.md` |
| AC-002-1 | T-002 | 见 `docs/specs/SPEC-REQ-003/verification.md` |
| AC-002-2 | T-002 | 见 `docs/specs/SPEC-REQ-003/verification.md` |
| AC-002-3 | T-002 | 见 `docs/specs/SPEC-REQ-003/verification.md` |
| AC-002-4 | T-002 | 见 `docs/specs/SPEC-REQ-003/verification.md` |
| AC-003-1 | T-003 | 见 `docs/specs/SPEC-REQ-003/verification.md` |
| AC-003-2 | T-003 | 见 `docs/specs/SPEC-REQ-003/verification.md` |
| AC-003-3 | T-003 | 见 `docs/specs/SPEC-REQ-003/verification.md` |
| AC-003-4 | T-003 | 见 `docs/specs/SPEC-REQ-003/verification.md` |
| AC-004-1 | T-004 | 见 `docs/specs/SPEC-REQ-003/verification.md` |
| AC-004-2 | T-004 | 见 `docs/specs/SPEC-REQ-003/verification.md` |
| AC-004-3 | T-004 | 见 `docs/specs/SPEC-REQ-003/verification.md` |
| AC-005-1 | T-005 | 见 `docs/specs/SPEC-REQ-003/verification.md` |
| AC-005-2 | T-005 | 见 `docs/specs/SPEC-REQ-003/verification.md` |

## 命令与结果

- Evidence recorded: Command: python -m unittest discover -s tests -v

## 未运行 / Not run

None。

## 风险与回滚

| 风险/依赖 | 影响 | 缓解措施 | 负责人 |
|---|---|---|---|
| 注册表扩展到 G2–G5 改变既有 Gate 行为 | 旧 Spec 可能新增失败 | 保留原检查逻辑与 ID；旧 Spec 全量回归；warn 不阻断 | sdd-kit 平台维护者 |
| 豁免范围实现错误 | 可能绕过不该绕过的检查 | 只匹配指定检查 ID + Gate + Spec + 产物哈希；redline 双保险 | sdd-kit 平台维护者 |
| 报告表格变更破坏解析 | inbox/metrics 无法读取 | 解析器兼容五列/六列和旧结果值 | sdd-kit 平台维护者 |
| `waive` 被 Agent 调用 | 人工边界失效 | CLI `--human`；MCP 不注册；负向测试 | sdd-kit 平台维护者 |
| 期限与时钟差异 | 豁免过早或过晚失效 | 统一 `parse_timestamp()` 和本地时区比较 | sdd-kit 平台维护者 |

## Gate 记录

# Gate 记录

| Gate | State | Mode | Result | Evidence | At |
| --- | --- | --- | --- | --- | --- |
| G0 | SPEC_READY | manual | PASS | 需求已确认 | 2026-11-23T17:04:57+08:00 |
| G1 | SPEC_READY | auto | PASS | spec check passed | 2026-11-23T17:04:57+08:00 |
| G2 | DESIGN_READY | auto | PASS | design.md: registry, waiver, report, inbox and metrics design checked | 2026-11-23T17:17:10+08:00 |
| G3 | TASKS_READY | auto | PASS | tasks.md: 5 vertical tasks with AC test mapping checked | 2026-11-23T17:20:25+08:00 |
| G4 | VERIFYING | auto | PASS | all tasks completed | 2026-11-23T18:16:36+08:00 |
| G5 | PR_READY | auto | PASS | verification.md submitted via CLI and checked | 2026-11-23T18:28:16+08:00 |

## 证据

- `docs/specs/SPEC-REQ-003/verification.md`
- `docs/specs/SPEC-REQ-003/gates.md`
- `sdd/reports/SPEC-REQ-003/gate1-report.md`
- `sdd/reports/SPEC-REQ-003/gate2-report.md`
- `sdd/reports/SPEC-REQ-003/gate3-report.md`
- `sdd/reports/SPEC-REQ-003/gate4-report.md`
- `sdd/reports/SPEC-REQ-003/gate5-report.md`
