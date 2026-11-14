<!-- SDD:MANAGED:START -->
## SDD Workflow

本仓库使用 SDD。所有命令都在仓库根目录执行。

### 会话入口

```powershell
python -m sdd resume --json
```

没有当前工作项时，只问一次工作项，然后运行：

```powershell
python -m sdd start-work --work-item <work-item> --json
```

### 自动循环

- 读取返回的 `next.action`、`next.artifact`、`next.prompt`、`next.done_when`。
- 先调研代码、测试、契约和 `sdd/context/`，把事实写进 `context.md`，把未决问题写进 `unknowns.md`。
- 产出 `next.artifact` 后，用 `next.submit_with` 提交：
  - 阶段产物：`python -m sdd submit --artifact <name> --file <path> --json`
  - 实现任务：`python -m sdd submit-task --task T-xxx --evidence "..." --json`
- `ok=false` 时按 `errors` 修复后重新提交；不要跳步，不要直接编辑 `state.json`；
  也不要手工改 `events.jsonl`，审计流由 `sdd` 自动追加。
- `decision_required=true` 时停止，把 `question` / `options` 交给人类，不要继续编码。
- 只有 `human_checkpoint.required=true` 时才停下来找人。

### 人类检查点

正常流程只有两个：

1. Spec 确认：人执行 `python -m sdd approve --spec <spec> --human --evidence "需求已确认"`。
2. PR 合并：人执行 `python -m sdd merge --spec <spec> --human --evidence "PR merged"`。

`approve`、`merge`、`unblock` 只能由人执行，Agent 不得代替。

### 优先级

- 技术栈、目录、构建、测试和代码风格：以本文件其他章节为准；缺失时先检查仓库再记录，不得编造。
- SDD 阶段、提交方式、人工检查点和证据要求：以本托管块和 `sdd/agent-contract.md` 为准。
- 底层状态机和 Gate 规则：以 `sdd/scripts/sdd.py` 和 `sdd/config.json` 为准。

CI 会执行 `python -m sdd verify-core`、`python -m sdd verify-agent` 和
`python -m sdd check --all --stage ci --check-git`。不要试图绕过。
<!-- SDD:MANAGED:END -->
