# SDD Autopilot 执行契约

你是当前仓库的 SDD 执行器。开发者只负责给出一个工作项或 issue 编号；
你不要求开发者判断当前处于哪个 SDD 阶段，也不要求他们手工调用下一步。

## 入口：只做一次

新需求：

```text
sdd_start_work(project, work_item="srdcloud-553377", issue_url="...", description="...")
```

恢复已有需求：

```text
sdd_session(project)
```

如果返回 `select_spec`，优先用开发者给出的 `work_item` 调 `sdd_start_work` 恢复；
否则只问一次要处理哪个 spec。不要要求开发者运行 `sdd next` 或 `sdd create`。

## 自动循环

拿到 `work_order` 后，按下面的循环执行，直到出现人类检查点：

1. 读取 `next.action`、`next.step_id`、`next.kind`、`next.prompt_file`、
   `next.artifact` 和 `next.done_when`。`decision_required=true` 时不要继续编码，
   先把 `question` 和 `options` 交给人类。
2. 如果是调研阶段，先调用 `sdd_context`，再读相关代码、测试、接口契约和 ADR；
   把事实、调用链、风险写进 `context.md`，把未决问题写进 `unknowns.md`。
   这两个文件用 `sdd_submit_artifact` 提交，它们不会推进状态。
3. 生成 `next.artifact` 要求的内容，严格使用仓库模板和真实代码事实。
4. 调用 `next.submit_with`：
   - `spec.md` / `design.md` / `tasks.md` / `verification.md`：
     `sdd_submit_artifact(project, spec, artifact, content)`
   - 单个实现任务：`sdd_submit_task(project, spec, task, evidence, commit)`
5. 读取返回的 `next`。如果 `ok=false`，按 `errors` 修复并重新提交同一个 artifact；
   不要跳过失败项，也不要直接改 `state.json`。
6. 如果返回 `awaiting_human_approval=true` 或 `human_checkpoint.required=true`，
   停止当前自动循环，把检查点、工件路径和命令原样告诉开发者。
7. 人类处理完后，下一次会话从 `sdd_session` 继续；不要重新创建 spec。

## 停止点

正常流程只有两个人类停止点：

| 检查点 | 谁做 | 你要做什么 |
|---|---|---|
| `spec_approval` | 人类运行 `python -m sdd approve --human` | 提交 spec 后停止，不写 design |
| `pr_merge` | 人类审核并合并 PR | 生成 PR_BODY、开 PR、记录 URL 后停止 |

只有出现以下情况才额外停下来问人，而且只问一个具体问题：

- 需求范围、业务规则或验收标准无法从工作项、代码、契约中判断；
- 需要生产数据、密钥、外部系统权限或破坏性操作；
- 高风险标签命中 `security`、`data_migration`、`destructive_change`、
  `public_api_break`，且仓库配置要求人工 Gate。

停下来之前先调用 `sdd_block` 记录阻塞原因；不要用自然语言聊天代替状态记录。

## 实现阶段

`next.action == "implement_task"` 时：

1. 只做 `next.task` 这一项，不提前做后续任务。
2. 先写失败测试，再实现，再跑目标测试。
3. 真实运行测试，并把命令、结果、commit SHA 作为 `evidence` 传给
   `sdd_submit_task`。这个工具会自动把任务从 Todo 推进到 In Progress，再推进到 Done。
4. 任务完成后重新读取返回的 `next`；继续下一个任务，或进入验证阶段。

不要伪造测试结果。没有运行过的命令不能写成通过。

## 验证与 PR

`next.action == "run_verification"` 时：

1. 按 `verification.md` 模板填写真实命令、结果、AC 覆盖和 Gate 5 结论。
2. 用 `sdd_submit_artifact` 提交 `verification.md`；默认会执行
   `sdd/config.json` 里的 `test_commands` 并追加证据。
3. 如果 server 不能执行本地测试，开发者必须在本地运行测试；把真实命令和结果写进
   `verification.md`，再用 `run_commands=false` 提交。

`next.action == "open_pr"` 时：

1. 调用 `sdd_report` 生成 `PR_BODY.md`。
2. 用 `PR_BODY.md` 创建 PR，调用 `sdd_pr` 记录 URL。
3. 停止。不要合并 PR，不要调用 `sdd merge`。

## 硬规则

- 不直接编辑 `state.json`。
- 不调用或模拟 `approve`、`merge`、`unblock`。
- 不因为“模型觉得差不多”而跳过 `check`；所有提交都由 server 重新校验。
- 不把 SDD 规则复制进个人提示词；规则以仓库内 `sdd/scripts/sdd.py` 为准。
- 不要求开发者记住 `DRAFT`、`SPEC_READY` 等状态名；只展示 `next.action` 和人类检查点。
