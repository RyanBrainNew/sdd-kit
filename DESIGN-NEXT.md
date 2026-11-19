# sdd-kit 下一阶段设计方案

> 状态：已确认（六项按推荐）；0.7.0 和 0.8.0 已实现  
> 日期：2026-11-18  
> 范围：0.7.0 可运维性、0.8.0 工作流预设、0.9.0 只读视图与 runner 契约  
> 结论：不引入自由 DAG，不引入服务端；在现有单状态机上补齐回退、待办、证据绑定和指标。

## 0. 一分钟版

这次只做四类能力，全部围绕“让人和 Agent 都更少猜”：

1. **可回退**：新增人工命令 `rewind`，允许回到更早阶段，保留审计，不删历史。
2. **可等待**：新增 `inbox`，汇总所有等人处理的 Spec，并给出可执行命令。
3. **可证明**：事件记录角色、会话和产物哈希；审批绑定到具体文件哈希。
4. **可配置但不失控**：工作流只允许 `sdd/workflows/` 里的命名预设，不允许用户画任意图。

不做的事：

- 不做可视化拖拽设计器。
- 不把状态机复制到 MCP、视图或 runner。
- 不做服务端数据库、Docker 平台或 token 计费。
- 不让 Agent 调用 `approve`、`merge`、`unblock`、`rewind`。

## 1. 现状与缺口

| 缺口 | 现状 | 证据 |
| --- | --- | --- |
| 没有回退边 | 只有 `BLOCKED` 回到原状态，不能回到更早阶段重做 | `sdd/scripts/sdd.py:1271` 的 `build_next_action` 只向前 |
| 人工 Gate 不完整 | 高层 `sdd complete` 没有把 `--human` 传下去 | `sdd/core.py:804` 的 `complete` 不接受 `human` 参数 |
| 没有待办聚合 | `board` 显示下一步，但不区分“等 Agent”和“等人” | `sdd/scripts/sdd.py:1605` |
| 事件缺角色与产物 | 事件已有 `actor/source`，但没有 `role/session/artifacts` | `sdd/scripts/sdd.py:236` |
| 审批不绑定产物 | `approve` 只记录一段自由文本 | `sdd/scripts/sdd.py:1785` |
| 没有指标 | CLI 没有 `metrics` 命令 | `sdd/cli.py` 的命令表 |
| 工作流写死 | 阶段与 Gate 固定在代码和 `config.json` | `sdd/scripts/sdd.py:86`、`sdd/config.json:39` |
| 独立审查不强制 | `review.md` 存在，但没有被 `next` 引用 | `sdd/prompts/review.md` |

### 1.1 现有阶段与 Gate 的真实映射

这张表是后续 `inbox`、`rewind` 和哈希绑定的基础。

| 当前状态 | Agent 产物 | Gate | 下一状态 |
| --- | --- | --- | --- |
| `DRAFT` | `spec.md` | G0 人工、G1 自动 | `SPEC_READY` |
| `SPEC_READY` | `design.md` | G2 | `DESIGN_READY` |
| `DESIGN_READY` | `tasks.md` | G3 | `TASKS_READY` |
| `TASKS_READY` | 无 | 无 | `IMPLEMENTING` |
| `IMPLEMENTING` | 每个 Task | G4 | `VERIFYING` |
| `VERIFYING` | `verification.md` | G5 | `PR_READY` |
| `PR_READY` | 无 | 人工 merge | `MERGED` |

## 2. 设计原则

继续遵守现有不变量，不新增第二套规则：

1. `sdd/scripts/sdd.py` 仍是唯一状态机。
2. `sdd/core.py` 仍通过子进程调用 `sdd.py`。
3. `sdd/mcp/` 只做适配；不新增 Gate 或阶段规则。
4. 人工动作仍强制 `--human`；MCP 不暴露人工动作。
5. 工件、状态和证据仍跟代码进 Git。
6. 所有新增能力都必须是可选的；没有新配置时，0.6.1 的流程保持不变。

## 3. 版本路线

| 版本 | 主题 | 内容 | 风险 |
| --- | --- | --- | --- |
| 0.7.0 | 可运维性 | `rewind`、`inbox`、事件 v2、产物哈希、审批身份、`metrics`、`complete --human` 修复 | 低到中 |
| 0.8.0 | 工作流预设 | `l2-standard`、`l2-hotfix`、`l2-strict`，Spec 固定预设版本（已实现） | 中 |
| 0.9.0 | 可见性 | 只读 HTML 运行视图、runner 契约 | 低 |

0.7.0 不改阶段图，只补命令和证据。0.8.0 才把阶段图参数化。

---

## 4. 0.7.0 详细设计

### 4.1 `sdd rewind`

#### 目标

让人可以把 Spec 送回更早阶段重做，同时保留“谁、何时、为什么、作废了什么”的完整记录。

#### CLI

```powershell
python -m sdd rewind --spec SPEC-ORDER-001 --to SPEC_READY `
  --reason "验证发现设计遗漏" --human --approver "张三 <zhang@example.com>"
```

参数：

| 参数 | 必填 | 说明 |
| --- | --- | --- |
| `--spec` | 是 | 目标 Spec |
| `--to` | 是 | 目标状态 |
| `--reason` | 是 | 写进事件和 `gates.md` |
| `--human` | 是 | 只允许人执行 |
| `--approver` | 否 | 默认取 `git config user.name` 和 `user.email` |
| `--force` | 否 | Spec 目录有未提交改动时仍继续 |
| `--reopen-task` | 否 | 回到 `IMPLEMENTING` 时指定要重开的 Task |
| `--reset-tasks` | 否 | 回到 `IMPLEMENTING` 时把所有 Task 重置为 `Todo` |

#### 允许的目标

只允许回到更早阶段，不允许去未来，也不允许从 `MERGED` 或 `BLOCKED` 直接回退。

| 当前状态 | 允许回到 |
| --- | --- |
| `SPEC_READY` | `DRAFT` |
| `DESIGN_READY` | `DRAFT`、`SPEC_READY` |
| `TASKS_READY` | `DRAFT`、`SPEC_READY`、`DESIGN_READY` |
| `IMPLEMENTING` | `DRAFT`、`SPEC_READY`、`DESIGN_READY`、`TASKS_READY` |
| `VERIFYING` | 以上全部，加 `IMPLEMENTING` |
| `PR_READY` | 以上全部，加 `VERIFYING` |
| `MERGED` | 不允许 |
| `BLOCKED` | 先 `unblock`，再 `rewind` |

#### 作废与归档规则

原则：**复制工件，移动 Gate 报告，追加记录，不删除历史。**

| 目标 | 归档到 `history/<时间戳>/` | 移走 Gate 报告 | 任务状态 |
| --- | --- | --- | --- |
| `DRAFT` | `spec.md`、`design.md`、`tasks.md`、`verification.md`、`PR_BODY.md` | G0–G5 | 全部重置为 `Todo` |
| `SPEC_READY` | `design.md`、`tasks.md`、`verification.md`、`PR_BODY.md` | G2–G5 | 全部重置为 `Todo` |
| `DESIGN_READY` | `tasks.md`、`verification.md`、`PR_BODY.md` | G3–G5 | 全部重置为 `Todo` |
| `TASKS_READY` | `verification.md`、`PR_BODY.md` | G4–G5 | 全部重置为 `Todo` |
| `IMPLEMENTING` | `verification.md`、`PR_BODY.md` | G4–G5 | `In Progress` 回到 `Todo`，`Done` 保留 |
| `VERIFYING` | `verification.md`、`PR_BODY.md` | G5 | 不变 |

说明：

- 工件是**复制**，原文件保留，Agent 下轮直接覆盖。
- Gate 报告是**移动**，这样 `check_gates` 会立即发现报告缺失。
- `gates.md` 追加 `SUPERSEDED` 行，不删旧行。
- 归档目录写一个 `manifest.json`，记录文件路径、SHA-256 和时间。
- `--to DESIGN_READY` 表示“保留已批准的 design，重做 tasks”，所以不作废 G2。
  要重写 design，应回退到 `SPEC_READY`。

#### 状态与事件

`state.json` 新增：

```json
{
  "reworks": [
    {
      "from": "VERIFYING",
      "to": "SPEC_READY",
      "reason": "验证发现设计遗漏",
      "at": "2026-11-18T15:00:00+08:00",
      "approver": "张三 <zhang@example.com>",
      "archived": [
        "docs/specs/SPEC-ORDER-001/history/20261118-150000/design.md"
      ],
      "invalidated_gates": ["G2", "G3", "G4", "G5"],
      "tasks_reset": true
    }
  ]
}
```

`events.jsonl` 追加一条 `rewind` 事件：

```json
{
  "schema": 2,
  "seq": 12,
  "at": "2026-11-18T15:00:00+08:00",
  "event": "rewind",
  "from_state": "VERIFYING",
  "to_state": "SPEC_READY",
  "evidence": "验证发现设计遗漏",
  "actor": "human",
  "approver": "张三 <zhang@example.com>",
  "reason": "验证发现设计遗漏",
  "rewind": {
    "archived": ["..."],
    "invalidated_gates": ["G2", "G3", "G4", "G5"],
    "tasks_reset": true
  }
}
```

#### 错误处理

| 情况 | 返回 |
| --- | --- |
| 目标是未来状态 | `rewind 只能回到更早阶段` |
| 目标是 `MERGED` | `MERGED 不能 rewind` |
| 当前是 `BLOCKED` | `先 unblock，再 rewind` |
| 缺少 `--human` | `rewind 需要 --human` |
| 缺少 `--reason` | `rewind 需要记录原因` |
| Spec 目录有未提交改动 | 列出文件；加 `--force` 才继续 |

#### 幂等性

同一目标重复执行时，第二次应报“已经在目标状态或更早”，不重复归档。

#### 回到 `IMPLEMENTING` 的任务处理

如果所有 Task 都是 `Done`，回到 `IMPLEMENTING` 后 `next` 会直接给 `finish_implementation`，Agent 没有可执行的 Task。

默认规则：

- 保留所有 `Done`；
- 把最后一个 `Done` Task 改回 `Todo`，作为返工入口；
- 需要指定别的 Task 时，加 `--reopen-task T-xxx`；
- 需要全部重做时，加 `--reset-tasks`。

这样不会默认抹掉已完成的证据，也不会让 Agent 卡在“没有待办 Task”。

### 4.2 `sdd inbox`

#### 目标

把所有“现在需要人做点什么”的 Spec 汇总成一个只读列表。Agent 不消费这个命令；它是给人的入口。

#### CLI

```powershell
python -m sdd inbox --json
python -m sdd inbox --stale-days 7
```

#### 输出

```json
{
  "ok": true,
  "kind": "inbox",
  "items": [
    {
      "spec": "SPEC-ORDER-001",
      "state": "DRAFT",
      "priority": 20,
      "action": "approve_spec",
      "reason": "G0 等待人工确认需求",
      "since": "2026-11-18T10:00:00+08:00",
      "artifact": "docs/specs/SPEC-ORDER-001/spec.md",
      "command": "python -m sdd approve --spec SPEC-ORDER-001 --human --evidence \"需求已确认\""
    }
  ]
}
```

#### 归类规则

| 条件 | `action` | 命令 |
| --- | --- | --- |
| `state=DRAFT` | `approve_spec` | `sdd approve --human` |
| `state=PR_READY` | `merge_pr` | `sdd merge --human` |
| `state=BLOCKED` | `unblock` | `sdd unblock --human` |
| 当前阶段的产物已通过校验，但退出 Gate 要求人工 | `manual_gate` | `sdd complete --human` |
| `IMPLEMENTING` 且所有 Task 为 `Done`、G4 要求人工 | `manual_gate` | `sdd complete --human` |
| 超过 `--stale-days` 没有事件 | `stale` | 无命令，只提示 |

`manual_gate` 的判断必须复用 `sdd.py` 的 Gate 规则，不在 `inbox` 里复制一份。做法是抽出一个纯函数：

```python
def gate_requires_human(config, gate, state) -> bool:
    ...
```

`gate_mode()` 内部也调用它。这样只有一处判断。

#### 排序

1. `BLOCKED`
2. `PR_READY`
3. `DRAFT`
4. `manual_gate`
5. `stale`

同优先级按 `since` 从旧到新。

`priority` 字段固定为：`BLOCKED=0`、`PR_READY=10`、`DRAFT=20`、`manual_gate=30`、`stale=40`。

#### 边界

- `inbox` 只读，不写 `state.json`、不写 `events.jsonl`。
- `inbox` 不执行命令，只打印命令。
- MCP 可以暴露 `sdd_inbox`，因为它只读。
- `inbox` 只跑 `check`，不跑 `sdd verify` 的 `test_commands`；因此不会执行测试。

### 4.3 人工 Gate 的等待语义

现在 Agent 提交 `tasks.md` 后，如果 G3 要求人工，`complete` 会直接报错，Spec 留在 `DESIGN_READY`。Agent 重试也会失败，但它不知道应该停下。

调整 `core.submit_artifact`：

1. 写入产物并跑 `check`。
2. 检查当前转换的 Gate 是否需要人工。
3. 如果需要人工，返回 `ok=true`、`awaiting_human_approval=true` 和 `human_checkpoint`。
4. 不推进状态；等人运行 `complete --human`。

转换 Gate 映射：

| 产物 | Gate |
| --- | --- |
| `spec.md` | G0 |
| `design.md` | G2 |
| `tasks.md` | G3 |
| `verification.md` | G5 |
| 最后一个 Task | G4 |

这样 Agent 的契约仍然简单：看到 `awaiting_human_approval=true` 就停。

#### 最后一个 Task 的 G4 顺序

现在 `command_complete --task` 先标记 Task Done，再检查 G4。如果 G4 要求人工，它会抛错，但 `save_state` 还没执行。结果是 `tasks.md` 已经变成 Done，`state.json` 却没有记录，重试还会报“任务已经是 Done”。

修正顺序：

1. 标记 Task Done，写 `verification.md` 证据。
2. 先 `save_state`，记录 `task_done`。
3. 如果这是最后一个 Task 且 G4 要求人工，返回 `awaiting_human_approval`，不推进到 `VERIFYING`。
4. 人运行 `sdd complete --human`，这时才记录 G4 并推进。

`submit_task` 也要把第 3 步转成结构化返回值，而不是当成失败。

#### `approve` 对 G1 的策略

`l2-strict` 会把 G1 设为人工。当前 `command_approve` 无条件把 G1 记成 `auto`，需要改成调用 `gate_mode(config, "G1", state, args.human)`。

这样 G1 的策略只有一处来源。

### 4.4 事件 schema v2

#### 新增字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `role` | string | `planner`、`designer`、`implementer`、`reviewer`、`verifier` |
| `session` | string | 会话哈希，不存原始主机线程 ID |
| `session_source` | string | `SDD_SESSION_KEY`、`CODEX_THREAD_ID` 等 |
| `executor` | string | `codex`、`claude`、`dsh`、`cursor`、`other` |
| `model` | string | 可选，来自 `SDD_MODEL` |
| `artifacts` | array | `{path, sha256, bytes}` |
| `approver` | string | 人工动作的确认人 |
| `workflow` | object | `{name, version, digest}`，0.8.0 起 |
| `rewind` | object | 回退详情 |
| `usage` | object | 可选，`{input_tokens, output_tokens}` |

#### 兼容

- 新事件写 `schema: 2`；旧事件保持 `schema: 1`，不回写。
- 读取方忽略未知字段。
- `sdd events` 默认输出旧格式；加 `--verbose` 才显示新字段。

#### 单一事件日志

继续只用一个 `events.jsonl`，但增加非状态迁移事件，例如 `check_failed`。

实现方式：

- 每条由 history 派生的事件增加 `history_index`。
- `append_event_log` 只追加尚未出现的 `history_index`。
- `check_failed` 事件立即追加，`history_index` 为 `null`。
- 旧日志没有 `history_index` 时，按原有顺序补号，保持兼容。

`check_failed` 事件用于计算 Gate 一次通过率和真实返工次数：

```json
{
  "schema": 2,
  "event": "check_failed",
  "at": "...",
  "stage": "tasks",
  "errors": ["AC-001-2 没有 Task 覆盖"],
  "actor": "agent",
  "role": "planner"
}
```

#### 元数据来源

优先级：命令行参数 > 环境变量 > 命令默认值。

| 变量 | 用途 |
| --- | --- |
| `SDD_SESSION_KEY` | 会话标识；`Workspace` 已支持 |
| `SDD_EXECUTOR` | 执行器 |
| `SDD_MODEL` | 模型名 |
| `SDD_ROLE` | 角色 |
| `SDD_ACTOR` | `agent` 或 `human` |

`Workspace._run` 负责把这些值传给子进程。直接运行 `sdd.py` 时，`sdd.py` 自己读环境变量。

### 4.5 产物哈希与审批绑定

#### 要解决的问题

现在 `approve` 只记录一段文本。Spec 在批准后被修改，CI 不会发现。G2/G3/G5 也一样。

#### 设计

每次记录 Gate 时，把绑定产物的哈希写进 `state.json` 和 Gate 报告。

| Gate | 绑定产物 |
| --- | --- |
| G0、G1 | `spec.md` |
| G2 | `design.md` |
| G3 | `tasks.md` 的任务计划字段 |
| G4 | `tasks.md` 的任务计划字段，加上每个 Task 的 commit SHA |
| G5 | `verification.md`；`PR_BODY.md` 的哈希记录在 merge 审批中 |

任务计划哈希只覆盖 `id/description/acs/frs/depends/parallel/acceptance/test/command`，
排除 `status`、`commit`、`done`。这样 Agent 推进 Task 时不会把 G3/G4 报告误判为篡改。

Gate 报告新增一节：

```markdown
## 4. 产物

| 产物 | SHA-256 | 字节 |
| --- | --- | --- |
| docs/specs/SPEC-ORDER-001/spec.md | 3f2a... | 18234 |
```

`check_gates` 读取这一节，重新计算文件哈希。不一致时返回：

```text
G0 批准的 spec.md 已被修改；请重新 approve 或 rewind
```

0.7.0 只强制文件哈希。G4 的 commit SHA 会记录，但暂不做 Git 祖先校验；等出现“评审后代码被替换”的真实案例，再把提交图校验加上。

#### 审批记录

```json
{
  "approvals": [
    {
      "action": "approve_spec",
      "approver": "张三 <zhang@example.com>",
      "at": "2026-11-18T10:00:00+08:00",
      "artifact": "docs/specs/SPEC-ORDER-001/spec.md",
      "sha256": "3f2a..."
    }
  ]
}
```

`merge` 同样记录 `PR_BODY.md` 哈希和 `head_sha`。

#### 兼容策略

| 阶段 | 旧 Gate 报告没有哈希 | 新 Gate 报告 |
| --- | --- | --- |
| 0.7.0 | 告警，不阻断 | 必须校验 |
| 0.8.0 | 由 `require_artifact_hash` 决定；新仓库默认 `true` | 必须校验 |

这样升级不会让历史 Spec 立刻失败。

### 4.6 审批身份

#### 设计

- `approve`、`merge`、`unblock`、`rewind` 都支持 `--approver`。
- 默认值取 `git config user.name` 和 `git config user.email`。
- 两者都为空时写 `unknown`；`require_approver=true` 时 CI 判失败。
- 记录到 `state["approvals"]`、Gate 报告和事件。
- `sdd/config.json` 新增 `require_approver: true`。
- `require_approver=true` 时，CI 要求最新审批记录有非空 `approver`。

#### 诚实边界

本地 CLI 无法证明“敲命令的人是谁”。`--approver` 只建立责任记录，不提供认证。

真正的硬控制仍然是：

- 分支保护；
- CODEOWNERS；
- PR review；
- CI 只信任受保护分支上的结果。

方案不声称 `--human` 等于身份认证。

### 4.7 `sdd metrics`

#### CLI

```powershell
python -m sdd metrics --json
python -m sdd metrics --since 2026-11-01 --json
```

#### 指标

| 指标 | 来源 |
| --- | --- |
| lead time | 首个事件到 `MERGED` |
| 阶段耗时 | 相邻状态事件的时间差 |
| 返工次数 | `rewind` 事件数 |
| 人工介入次数 | `approve`、`merge`、`unblock`、`rewind`、`manual_gate` |
| Gate 一次通过率 | `check_failed` 与对应 Gate |
| Task 周期 | `task_start` 到 `task_done` |
| AC 覆盖率 | `verification.md` 与 `spec.md` |
| 产物变更次数 | 同一路径的哈希变化次数 |

#### 输出

```json
{
  "ok": true,
  "kind": "metrics",
  "since": "2026-11-01",
  "specs": [
    {
      "spec": "SPEC-ORDER-001",
      "lead_time_hours": 31.5,
      "stage_hours": {"DRAFT": 2.0, "SPEC_READY": 4.5},
      "reworks": 1,
      "human_interventions": 3,
      "gate_failures": 2
    }
  ],
  "aggregate": {
    "specs": 12,
    "median_lead_time_hours": 28.0,
    "median_reworks": 0.0
  }
}
```

#### 不做成本

CLI 看不到可靠的 token 用量。0.7.0 不做成本统计。

如果调用方愿意传，`usage` 字段可以记录；没有就不显示。

### 4.8 修复 `complete --human`

这是一个现有缺口，不是新功能：

- `sdd/core.py:804` 的 `Workspace.complete` 不接受 `human`。
- `sdd/cli.py` 的 `complete` 解析了 `--human`，但没有传给 core。
- 结果是 G2/G3/G5 设成 `human` 时，高层 CLI 无法完成转换。

修复：

1. `Workspace.complete(..., human=False)` 增加参数。
2. 为真时给 `sdd.py complete` 加 `--human`。
3. CLI 把 `a.human` 传进去。
4. 测试覆盖 G2/G3/G5 三种人工 Gate。

---

## 5. 0.8.0 工作流预设

### 5.1 约束

只允许**命名预设**，不允许用户画任意 DAG。

每个预设只能做三件事：

1. 从固定的阶段序列里选一个**子序列**。
2. 声明每个阶段需要哪个产物。
3. 声明每个 Gate 的默认策略。

阶段之间的边仍然只有“按顺序向前”和 `BLOCKED`。这样 CI 仍然能预知每个 Spec 该有哪些工件。

### 5.2 目录

```text
sdd/workflows/
  l2-standard.json
  l2-hotfix.json
  l2-strict.json
```

`sdd/workflows/` 加入 `PROTECTED_DIRS`，跟其他核心文件一起进 manifest。

### 5.3 预设结构

```json
{
  "schema": 1,
  "name": "l2-standard",
  "version": 1,
  "description": "公司 L2 默认路径",
  "stages": [
    "DRAFT",
    "SPEC_READY",
    "DESIGN_READY",
    "TASKS_READY",
    "IMPLEMENTING",
    "VERIFYING",
    "PR_READY",
    "MERGED"
  ],
  "artifacts": {
    "DRAFT": "spec.md",
    "SPEC_READY": "design.md",
    "DESIGN_READY": "tasks.md",
    "IMPLEMENTING": "tasks.md",
    "VERIFYING": "verification.md",
    "PR_READY": "PR_BODY.md"
  },
  "gates": {
    "G0": "human",
    "G1": "auto",
    "G2": "auto_if_no_risk",
    "G3": "auto",
    "G4": "auto",
    "G5": "auto"
  },
  "required_gates": {
    "SPEC_READY": ["G0", "G1"],
    "DESIGN_READY": ["G0", "G1", "G2"],
    "TASKS_READY": ["G0", "G1", "G2", "G3"],
    "IMPLEMENTING": ["G0", "G1", "G2", "G3"],
    "VERIFYING": ["G0", "G1", "G2", "G3", "G4"],
    "PR_READY": ["G0", "G1", "G2", "G3", "G4", "G5"],
    "MERGED": ["G0", "G1", "G2", "G3", "G4", "G5"]
  },
  "allow_rewind_to": [
    "DRAFT",
    "SPEC_READY",
    "DESIGN_READY",
    "TASKS_READY",
    "IMPLEMENTING",
    "VERIFYING"
  ],
  "review_required": false
}
```

### 5.4 三个预设

#### `l2-standard`

与 0.7.0 完全一致，作为默认。

#### `l2-hotfix`

推荐先做“同阶段、轻设计”，不直接砍掉 `design.md`：

| 项 | 取值 |
| --- | --- |
| 阶段 | 与 standard 相同 |
| 设计产物 | `design.md`，由 `design-lite.md` 模板生成，只含根因、修复策略、影响范围、回滚 |
| G2 | `auto` |
| 风险限制 | 只允许 `risk=low` 或 `risk=medium`，且不命中 `risk_stop` |

如果公司 L2 明确允许紧急修复跳过设计，再把 `DESIGN_READY` 从 `stages` 移除，把修复方案并进 `spec.md` 的 `## 修复方案`。这个开关需要你确认，默认不打开。

文件名仍是 `design.md`，这样 `submit` 的 artifact 列表、MCP 工具和现有调用方都不用变；只改渲染模板和 `check_design` 的校验深度。

`new` / `start-work` 在创建 Spec 前校验风险：`risk=high` 或命中 `risk_stop` 时拒绝 `l2-hotfix`，提示改用 `l2-standard` 或 `l2-strict`。

#### `l2-strict`

用于安全、数据迁移、破坏性变更、公共 API 破坏。

| 项 | 取值 |
| --- | --- |
| 阶段 | 与 standard 相同 |
| G0–G5 | 全部 `human` |
| `review_required` | `true` |
| 审查证据 | `verification.md` 必须有 `## 独立审查` |

`## 独立审查` 至少包含：

- Reviewer；
- Session；
- Model；
- Findings；
- Blocking issues: none。

CI 比较 implementer 与 reviewer 的 session。相同则失败。

同样要说明：session 可伪造。这是审计，不是认证。

### 5.5 Spec 固定预设

创建 Spec 时写入：

```json
{
  "workflow": {
    "name": "l2-standard",
    "version": 1,
    "digest": "sha256:..."
  }
}
```

规则：

1. `sdd new` / `start-work` 支持 `--workflow`。
2. 没有传时用 `sdd/config.json` 的 `workflow`，默认 `l2-standard`。
3. 旧 Spec 没有 `workflow` 字段时，按 `l2-standard@1` 处理。
4. 修改预设文件不自动影响旧 Spec。
5. 预设内容变化必须升 `version`；不升版本会被 digest 校验发现。

### 5.6 升级预设

新增人工命令：

```powershell
python -m sdd upgrade-workflow --spec SPEC-ORDER-001 `
  --to l2-standard@2 --reason "统一到新门禁" --human
```

规则：

- 只允许人执行。
- 只允许升到更高 `version`；跨预设必须写明 `reason`。
- 升级后重新校验现有 Gate；缺失的 Gate 进入 `inbox`。
- 旧版本记录保留在 `state["workflow_history"]`。

0.8.0 可以先不实现这个命令，只保证旧 Spec 继续可校验；命令作为后续补充。

### 5.7 配置优先级

```text
命令行参数 > sdd/config.json.gate_overrides
> 旧版 sdd/config.json.gates（仅当整份已偏离标准默认）> 预设 gates > 代码默认值
```

`gate_overrides` 用于项目级覆盖；旧的 `gates` 如果仍是标准默认，就视为未定制，
让预设生效；只有整份 `gates` 被改过才作为显式覆盖。这样现有业务仓库不需要改配置，
也不会把 `l2-strict` 悄悄降级。

### 5.8 实现补充（0.8.0）

实现时补了两个设计细节：

1. Spec 创建时把完整预设复制到 `docs/specs/<Spec>/workflow.json`，而不是只记
   `name/version/digest`。这样仓库预设升级后，旧 Spec 仍按创建时的规则校验。
2. 预设 `gates` 是工作流差异的主来源；项目级覆盖使用
   `sdd/config.json.gate_overrides`。旧的 `gates` 只在没有预设命中时兜底，
   避免 `l2-strict` 被历史通用配置悄悄降级。

`upgrade-workflow` 按设计暂缓到后续版本；当前换预设需要新建 Spec。

---

## 6. 0.9.0 只读视图与 runner

### 6.1 `sdd view`

```powershell
python -m sdd view --spec SPEC-ORDER-001 --out .sdd/runtime/view/SPEC-ORDER-001.html
```

内容：

- 头部：Spec、状态、工作流、风险、PR；
- 时间线：`events.jsonl`；
- Gate 表：状态、模式、证据、产物哈希；
- Task 表：状态、AC、commit；
- 工件列表：链接到文件。

约束：

- 只读，不写 `state.json`；
- 单文件 HTML，不依赖外部 CSS/JS；
- 不复制状态规则，只调用 `sdd status/events/board --json`；
- 不做拖拽、不做编辑、不做运行。

### 6.2 runner 契约

新增 `deploy/runner/CONTRACT.md`，描述外部 runner 如何接入：

1. 准备仓库和隔离环境；
2. 调 `sdd start-work`；
3. 读 `next`；
4. 运行 Agent；
5. 调 `submit` / `submit-task`；
6. 遇到 `human_checkpoint` 停止并通知人；
7. 收集日志、退出码和产物哈希。

runner 不允许调用 `approve`、`merge`、`unblock`、`rewind`。

Docker 沙箱属于 runner，不属于 `sdd-kit` 核心。

---

## 7. 文件与接口影响

| 文件 | 0.7.0 | 0.8.0 |
| --- | --- | --- |
| `sdd/scripts/sdd.py` | 新增 `rewind`、`inbox`、`metrics`、事件 v2、哈希 | 读取预设，按预设推进 |
| `sdd/core.py` | 包装新命令，修 `complete --human` | 透传 `workflow` |
| `sdd/cli.py` | 新增三个命令 | 新增 `--workflow`、`upgrade-workflow` |
| `sdd/mcp/server.py` | 新增只读 `sdd_inbox` | 无人工动作 |
| `sdd/mcp/service.py` | 适配 `inbox` | 适配 `workflow` 字段 |
| `sdd/templates/verification.md` | 无 | 增加 `## 独立审查` |
| `sdd/templates/design-lite.md` | 无 | 新增 |
| `sdd/prompts/review.md` | 无 | 接入 strict 校验 |
| `sdd/agent-block.md` | 说明 `inbox`、`rewind` 是人工动作 | 说明 `--workflow` |
| `sdd/agent-contract.md` | 同步新命令和边界 | 同步预设规则 |
| `README.md`、`ARCHITECTURE.md` | 同步 | 同步 |
| `bootstrap.py` | 写入新配置默认值 | 复制 `sdd/workflows/` |
| `deploy/runner/CONTRACT.md` | 无 | 0.9.0 新增 |
| `sdd/manifest.json`、`sdd/VERSION` | 升到 0.7.0 | 升到 0.8.0 |

版本号同时改 `sdd/__init__.py` 和 `sdd/scripts/sdd.py` 的 `VERSION`。`Workspace.AUTOPILOT_CONTRACT["human_only"]` 要加入 `rewind` 和 `upgrade_workflow`。

`sdd/config.json` 新增：

```json
{
  "workflow": "l2-standard",
  "require_approver": true,
  "require_artifact_hash": true
}
```

旧仓库没有这三个键时使用默认值，不报错。

默认值策略：

- `require_approver` 代码默认 `false`，保证旧仓库升级不失败；
- `bootstrap.py` 新建仓库时写入 `true`；
- `require_artifact_hash` 代码默认 `false`，新仓库写入 `true`；
- `workflow` 代码默认 `l2-standard`。

---

## 8. 测试计划

### 8.1 单元测试

`rewind`：

- 每个合法源状态回到每个合法目标；
- 未来状态、`MERGED`、`BLOCKED` 被拒绝；
- 无 `--human` 被拒绝；
- Gate 报告被移动，`gates.md` 追加 `SUPERSEDED`；
- 工件被复制，任务状态按规则重置；
- 事件包含 `rewind`、`approver`、`reason`。

`inbox`：

- DRAFT、PR_READY、BLOCKED 分类正确；
- G2/G3/G5 人工 Gate 能出现；
- 只读，不修改文件；
- 排序稳定。

事件：

- 新事件是 `schema: 2`；
- 旧 `events.jsonl` 仍可读；
- `check_failed` 不破坏 history 追加；
- 产物哈希正确。

哈希与审批：

- 批准后修改 `spec.md`，CI 失败；
- 重新 `approve` 后通过；
- 旧报告没有哈希时只告警；
- `require_approver=true` 时缺 approver 失败。

预设：

- `l2-standard` 行为与 0.7.0 一致；
- `l2-hotfix` 的 G2 是 `auto`，高风险被拒绝；
- `l2-strict` 要求独立审查；
- 旧 Spec 回退到 `l2-standard@1`；
- `check --all` 按每个 Spec 的固定预设校验。

### 8.2 集成测试

- 现有完整 CLI 流程仍到 `PR_READY`；
- `bootstrap.py` 能复制新目录；
- `sync-agent` 更新托管块；
- `verify-core` 通过；
- MCP 工具列表不出现 `approve`、`merge`、`unblock`、`rewind`；
- `sdd_inbox` 只读。

### 8.3 回归命令

```powershell
$env:PYTHONIOENCODING='utf-8'
python -m unittest discover -s tests -v
python -m sdd verify-core
python -m sdd verify-agent
python -m sdd check --all --stage ci --check-git
```

---

## 9. 风险与边界

| 风险 | 影响 | 缓解 |
| --- | --- | --- |
| `rewind` 被滥用 | 流程反复，交付变慢 | 只允许人执行；`metrics` 统计返工 |
| 哈希绑定误报 | 批准后格式化导致 CI 失败 | 明确错误提示；重新走 Gate 或 `rewind` |
| 预设碎片化 | 每个仓库证据形状不同 | 只允许核心预设；版本固定；CI 校验 |
| 事件字段膨胀 | 读取方兼容问题 | 只增不改；`schema` 版本化 |
| 审批身份被伪造 | 责任记录失真 | 明确边界；硬控制放在分支保护与 CODEOWNERS |
| 人工 Gate 等待语义变化 | Agent 可能提前停 | 契约统一为 `awaiting_human_approval` |
| 同一秒多次 rewind | 归档目录冲突 | 时间戳加短序号或随机后缀 |

不做的事再列一次：

- 不自动合并；
- 不让 Agent 代替人确认需求；
- 不伪造测试结果；
- 不做自由 DAG；
- 不做服务端数据库；
- 不做 token 计费。

---

## 10. 待确认决策

请逐条确认。推荐项是默认值；回复“按推荐”即可。

| ID | 决策 | 推荐 | 备选 | 影响 |
| --- | --- | --- | --- | --- |
| D1 | `rewind` 是否只允许人执行 | 是，强制 `--human` | 允许 Agent 提议 | 审计强度 |
| D2 | `rewind` 目标范围 | 到 `VERIFYING`，不含 `MERGED` | 只允许回到 `TASKS_READY` | 返工灵活性 |
| D3 | 回退时是否归档并重置 | 复制工件、移动 Gate 报告、重置任务 | 只改状态 | 可追溯性 |
| D4 | 是否记录 `check_failed` | 是，单一 `events.jsonl` | 只记成功事件 | 指标完整性 |
| D5 | 产物哈希绑定强度 | 0.7 新报告强制，旧报告告警 | 立即全量强制 | 升级摩擦 |
| D6 | 是否要求 `approver` | 记录；新仓库默认 `true` | 永远可选 | 责任记录 |
| D7 | 是否允许阶段子集预设 | 允许，但只在核心预设中 | 只允许改 Gate 策略 | 工作流弹性 |
| D8 | `l2-hotfix` 是否跳过 `design.md` | 先不跳过，用 `design-lite` | 跳过并并入 Spec | 公司 L2 合规 |
| D9 | 配置与预设优先级 | 配置覆盖预设 | 预设覆盖配置 | 项目自治 |
| D10 | 是否把预设固定进 Spec | 是，`name/version/digest` | 只读当前配置 | 可重复性 |
| D11 | `metrics` 是否含成本 | 不含 | 记录可选 usage | 数据可信度 |
| D12 | 是否做只读 HTML 视图 | 0.9 做 | 不做 | 展示效果 |
| D13 | MCP 暴露范围 | 只加 `sdd_inbox` | 也暴露 `metrics` | 边界清晰 |
| D14 | 版本节奏 | 0.7 → 0.8 → 0.9 | 合并成一个大版本 | 交付风险 |
| D15 | 是否修 `complete --human` | 是，0.7 必修 | 单独热修 | 现有缺口 |
| D16 | strict 是否要求不同 session 审查 | 是，CI 比较 | 只要求文字声明 | 独立性 |

### 10.1 如果你只想先确认六个

1. **D1**：`rewind` 只允许人执行。
2. **D3**：回退要归档、移动 Gate 报告、重置任务。
3. **D5**：产物哈希先对新报告强制，旧报告告警。
4. **D8**：`l2-hotfix` 先不跳过 `design.md`。
5. **D10**：预设固定进 Spec，旧 Spec 回退到 `l2-standard@1`。
6. **D13**：MCP 只加只读 `sdd_inbox`。

这六项确定后，0.7.0 的实现边界就清楚了；其余可以在 0.8.0 前再定。

---

## 11. 建议实施顺序

### 第一步：0.7.0-a，证据基础

1. 修 `complete --human`。
2. 事件 schema v2 与 `check_failed`。
3. 产物哈希与 Gate 报告校验。
4. 审批身份记录。

这一组先做，因为后面的 `rewind`、`inbox`、`metrics` 都依赖它。

### 第二步：0.7.0-b，人工操作面

1. `sdd inbox`。
2. `sdd rewind`。
3. `sdd metrics`。
4. README、agent-contract、agent-block、prompts 同步。

### 第三步：0.8.0，预设

1. `sdd/workflows/` 与加载器。
2. Spec 固定预设。
3. `l2-hotfix`、`l2-strict`。
4. 独立审查校验。
5. 试点一个业务仓库。

### 第四步：0.9.0，展示与 runner

1. `sdd view --html`。
2. `deploy/runner/CONTRACT.md`。
3. 评估是否用 LoopForge 作为 runner 实现。

---

## 12. 验收标准

0.7.0 完成时，应满足：

- 现有完整流程测试全部通过；
- 能从 `VERIFYING` 回退到 `DESIGN_READY`，并重新走到 `PR_READY`；
- `inbox` 能列出 DRAFT、PR_READY、BLOCKED 和人工 Gate；
- 批准后修改 `spec.md`，CI 能拦住；
- `metrics` 能输出 lead time、返工和人工介入；
- MCP 没有新增人工动作；
- `verify-core`、`verify-agent` 通过；
- 版本与 manifest 一致。

0.8.0 完成时，应满足：

- 旧 Spec 不需要迁移即可继续校验；
- 新 Spec 固定 `workflow`；
- `l2-hotfix` 不能用于高风险；
- `l2-strict` 缺独立审查时 CI 失败；
- `check --all` 按 Spec 的预设校验。
