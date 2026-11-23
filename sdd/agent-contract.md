# SDD Agent Contract

本文件是仓库内唯一的 SDD 流程说明。`AGENTS.md` 的托管块只负责把 Agent 引导到这里。
CLI 是地基，MCP 只是可选适配器；没有 MCP 也能跑完整流程。
Agent 不应向开发者询问当前阶段，只应询问一次工作项，然后按 `next.action` 执行。

## 1. 入口

新需求：

```powershell
python -m sdd start-work --work-item srdcloud-553377 --issue-url "https://..." --json
```

需要非默认流程时加 `--workflow l2-hotfix` 或 `--workflow l2-strict`。工作流由
创建 Spec 的人决定；Agent 不要自行改工作流。

恢复当前会话：

```powershell
python -m sdd resume --json
```

`resume` 优先读取 `.sdd/runtime/sessions/` 中当前会话的任务指针。  
一个仓库可以同时有多个活跃 Spec；不同会话各自绑定自己的 Spec。

## 2. 自动循环

1. 读取 `next.action`、`next.step_id`、`next.kind`、`next.prompt_file`、
   `next.artifact`、`next.done_when` 和 `next.context_bundle`。
   `decision_required=true` 时必须停止，
   把 `question` / `options` 交给人类。
2. 按 `context_bundle` 的 FR/AC、Design 章节、契约、约束、`allowed_paths`
   和 `exclude` 调研，写入 `context.md` 和 `unknowns.md`；范围为空时不要自行扩大。
3. 生成 `next.artifact` 要求的内容。
4. 调用 `next.submit_with`：
   - 阶段产物：`python -m sdd submit --artifact <name> --file <path> --json`
   - 实现任务：`python -m sdd submit-task --task T-001 --evidence "..." --json`
5. 如果返回 `ok=false`，按 `errors` 修复并重新提交。
6. 如果返回 `awaiting_human_approval=true` 或 `human_checkpoint.required=true`，停止自动循环。
7. 人处理完后，下一次会话从 `resume` 继续，不要重新创建 Spec。

## 3. 人类检查点

`l2-standard` 正常流程只有两个人类停止点：

| 检查点 | 谁做 | 命令 |
|---|---|---|
| Spec 确认 | 人 | `python -m sdd approve --spec <spec> --human --evidence "需求已确认"` |
| 交付确认（确认后才创建 PR） | 人 | `python -m sdd merge --spec <spec> --human --evidence "交付已确认"` |

人类确认交付后，Agent 才用 `PR_BODY.md` 创建 PR；PR 的审核合并由管理员在
GitHub 完成，不产生额外的 SDD 状态 PR。

`l2-hotfix` 仍是两个停止点，但 G2 自动通过，设计使用轻量模板；高风险或命中
`risk_stop` 的需求不允许使用该预设。`l2-strict` 的 G0–G5 全部需要人工确认，
`verification.md` 还必须有独立审查章节，reviewer session 不能等于实现 session。

`approve`、`merge`、`unblock`、`rewind` 只能由人执行；MCP 不暴露这些工具。
人工命令可加 `--approver "张三 <zhang@example.com>"`；不传时取 Git 配置。
Agent 不传 `--approver`，也不得代替人执行这些命令。

当当前阶段的自动检查通过、但 Gate 要求人工时，`submit` / `submit-task` 会返回
`awaiting_human_approval=true` 和 `human_checkpoint`。Agent 必须停止，
不要继续调用 `complete`。人可以运行 `python -m sdd inbox --json` 查看所有待办。

`rewind` 只允许回到更早阶段，并且必须带 `--reason`。它会归档被作废的工件、
移动 Gate 报告、重置相关 Task，并在 `events.jsonl` 记录 `rewind` 事件。

Gate 报告会绑定当前产物的 SHA-256。批准后修改 `spec.md`、`design.md`、
`tasks.md` 的任务计划或 `verification.md`，CI 会失败并要求重新过 Gate 或回退。
任务执行导致的 `status`、`commit`、`done` 变化不在 `tasks.md` 哈希范围内。
文本工件按 LF 规范化后计算哈希，并兼容历史 CRLF 哈希；只有行尾变化不视为修改，
正文变化仍必须阻断。

Spec 创建时会把工作流预设快照到 `docs/specs/<Spec>/workflow.json`；后续修改
`sdd/workflows/` 不会影响旧 Spec。Agent 不得手工编辑该快照或 `state.json.workflow`。

## 4. 强制边界

- 不直接编辑 `state.json`。
- 不手工编辑 `events.jsonl`；它是由 `sdd` 自动追加的审计流。
- 不跳过 `sdd submit` 的校验。
- 不伪造测试结果。
- 不手写 `PASS` 绕过 G5；必须由 `sdd verify` 写入 Command/CWD/Exit/Head/Plan-Hash/At。
- AC 标签必须位于 `def test_*` 函数体内；任务表测试名必须能在测试文件中定位。
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
