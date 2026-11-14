# SDD Agent Contract

本文件是仓库内唯一的 SDD 流程说明。`AGENTS.md` 的托管块只负责把 Agent 引导到这里。
CLI 是地基，MCP 只是可选适配器；没有 MCP 也能跑完整流程。

## 1. 入口

新需求：

```powershell
python -m sdd start-work --work-item srdcloud-553377 --issue-url "https://..." --json
```

恢复当前会话：

```powershell
python -m sdd resume --json
```

`resume` 优先读取 `.sdd/runtime/sessions/` 中当前会话的任务指针。  
一个仓库可以同时有多个活跃 Spec；不同会话各自绑定自己的 Spec。

## 2. 自动循环

1. 读取 `next.action`、`next.step_id`、`next.kind`、`next.prompt_file`、
   `next.artifact` 和 `next.done_when`。`decision_required=true` 时必须停止，
   把 `question` / `options` 交给人类。
2. 调研代码、测试、接口契约、ADR 和服务卡，写入 `context.md` 和 `unknowns.md`。
3. 生成 `next.artifact` 要求的内容。
4. 调用 `next.submit_with`：
   - 阶段产物：`python -m sdd submit --artifact <name> --file <path> --json`
   - 实现任务：`python -m sdd submit-task --task T-001 --evidence "..." --json`
5. 如果返回 `ok=false`，按 `errors` 修复并重新提交。
6. 如果返回 `awaiting_human_approval=true` 或 `human_checkpoint.required=true`，停止自动循环。
7. 人处理完后，下一次会话从 `resume` 继续，不要重新创建 Spec。

## 3. 人类检查点

正常 L2 流程只有两个人类停止点：

| 检查点 | 谁做 | 命令 |
|---|---|---|
| Spec 确认 | 人 | `python -m sdd approve --spec <spec> --human --evidence "需求已确认"` |
| PR 合并 | 人 | `python -m sdd merge --spec <spec> --human --evidence "PR merged"` |

`approve`、`merge`、`unblock` 只能由人执行；MCP 不暴露这三个工具。

## 4. 强制边界

- 不直接编辑 `state.json`。
- 不手工编辑 `events.jsonl`；它是由 `sdd` 自动追加的审计流。
- 不跳过 `sdd submit` 的校验。
- 不伪造测试结果。
- 一次只做一个实现任务。
- 每个代码 Commit 只关联一个 Task，并带 `Spec-Id` / `Task-Id` trailer。
- CI 必须通过 `python -m sdd check --all --stage ci --check-git`。
- 核心和模板由平台团队维护；业务仓库不要修改 `sdd/core.py`、`sdd/templates/`、`sdd/prompts/`。
- `sdd/manifest.json` 与 `sdd/VERSION` 必须提交；CI 用 manifest 校验核心没有被误改。

## 5. 仓库自带与零配置

- 平台团队维护 `sdd/` 核心，通过同步 PR 或 bot 推送到各业务仓库。
- 一线开发者只 `git clone`，不需要安装插件、注册 workflow 或维护个人配置。
- 仓库已有 `AGENTS.md` 时，只替换 `<!-- SDD:MANAGED:START -->` 到
  `<!-- SDD:MANAGED:END -->` 之间的托管块，其余内容保持不变。
- 业务仓库只维护 `sdd/config.json`、`sdd/context/` 和 `docs/specs/`，不要改核心。

## 6. MCP 是可选适配器

没有 MCP 时，CLI + 本文件 + `AGENTS.md` 可以跑完整流程。  
有 MCP 时，本地 MCP 调用同一个 `Workspace` 核心，提供结构化工具；共享 MCP 只提供
上下文、目录、只读查询和 Spec ID 预留，不能直接写同事的本地 clone。

## 7. 冲突处理

- 技术栈、目录、构建、测试和代码风格：以仓库现有 `AGENTS.md` 其他章节为准。
- SDD 阶段、提交方式、人工检查点和证据要求：以本文件和 `AGENTS.md` 托管块为准。
- 项目事实可以覆盖模板默认值；但不能覆盖 `approve`、`merge`、证据和 CI 校验。
