<!-- SDD:MANAGED:START -->
# SDD Agent 执行协议

你是本仓库的 SDD 执行 Agent。开发者只需要给一个工作项；**不要问“现在是什么阶段”**，
也不要让开发者选择 `DRAFT`、`SPEC_READY` 等状态。阶段、下一步和是否停下由仓库内 CLI 决定。

## 0. 硬规则

- 所有命令都在仓库根目录执行。
- 唯一状态机是 `sdd/scripts/sdd.py`。不要手改 `state.json` 或 `events.jsonl`。
- 不要跳过 `submit` / `submit-task`；`ok=false` 时按 `errors` 修复后重试。
- `approve`、`reapprove`、`merge`、`unblock`、`rewind`、`waive` 只能由人执行，Agent 不得代替。
- `l2-standard` 正常流程只有两个人工检查点：Spec 确认、交付确认；
  交付确认后才创建 PR，PR 的审核合并由管理员在 GitHub 完成；
  `l2-strict` 的 G0–G5 全部需要人工确认。
- 首次接入由平台团队执行一次 `sdd init`；旧入口 `bootstrap.py` 保留为兼容 shim。

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

需要紧急修复、严格流程或存量重构时，由创建需求的人加 `--workflow l2-hotfix`、
`--workflow l2-strict` 或 `--workflow l2-refactor`；Agent 不要自行选择或修改工作流。

## 2. 自动循环

1. 读取 `next.action`、`next.step_id`、`next.kind`、`next.prompt_file`、
   `next.artifact`、`next.done_when`、`next.submit_with` 和 `next.context_bundle`。
2. 只按 `context_bundle` 的范围调研代码、测试、契约、ADR、知识索引和
   `sdd/context/`；把事实写进 `context.md`，把未决问题写进 `unknowns.md`。
3. 产出 `next.artifact` 要求的内容。
4. 调用 `next.submit_with` 提交：
   - 阶段产物：`python -m sdd submit --artifact <name> --file <path> --json`
   - 实现任务：`python -m sdd submit-task --task T-xxx --evidence "..." --json`
   - 状态迁移：`python -m sdd complete --evidence "..." --json`
5. `ok=false`：按 `errors` 修复后重新提交。
6. `decision_required=true`：停止，只把 `question` 和 `options` 交给人类。
7. `human_checkpoint.required=true`：停止，并告诉人类执行 `human_checkpoint.command`。
8. 否则继续读取新的 `next.action`，直到 `done` 或人工检查点。

每个阶段只执行一个动作、用一个提交命令；不要绕过 CLI 批量推进。

## 3. 人类检查点与例外动作

正常流程只有两个人工检查点：

1. Spec 确认：人执行
   `python -m sdd approve --spec <spec> --human --evidence "需求已确认"`。
2. PR 合并：人执行
   `python -m sdd merge --spec <spec> --human --evidence "PR merged"`。

例外动作：

- 审批后范围变化：人执行
  `python -m sdd reapprove --spec <spec> --human --reason "..." --evidence "..."`。
  Agent 必须先执行 `python -m sdd change --spec <spec> --reason "..."` 登记变更；
  存在 pending change-set 时不得提交代码。
- 回退/返工：人执行
   `python -m sdd rewind --spec <spec> --to <stage> --reason "..." --human`。
- 解除阻塞：人执行
   `python -m sdd unblock --spec <spec> --human --evidence "..."`。
- 范围化豁免：人执行
   `python -m sdd waive --spec <spec> --check <id> --scope "..." --reason "..." --expires <iso> --evidence "..." --human`。
   豁免只对可豁免的非红线 required 检查有效，并绑定 Gate 产物哈希。

人可以用 `python -m sdd inbox --json` 查看所有等待处理的事项；
用 `python -m sdd events --spec <spec> --json` 和 `python -m sdd metrics --json`
查看审计链与质量指标。Agent 不代替人创建豁免。

## 4. 优先级

- 技术栈、目录、构建、测试和代码风格：以本文件其他章节为准；缺失时先检查仓库再记录，不得编造。
- SDD 阶段、提交方式、人工检查点和证据要求：以本托管块和 `sdd/agent-contract.md` 为准。
- 底层状态机和 Gate 规则：以 `sdd/scripts/sdd.py` 和 `sdd/config.json` 为准。

CI 会执行 `python -m sdd verify-core`、`python -m sdd verify-agent` 和
`python -m sdd check --all --stage ci --check-git`。不要试图绕过。

`verification-evidence.jsonl` 是真实测试证据；`events.jsonl` 是带哈希链的审计流。
只在 Markdown 写 PASS、伪造退出码或手工重写事件都会失败。
<!-- SDD:MANAGED:END -->
