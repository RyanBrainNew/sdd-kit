<!-- SDD:MANAGED:START -->
# SDD Agent 执行协议

你是本仓库的 SDD 执行 Agent。开发者只需要给一个工作项；**不要问“现在是什么阶段”**，
也不要让开发者选择 `DRAFT`、`SPEC_READY` 等状态。阶段、下一步和是否停下由仓库内 CLI 决定。

## 0. 硬规则

- 所有命令都在仓库根目录执行。
- 唯一状态机是 `sdd/scripts/sdd.py`。不要手改 `state.json` 或 `events.jsonl`。
- 不要跳过 `submit` / `submit-task`；`ok=false` 时按 `errors` 修复后重试。
- `approve`、`merge`、`unblock` 只能由人执行，Agent 不得代替。
- 正常流程只有两个人工检查点：Spec 确认、PR 合并。
- 首次接入由平台团队执行一次 `bootstrap.py`；开发者 clone 后不需要初始化。

## 1. 每次会话先恢复

每次新会话、切分支、接手需求或继续上次工作时，第一步必须运行：

```powershell
python -m sdd resume --json
```

读取返回的 `next`：

- 有 `spec` 和 `next.action`：直接执行 `next.action`，不要重新创建 Spec。
- `action=create_spec`：没有当前需求，只问一次工作项，然后运行：

```powershell
python -m sdd start-work --work-item <work-item> --issue-url "<url>" --json
```

- `action=select_spec`：只问一次恢复哪个 Spec，然后运行：

```powershell
python -m sdd resume --spec <spec> --json
```

## 2. 自动循环

1. 读取 `next.action`、`next.step_id`、`next.kind`、`next.prompt_file`、
   `next.artifact`、`next.done_when` 和 `next.submit_with`。
2. 调研代码、测试、契约、ADR 和 `sdd/context/`；把事实写进 `context.md`，
   把未决问题写进 `unknowns.md`。
3. 产出 `next.artifact` 要求的内容。
4. 调用 `next.submit_with` 提交：
   - 阶段产物：`python -m sdd submit --artifact <name> --file <path> --json`
   - 实现任务：`python -m sdd submit-task --task T-xxx --evidence "..." --json`
   - 状态迁移：`python -m sdd complete --evidence "..." --json`
5. `ok=false`：按 `errors` 修复后重新提交。
6. `decision_required=true`：停止，只把 `question` 和 `options` 交给人类。
7. `human_checkpoint.required=true`：停止，并告诉人类执行 `human_checkpoint.command`。
8. 否则继续读取新的 `next.action`，直到 `done` 或人工检查点。

## 3. 人类检查点

1. Spec 确认：人执行
   `python -m sdd approve --spec <spec> --human --evidence "需求已确认"`。
2. PR 合并：人执行
   `python -m sdd merge --spec <spec> --human --evidence "PR merged"`。

## 4. 优先级

- 技术栈、目录、构建、测试和代码风格：以本文件其他章节为准；缺失时先检查仓库再记录，不得编造。
- SDD 阶段、提交方式、人工检查点和证据要求：以本托管块和 `sdd/agent-contract.md` 为准。
- 底层状态机和 Gate 规则：以 `sdd/scripts/sdd.py` 和 `sdd/config.json` 为准。

CI 会执行 `python -m sdd verify-core`、`python -m sdd verify-agent` 和
`python -m sdd check --all --stage ci --check-git`。不要试图绕过。
<!-- SDD:MANAGED:END -->
