# SDD 执行手册（CLI-first）

本文件是业务仓库内的 SDD 操作说明。完整的接入、架构和模式说明见根目录 `README.md`。

一句话：

```text
开发者给一个工作项
  -> Agent 用 python -m sdd 自动循环
  -> 人只在 Spec 确认和 PR 合并时介入
  -> CI 做最终硬校验
```

## 1. 人只需要做三件事

| 时机 | 人做什么 | 命令 |
|---|---|---|
| 仓库接入（平台团队，一次） | 执行 bootstrap、补项目事实、配 CODEOWNERS | `python bootstrap.py ...` |
| 每个需求 | 审 `spec.md` 并确认 | `python -m sdd approve --spec <spec> --human --evidence "需求已确认"` |
| 每个需求 | 审 PR、合并并登记 | `python -m sdd merge --spec <spec> --human --evidence "PR merged"` |

`approve`、`merge`、`unblock` 都强制 `--human`；Agent 不得代替。

## 2. Agent 会话开始

所有命令在仓库根目录执行。

恢复当前会话：

```powershell
python -m sdd resume --json
```

新需求：

```powershell
python -m sdd start-work --work-item srdcloud-553377 --json
```

`resume` 的查找顺序：

1. `.sdd/runtime/sessions/` 中当前会话绑定的 Spec；
2. 当前 Git 分支名里的 `SPEC-XXX-NNN`；
3. 仓库只有一个活跃 Spec；
4. 都没有，才问一次。

Agent 不需要知道 `DRAFT`、`SPEC_READY` 等状态名，只读 `next.action`。

## 3. 自动循环

1. 读取 `next.action`、`next.step_id`、`next.kind`、`next.prompt_file`、
   `next.artifact`、`next.done_when`；`decision_required=true` 时停止并把
   `question` / `options` 交给人类；
2. 调研代码、测试、契约、ADR 和 `sdd/context/`；
3. 把事实写进当前 Spec 的 `context.md`，未决问题写进 `unknowns.md`；
4. 生成 `next.artifact`；
5. 用 `next.submit_with` 提交：
   - 阶段产物：`python -m sdd submit --artifact <name> --file <path> --json`
   - 实现任务：`python -m sdd submit-task --task T-xxx --evidence "..." --json`
6. `ok=false` 时按 `errors` 修复后重新提交；
7. `human_checkpoint.required=true` 时停止，等人处理。

不要直接编辑 `state.json`；不要跳过 `submit` 的校验。

## 4. 状态机与提交动作

```text
DRAFT
  -> SPEC_READY      人 approve --human
  -> DESIGN_READY    submit design.md
  -> TASKS_READY     submit tasks.md
  -> IMPLEMENTING    自动开始
  -> VERIFYING       所有 Task 完成
  -> PR_READY        submit verification.md
  -> MERGED          人 merge --human

任意状态 -> BLOCKED -> 人 unblock --human -> 原状态
```

| 状态 | Agent 做什么 | 提交方式 |
|---|---|---|
| `DRAFT` | 写 `spec.md` | `submit --artifact spec.md`，然后停 |
| `SPEC_READY` | 写 `design.md` | `submit --artifact design.md` |
| `DESIGN_READY` | 写 `tasks.md` | `submit --artifact tasks.md` |
| `TASKS_READY` | 无需操作 | 上一次 submit 自动进入 `IMPLEMENTING` |
| `IMPLEMENTING` | 一次做一个 Task | `submit-task --task T-xxx` |
| `VERIFYING` | 写 `verification.md` | `submit --artifact verification.md` |
| `PR_READY` | 生成并开 PR | `report`，然后 `pr --url ...` |
| `MERGED` | 结束 | 无 |
| `BLOCKED` | 等人回答 | 人 `unblock --human` |

## 5. 常用命令

```powershell
# 恢复 / 开始
python -m sdd resume --json
python -m sdd start-work --work-item srdcloud-553377 --title "订单取消" --domain ORDER --json

# 查看
python -m sdd board
python -m sdd current --json
python -m sdd status --json
python -m sdd next --json
python -m sdd check --spec SPEC-ORDER-001 --stage spec --json

# 提交阶段产物
python -m sdd submit --spec SPEC-ORDER-001 --artifact spec.md --file docs/specs/SPEC-ORDER-001/spec.md --json

# 提交实现任务（自动 start + complete）
python -m sdd submit-task --spec SPEC-ORDER-001 --task T-001 --commit abc1234 --evidence "pytest: 3 passed" --json

# 人类动作
python -m sdd approve --spec SPEC-ORDER-001 --human --evidence "需求已确认"
python -m sdd merge --spec SPEC-ORDER-001 --human --evidence "PR merged"
python -m sdd unblock --spec SPEC-ORDER-001 --human --evidence "产品已确认"

# 报告与 PR
python -m sdd report --spec SPEC-ORDER-001 --json
python -m sdd pr --spec SPEC-ORDER-001 --url "https://example.invalid/pr/1"

# 核心与 AGENTS 校验
python -m sdd verify-core
python -m sdd verify-agent
python -m sdd check --all --stage ci --check-git
```

## 6. MCP（可选）

没有 MCP，CLI 能跑完整流程。有 MCP 时，它只是把同一套能力包装成工具：

| 工具 | 用途 |
|---|---|
| `sdd_session` | 恢复当前会话 |
| `sdd_start_work` | 提交一个工作项，建/恢复 Spec |
| `sdd_submit_artifact` | 提交阶段产物并自动推进 |
| `sdd_submit_task` | 自动 start + complete 一个 Task |
| `sdd_status` / `sdd_next` / `sdd_check` | 读取状态和校验 |
| `sdd_board` | 查看 Spec、Task 状态和进度 |
| `sdd_context` / `sdd_read_artifact` | 读取上下文和工件 |
| `sdd_report` / `sdd_pr` / `sdd_verify` | 报告、PR、验证 |

不提供 `approve`、`merge`、`unblock`。

本地 MCP：

```powershell
python -m pip install -r sdd/mcp/requirements.txt
python -m sdd.mcp.server --root . --transport stdio
```

共享 MCP 只做上下文、项目目录、Spec ID 预留和只读查询，不能直接写同事本地 clone。

## 7. 人类检查清单

Spec 确认时看：

- 工作项 ID 是否正确；
- In/Out of Scope 是否可判定；
- 每条 AC 是否可测试；
- 是否有未解决的 `[NEEDS CLARIFICATION]`。

PR 审核时看：

- `PR_BODY.md` 四要素是否齐全；
- 每条 AC 是否有测试或证据；
- 是否有未解释的 diff；
- CI 的 `verify-core` / `verify-agent` / `check` 是否通过；
- 高风险变更是否有对应 Gate 记录。

## 8. 多微服务上下文

Agent 在写 Spec/Design 前先读：

- `sdd/context/services.yaml`：服务目录、负责人、依赖、测试/启动命令；
- `sdd/context/services/*.md`：服务卡；
- `sdd/context/contracts/`：OpenAPI、protobuf、事件 schema；
- `sdd/context/adr/`：仍然约束代码的 ADR；
- `sdd/context/glossary.md`：领域术语；
- `docs/specs/<id>/context.md` 和 `unknowns.md`：本需求背景和未决问题。

只记录仍会影响下一次改动的事实，不要搬历史流水账。

## 9. 出问题怎么办

| 现象 | 处理 |
|---|---|
| 多个活跃 Spec | 用会话指针、分支名或 `--spec` 明确 |
| 还有 TODO/占位符 | 补完工件，不要删检查 |
| 有 `[NEEDS CLARIFICATION]` | 停下问一个具体问题 |
| Hook 不生效 | `git config core.hooksPath .githooks` |
| 测试命令为空 | 配置 `sdd/config.json` 的 `test_commands` |
| Agent 想改 `state.json` | 拒绝；改用 `submit` / `submit-task` / `block` |
| Agent 想 approve/merge | 拒绝；这是人类动作 |
| `verify-core` 失败 | 恢复平台发布版本，或由平台团队重新生成 manifest |
