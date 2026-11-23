# SPEC-REQ-005 全量 commit 审计与 sdd trace

## Spec 文件

- `docs/specs/SPEC-REQ-005/spec.md`
- Issue: `https://github.com/RyanBrainNew/sdd-kit/issues/21`

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
- AC-003-4
- AC-003-5
- AC-004-1
- AC-004-2
- AC-004-3
- T-001 实现 merge-base 全量 commit 扫描与代码 commit trailer 校验
- T-002 实现 docs/其它类型规则、引用存在性与 merge-base 缺失错误
- T-003 实现 trace test/AC/commit 三入口与完整链路 JSON
- T-004 实现断链 missing、多命中/只读保护
- T-005 同步 CLI/文档/版本/manifest，兼容历史并修复 PRD 行落点

## 变更说明

- 高层方案：新增 Git 只读解析层（merge-base、commit 列表、单 commit 解析），
  `check_git()` 逐 commit 调用同一校验函数；`trace` 复用该解析层与现有
  `parse_tasks()`、`scan_test_definitions()`、`parse_change_set()`、
  `verification-evidence.jsonl` 读取函数。
- 关键决策：
  1. merge-base 解析顺序为 `origin/main`、`main`、`master`；都失败则明确报错。
  2. 跳过 merge commit（父提交 >= 2）；普通 commit 必须且只能有一个 `Spec-Id`。
  3. 代码类型 `feat/fix/perf/hotfix` 必须有且只有一个 `Task-Id`；`docs` 不得有；
     其他类型允许 0 或 1 个。
  4. 每个 commit 按自身 `Spec-Id` 校验，不按当前检查的 Spec 校验，避免多 Spec 分支误报。
  5. `trace` 只读，不写 state/events/change-set；断链统一进入 `missing` 数组。
  6. 多个 Spec 命中同一 AC 时返回候选并标记 `ambiguous`，不猜测。
- 方案对比：
  - 继续用 `git log -20`：无法发现早期坏 commit，放弃。
  - 只校验当前 Spec：多 Spec 分支会产生错误归属，放弃。
  - trace 写缓存文件：违反只读要求，放弃。

## AC 验证清单

| AC | Task | Evidence |
| --- | --- | --- |
| AC-001-1 | T-001 | 见 `docs/specs/SPEC-REQ-005/verification.md` |
| AC-001-2 | T-001 | 见 `docs/specs/SPEC-REQ-005/verification.md` |
| AC-001-3 | T-002 | 见 `docs/specs/SPEC-REQ-005/verification.md` |
| AC-002-1 | T-001 | 见 `docs/specs/SPEC-REQ-005/verification.md` |
| AC-002-2 | T-002 | 见 `docs/specs/SPEC-REQ-005/verification.md` |
| AC-002-3 | T-002 | 见 `docs/specs/SPEC-REQ-005/verification.md` |
| AC-003-1 | T-003 | 见 `docs/specs/SPEC-REQ-005/verification.md` |
| AC-003-2 | T-003 | 见 `docs/specs/SPEC-REQ-005/verification.md` |
| AC-003-3 | T-003 | 见 `docs/specs/SPEC-REQ-005/verification.md` |
| AC-003-4 | T-004 | 见 `docs/specs/SPEC-REQ-005/verification.md` |
| AC-003-5 | T-004 | 见 `docs/specs/SPEC-REQ-005/verification.md` |
| AC-004-1 | T-005 | 见 `docs/specs/SPEC-REQ-005/verification.md` |
| AC-004-2 | T-005 | 见 `docs/specs/SPEC-REQ-005/verification.md` |
| AC-004-3 | T-005 | 见 `docs/specs/SPEC-REQ-005/verification.md` |

## 命令与结果

以下命令由 `sdd verify` 真实执行并写入结构化证据；命令、目录、退出码、
Head、Plan-Hash 和执行时间见本报告“结果”章节及
`docs/specs/SPEC-REQ-005/verification-evidence.jsonl`。

- 全量测试：`python -m unittest discover -s tests -v`
- 核心校验：`python -m sdd verify-core`
- Agent 契约校验：`python -m sdd verify-agent`
- 全量 CI 检查：`python -m sdd check --all --stage ci --check-git`

- Evidence recorded: Command: python -m unittest discover -s tests -v

- Evidence recorded: Command: python -m unittest discover -s tests -v

- Evidence recorded: Command: python -m unittest discover -s tests -v

- Evidence recorded: Command: python -m unittest discover -s tests -v

## 未运行 / Not run

None。MCP SDK 用例在未安装 SDK 的本地环境按既有约定跳过。

## 风险与回滚

| 风险 | 影响 | 缓解 | 负责人 |
|---|---|---|---|
| 分支没有 main/master | 无法确定范围 | 明确错误并提示配置主干 | 平台维护者 |
| merge commit 无 trailer | 误报 | 跳过父提交 >= 2 的 commit | 平台维护者 |
| 多 Spec 共享 AC | trace 误归属 | 输出 ambiguous 候选 | 平台维护者 |
| trace 读取大量证据 | 变慢 | 只读单个 Spec 目录 | 平台维护者 |

## Gate 记录

# Gate 记录

| Gate | State | Mode | Result | Evidence | At |
| --- | --- | --- | --- | --- | --- |
| G0 | SPEC_READY | manual | PASS | 需求已确认 | 2026-11-23T22:41:42+08:00 |
| G1 | SPEC_READY | auto | PASS | spec check passed | 2026-11-23T22:41:42+08:00 |
| G2 | DESIGN_READY | auto | PASS | design.md submitted via CLI and checked | 2026-11-23T22:42:57+08:00 |
| G3 | TASKS_READY | auto | PASS | tasks.md submitted via CLI and checked | 2026-11-23T22:46:15+08:00 |
| G4 | VERIFYING | auto | PASS | all tasks completed | 2026-11-23T22:58:51+08:00 |
| G5 | PR_READY | auto | PASS | verification.md submitted via CLI and checked | 2026-11-24T00:05:56+08:00 |

## 证据

- `docs/specs/SPEC-REQ-005/verification.md`
- `docs/specs/SPEC-REQ-005/gates.md`
- `sdd/reports/SPEC-REQ-005/gate1-report.md`
- `sdd/reports/SPEC-REQ-005/gate2-report.md`
- `sdd/reports/SPEC-REQ-005/gate3-report.md`
- `sdd/reports/SPEC-REQ-005/gate4-report.md`
- `sdd/reports/SPEC-REQ-005/gate5-report.md`
