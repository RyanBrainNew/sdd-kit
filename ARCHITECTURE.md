# 为什么是这套结构

本文解释 `sdd-kit` 的设计取舍，方便在公司内部评审、试点和后续演进。结论先行：

> SDD 不是一个工具，而是一组可验证的契约：工件、追溯、Gate、证据。
> 工具只应该负责“让契约自动执行”，不应该把契约本身复制到每个工具里。

## 1. 从第一性原理拆问题

公司要求 SDD-L2，真正要保证的只有五件事：

1. **需求可追溯**：代码改动能回到工作项和 Spec。
2. **验收可测试**：每条 AC 都有明确的执行路径和证据。
3. **阶段有门禁**：Spec、Design、Tasks、实现、验证不能跳步。
4. **证据可审计**：Gate 报告、测试结果、commit trailer、PR 正文都在 Git 里。
5. **人不被流程淹没**：人只在需求确认和最终合并两个高价值节点介入。

其余都是实现手段。判断一个方案是否合适，只看它是否以最低摩擦满足这五条。

## 2. 五个彼此独立的关注点

很多方案之所以重，是因为把下面五层揉成了一个产品：

| 层 | 回答的问题 | 本方案 |
|---|---|---|
| 方法层 | Agent 应该怎么工作 | `sdd/prompts/` + Matt 风格的 TDD/review 习惯 |
| 状态层 | 当前做到哪一步、下一步是什么 | `sdd/scripts/sdd.py` 状态机 |
| 上下文层 | AI 需要知道哪些系统事实 | `sdd/context/` + `sdd_context` |
| 强制层 | 做错了能不能拦住 | Git Hook + CI `sdd check` |
| 交付层 | 人通过什么入口使用 | 仓库 CLI、共享 MCP、dsh 薄适配 |

拆开之后，每一层都可以独立替换：

- 换 Agent（Codex、Claude、dsh、内部 harness）不影响状态机；
- 换入口（CLI、MCP、IDE 插件）不影响规则；
- 换 CI（GitHub、GitLab、Jenkins）只换一个 job；
- 换方法（TDD、review、triage）只换 prompt。

这就是“薄内核 + 适配器”的结构。

## 3. 总体结构

```text
┌─────────────────────────────────────────────────────────┐
│  交付层：Codex / Claude / dsh / IDE / 自动化 Agent        │
│  只负责：读上下文、改代码、跑测试、提交证据                │
└───────────────┬─────────────────────────┬───────────────┘
                │ MCP tools               │ shell / git
┌───────────────▼───────────────┐ ┌───────▼───────────────┐
│ 共享 MCP 控制面（可选）        │ │ 仓库内 CLI（必需）     │
│ registry + 工具适配 + 审计入口 │ │ sdd/scripts/sdd.py    │
└───────────────┬───────────────┘ └───────┬───────────────┘
                │ 调用各仓库脚本           │ 唯一状态机
                └─────────────┬────────────┘
┌─────────────────────────────▼───────────────────────────┐
│ 仓库内 SDD 核心                                          │
│  state.json / templates / prompts / gates / checks       │
│  sdd/context：服务卡、契约、ADR、术语                     │
└─────────────────────────────┬───────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────┐
│ 强制层：Git Hook + CI                                     │
│  check --all --stage ci --check-git                       │
└─────────────────────────────────────────────────────────┘
```

关键约束：

- **状态机只有一份**：`sdd/scripts/sdd.py`。
- **MCP 不复制规则**：只解析 project、调用脚本、返回结构化结果。
- **dsh 不复制规则**：只做 session 注入、斜杠命令、commit/finish hook。
- **CI 不信任 Agent**：直接检查文件和 Git 历史。
- **人保留两个开关**：`approve`、`merge`。

## 4. 和 aidlc / Trellis / Matt skills 的关系

### 4.1 它们不是同一层的东西

| 方案 | 强项 | 缺什么 | 适合位置 |
|---|---|---|---|
| aidlc | 强流程、强审计、完整证据链 | 初始化和日常操作重，vibecoding 体验差 | 高风险变更的 strict 模式 |
| Trellis | 初始化后接近无感，体验好 | 公司要求的 Spec/Gate/trailer/CI 需另补 | 开发体验参考 |
| Matt skills | TDD、triage、review 等方法很好 | 没有仓库状态机、Gate 报告、CI 强制 | Agent 的方法层 |
| 本 kit | 仓库自带、状态机、CI 硬校验、两个人工点 | 需要一次性接入和上下文补录 | L2 默认路径 |

### 4.2 Matt skills 能直接满足 SDD 吗

不能。Matt skills 解决的是“Agent 怎么把活干好”，不是“公司怎么证明活按流程干了”。

缺的是：

- Spec / Design / Tasks / Verification 的固定工件；
- 状态机和阶段门禁；
- Gate 0–5 报告；
- commit trailer 和 PR 四要素；
- CI 对追溯链的硬校验。

正确用法是把 Matt 的方法嵌进 `sdd/prompts/`，而不是拿 skills 代替 SDD。

### 4.3 aidlc 能不能跑出 Trellis 的感觉

能接近，但代价是削掉它最有价值的部分。aidlc 的慢不是实现问题，而是“每步都留下可审计痕迹”的必然成本。

如果目标只是 L2，没必要把 aidlc 的完整仪式搬进日常开发。更合理的做法是：

- 默认走本 kit 的 L2 轻流程；
- 高风险变更（安全、数据迁移、破坏性变更、公共 API 破坏）切到 strict 模式；
- strict 模式可以复用 aidlc 或本 kit 的 `--human` Gate。

### 4.4 Trellis 值得学什么

值得学的是体验，不是它的内部规则：

- 初始化一次，之后不要求每个人记命令；
- Agent 自动读上下文和当前任务；
- 人只看到“要做什么”和“结果是什么”；
- 流程在后台执行，不打断编码节奏。

本 kit 用 `AGENTS.md + python -m sdd + 可选 MCP + CI` 达到同样效果，但把公司要求的工件和证据留在仓库里。

### 4.5 Spec Kitty 值得学什么，为什么没有直接采用

Spec Kitty 是开源扫描里控制面最接近本 kit 的产品。值得学的是：

- `next --json` 这种确定性的“下一步”接口；
- work package lane 和 `.worktrees/` 的并行隔离；
- `review / accept / merge / retrospective` 的审计链；
- built-in / org / project 三层 Charter/Doctrine 的分发方式。

不能直接采用的原因不是 star 数，而是边界：

- 它要求项目级 `spec-kitty init` / `verify-setup`，与“clone 即用、无个人初始化”冲突；
- 公司 6 个骨架、G0–G5、AC 追溯、trailer、PR 四要素、PRD index 不在内建范围；
- 截至 2026-11-14，官方文档明确 gate mechanism 尚未成为 shipped behaviour，
  当前 gate fault 仍 fail open，不能直接充公司硬门禁；
- 它处在 4.0.0rc8 快速迭代期，作为公司底座需要锁版本和额外维护。

因此本 kit 保留“仓库内硬状态机 + CI 证据链”，只借鉴 Spec Kitty 的任务控制、
worktree 和 org doctrine 思路。中期若要收敛到开源底座，优先评估
“Spec Kitty + 公司 L2 Charter/Gate/CI 适配包”，而不是无适配直接替换。

### 4.6 控制面对照：我们吸收了什么，没吸收什么

| 能力 | Spec Kitty | 本 kit 当前做法 | 结论 |
|---|---|---|---|
| 确定性下一步 | `next --json` 返回 `kind/action/step_id/prompt_file/question/options` | `next` 返回 `action/state/step_id/kind/prompt_file/artifact/done_when` | 已吸收核心契约 |
| 当前任务视图 | work package kanban + lane 事件 | `sdd board` + `task_counts` | 已吸收轻量版 |
| 任务状态 | 9 个 lane、27 个合法迁移、append-only event log | `Todo / In Progress / Done` + `state.json` history + `events.jsonl` 审计流 | 保留轻量 L2 模型，吸收事件流 |
| 并行隔离 | 自动计算 lane、每个 lane 一个 worktree | 会话指针 + 分支回退；一个 Spec/分支 | 暂不自动创建 worktree |
| 评审闭环 | implement → review → approve → done | Task 完成 → PR → 人工 merge | 公司 L2 只需 PR 级评审 |
| 治理分发 | Charter/Doctrine pack | 仓库 bootstrap + manifest + 同步 bot | 用更轻的方式解决 |

这不是“谁更先进”的判断，而是成本/收益判断。Spec Kitty 的 lane 和 worktree 对
高并发、多 Agent、强审计很有价值；对本阶段的 L2 默认路径，它们带来的 Git、
权限和培训成本高于收益。等出现“同一仓库多个 Agent 并行改代码”的真实需求，再把
worktree/lane 作为可选的 execution adapter 接入。

## 5. 两种开发模式：本地 clone vs 服务端工作区

核心事实只有一句：

> MCP server 只能操作**它所在进程能访问到的文件系统**。

这决定了架构只能是下面两种之一，或者它们的混合。

### 5.1 模式 B：本地 clone + 本地 MCP（现在推荐）

```text
开发者电脑
  repo clone
    ├─ sdd/scripts/sdd.py       # 仓库自带，跟分支走
    ├─ docs/specs/<id>/         # 当前分支的 Spec 和 state.json
    └─ local MCP (stdio)        # 只操作这个 clone

共享 MCP（可选，只读）
  └─ registry / context / 审计索引
```

工作方式：

1. 每个开发者 `git clone`；
2. 本地启动 `python -m sdd.mcp.server --root . --transport stdio`；
3. Agent 通过 `python -m sdd`（或可选的本地 MCP）推进状态，状态写进当前工作区；
4. 工件跟代码一起 commit、push、开 PR；
5. CI 跑 `sdd check --all --stage ci --check-git`；
6. 合并后，Spec 和 `state.json` 一起进主干。

优点：

- 不改变本地开发习惯；
- 每个开发者有独立工作区，互不覆盖；
- 不需要把代码放服务端；
- 接入成本最低。

代价：

- 共享 MCP 不能替别人写本地文件；
- 共享 MCP 只能做上下文、目录、只读查询和审计索引；
- 如果要做全自动 issue agent，仍需要服务端 runner。

### 5.2 模式 A：服务端工作区 + 共享 MCP（后期）

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

工作方式：

1. 仓库放在服务端或共享盘；
2. 每个需求/任务开一个 git worktree，而不是所有人编辑同一个目录；
3. 共享 MCP 按 `project + worktree` 操作；
4. 开发者在远程 IDE 或 Web 终端里工作；
5. CI 和自动化 Agent 也在服务端执行。

优点：

- 真正一个 server、一个版本、一个环境；
- 适合统一治理、远程开发、issue 自动开发；
- 代码、测试、Agent 执行环境一致。

代价：

- 远程 IDE 体验和网络延迟；
- 权限隔离、资源配额、secrets 管理；
- 需要 worktree 生命周期管理；
- 比本地模式重，不适合作为第一步。

**共享工作区不等于所有人编辑同一个目录。** 必须一个 Spec/任务一个 worktree，否则 `state.json`、工作区文件和 Git 分支会互相踩。

### 5.3 混合模式：共享控制面 + 本地执行

如果既想要“一个 server 统一版本”，又想保留本地开发：

- 共享 MCP 负责：项目目录、上下文、只读查询、审计索引；
- 本地 MCP/CLI 负责：写 `state.json`、创建 Spec、推进阶段；
- 两边通过 Git 分支同步，而不是让远端进程直接改本地文件。

这是当前最现实的过渡形态：**共享控制面是一个 server，但写入仍发生在本地工作区**。

### 5.4 多人同仓库的并发规则

同一仓库多人开发时，必须遵守：

1. **一个 Spec 一个分支/工作树，一个 owner**；不要两个人同时改同一个 `state.json`。
2. **Spec ID 不能只靠本地扫描分配**；多人并行时容易都生成 `SPEC-ORDER-001`。共享模式使用 `sdd_reserve_spec_id` 原子分配，再把返回的 ID 传给 `sdd_create_spec`。
3. **`docs/prd-index.md` 是共享文件**；并行分支容易冲突，建议由 CI 从各 Spec 元数据重新生成，或约定合并顺序。
4. **`state.json` 只由状态命令写**；冲突时以当前分支的 Spec 状态为准，不要手工合并出非法状态。
5. **CI 在合并前跑 `--all`**；避免只校验当前 Spec，漏掉其他分支带进来的问题。

这几条比“用哪个 MCP”更重要。工具不能替代分支纪律。

## 6. 多微服务知识没有沉淀，怎么办

这是 AI 自动开发真正的瓶颈，不是模型能力。解决办法不是“让 Agent 更聪明”，而是补一个最小上下文层：

```text
sdd/context/
  services.yaml          # 服务目录、负责人、依赖、测试命令
  services/*.md          # 每个服务一页卡
  contracts/             # OpenAPI / protobuf / 事件 schema
  adr/                   # 仍然约束代码的决策
  glossary.md            # 领域术语
docs/specs/<id>/context.md  # 本需求特有背景
```

`sdd_context` 会把这些内容和当前 Spec 的 `context.md`、`unknowns.md` 一起返回给 Agent。

最小启动顺序：

1. 先补 3–5 个最常改的服务卡；
2. 再补跨服务契约；
3. 再补仍然有效的 ADR；
4. 最后补术语表。

不要一开始追求“全量知识库”。只记录仍会影响下一次改动的事实，按需增长。

## 7. 自动化 Agent 适合哪套

如果目标是“issue 进来后 Agent 自动开发，人只审 PR”，推荐顺序是：

1. **本 kit 的仓库状态机 + CI**：保证 Agent 不跳步、产物可查。
2. **本地 MCP（模式 B）**：先让开发者本地跑通，不改代码位置；新需求只调用
   `sdd_start_work`，阶段产物用 `sdd_submit_artifact` / `sdd_submit_task` 自动推进。
3. **共享 MCP（模式 A）**：统一入口、上下文和审计。
4. **服务端 runner**：让 Agent 在可控环境里执行。
5. **dsh 薄适配**：把 session 注入、斜杠命令、commit/finish hook 接到现有 harness。

不建议把全自动 Agent 直接建立在 aidlc 的完整仪式上，成本高、反馈慢；也不建议只用 Trellis 或 Matt skills，因为缺少公司要求的硬证据。

自动化的关键不是让 Agent 记住状态机，而是让它只消费 `next.action`：
server 返回下一步和可提交工具，Agent 产出后用 `next.submit_with` 提交，server 重新校验。
这样开发者只提供一次工作项，中间阶段由 Agent 循环和 MCP 硬门禁串起来；人类只保留
spec 审批和 PR 合并两个检查点。

## 8. 为什么不直接 fork 一个 harness

可以，但不应该作为第一步。

harness 适合控制“模型怎么被调用、工具怎么暴露、会话怎么管理”；SDD 适合控制“工件和证据是否成立”。两者混在一起会导致：

- 流程规则和模型调用绑死，换模型/换 harness 就要重写；
- CI 无法独立校验；
- 本地开发和自动化 runner 行为不一致；
- 升级一个工具影响全公司。

正确顺序是：

1. 先把 SDD 核心做成仓库内可独立运行的 CLI；
2. 再用 MCP 暴露成共享控制面；
3. 最后才在 dsh/harness 里做薄适配。

只有确认“薄适配无法满足”时，才考虑 fork harness。

## 9. 分阶段落地

### 阶段 A：单仓库试点（1–2 周）

- 选一个微服务或前端项目；
- 复制 `AGENTS.md` + `sdd/`；
- 填项目事实和 `test_commands`；
- 跑一个小需求，验证 Spec → PR 全链路；
- 收集“哪些检查误报、哪些提示词不顺手”。

### 阶段 B：模板化（2–4 周）

- 把接入步骤固化成脚本或模板仓库；
- 统一 `config.json` 默认值；
- 补 3–5 个服务卡和跨服务契约；
- 把 `sdd check` 接进现有 CI。

### 阶段 C：共享控制面（1–2 月）

- 部署一个 MCP server；
- 维护一份 registry；
- 接公司 SSO/网关；
- 统一版本和升级流程；
- 先只读/上下文/校验，再逐步开放状态写入。

### 阶段 D：自动化（按需）

- issue agent 接 MCP；
- 服务端 runner 执行；
- 人只审 PR；
- 高风险变更自动切 strict 模式。

## 10. 成功标准

不要用“大家有没有写文档”衡量，用这些指标：

- 新需求从创建 Spec 到开 PR 的 lead time；
- `sdd check` 一次通过率；
- PR 中 AC 证据缺失的比例；
- 因上下文缺失导致的返工次数；
- 人工介入次数（目标：需求确认 + PR 合并）；
- 高风险变更的 Gate 记录完整率。

如果这些指标变好，流程就是有效的；如果只是文档变多、PR 变慢，说明仪式过重，应继续削减。

## 11. 已知边界

- 不自动合并 PR；
- 不替人确认需求；
- 不伪造测试结果；
- 不保证 L2 全量认证；
- `sdd_verify` 依赖 server 能执行目标仓库测试；
- 远端 MCP 不能直接修改开发者本地 clone；
- 历史项目知识仍需人工补录，工具只能降低补录成本。
