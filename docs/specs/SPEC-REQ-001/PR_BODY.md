# SPEC-REQ-001 工件哈希 CRLF/LF 规范化与 SDD CI 门禁对齐

## Spec 文件

- `docs/specs/SPEC-REQ-001/spec.md`
- Issue: `https://github.com/RyanBrainNew/sdd-kit/issues/15`

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
- T-001 在唯一状态机中增加文本工件 LF 规范化哈希，并让 Gate 记录使用稳定摘要
- T-002 增加历史 CRLF 哈希候选兼容，并确保新 Gate 记录写入 LF 哈希
- T-003 让 GitHub Actions 执行 SDD 三项门禁，并同步 README、agent-contract、版本和 manifest

## 变更说明

- 高层方案：在 `sdd/scripts/sdd.py` 内增加统一的文本工件哈希入口。文本工件先解码为 UTF-8，再把 `CRLF` 和孤立 `CR` 统一转换为 `LF`，最后计算 SHA-256；非 UTF-8 或非文本扩展名退回原始字节哈希。
- 关键决策：
  1. 新记录使用 LF 规范化哈希，和仓库 `.gitattributes` 的 `eol=lf` 约定一致。
  2. 校验时从当前文件生成原始、LF、CRLF 三种候选哈希，与历史记录比较；这样历史 CRLF 哈希和未来 LF 哈希都能验证。
  3. 只放宽“行尾表示差异”，不放宽正文变化；正文变化时三种候选都不等于历史哈希。
  4. `tasks.md#plan` 继续使用已有的结构化 `task_plan_hash()`，不纳入本次文本哈希改造。
- 方案对比：
  - 只改 `.gitattributes` 为 CRLF：会改变全仓库文本约定，且不能兼容已有 LF 记录，放弃。
  - 手工迁移所有历史 `state.json`：违反“不手改审计文件”约束，放弃。
  - 统一规范化哈希并兼容历史候选：改动集中、可回归、兼容旧记录，采用。

## AC 验证清单

| AC | Task | Evidence |
| --- | --- | --- |
| AC-001-1 | T-001 | 见 `docs/specs/SPEC-REQ-001/verification.md` |
| AC-001-2 | T-001 | 见 `docs/specs/SPEC-REQ-001/verification.md` |
| AC-001-3 | T-001 | 见 `docs/specs/SPEC-REQ-001/verification.md` |
| AC-002-1 | T-002 | 见 `docs/specs/SPEC-REQ-001/verification.md` |
| AC-002-2 | T-002 | 见 `docs/specs/SPEC-REQ-001/verification.md` |
| AC-002-3 | T-002 | 见 `docs/specs/SPEC-REQ-001/verification.md` |
| AC-003-1 | T-003 | 见 `docs/specs/SPEC-REQ-001/verification.md` |
| AC-003-2 | T-003 | 见 `docs/specs/SPEC-REQ-001/verification.md` |
| AC-003-3 | T-003 | 见 `docs/specs/SPEC-REQ-001/verification.md` |

## 命令与结果

- Evidence recorded: Command: python -m unittest discover -s tests -v

## 未运行 / Not run

- 本地未安装 `mcp` SDK，2 个 `test_mcp_server` 用例跳过；GitHub Actions 会安装 `sdd/mcp/requirements.txt` 后运行它们。
- 未对历史已合并 Spec 重新执行 Gate、rewind 或人工再审批（Spec Out-of-Scope）。
- 未在合并后重跑历史 Gate；已 `MERGED` 的历史 Spec 以 `state.json` 审计记录为准。

## 风险与回滚

| 风险/依赖 | 影响 | 缓解措施 | 负责人 |
|---|---|---|---|
| 兼容逻辑过宽 | 可能把真实正文修改误判为行尾变化 | 增加正文变化回归测试，确保三个候选都不匹配 | sdd-kit 平台维护者 |
| 历史记录格式不一致 | 解析失败或漏报 | 只解析现有 Gate 报告结构，不新增格式 | sdd-kit 平台维护者 |
| 非 UTF-8 工件 | 解码失败 | 捕获解码错误，退回原始字节哈希 | sdd-kit 平台维护者 |
| CI 门禁步骤导致 PR 首次失败 | 阻塞交付 | 在本地先跑三项门禁，并使用带 `Spec-Id` / `Task-Id` 的提交信息 | sdd-kit 平台维护者 |

## Gate 记录

# Gate 记录

| Gate | State | Mode | Result | Evidence | At |
| --- | --- | --- | --- | --- | --- |
| G0 | SPEC_READY | manual | PASS | 需求已确认 | 2026-11-23T11:19:15+08:00 |
| G1 | SPEC_READY | auto | PASS | spec check passed | 2026-11-23T11:19:15+08:00 |
| G2 | DESIGN_READY | auto | PASS | design.md submitted via CLI and checked | 2026-11-23T11:22:06+08:00 |
| G3 | TASKS_READY | auto | FAILED | design.md submitted via CLI and checked | 2026-11-23T11:22:08+08:00 |
| G3 | TASKS_READY | auto | PASS | tasks.md submitted via CLI and checked | 2026-11-23T11:25:34+08:00 |
| G4 | VERIFYING | auto | PASS | all tasks completed | 2026-11-23T11:46:34+08:00 |
| G5 | PR_READY | auto | PASS | verification.md submitted via CLI and checked | 2026-11-23T12:41:57+08:00 |

## 证据

- `docs/specs/SPEC-REQ-001/verification.md`
- `docs/specs/SPEC-REQ-001/gates.md`
- `sdd/reports/SPEC-REQ-001/gate1-report.md`
- `sdd/reports/SPEC-REQ-001/gate2-report.md`
- `sdd/reports/SPEC-REQ-001/gate3-report.md`
- `sdd/reports/SPEC-REQ-001/gate4-report.md`
- `sdd/reports/SPEC-REQ-001/gate5-report.md`
