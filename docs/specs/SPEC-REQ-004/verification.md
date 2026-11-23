# 审批版本绑定、change-set 与 impact验证报告

## 1. 元数据

| 项 | 内容 |
|---|---|
| Spec ID | SPEC-REQ-004 |
| 工作项 ID | SDD-GOV-001 |
| 作者 | SDD Agent |
| 创建日期 | 2026-11-23T19:32:26+08:00 |
| 验证时间 | 2026-11-23T19:32:26+08:00 |
| 工作流 | l2-standard |

## 2. 命令

<!-- TODO: 记录实际执行的命令、目录和退出码；sdd verify 会自动追加命令证据。 -->

- 待填写

## 3. 结果

<!-- TODO: 逐条写实际结果，不要写“应该通过”。 -->

待填写。

- Evidence recorded: Task T-001

- Evidence recorded: Task T-002

- Evidence recorded: Task T-003

- Evidence recorded: Task T-004

### Task T-004

- At: 2026-11-23T21:22:21+08:00

python -m unittest tests.test_governance.ChangeEnforcementTests -v: 3 passed; pre-commit and stage checks enforce pending/docs-only change rules

### Task T-003

- At: 2026-11-23T21:21:06+08:00

python -m unittest tests.test_governance.ChangeSetTests -v: 4 passed; change-set fields, approval write-back and invalid-reference rejection implemented

### Task T-002

- At: 2026-11-23T21:19:57+08:00

python -m unittest tests.test_governance.ImpactTests -v: 3 passed; impact JSON and missing-reference validation implemented

### Task T-001

- At: 2026-11-23T21:18:46+08:00

python -m unittest tests.test_governance.ApprovalBindingTests -v: 4 passed; py_compile passed; approval digest and reapprove implemented

## 4. 未运行

None。

## 5. AC 覆盖

<!-- TODO: 每个 AC 一行，写 AC -> 测试/证据映射。 -->

| AC | 测试/证据 | 结果 |
|---|---|---|
| AC-001-1 | 待填写 | 待填写 |

## 6. Gate 5 结论

<!-- TODO: 填 PASS 或 FAILED，并说明残余风险。 -->

待填写。

## 7. 独立审查

| 项 | 内容 |
|---|---|
| Reviewer | 独立复核（只读审查） |
| Session | review-20261123-governance |
| Model | gpt-5-codex |
| Scope | `sdd/scripts/sdd.py`、`sdd/scripts/sdd_ext.py`、`sdd/core.py`、`sdd/cli.py`、`tests/test_governance.py`；AC-001-1…AC-004-3 |
| Findings | 未发现可执行问题。复核确认 AC-001-3/AC-004-3 测试标签、change-set 空 Task 校验、审批报告刷新和文档同步均已收口。 |
| Blocking issues | none |
