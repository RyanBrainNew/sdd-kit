# SPEC-DEVTOOLS-002 轻量、可自定义、全链路可溯源的 SDD-L2 执行内核

## Spec 文件

- `docs/specs/SPEC-DEVTOOLS-002/spec.md`
- Issue: `https://github.com/RyanBrainNew/sdd-kit/issues/7`

## Spec Item 列表

- AC-001-1
- AC-001-2
- AC-001-3
- AC-001-4
- AC-002-1
- AC-002-2
- AC-002-3
- AC-002-4
- AC-002-5
- AC-003-1
- AC-003-2
- AC-003-3
- AC-003-4
- AC-003-5
- AC-004-1
- AC-004-2
- AC-004-3
- AC-004-4
- AC-004-5
- AC-004-6
- AC-005-1
- AC-005-2
- AC-005-3
- AC-005-4
- AC-005-5
- AC-006-1
- AC-006-2
- AC-006-3
- AC-006-4
- AC-006-5
- AC-006-6
- AC-006-7
- AC-007-1
- AC-007-2
- AC-007-3
- AC-007-4
- AC-007-5
- AC-007-6
- AC-008-1
- AC-008-2
- AC-008-3
- AC-008-4
- AC-008-5
- AC-009-1
- AC-009-2
- AC-009-3
- AC-009-4
- AC-009-5
- AC-010-1
- AC-010-2
- AC-010-3
- AC-010-4
- AC-010-5
- AC-010-6
- T-001 实现 FEAT 元数据、PRD 结构化追溯、G0/G1 独立检查项和稳定报告
- T-002 建立 Gate 检查注册表并让 `check`/Gate 报告输出 `pass/warn/block` 与稳定 ID
- T-003 实现 `context_bundle`、知识/契约/Pattern 选择、允许范围与排除列表
- T-004 实现可复验命令证据、测试定位、AC 块扫描和 G4/G5 阻断
- T-005 实现 Profile v2 校验、`l2-refactor` 示例和旧快照兼容
- T-006 实现 `warn`、人工豁免、到期重校验、inbox 与安全红线
- T-007 实现通用 Review 契约、三类 overlay、finding 校验和 medium/high 强制审查
- T-008 实现最小知识索引、Fix Pattern 文档与真实闭环示例
- T-009 扩展 metrics、审计事件和质量回流指标
- T-010 完成标准符合性文档、模板/提示词/README/Agent 协议、版本与 manifest，执行全量验收

## 变更说明

- 高层方案：
  1. `sdd/scripts/sdd.py` 继续独占阶段迁移、Gate 编排、人工动作和 CLI 命令。
  2. 新增 `sdd/scripts/sdd_ext.py`，只放无状态纯函数和常量：检查注册表、Profile v2 校验、证据/豁免/Review 解析、知识索引与 Fix Pattern 读取、指标聚合。该模块不执行 `transition`，不保存状态。
  3. `build_next_action` 在返回 `next` 时按当前 Task 生成 `context_bundle`；`core.Workspace` 仍只通过子进程读取 `next`，不复制上下文选择规则。
  4. `sdd verify` 将每条命令证据追加到当前 Spec 的 `verification-evidence.jsonl`；G5 读取证据文件，不接受只在 Markdown 中写 PASS。
  5. Profile v2 使用 `schema: 2`；schema 1 快照保持只读兼容。新 Profile 可声明检查项组合、人工检查点、Review 风险阈值、上下文 include/exclude 和风险标签。
  6. Gate 结果统一由检查注册表生成 `pass/warn/block/waived`；错误文本仍保留给现有调用方，但 JSON 和 Gate 报告同时输出稳定检查 ID。
  7. 人工豁免写入 `state.json.waivers` 和审计事件；安全红线检查 ID 在注册表中标记为不可豁免。
  8. Review 采用“通用契约 + overlay”；overlay 只提供审查规则和 finding 模板，不参与状态迁移。
  9. 知识索引与 Fix Pattern 使用仓库内 Markdown；`context_bundle` 按 FEAT/FR/AC、允许路径和技术栈选择内容。
- 关键决策：
  - 不把 Profile 做成通用脚本或 DAG。有限模型才可校验、可快照、可审计。
  - 不把证据放到集中数据库。JSONL + Git + 产物哈希足以完成单仓库审计，且符合轻量目标。
  - 不为旧 Spec 回填新必填项。旧快照和旧状态按原规则运行，新规则只对新建或重新进入对应 Gate 的 Spec 生效。
  - 不把检查结果简单降级为字符串。字符串继续用于兼容，结构化检查 ID 用于治理。
- 方案对比：
  - 方案 A（采用）：单状态机 + 纯函数扩展模块 + 仓库内声明式数据。改动可控、无部署、容易审计。
  - 方案 B：拆成独立工作流服务。可集中管理，但引入服务端和数据库，违反轻量目标。
  - 方案 C：把 v7 全部模板和技能搬入仓库。覆盖更广，但上下文成本和维护成本过高，且会削弱“简单”。

## AC 验证清单

| AC | Task | Evidence |
| --- | --- | --- |
| AC-001-1 | T-002 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-001-2 | T-002 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-001-3 | T-001 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-001-4 | T-002 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-002-1 | T-001 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-002-2 | T-001 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-002-3 | T-001 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-002-4 | T-001 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-002-5 | T-001 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-003-1 | T-003 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-003-2 | T-003 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-003-3 | T-003 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-003-4 | T-003 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-003-5 | T-003 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-004-1 | T-004 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-004-2 | T-004 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-004-3 | T-004 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-004-4 | T-004 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-004-5 | T-004 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-004-6 | T-006 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-005-1 | T-005 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-005-2 | T-005 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-005-3 | T-005 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-005-4 | T-005 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-005-5 | T-005 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-006-1 | T-002 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-006-2 | T-006 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-006-3 | T-002 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-006-4 | T-006 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-006-5 | T-006 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-006-6 | T-006 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-006-7 | T-009 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-007-1 | T-007 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-007-2 | T-007 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-007-3 | T-007 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-007-4 | T-007 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-007-5 | T-007 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-007-6 | T-007 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-008-1 | T-008 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-008-2 | T-008 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-008-3 | T-008 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-008-4 | T-003 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-008-5 | T-008 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-009-1 | T-008 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-009-2 | T-003 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-009-3 | T-008 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-009-4 | T-003 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-009-5 | T-009 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-010-1 | T-005 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-010-2 | T-009 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-010-3 | T-005 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-010-4 | T-010 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-010-5 | T-010 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-010-6 | T-010 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |

## 命令与结果

| 命令 | 目录 | 退出码 | 结果 |
|---|---|---:|---|
| `python -m unittest discover -s tests -v` | 仓库根目录 | 0 | 138 项，136 通过，0 失败，2 跳过；跳过项为未安装可选 MCP SDK |
| `python -m unittest tests.test_evolution.ProfileTests tests.test_evolution.GateRegistryTests tests.test_evolution.WaiverTests tests.test_evolution.EvidenceTests -v` | 仓库根目录 | 0 | 15 项通过 |
| `python -m unittest tests.test_evolution.DocsReleaseTests -v` | 仓库根目录 | 0 | 2 项通过 |
| `python -m unittest tests.test_cli.CliTest.test_full_cli_loop_reaches_pr_ready -v` | 仓库根目录 | 0 | 1 项通过，确认 `python -m sdd verify` 可用并写入证据 |
| `python -m sdd manifest --write` | 仓库根目录 | 0 | 版本 0.9.0，48 个受保护文件 |
| `python -m sdd verify-core` | 仓库根目录 | 0 | verify_core passed |
| `python -m sdd verify-agent` | 仓库根目录 | 0 | verify_agent passed |

- Evidence recorded: Command: python -m unittest discover -s tests -v

## 未运行 / Not run

无。未安装可选 MCP SDK 的两个用例按设计跳过，不影响 CLI 核心路径。

## 风险与回滚

| 风险/依赖 | 影响 | 缓解措施 | 负责人 |
|---|---|---|---|
| 旧 Spec 没有 FEAT、证据文件和 schema 2 快照 | 全量 CI 可能因新规则失败 | 只对新 Spec/新 Gate 强制；旧快照按 schema 1 解释；增加兼容测试 | 平台维护者 |
| 测试名解析依赖任务表格式 | 合法但不同写法可能被误判 | 支持 `Module.Class#method`、`Class#method` 和方法名三种形式，错误提示给出可接受格式 | 平台维护者 |
| 证据 JSONL 被手工伪造 | G5 以假证据通过 | 记录输出 sha256、时间、退出码和命令；CI 可用真实执行覆盖；对异常事件标记 | 平台维护者 |
| Review overlay 过多导致上下文膨胀 | Agent 注意力下降 | 只加载与文件扩展名/任务范围匹配的 overlay；默认一个通用契约 | 质量负责人 |
| 知识索引与 Pattern 过期 | 误用历史规则 | 记录版本、Owner、状态和适用范围；未验证 Pattern 只作参考 | 业务 Owner |
| 自定义 Profile 过度复杂 | 使用者配置错误 | 有限 schema、显式校验、`l2-refactor` 示范、错误定位到字段 | 工作流设计者 |

## Gate 记录

# Gate 记录

| Gate | State | Mode | Result | Evidence | At |
| --- | --- | --- | --- | --- | --- |
| G0 | SPEC_READY | manual | PASS | 需求已确认 | 2026-11-23T11:01:13+08:00 |
| G1 | SPEC_READY | auto | PASS | spec check passed | 2026-11-23T11:01:13+08:00 |
| G2 | DESIGN_READY | auto | PASS | design.md submitted via CLI and checked | 2026-11-23T11:18:31+08:00 |
| G3 | TASKS_READY | auto | PASS | tasks.md submitted via CLI and checked | 2026-11-23T11:22:10+08:00 |
| G4 | VERIFYING | auto | FAILED | 标准符合性、文档/协议/版本/manifest 收口完成；独立审查 HIGH 问题已修复并回归通过；全量 134 项测试 132 通过、2 跳过；补充 python -m sdd verify CLI 入口。 | 2026-11-23T14:04:43+08:00 |
| G4 | VERIFYING | auto | FAILED | T-001 至 T-010 全部完成；G4 复核通过；补充追加章节回归测试和 python -m sdd verify CLI 入口。 | 2026-11-23T14:05:41+08:00 |
| G4 | VERIFYING | auto | PASS | T-001 至 T-010 全部完成；G4 复核通过；补充章节追加与 Python AST 测试扫描回归。 | 2026-11-23T14:06:52+08:00 |
| G5 | PR_READY | auto | PASS | 全量 138 项测试 136 通过、2 跳过；sdd verify 证据与 AC 覆盖通过；独立审查和事件链有效。 | 2026-11-23T14:14:49+08:00 |

## 证据

- `docs/specs/SPEC-DEVTOOLS-002/verification.md`
- `docs/specs/SPEC-DEVTOOLS-002/gates.md`
- `sdd/reports/SPEC-DEVTOOLS-002/gate1-report.md`
- `sdd/reports/SPEC-DEVTOOLS-002/gate2-report.md`
- `sdd/reports/SPEC-DEVTOOLS-002/gate3-report.md`
- `sdd/reports/SPEC-DEVTOOLS-002/gate4-report.md`
- `sdd/reports/SPEC-DEVTOOLS-002/gate5-report.md`
