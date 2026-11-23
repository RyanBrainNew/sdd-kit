# 低成本推广手册

目标：让 SDD 成为仓库的默认路径，而不是要求每个人额外学习一个工具。

## 1. 推广原则

1. **只要求仓库里有 `sdd/` 和 `AGENTS.md`**，不要求统一 IDE 或插件。
2. **不改变现有 CI**，只增加一个 `sdd` job。
3. **不让工程师记命令**：Agent 读 `sdd/README.md`，运行 `python -m sdd resume`。
4. **不追求一次全量接入**：先一个仓库、一个小需求。
5. **不把流程做成审批链**：人只在需求确认和 PR 合并出现。
6. **先证明 L2 强制路径，再谈 L3/L4 增强**：覆盖与缺口以
   [标准符合性基线](docs/STANDARD-CONFORMANCE.md) 为准。

## 2. 第一周：单仓库试点

选一个满足以下条件的仓库：

- 有一个 3–5 天能完成的小需求；
- 有可运行的单元测试；
- 负责人愿意配合收集问题；
- 不是最高风险的核心交易链路。

接入：

```powershell
cd D:\repos\order-api
python D:\tools\sdd-kit\bootstrap.py --test-command "python -m pytest -q" --ci gitlab
```

`--target` 默认当前目录，`--project` 默认取目录名；不写这两个参数即可。

然后：

1. 填 `AGENTS.md` 第 4–6 节的真实项目事实；
2. 跑 `python -m sdd verify-core` 和 `python -m sdd verify-agent` 自检；
3. 用一个真实小需求走完 Spec → approve → Design → Tasks → 实现 → 验证 → PR；
4. 记录每次卡住的地方。

试点结束时只问三个问题：

- 哪些检查是误报？
- 哪些提示词让 Agent 走偏？
- 哪些步骤可以自动化掉？

同时抽取三组证据：

- `events --json` 的审计链是否有效；
- `metrics --json` 的豁免率、逃逸缺陷、重开率和 Gate 一次通过率；
- 中高风险需求是否有独立 Review，阻断 finding 是否关闭。

## 3. 第二周：模板化

根据试点结果做三件事：

- 把 `AGENTS.md` 的项目事实做成仓库模板；
- 把 `test_commands` 默认值写进模板；
- 把 `sdd check` 接进现有 CI。

不要在这个阶段加新规则。先把已有流程跑顺。

## 4. 第三至四周：多仓库接入

按风险从低到高接入：

1. 前端项目；
2. 非核心后端服务；
3. 核心服务；
4. 高风险变更走 strict 模式；
5. 存量重构使用 `l2-refactor`，不修改核心状态机。

每个仓库只需要：

- `sdd/`；
- `AGENTS.md`；
- `sdd/config.json` 的真实测试命令；
- CI 里的一个 `sdd` job。

共享 MCP 在这个阶段可以只做只读查询和上下文，不急于接管状态写入。

## 5. MCP 的接入顺序

### 阶段 1：本地模式

每个开发者本地 clone，启动：

```powershell
python -m sdd.mcp.server --root . --transport stdio
```

先让 Agent 用本地 MCP 走通 `sdd_session / sdd_submit_artifact / sdd_submit_task`。这一步不依赖服务端，也不改变代码位置。

### 阶段 2：共享只读

部署一个共享 MCP，只开放：

- `sdd_health`
- `sdd_list_projects`
- `sdd_status`
- `sdd_context`

用于统一项目目录、上下文和审计索引，不允许写状态。

### 阶段 3：共享工作区 / runner

当远程 IDE 或 issue 自动开发成熟后，再把代码放到服务端 worktree，开放：

- `sdd_check`
- `sdd_create_spec`
- `sdd_start`
- `sdd_complete`
- `sdd_verify`

每一步都观察一周，确认没有误操作再开放下一步。

## 6. 对工程师怎么说

可以直接发这段话：

```text
这个仓库已经内置 SDD 流程，不需要你装插件或注册 workflow。
你只需要像平常一样提需求，Agent 会读 AGENTS.md 和 sdd/README.md，
按 python -m sdd 返回的 next.action 推进。

你需要在两个地方看一眼：
1. Spec 写完后确认需求，运行 python -m sdd approve --human；
2. PR 合并后运行 python -m sdd merge --human。

CI 会自动检查工件和追溯关系，不通过就补，不要绕过。
```

## 7. 常见阻力与处理

| 阻力 | 处理 |
|---|---|
| “文档太多，影响开发速度” | 只保留 L2 必需工件；用模板和 Agent 自动填 |
| “每个人都要学新工具” | 不要求学工具，Agent 读仓库规则；人只记两个命令 |
| “历史项目没有上下文” | 先补 3–5 个最常改的服务卡，按需增长 |
| “CI 老红” | 先 `--stage ci` 观察，修误报后再设为 required |
| “Agent 不按流程走” | 用 `AGENTS.md` 托管块 + CLI 返回的 `next.action` + CI 三重约束 |
| “高风险变更怎么办” | 自动切 strict 模式，G2 要求人工 `--human` |

## 8. 度量

每月看一次：

- 新需求 Spec → PR 的 lead time；
- `sdd check` 一次通过率；
- 按检查 ID 的通过率、告警率和阻断率；
- 人工豁免率及其到期重校验次数；
- 逃逸缺陷数、Spec 重开率和 Gate 一次通过率；
- PR 中 AC 证据缺失比例；
- 人工介入次数；
- 因上下文缺失导致的返工次数。

指标变差时，优先删规则，不要加规则。

## 9. 不要做的事

- 不要要求所有人使用同一个 IDE 或 Agent；
- 不要把 `approve` / `merge` 自动化；
- 不要用“文档数量”衡量成功；
- 不要把 `warn` 当作 `pass`，也不要把人工豁免当成默认路径；
- 不要在第一个月就接全量微服务；
- 不要为了全自动而绕过高风险 Gate；
- 不要把 MCP 当成能直接改所有人本地仓库的魔法。
