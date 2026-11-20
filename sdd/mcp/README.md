# SDD MCP 适配层

这个目录把仓库内的 `sdd.py` 暴露成 MCP 工具。  
状态机仍然只有一份，MCP 只是适配器；它可以跑在本地，也可以跑在共享服务端。

## 两种运行形态

| 形态 | 代码在哪里 | MCP 怎么跑 | 适合 |
|---|---|---|---|
| **本地模式** | 每个开发者本地 clone | 每个开发者本地 `stdio` MCP | 现在就要推广；多人各自开发 |
| **共享模式** | 服务端工作区 / 共享盘 | 一个共享 `streamable-http` MCP | 后期统一环境、issue 自动开发 |

### 本地模式

每个开发者在自己仓库根目录启动：

```powershell
python -m sdd.mcp.server --root . --transport stdio
```

这时 server 进程就在开发者机器上，能看到该开发者的工作区，所有 `sdd_*` 工具直接操作本地 clone。  
不需要 registry，不需要把代码放到服务端。

Agent/dsh 的 MCP 配置示例见 `local-config.example.json`。

### 共享模式

服务端能看到已注册仓库时：

```powershell
python -m sdd.mcp.server --registry sdd-mcp.json `
  --transport streamable-http --host 0.0.0.0 --port 8765 --path /mcp
```

这时一个 server 可以服务多个项目，但**只能操作 server 能访问到的文件系统**，不能直接改同事本地 clone。

## 它负责什么

- 本地模式：直接解析 `--root` 指向的当前仓库；
- 共享模式：按 `project` 解析到已注册的仓库；
- 调用该仓库的 `sdd/scripts/sdd.py`；
- 返回结构化的 `status / next / check / complete / verification`；
- 读取 service card、ADR、contracts 和 spec context；
- 共享模式下统一版本、统一部署、统一审计入口。

## 它不负责什么

- 不替代 dsh/Codex/Claude 改代码；
- 不暴露 `approve` 和 `merge`，这两个永远是人；
- 不把 SDD 规则复制进 MCP；规则仍在仓库的 `sdd.py` 和 `config.json`；
- 不自动合并 PR。
- 不在 server 看不到的本地 clone 上写文件。

## 安装

```powershell
python -m pip install -r sdd/mcp/requirements.txt
```

本地模式用 `--root .`，共享模式用 `--registry sdd-mcp.json`。

共享 HTTP 健康检查：

```powershell
python sdd/mcp/smoke_client.py http://127.0.0.1:8765/mcp
```

## 注册文件

`registry.json` 是服务端唯一需要维护的配置：

```json
{
  "workspace_root": "/workspaces",
  "projects": {
    "order-platform": {
      "path": "order-platform",
      "description": "Order domain control repository",
      "tags": ["domain:order"]
    },
    "payment-api": {
      "path": "payment-api",
      "description": "Payment backend service",
      "tags": ["service:payment"]
    }
  }
}
```

`path` 可以是绝对路径，也可以是相对 `workspace_root` 的路径。  
每个项目必须有：

```text
<project>/sdd/scripts/sdd.py
<project>/sdd/config.json
```

## MCP 工具

Agent 可用：

- `sdd_health`
- `sdd_list_projects`
- `sdd_start_work`（新需求入口）
- `sdd_session`（恢复入口）
- `sdd_list_specs`
- `sdd_board`（Spec/Task 看板与进度）
- `sdd_inbox`（只读列出等待人工处理的事项）
- `sdd_events`（append-only 状态与人工检查点审计流）
- `sdd_submit_artifact`（阶段产物提交，自动校验/推进）
- `sdd_submit_task`（单 Task 提交，自动 start + complete）
- `sdd_status`
- `sdd_next`
- `sdd_check`
- `sdd_reserve_spec_id`
- `sdd_create_spec`
- `sdd_start`
- `sdd_complete`
- `sdd_verify`
- `sdd_report`
- `sdd_pr`
- `sdd_block`
- `sdd_read_artifact`
- `sdd_context`

人类专用、故意不暴露：

- `sdd approve`
- `sdd merge`
- `sdd unblock`
- `sdd rewind`

`sdd_start_work` 和 `sdd_create_spec` 支持可选 `workflow` 参数
（`l2-standard` / `l2-hotfix` / `l2-strict`）；工作流由创建 Spec 的人决定，
MCP 不提供修改工作流的工具。

## 多人并行时的 Spec ID

`sdd_reserve_spec_id` 在共享模式下使用 registry workspace 里的原子计数器，多个分支/worktree 不会拿到同一个编号。

本地模式下计数器在各自 clone 里，只能防本机重复；多人并行时仍应调用共享 MCP 的 `sdd_reserve_spec_id`，再把返回的 `spec_id` 传给本地 `sdd_create_spec`/`sdd.py new`。

分配器用 registry workspace 里的锁文件保证单 server / 共享文件系统下的原子性。如果要多副本部署，应把计数器换成数据库或 Redis 的原子操作。

## MCP 如何串起 SDD

### 开发者视角：只给一个工作项

开发者不需要判断当前是 `DRAFT`、`SPEC_READY` 还是 `IMPLEMENTING`。新需求只说：

```text
根据 srdcloud-553377 做这次开发
```

Agent 只调用一次：

```text
sdd_start_work(project, work_item="srdcloud-553377", issue_url="...", description="...")
```

它返回 `work_order`、`next.action`、`next.submit_with`、`research_checklist` 和
`human_checkpoint`。后续 Agent 不再询问阶段，只按 `next.action` 产出并提交。

### 自动循环

```text
新需求: sdd_start_work
  └─ 写 spec.md -> sdd_submit_artifact
       └─ 停在 human_checkpoint=spec_approval
            └─ 人类 approve

恢复: sdd_session
  └─ next.action=write_design -> 写 design.md -> sdd_submit_artifact
  └─ next.action=write_tasks  -> 写 tasks.md  -> sdd_submit_artifact
       └─ 自动进入 IMPLEMENTING，返回 implement_task
  └─ next.action=implement_task -> sdd_submit_task
       └─ 自动 start + complete，返回下一个 Task 或 run_verification
  └─ next.action=run_verification -> 写 verification.md -> sdd_submit_artifact
       └─ 自动跑 test_commands，校验后进入 PR_READY
  └─ next.action=confirm_merge -> sdd_report -> 停在 human_checkpoint=delivery_confirmation
       └─ 人类确认交付（sdd merge --human）
  └─ next.action=open_pr -> 提交确认状态 -> 开 PR -> sdd_pr 记录 URL
```

`sdd_submit_artifact` 支持 `context.md`、`unknowns.md` 作为非推进型调研产物；
这两个文件可以多次更新，不改变状态。

### 为什么不会“光有工具、流程串不起来”

MCP 本身不会监听文件，也不会自己调用模型。真正把流程串起来的是三层：

1. **Agent 循环契约**：`sdd/prompts/autopilot.md` 要求 Agent 只按 `next.action` 工作，
   不向开发者询问阶段；每次产出后必须调用 `next.submit_with`。
2. **MCP 硬门禁**：`sdd_submit_artifact` / `sdd_submit_task` 会重新检查当前状态和工件，
   顺序不对、工件不合格、Task 未开始、验证未填都会返回 `ok=false` 和结构化 errors。
3. **harness / CI 兜底**：dsh 的 `session_start` 注入工作单，`before_finish` 调 `sdd_check`；
   merge 前 CI 再跑 `sdd check --all --stage ci --check-git`。

所以模型即使比较笨，也不能用“我觉得完成了”绕过状态机；它只能修当前返回的错误。

### 哪些是硬约束，哪些只是建议

| 环节 | 约束 | 类型 |
|---|---|---|
| 新需求 | `sdd_start_work` 建/恢复 Spec，不允许手工猜 spec_id | 建议入口 |
| DRAFT | `sdd_submit_artifact("spec.md")` 后必须人类 `approve`，不能继续 design | 硬 |
| SPEC_READY | `sdd_submit_artifact("design.md")` 内部重新跑 Design 校验 | 硬 |
| DESIGN_READY | `sdd_submit_artifact("tasks.md")` 内部重新跑 Tasks 校验 | 硬 |
| TASKS_READY | 提交 tasks 后自动再次校验并进入 IMPLEMENTING | 硬 |
| IMPLEMENTING | `sdd_submit_task` 自动 start 后再 complete，不能跳 Task | 硬 |
| IMPLEMENTING | 所有 Task 未 Done 时不能进入 VERIFYING | 硬 |
| VERIFYING | `sdd_submit_artifact("verification.md")` 自动执行 test_commands | 硬 |
| VERIFYING | AC 覆盖、测试标记、G0–G4 报告不全则拒绝 | 硬 |
| PR_READY | 等待人类确认交付，不能创建或记录 PR | 硬 |
| MERGED | 确认后才创建 PR，用 `sdd_pr` 记录 URL | 硬 |
| 任意阶段 | `approve` / `merge` / `unblock` 没有 MCP 工具 | 硬（人类） |
| 测试证据 | 不能验证“证据是否真实”，只能要求非空并做工件校验 | 软 |

关键点：**`next.action` 是 Agent 的唯一调度信号，`sdd_submit_*` 是硬门禁。**

低层 `sdd_next` / `sdd_check` / `sdd_start` / `sdd_complete` 仍保留，用于调试、
人类排障和非 dsh harness 兼容；正常 Agent 不应手工串这些工具。

### 还缺什么

- MCP 不能证明 Agent 真的跑了测试；最终仍要靠 CI 和人工 PR 审核。
- `docs/prd-index.md` 是共享文件，多人并行仍可能冲突，后续应由 CI 重新生成。
- dsh 的 `session_start` / `before_finish` / `before_commit` 目前是契约文档，
  需要在 dsh 插件 API 确认后接上；没有插件时靠 AGENTS.md 和 server instructions。

## 多人同仓库的两种模式

核心事实只有一句：

> MCP server 只能操作**它所在进程能访问到的文件系统**。

### 模式 B：本地 clone + 本地 MCP（推荐现在用）

```text
开发者电脑
  repo clone
    ├─ sdd/scripts/sdd.py       # 仓库自带，跟着分支走
    ├─ docs/specs/...           # 当前分支的 Spec 和 state.json
    └─ local MCP (stdio)        # 只操作这个 clone

共享 MCP（可选，只读）
  └─ registry / context / 审计索引
```

流程：

1. 开发者 `git clone` 仓库；
2. Agent 用本地 stdio MCP，或直接调用 `sdd.py`；
3. 状态和工件写进当前工作区，跟代码一起 commit；
4. 人工确认交付后，Agent push 分支、开 PR；
5. CI 跑 `sdd check --all --stage ci --check-git`；
6. PR 合并后，Spec 和 `state.json` 一起进主干。

要点：

- **不需要把代码放服务端**；
- 每个开发者有独立工作区，互不覆盖；
- 共享 MCP 不能替别人写本地文件，只能提供上下文/目录/只读查询；
- 这是多人共同开发一个仓库时最现实的起步方式。

### 模式 A：服务端工作区 + 共享 MCP（后期）

```text
服务端
  worktrees/
    order-api/SPEC-ORDER-001/   # 一个 Spec/任务一个 worktree
    order-api/SPEC-ORDER-002/
  shared MCP
    └─ 操作这些 worktree

开发者
  └─ 远程 IDE / Web IDE / Agent
```

流程：

1. 仓库放在服务端或共享盘；
2. 每个需求/任务开一个 git worktree，而不是所有人编辑同一个目录；
3. 共享 MCP 按 `project + worktree` 操作；
4. 开发者在远程 IDE 或 Web 终端里工作；
5. CI 和自动化 Agent 也在服务端执行。

要点：

- **共享工作区不等于所有人编辑同一个目录**；必须一个 Spec/任务一个 worktree；
- 一个 server、一个版本、一个环境，适合后期统一治理；
- 需要解决远程 IDE 体验、权限隔离、资源配额和 secrets 管理；
- 服务端 runner 可以进一步做到 issue 进来后全自动开发、人只审 PR。

### 混合模式：共享控制面 + 本地执行

如果既想要“一个 server 统一版本”，又想保留本地开发：

- 共享 MCP 负责：项目目录、上下文、只读查询、审计索引；
- 本地 MCP/CLI 负责：写 `state.json`、创建 Spec、推进阶段；
- 两边通过 Git 分支同步，而不是让远端进程直接改本地文件。

这就是当前推荐的过渡形态：**共享控制面是事实上的一个 server，但写入仍发生在本地工作区**。

## `sdd_verify` 的边界

`sdd_verify` 会在 **server 所在环境** 执行目标仓库的 `test_commands`。只有当 server 能访问仓库且测试环境完整时，结果才可信。

- 本地模式：server 就在开发者机器上，`sdd_verify` 可信；
- 共享工作区 / 服务端 runner：server 能执行目标仓库测试时可用；
- 共享控制面 + 本地执行：本地跑测试，把真实命令和结果写进 `verification.md`，
  然后用 `sdd_submit_artifact(..., run_commands=false)` 提交。

不要把“server 返回成功”误解成“同事本地测试通过”。

## 安全

- 不要把 MCP server 直接暴露到公网；
- 前面放公司 SSO/API Gateway/Nginx；
- 限制 `registry.json` 只能由 SDD owner 修改；
- 只挂载需要的工作区，不要挂载整个 home；
- server 不暴露 approve/merge，减少误操作面；
- 审计证据仍在 git 里，不以 server 日志作为唯一证据。

## 版本维护

- 镜像/服务版本跟 `sdd/__init__.py` 和 `sdd/mcp/__init__.py` 的版本一致；
- 共享模式升级只换 server 镜像；
- 本地模式建议固定 Python 包版本，并提供一条自动更新命令；
- `sdd_health` 返回版本、模式（`local` / `registry`）和项目数，便于确认大家连的是同一个版本。
