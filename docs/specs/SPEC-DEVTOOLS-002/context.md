# 需求上下文

- Work item: `SDD-EPIC-007`
- Issue: https://github.com/RyanBrainNew/sdd-kit/issues/7

## 原始需求

issue #7 是 sdd-kit 下一阶段总纲（epic），核心结论是：SDD 的难点不在阶段数量，
而在“输入可信、生成受控、验证可证、错误能回流”。issue 明确按 P0 → P1 → P2
实施，并要求“每个 PR 只做一类改动，保持 diff 聚焦”。

本 Spec 只承接 P0（标准符合性 + G0/FEAT、`context_bundle`、G4/G5 可复验证据）。
P1（Profile v2、检查项 warn/waiver、Review overlay）和 P2（知识基线、BAR/Fix Pattern）
另立 Spec，不在本次范围。

## 调研事实

- 仓库唯一状态机是 `sdd/scripts/sdd.py`（约 4568 行）；`sdd/core.py` 通过子进程调用
  `sdd.py`，`sdd/mcp/` 只是薄适配器。任何新检查必须落在 `sdd.py`，不能在 MCP 或
  core 里复制阶段/Gate 规则。
- 当前阶段链路：`DRAFT` → `SPEC_READY` → `DESIGN_READY` → `TASKS_READY` →
  `IMPLEMENTING` → `VERIFYING` → `PR_READY` → `MERGED`；`GATE_ARTIFACTS` 在
  `sdd/scripts/sdd.py:110`，G0/G1 都绑定 `spec.md`。
- `check_spec()`（`sdd/scripts/sdd.py:1193`）只校验 Spec ID、工作项 ID、In/Out-Scope、
  FR/AC 编号与单条 AC 的 Given/When/Then；不校验 FEAT，也不解析 PRD 映射表。
- `ensure_prd_index()`（`sdd/scripts/sdd.py:1499`）会自动分配 `FEAT-00N`，写入一张
  7 列扁平表（工作项 / PRD 链接 / 版本 / FEAT / Spec ID / 摘要 / 澄清标记）。
  `check_prd_index()`（`sdd/scripts/sdd.py:1558`）只检查 Spec ID 和工作项 ID 是否
  “在任意行出现过”，不检查 FEAT 唯一性、FEAT 与 Spec 一致性、FR/AC 映射或孤儿项。
- `command_approve()`（`sdd/scripts/sdd.py:3030` 起）把 G0 实现为
  `run_checks(stage="spec")` + `check_prd_index`；G0 和 G1 各自写死 4 条检查项，
  全部固定为 `PASS`，没有稳定检查 ID，也没有独立的“建议项/阻断项”字段。
- `write_gate_report()`（`sdd/scripts/sdd.py:1762`）的检查项表头是
  `检查项 | 结果 | 证据`，总体结果是 `PASS/FAILED`；报告已绑定产物 SHA-256。
- `build_next_action()`（`sdd/scripts/sdd.py:2071`）是 `next` 的唯一来源；
  `implement_task` 目前只返回 `task`、`acceptance_criteria`、`task_description`。
  `resume --json` 的 `next` 直接来自该函数（`sdd/core.py:373` 的 `_session_payload`）。
- `Workspace.context()`（`sdd/core.py:1029`）把所有 `sdd/context/**` 与当前 Spec 的
  `context.md` / `unknowns.md` 平铺返回，默认 12000 字符；没有 Task、FR/AC、
  design 章节、契约、约束、允许范围或排除列表的映射。
- Task 表的“单元测试类/方法”和“单 Task 测试命令”目前只校验非空
  （`task_table_error()`，`sdd/scripts/sdd.py:1118`），不校验测试是否真实存在。
- `check_verification()`（`sdd/scripts/sdd.py:1333`）只要求“命令/结果”章节有内容、
  Gate 5 结论包含 PASS；不检查命令退出码，也不要求证据来自真实执行。
- `command_verify()`（`sdd/scripts/sdd.py:3617`）执行 `config.test_commands`，
  并把 Command / CWD / Exit / 输出追加到 `verification.md` 的“命令”章节；
  `test_commands` 为空时只打印提示并返回 0，等同于“验证通过”。
- `submit verification.md` 在 `core.submit_artifact()`（`sdd/core.py:500`）里先执行
  `verify` 再 `check`；CLI 支持 `--no-run-commands`，可完全跳过真实执行。
- `check_test_coverage()`（`sdd/scripts/sdd.py:1450`）只做 AC 标签的并集匹配：
  测试文件里出现 `[AC-xxx]` 就算覆盖，不要求存在对应测试方法，也不要求该测试被执行。
- `sdd/config.json` 当前 `test_commands` 为空，`require_approver` 与
  `require_artifact_hash` 均为 `false`；l2-standard 低风险流程不应因本次改动增加
  人工检查点。
- 仓库只使用 Python 标准库；核心改动必须同步测试、README、`sdd/agent-contract.md`
  和提示词，并执行 `python -m sdd manifest --write` 更新 `sdd/manifest.json`。
- 现有回归命令：`python -m unittest discover -s tests -v`、
  `python -m sdd verify-core`、`python -m sdd verify-agent`、
  `python -m sdd check --all --stage ci --check-git`。
- `docs/prd-index.md` 现在已有 FEAT-002 → SPEC-DEVTOOLS-002 的扁平行；
  本次要把它升级为可解析的 `工作项 → FEAT → Spec → FR/AC` 结构化映射。

## 影响面

- 核心：`sdd/scripts/sdd.py`、`sdd/core.py`、`sdd/cli.py`。
- 模板与提示词：`sdd/templates/spec.md`、`sdd/prompts/spec.md`。
- 文档：`docs/STANDARD-CONFORMANCE.md`（新增）、`docs/prd-index.md`、`README.md`、
  `sdd/README.md`、`sdd/agent-contract.md`、`AGENTS.md` 托管块（经 `sync-agent`）。
- 测试：`tests/test_sdd.py`、`tests/test_cli.py`、`tests/test_mcp_service.py` 及新增
  上下文包/证据校验用例。

## 未决问题

- 见 `unknowns.md`。
