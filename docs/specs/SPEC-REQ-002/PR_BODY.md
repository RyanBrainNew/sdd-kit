# SPEC-REQ-002 工作流 Profile v2：可声明扩展与 workflow validate

## Spec 文件

- `docs/specs/SPEC-REQ-002/spec.md`
- Issue: `https://github.com/RyanBrainNew/sdd-kit/issues/7`

## Spec Item 列表

- AC-001-1
- AC-001-2
- AC-001-3
- AC-002-1
- AC-002-2
- AC-002-3
- AC-003-1
- AC-003-2
- AC-003-3
- AC-004-1
- AC-004-2
- AC-005-1
- AC-005-2
- AC-005-3
- T-001 增加 schema 2 校验、严格字段白名单和 workflow validate 核心入口
- T-002 实现阶段子序列校验与安全跳过，保留强制 Gate 和人工检查点
- T-003 让 gate_checks、human_checkpoints、risk_stop、context_rules 在运行时生效
- T-004 新增 `workflow validate` CLI，输出结构化结果与字段错误
- T-005 新增 l2-refactor 示范 profile，并同步文档、版本、manifest 与兼容测试

## 变更说明

- 高层方案：在唯一状态机内把 profile 校验拆成 v1 与 v2 两条路径；
  `validate_workflow_preset` 按 `schema` 分派。v1 保持现有逻辑不变，v2 增加
  严格字段白名单、阶段子序列、检查项选择、人工检查点、风险标签和上下文规则。
  运行时仍由 `sdd/scripts/sdd.py` 解释 profile，profile 只提供数据。
- 关键决策：
  1. 保留现有三个 schema 1 预设，不修改其内容；新能力只用新增 schema 2 profile
     验证，避免旧 Spec 的 digest 和快照语义漂移。
  2. `stages` 必须是规范阶段的严格递增子序列，首 `DRAFT`、尾 `MERGED`。
     状态迁移统一经过 `resolve_declared_transition()`：目标阶段未声明时，前进到
     下一个已声明阶段；被跳过阶段的强制 Gate 必须折叠到下一个已声明阶段。
  3. `gate_checks` 只能裁剪 advisory 检查；每个 Gate 的 required 检查必须全部
     保留，否则 profile 校验失败。
  4. `human_checkpoints` 必须包含 `approve_spec` 与 `confirm_delivery`；
     `complete_gate` 只能绑定 `gates` 中策略为 `human` 的 Gate。
  5. `risk_stop` 与 `config.risk_stop` 取并集，只扩大停止范围，不能缩小。
  6. `context_rules` 只能裁剪或补充仓库内相对路径；拒绝绝对路径、`..`、
     其他 Spec 目录和仓库外文件。
  7. `workflow validate` 只读 profile，不写 `state.json`，成功时返回规范化 digest。
- 方案对比：
  - 把所有预设升级为 schema 2：会让旧 Spec 的仓库预设 digest 变化，增加迁移风险，放弃。
  - 用 Python 文件作为 profile：会引入可执行配置和供应链风险，放弃。
  - JSON schema 2 + 严格白名单 + 有限子序列：可审计、可校验、diff 小，采用。

## AC 验证清单

| AC | Task | Evidence |
| --- | --- | --- |
| AC-001-1 | T-001 | 见 `docs/specs/SPEC-REQ-002/verification.md` |
| AC-001-2 | T-001 | 见 `docs/specs/SPEC-REQ-002/verification.md` |
| AC-001-3 | T-001 | 见 `docs/specs/SPEC-REQ-002/verification.md` |
| AC-002-1 | T-002 | 见 `docs/specs/SPEC-REQ-002/verification.md` |
| AC-002-2 | T-002 | 见 `docs/specs/SPEC-REQ-002/verification.md` |
| AC-002-3 | T-002 | 见 `docs/specs/SPEC-REQ-002/verification.md` |
| AC-003-1 | T-003 | 见 `docs/specs/SPEC-REQ-002/verification.md` |
| AC-003-2 | T-003 | 见 `docs/specs/SPEC-REQ-002/verification.md` |
| AC-003-3 | T-003 | 见 `docs/specs/SPEC-REQ-002/verification.md` |
| AC-004-1 | T-004 | 见 `docs/specs/SPEC-REQ-002/verification.md` |
| AC-004-2 | T-004 | 见 `docs/specs/SPEC-REQ-002/verification.md` |
| AC-005-1 | T-005 | 见 `docs/specs/SPEC-REQ-002/verification.md` |
| AC-005-2 | T-005 | 见 `docs/specs/SPEC-REQ-002/verification.md` |
| AC-005-3 | T-005 | 见 `docs/specs/SPEC-REQ-002/verification.md` |

## 命令与结果

- Evidence recorded: Command: python -m unittest discover -s tests -v

## 未运行 / Not run

- 本地未安装 `mcp` SDK 时，2 个 MCP 相关用例会跳过；GitHub Actions 安装
  `sdd/mcp/requirements.txt` 后执行。
- 未执行 `upgrade-workflow`；本 Spec Out-of-Scope。
- 未实现 warn/waiver、Review overlay、知识索引和 BAR/Fix Pattern；属于 issue #7
  的后续 P1/P2 工作。

## 风险与回滚

| 风险/依赖 | 影响 | 缓解措施 | 负责人 |
|---|---|---|---|
| v2 分派破坏 v1 行为 | 旧 Spec 校验失败 | v1 逻辑原样保留；旧 Spec 全量回归 | sdd-kit 平台维护者 |
| 阶段跳过导致 Gate 丢失 | 合规缺口 | 校验 required Gate 折叠规则；负向测试 | sdd-kit 平台维护者 |
| profile 关闭 required 检查 | 绕过强制检查 | 校验 required 子集；拒绝非法 profile | sdd-kit 平台维护者 |
| context 规则越界 | 读取其他 Spec 或仓库外文件 | 相对路径校验、排除规则、负向测试 | sdd-kit 平台维护者 |
| 旧快照 digest 漂移 | 审计不可复验 | 现有三预设保持 schema 1 不变 | sdd-kit 平台维护者 |

## Gate 记录

# Gate 记录

| Gate | State | Mode | Result | Evidence | At |
| --- | --- | --- | --- | --- | --- |
| G0 | SPEC_READY | manual | PASS | 需求已确认 | 2026-11-23T14:39:52+08:00 |
| G1 | SPEC_READY | auto | PASS | spec check passed | 2026-11-23T14:39:52+08:00 |
| G2 | DESIGN_READY | auto | PASS | design.md submitted via CLI and checked | 2026-11-23T14:43:36+08:00 |
| G3 | TASKS_READY | auto | PASS | tasks.md submitted via CLI and checked | 2026-11-23T14:45:25+08:00 |
| G4 | VERIFYING | auto | PASS | all tasks completed | 2026-11-23T15:24:27+08:00 |
| G5 | PR_READY | auto | PASS | verification.md submitted via CLI and checked | 2026-11-23T15:59:40+08:00 |

## 证据

- `docs/specs/SPEC-REQ-002/verification.md`
- `docs/specs/SPEC-REQ-002/gates.md`
- `sdd/reports/SPEC-REQ-002/gate1-report.md`
- `sdd/reports/SPEC-REQ-002/gate2-report.md`
- `sdd/reports/SPEC-REQ-002/gate3-report.md`
- `sdd/reports/SPEC-REQ-002/gate4-report.md`
- `sdd/reports/SPEC-REQ-002/gate5-report.md`
