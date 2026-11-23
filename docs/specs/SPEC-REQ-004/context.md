# 需求上下文

- Work item: `SDD-GOV-001`
- Issue: https://github.com/RyanBrainNew/sdd-kit/issues/20

## 原始需求

issue #20（父 issue #8）要求：

- G0/G1 记录 `approved_spec_digest` / `approved_at` / `approved_by` /
  `approval_evidence`。
- 审批后 Spec digest 变化时阻断，并新增人工 `reapprove`。
- 新增 `change-set.md` 与 `sdd change`。
- 新增只读 `sdd impact --json`，输出 FEAT/FR/AC/Task/测试/代码路径。
- 审批后变更必须先更新文档与 change-set，再 `reapprove`，再允许代码提交。
- change-set 缺字段或引用不存在对象时失败；纯文档/配置变更走显式豁免。

## 调研事实

- `command_approve()` 当前只在 `approvals` 追加 `sha256`，没有顶层
  `approved_spec_digest`、审批时间和审批证据字段。
- G0/G1 报告由 `write_gate_report()` 生成，已有“产物”表记录 `spec.md`
  哈希，但没有显式声明“审批版本摘要”。
- `check_gates()` 已能发现 G1 报告绑定的 `spec.md` 哈希变化，但错误提示
  只要求“重新执行对应 Gate 或 rewind”，没有 `change-set` / `reapprove` 路径。
- `run_checks()` 在 design/tasks/verify/ci 阶段统一执行 Gate 与工件校验，
  是加入审批摘要校验和 pending change-set 校验的收口位置。
- `hook_pre_commit()` 能看到暂存文件与当前 Spec，但当前只检查重复版本文件、
  `spec.md` 合法性和澄清标记；`hook_commit_msg()` 已校验 Commit Trailer。
- CI 的 `check --all --stage ci --check-git` 会逐 Spec 调用 `run_checks()`。
- `sdd/cli.py` 的 `Workspace` 通过子进程调用 `sdd/scripts/sdd.py`；
  MCP 只在 `sdd/mcp/` 注册薄适配，人工动作没有暴露。
- `declared_code_paths()` 能从反引号路径中提取代码文件；
  `parse_tasks()` 能解析 Task 表、AC、测试类/方法和测试命令。
- `artifact_sha256()` 已对 Markdown 等文本工件做 CRLF/LF 规范化。
- `docs/prd-index.md` 的 FEAT 映射表由 `sync_feat_map()` 按 Spec 重建。

## 影响范围

- 核心：`sdd/scripts/sdd.py` 的审批、Gate 校验、hook、CI 检查与 CLI。
- 扩展检查注册表：`sdd/scripts/sdd_ext.py` 增加审批摘要与 change-set 检查 ID。
- CLI 编排：`sdd/cli.py` 增加 `reapprove`、`change`、`impact`。
- 状态：`state.json` 增加审批绑定字段；只能由 CLI 写入。
- 工件：新增 `docs/specs/<spec>/change-set.md`。
- 文档：README、`sdd/README.md`、`sdd/agent-contract.md`、
  `sdd/agent-block.md`、`docs/GUIDE.md`。
- 发布：`sdd/VERSION`、`sdd/__init__.py`、`sdd/manifest.json`。

## 约束与排除

- 不新增服务端、数据库、常驻进程或第三方依赖。
- 不实现 issue #21 的全量 commit 审计与 `sdd trace`。
- 不迁移或重写历史 MERGED Spec 的 state 与 Gate 报告。
- 不允许 Agent 调用 `approve` / `reapprove` / `merge` / `unblock` /
  `rewind` / `waive`，也不允许 MCP 暴露这些动作。
