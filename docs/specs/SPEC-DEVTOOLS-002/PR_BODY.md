# SPEC-DEVTOOLS-002 SDD-L2 内核 P0：标准符合性、上下文包与可复验证据

## Spec 文件

- `docs/specs/SPEC-DEVTOOLS-002/spec.md`
- Issue: `https://github.com/RyanBrainNew/sdd-kit/issues/7`

## Spec Item 列表

- AC-001-1
- AC-001-2
- AC-001-3
- AC-002-1
- AC-002-2
- AC-002-3
- AC-002-4
- AC-002-5
- AC-002-6
- AC-002-7
- AC-002-8
- AC-003-1
- AC-003-2
- AC-003-3
- AC-003-4
- AC-004-1
- AC-004-2
- AC-004-3
- AC-004-4
- AC-004-5
- AC-005-1
- AC-005-10
- AC-005-2
- AC-005-3
- AC-005-4
- AC-005-5
- AC-005-6
- AC-005-7
- AC-005-8
- AC-005-9
- T-001 在状态机内建立检查项注册表，并让 G0/G1 报告输出稳定检查 ID、级别、结果和证据
- T-002 打通 FEAT 追溯链：Spec 元数据、PRD 索引结构化映射、G0-04/G0-05 检查与 MERGED legacy 分支
- T-003 在 `next` 中生成最小 `context_bundle`，覆盖 Task、FR/AC、Design 章节、契约、约束、模式、范围与排除列表
- T-004 让 G5 只接受真实命令证据：结构化证据块、退出码校验、空 test_commands 阻断、MERGED legacy 兼容
- T-005 校验 Task 测试名可定位、AC 覆盖来自真实测试函数，并对中高风险补齐结构化独立 review 证据
- T-006 交付标准符合性映射，并同步 README、agent-contract、提示词、版本与 manifest

## 变更说明

- 高层方案：保留唯一状态机，在 `sdd/scripts/sdd.py` 内增加五个可复用能力，并让 `sdd/core.py`、`sdd/cli.py`、MCP 只透传结果。
  1. **检查项注册表**：用代码内常量声明稳定的 `G0-01`…`G5-xx`，每个 Gate 通过 dispatch 执行检查项，Gate 报告按注册表输出 ID、级别、结果和证据。
  2. **FEAT 结构化索引**：Spec 元数据增加 `FEAT ID`；`docs/prd-index.md` 增加 `FEAT 映射` 表，按 FR 一行记录 FR 与 AC；检查器解析表格而不是做全文包含。
  3. **最小上下文包**：在 `build_next_action()` 内按当前状态生成只读 `context_bundle`，不写 `state.json`，不新增必填文档。
  4. **可复验证据**：`sdd verify` 写结构化命令块；G5 解析退出码和输出摘要；G4/G5 校验测试名可定位、AC 覆盖来自真实测试函数。
  5. **兼容层**：只对新建或未合并 Spec 启用新强制规则；已 `MERGED` 的历史 Spec 走 legacy 分支，报告中显式标注。
- 关键决策：
  1. 注册表放在 `sdd/scripts/sdd.py` 而不是 JSON：它属于状态机规则，必须与代码同版本、同 manifest；新增 JSON 会制造第二个规则源。
  2. `context_bundle` 按需计算、不落盘：避免会话缓存漂移，也满足 `resume` 只读要求。
  3. 证据只认 `sdd verify` 的结构化块：格式单一、可解析、可复跑；手写 PASS 不构成证据。
  4. legacy 以 `state == MERGED` 且缺少 FEAT/新证据标记识别：只保护历史交付，不提供新 Spec 的逃生门。
- 方案对比：
  - 方案 A（采用）：状态机内注册表 + 文档内结构化索引，零新增运行时文件、零第三方依赖。
  - 方案 B：独立 `checks.json` + 通用 DSL。可配置性更强，但会把规则拆成两份，且 P1 才需要，P0 不采用。
  - 方案 C：把 `context_bundle` 持久化到 `.sdd/runtime`。读取更快，但会引入缓存失效和状态漂移，不采用。

## AC 验证清单

| AC | Task | Evidence |
| --- | --- | --- |
| AC-001-1 | T-006 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-001-2 | T-006 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-001-3 | T-006 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-002-1 | T-002 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-002-2 | T-002 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-002-3 | T-002 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-002-4 | T-002 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-002-5 | T-002 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-002-6 | T-002 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-002-7 | T-002 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-002-8 | T-002 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-003-1 | T-001 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-003-2 | T-001 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-003-3 | T-001 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-003-4 | T-001 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-004-1 | T-003 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-004-2 | T-003 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-004-3 | T-003 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-004-4 | T-003 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-004-5 | T-003 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-005-1 | T-004 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-005-10 | T-004 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-005-2 | T-004 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-005-3 | T-004 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-005-4 | T-005 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-005-5 | T-005 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-005-6 | T-005 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-005-7 | T-005 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-005-8 | T-004 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |
| AC-005-9 | T-004 | 见 `docs/specs/SPEC-DEVTOOLS-002/verification.md` |

## 命令与结果

- Evidence recorded: Command: python -m unittest discover -s tests -v

## 未运行 / Not run

- MCP SDK 未安装，`test_mcp_server` 的 2 个用例按设计跳过；不影响 CLI、状态机和 Gate 检查。
- 未执行真实 GitHub PR 合并；那是人类检查点。

## 风险与回滚

| 风险/依赖 | 影响 | 缓解措施 | 负责人 |
|---|---|---|---|
| 新 G0 规则误伤历史 Spec | CI 对已合并 Spec 失败 | MERGED legacy 分支 + 回归测试 | 平台维护者 |
| 测试名定位误判动态测试 | G4 误阻断 | 支持模块/类/方法多种写法；错误列出原始引用；测试夹具覆盖 | 平台维护者 |
| 证据解析格式漂移 | G5 误判 | 单一写入方 `command_verify`；解析器与写入方共用常量；往返测试 | 平台维护者 |
| `allowed_paths` 派生不可靠 | 上下文范围为空 | 返回空数组 + 提示，不扩大范围；文档说明派生来源 | Spec 负责人 |
| 现有测试夹具与旧格式冲突 | 回归失败 | 同步更新 `tests/test_sdd.py`、`tests/test_cli.py`、`tests/test_mcp_service.py` | 平台维护者 |
| 核心改动未更新 manifest | `verify-core` 失败 | 升 `sdd/VERSION` 并运行 `python -m sdd manifest --write` | 平台维护者 |

## Gate 记录

# Gate 记录

| Gate | State | Mode | Result | Evidence | At |
| --- | --- | --- | --- | --- | --- |
| G0 | SPEC_READY | manual | PASS | 需求已确认 | 2026-11-20T17:30:46+08:00 |
| G1 | SPEC_READY | auto | PASS | spec check passed | 2026-11-20T17:30:46+08:00 |
| G2 | DESIGN_READY | auto | PASS | design.md submitted via CLI and checked | 2026-11-20T17:33:49+08:00 |
| G3 | TASKS_READY | auto | PASS | tasks.md submitted via CLI and checked | 2026-11-20T17:34:27+08:00 |
| G4 | VERIFYING | auto | PASS | all tasks completed | 2026-11-20T18:12:25+08:00 |
| G5 | PR_READY | auto | PASS | verification.md submitted via CLI and checked | 2026-11-20T18:21:07+08:00 |

## 证据

- `docs/specs/SPEC-DEVTOOLS-002/verification.md`
- `docs/specs/SPEC-DEVTOOLS-002/gates.md`
- `sdd/reports/SPEC-DEVTOOLS-002/gate1-report.md`
- `sdd/reports/SPEC-DEVTOOLS-002/gate2-report.md`
- `sdd/reports/SPEC-DEVTOOLS-002/gate3-report.md`
- `sdd/reports/SPEC-DEVTOOLS-002/gate4-report.md`
- `sdd/reports/SPEC-DEVTOOLS-002/gate5-report.md`
