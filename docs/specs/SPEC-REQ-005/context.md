# 需求上下文

- Work item: `SDD-GOV-002`
- Issue: https://github.com/RyanBrainNew/sdd-kit/issues/21

## 原始需求

issue #21（父 issue #8）要求：

- `check --check-git` 从 merge-base 扫描分支全部 commit，不再只看最近 20 条。
- 代码 commit 必须且只能有一个 Spec-Id 和 Task-Id；文档 commit 不得带 Task-Id。
- 引用的 Spec/Task/工作项必须存在且一致。
- 新增只读 `sdd trace --test/--ac/--commit`，输出完整链路。
- 断链时输出 missing link。
- 不修改 state/events，不执行人工动作。

## 调研事实

- `check_git()` 当前用 `git log -20 --pretty=%B`，只检查最近 20 条里是否出现
  `Spec-Id: <spec>`，不校验 Task-Id、存在性或工作项一致性。
- `hook_commit_msg()` 已实现单条 commit 的 trailer 规则：代码类必须有且只有一个
  Task-Id，docs 不得有 Task-Id，Spec 与工作项要一致。
- `check --all --stage ci --check-git` 会对每个非 MERGED Spec 调用 `check_git()`。
- `scan_test_definitions()` 能定位测试函数及其函数体内的 AC 标签。
- `parse_tasks()` 提供 Task->AC/FR、测试选择器和 Commit SHA。
- `state.json.approvals`、`approved_spec_digest` 与 `change-set.md` 可提供审批和变更链。
- `verification-evidence.jsonl` 提供 Spec/Task 维度的命令证据。
- `sdd/core.py` 通过子进程调用 `sdd/scripts/sdd.py`；MCP 不暴露人工动作。

## 影响范围

- 核心：`sdd/scripts/sdd.py` 的 `check_git()`、commit 解析、`trace` 构建与 CLI。
- CLI：`sdd/cli.py` 增加 `trace`。
- 测试：新增 commit 审计与 trace 测试。
- 文档：README、`sdd/README.md`、`sdd/agent-contract.md`、
  `docs/STANDARD-CONFORMANCE.md`、版本与 manifest。

## 约束与排除

- 不新增服务端、数据库、常驻进程或第三方依赖。
- 不修改历史 commit 或重写 Git 历史。
- trace 不写 state、events、change-set 或任何文件。
- 不实现语义 diff 或外部工作项 API 访问。
