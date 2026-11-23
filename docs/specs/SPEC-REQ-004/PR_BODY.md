# SPEC-REQ-004 审批版本绑定、change-set 与 impact

## Spec 文件

- `docs/specs/SPEC-REQ-004/spec.md`
- Issue: `https://github.com/RyanBrainNew/sdd-kit/issues/20`

## Spec Item 列表

- AC-001-1
- AC-001-2
- AC-001-3
- AC-001-4
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
- T-001 审批摘要写入 state/G0-G1 报告，新增人工 reapprove 与 G1-08 阻断
- T-002 新增只读 impact，输出 FEAT/FR/AC/Task/测试/代码路径与审批需求
- T-003 新增 change-set 解析/写入、sdd change 与 reapprove 回写 approved
- T-004 pre-commit 与 stage 检查阻断 pending/非法 docs-only 代码提交
- T-005 CLI/MCP 边界、历史兼容、文档、版本与 manifest 发布同步

## 变更说明

- 高层方案：把“审批版本”作为 `state.json` 的一等字段，由 `approve` 和
  `reapprove` 写入；所有后续阶段通过统一函数比对当前 `spec.md` 规范化摘要。
  审批后的范围变化先用 `sdd change` 生成 `change-set.md`，再由人类
  `reapprove` 同时更新审批摘要和 change-set 状态；pre-commit 与 CI 读取同一
  change-set，阻断未批准的代码提交。
- 关键决策：
  1. 复用 `artifact_sha256()`，文本摘要继续做 CRLF/LF 规范化，避免平台差异。
  2. 新增 `G1-08`（审批版本绑定）和 `G1-09`（变更审批先行）两个稳定检查 ID，
     错误文本以 ID 开头，复用现有 `stage_check_results()` 分类。
  3. `change-set.md` 使用结构化 Markdown 列表记录，每个 `CHG-NNN` 是一个
     可解析记录；不引入 JSON 旁路文件或数据库。
  4. `reapprove` 是 CLI 人工动作，强制 `--human`、`--reason`、`--evidence`；
     MCP 不暴露，`Workspace` 方法仍需显式 `human=True`。
  5. `impact` 只读，不写 state、不写 change-set；所有写动作仍由
     `sdd change` / `sdd reapprove` 完成。
  6. MERGED 历史 Spec 跳过新字段强制校验，避免 `check --all` 回归失败；
     活跃 Spec 缺字段必须阻断并输出迁移命令。
- 方案对比：
  - 只依赖 G1 报告哈希：无法表达“已重新审批”，也无法关联 change-set，放弃。
  - 为每次变更创建新 Spec：破坏 Spec ID 稳定性与追溯，放弃。
  - 用 JSON 单独存 change-set：增加人工可读性和审查成本，采用 Markdown。
  - 在 hook 中解析自然语言判断语义变化：不可靠，改为显式 change-set。

## AC 验证清单

| AC | Task | Evidence |
| --- | --- | --- |
| AC-001-1 | T-001 | 见 `docs/specs/SPEC-REQ-004/verification.md` |
| AC-001-2 | T-001 | 见 `docs/specs/SPEC-REQ-004/verification.md` |
| AC-001-3 | T-001 | 见 `docs/specs/SPEC-REQ-004/verification.md` |
| AC-001-4 | T-001 | 见 `docs/specs/SPEC-REQ-004/verification.md` |
| AC-002-1 | T-002 | 见 `docs/specs/SPEC-REQ-004/verification.md` |
| AC-002-2 | T-002 | 见 `docs/specs/SPEC-REQ-004/verification.md` |
| AC-002-3 | T-002 | 见 `docs/specs/SPEC-REQ-004/verification.md` |
| AC-003-1 | T-003 | 见 `docs/specs/SPEC-REQ-004/verification.md` |
| AC-003-2 | T-003 | 见 `docs/specs/SPEC-REQ-004/verification.md` |
| AC-003-3 | T-004 | 见 `docs/specs/SPEC-REQ-004/verification.md` |
| AC-003-4 | T-004 | 见 `docs/specs/SPEC-REQ-004/verification.md` |
| AC-003-5 | T-003 | 见 `docs/specs/SPEC-REQ-004/verification.md` |
| AC-004-1 | T-005 | 见 `docs/specs/SPEC-REQ-004/verification.md` |
| AC-004-2 | T-005 | 见 `docs/specs/SPEC-REQ-004/verification.md` |
| AC-004-3 | T-005 | 见 `docs/specs/SPEC-REQ-004/verification.md` |

## 命令与结果

以下命令由 `sdd verify` 真实执行并写入结构化证据；命令、目录、退出码、
Head、Plan-Hash 和执行时间见本报告“结果”章节及
`docs/specs/SPEC-REQ-004/verification-evidence.jsonl`。

- 全量测试：`python -m unittest discover -s tests -v`
- 核心校验：`python -m sdd verify-core`
- Agent 契约校验：`python -m sdd verify-agent`
- 全量 CI 检查：`python -m sdd check --all --stage ci --check-git`

- Evidence recorded: Command: python -m unittest discover -s tests -v

## 未运行 / Not run

None。MCP SDK 用例在未安装 SDK 的本地环境按既有约定跳过，不影响核心路径。

## 风险与回滚

| 风险 | 影响 | 缓解 | 负责人 |
|---|---|---|---|
| 旧活跃 Spec 没有 `approved_spec_digest` | 升级后首次检查阻断 | 输出明确 `reapprove --reason legacy-migration` 命令 | 平台维护者 |
| change-set 手工编辑破坏格式 | 解析失败或误判 | 必填字段校验 + 明确错误行号/变更 ID | 平台维护者 |
| hook 在无 state 的仓库运行 | 误阻断 | 只处理存在 state.json 的 Spec 目录 | 平台维护者 |
| 多活跃 Spec 互相影响 | 无关提交被阻断 | 只对存在 pending 记录或摘要变化的 Spec 阻断 | 平台维护者 |
| 文本摘要受换行影响 | 跨平台误报 | 复用 CRLF/LF 规范化哈希 | 平台维护者 |

## Gate 记录

# Gate 记录

| Gate | State | Mode | Result | Evidence | At |
| --- | --- | --- | --- | --- | --- |
| G0 | SPEC_READY | manual | PASS | 需求已确认 | 2026-11-23T21:01:44+08:00 |
| G1 | SPEC_READY | auto | PASS | spec check passed | 2026-11-23T21:01:44+08:00 |
| G2 | DESIGN_READY | auto | PASS | design.md submitted via CLI and checked | 2026-11-23T21:05:19+08:00 |
| G3 | TASKS_READY | auto | PASS | tasks.md submitted via CLI and checked | 2026-11-23T21:09:52+08:00 |
| G4 | VERIFYING | auto | PASS | all tasks completed | 2026-11-23T21:29:49+08:00 |
| G5 | PR_READY | auto | PASS | verification.md submitted via CLI and checked | 2026-11-23T22:02:57+08:00 |

## 证据

- `docs/specs/SPEC-REQ-004/verification.md`
- `docs/specs/SPEC-REQ-004/gates.md`
- `sdd/reports/SPEC-REQ-004/gate1-report.md`
- `sdd/reports/SPEC-REQ-004/gate2-report.md`
- `sdd/reports/SPEC-REQ-004/gate3-report.md`
- `sdd/reports/SPEC-REQ-004/gate4-report.md`
- `sdd/reports/SPEC-REQ-004/gate5-report.md`
