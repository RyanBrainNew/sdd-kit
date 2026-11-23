# 全量 commit 审计与 sdd trace 规格说明书（Spec）

## 1. 元数据

| 项 | 内容 |
|---|---|
| Spec ID | SPEC-REQ-005 |
| 工作项 ID | SDD-GOV-002 |
| FEAT ID | FEAT-007 |
| 原始需求来源 | https://github.com/RyanBrainNew/sdd-kit/issues/21 |
| 作者 | SDD Agent |
| 创建日期 | 2026-11-23 |
| 状态 | Draft |
| 版本号 | 1.0.0 |
| 产品类型 | 传统产品 |
| 模板适配 | 标准 21 节模板；UI、AI 与多智能体章节标注不适用 |
| 关联人 | 产品负责人：RyanBrainNew；技术负责人：sdd-kit 平台维护者 |
| 原型版本 | 不涉及 |

## 2. 范围声明

- In-Scope：把 commit 审计从“最近 20 条”升级为分支全量审计，并提供只读追溯。
  1. `check --check-git` 从 `git merge-base` 到 HEAD 扫描分支全部 commit。
  2. 代码 commit 必须有且只有一个 `Spec-Id` 与一个 `Task-Id`；文档 commit 不得带 `Task-Id`。
  3. 引用的 Spec、Task 与工作项必须真实存在且一致。
  4. 新增只读 `sdd trace --test/--ac/--commit`，输出稳定 JSON 追溯链。
  5. 断链时输出 `missing`，不伪造完整链路。
  6. 同步 CLI、README、执行手册、Agent 契约、版本与 manifest。
- Out-of-Scope：
  1. 不新增服务端、数据库、常驻进程、第三方依赖或可视化追溯台。
  2. 不修改 `state.json` / `events.jsonl`，不执行人工动作。
  3. 不重写历史 commit，不改变 Git 分支保护或 PR 审核策略。
  4. 不实现语义 diff 或自然语言需求追溯。
  5. 不追溯未纳入 Git 的外部工作项系统内容。
  6. 不改变 Gate 通过条件和现有 phase 状态机。

## 3. 业务上下文

### 3.1 干系人与角色

| 角色 | 诉求 | 使用场景 | 责任边界 |
|---|---|---|---|
| 平台维护者 | 分支中任意位置的坏 commit 都能被发现 | 维护 CI 与提交规范 | 维护规则，不替人改历史 |
| 执行 Agent | 能从测试或 AC 反查完整交付链路 | 定位影响面、补证据 | 只读调用 trace |
| 审计人员 | 能确认 commit、审批、change-set 与证据的对应关系 | 审计交付 | 只读，不修改状态 |
| 管理员 | PR 合并前看到明确断链 | 审核 PR | 决定是否合并 |

### 3.2 业务流程

1. `check --check-git` 找到当前分支相对主干的 merge-base。
2. 引擎逐个解析 merge-base 之后的 commit，跳过 merge commit。
3. 每个 commit 校验 trailer、Spec/Task 存在性与工作项一致性；任一失败即阻断。
4. 审计人员或 Agent 用 `sdd trace` 从测试、AC 或 commit 入口反查链路。
5. 链路完整时输出结构化 JSON；断链时输出明确的 `missing` 项。

### 3.3 业务规则

- BR-001：`sdd/scripts/sdd.py` 仍是唯一状态机；trace 只读。
- BR-002：审计范围是 merge-base 到 HEAD，不使用“最近 N 条”截断。
- BR-003：merge commit 不要求 trailer；非 merge commit 必须符合提交规范。
- BR-004：代码 commit 指 `feat/fix/perf/hotfix`；文档 commit 指 `docs`。
- BR-005：commit 的 `Spec-Id` 必须指向存在的 Spec，`Task-Id` 必须指向该 Spec 的 Task。
- BR-006：commit 首行工作项必须与 Spec 元数据工作项一致。
- BR-007：trace 不写任何文件，不改变状态、事件或 Gate 报告。
- BR-008：trace 的 JSON 字段名和层级属于稳定契约。
- BR-009：历史 MERGED Spec 的既有结论不被新审计规则回写。
- BR-010：只使用 Python 标准库。

## 4. 功能需求与验收条件

### FR-001 分支全量 commit 审计

- 功能描述：从 merge-base 扫描分支全部 commit，不再只看最近 20 条。
- 用户场景：分支中间某条 commit 漏了 Task-Id，CI 仍能定位并阻断。
- 验收条件：
  - AC-001-1：Given 当前分支与主干存在 merge-base，When 执行 `check --check-git`，Then 审计范围覆盖 merge-base 之后的全部 commit。【执行路径：本地单元测试】
  - AC-001-2：Given 分支包含超过 20 条 commit 且第 10 条缺少 Task-Id，When 执行审计，Then 返回该 commit SHA 与缺失 trailer。【执行路径：本地单元测试】
  - AC-001-3：Given 范围内存在 merge commit 或找不到主干，When 执行审计，Then 跳过 merge commit；无 merge-base 时给出明确错误而不是静默通过。【执行路径：本地单元测试】

### FR-002 Commit Trailer 与引用一致性

- 功能描述：代码 commit 必须有且只有一个 `Spec-Id` 和 `Task-Id`；文档 commit 不得带 Task-Id；
  引用对象必须存在且工作项一致。
- 用户场景：审计人员能从 commit 直接定位 Spec 与 Task，避免孤儿提交。
- 验收条件：
  - AC-002-1：Given 代码 commit，When 解析 trailer，Then 必须恰好一个合法 `Spec-Id` 和一个合法 `Task-Id`，否则阻断。【执行路径：本地单元测试】
  - AC-002-2：Given 文档 commit，When 解析 trailer，Then 不得出现 `Task-Id`；出现即阻断。【执行路径：本地单元测试】
  - AC-002-3：Given `Spec-Id` 或 `Task-Id` 在仓库中不存在，或 commit 工作项与 Spec 元数据不一致，When 审计，Then 返回可定位错误。【执行路径：本地单元测试】

### FR-003 只读 trace 三入口

- 功能描述：新增 `sdd trace --test/--ac/--commit`，输出稳定 JSON 追溯链。
- 用户场景：从失败测试或 AC 快速反查 Task、Spec、审批、change-set、commit 与证据。
- 验收条件：
  - AC-003-1：Given 测试选择器，When 执行 `sdd trace --test <selector> --json`，Then 输出 test -> AC -> Task -> Spec -> FEAT -> 工作项 -> 审批 -> change-set -> commits -> evidence 链路。【执行路径：本地单元测试】
  - AC-003-2：Given AC ID，When 执行 `sdd trace --ac <AC> --json`，Then 输出同一 schema 的链路与关联测试选择器。【执行路径：本地单元测试】
  - AC-003-3：Given commit SHA，When 执行 `sdd trace --commit <sha> --json`，Then 从 commit trailer 反查 Spec/Task/AC 与证据。【执行路径：本地单元测试】
  - AC-003-4：Given 链路中任一对象不存在，When 执行 trace，Then `ok=false` 且 `missing` 列出断链位置与原因。【执行路径：本地单元测试】
  - AC-003-5：Given trace 调用，When 检查仓库，Then 不修改 state、events、change-set 或任何文件；JSON 字段保持稳定。【执行路径：本地单元测试】

### FR-004 边界、兼容与发布

- 功能描述：保持人工边界、历史兼容与发布同步。
- 用户场景：平台升级后旧仓库不被历史 commit 误伤，新分支获得全量审计。
- 验收条件：
  - AC-004-1：Given trace 与审计命令，When 检查 CLI/MCP 暴露面，Then 不新增人工动作，MCP 不暴露任何人工动作。【执行路径：本地单元测试】
  - AC-004-2：Given MERGED 历史 Spec，When 执行 `check --all --stage ci`，Then 不因历史 commit 审计被重新判失败。【执行路径：本地单元测试 + `check --all`】
  - AC-004-3：Given 修改受保护核心，When 执行全量测试、`verify-core`、`verify-agent` 与 CI，Then 版本、manifest、文档和测试全部一致通过。【执行路径：本地单元测试 + CI】

## 5. 边界与异常

| 场景类型 | 场景描述 | 关联FR/AC | 预期行为 |
|---|---|---|---|
| 边界场景 | 分支有 30 条 commit，坏 commit 在第 10 条 | FR-001；AC-001-2 | 全量扫描并定位该 commit |
| 边界场景 | commit 是 GitHub merge commit | FR-001；AC-001-3 | 跳过 trailer 校验 |
| 异常场景 | 仓库没有 main/master/origin/main | FR-001；AC-001-3 | 返回明确“无法确定 merge-base”错误 |
| 异常场景 | trace 入口在多个 Spec 中命中 | FR-003；AC-003-5 | 输出候选列表并要求更精确输入，不猜测 |
| 异常场景 | commit 引用的 Task 已删除 | FR-002；AC-002-3 | 阻断并指出 commit 与 Task |

## 6. 非功能需求

| 类型 | 要求 | 指标/验收方式 | 关联FR/AC |
|---|---|---|---|
| 性能 | 100 条 commit 内审计在 5 秒内完成 | 本地单元测试观察 | FR-001；AC-001-2 |
| 安全 | trace 只读，不执行写操作 | 文件哈希前后对比 | FR-003；AC-003-5 |
| 可用性 | 错误包含 commit SHA、Spec/Task 与缺失原因 | 负向单元测试 | FR-002；AC-002-3 |
| 兼容性 | MERGED 历史 Spec 不被重新判失败 | `check --all` 回归 | FR-004；AC-004-2 |

## 7. 外部接口

| 方法 | 路径 | 用途 | 归属AC |
|---|---|---|---|
| CLI | `sdd trace --test <selector> --json` | 从测试追溯 | AC-003-1 |
| CLI | `sdd trace --ac <AC> --json` | 从 AC 追溯 | AC-003-2 |
| CLI | `sdd trace --commit <sha> --json` | 从 commit 追溯 | AC-003-3 |

- 请求/响应示例：见 design 的 trace schema。
- 契约文件：不新增外部网络契约。

## 8. 数据模型

- 不新增持久化实体；trace 读取 Git、Spec/Tasks、state、change-set 与证据 JSONL。
- 数据流：入口选择器 -> 测试/AC/commit -> Task -> Spec -> FEAT/工作项 -> 审批 -> change-set -> commits -> evidence。

## 9. 约束与假设

- 技术约束：Python 标准库；状态机唯一入口不变。
- 业务约束：trace 只读，人工动作边界不变。
- 假设条件：主干分支名为 `main`、`master` 或可解析的 `origin/main`。

## 10. 变更历史

| 日期 | 版本 | 变更内容 | 作者 |
|---|---|---|---|
| 2026-11-23 | 1.0.0 | 初始版本 | SDD Agent |

> 本文件原地修改，以 Git 历史作为物理版本、元数据版本号作为语义版本；禁止创建平行版本文件。

## 11. AI能力规格

不适用（传统产品）。

## 12. 上下文与知识规格

不涉及。

## 13. 统计性验收标准

不涉及。

## 14. AI安全合规

不适用。

## 15. 成本与性能

不涉及。

## 16. 运行监控与效果度量

不涉及。

## 17. 自主程度与人机分工

不适用（仅 AI 原生·L4 产品填写）。

## 18. Agent行为规格

不适用（仅 AI 原生·L4 产品填写）。

## 19. 审计与回放

不适用（仅 AI 原生·L4 产品填写）。

## 20. 多智能体协同

不涉及。

## 21. 自检清单（评审辅助，不作Gate依据）

- [x] Spec ID 格式正确，并与目录名一致。
- [x] 工作项 ID 存在且不含前导 `%`。
- [x] In-Scope 和 Out-of-Scope 均已明确填写。
- [x] FR/AC 编号唯一、稳定，每个 FR 至少包含一条 AC。
- [x] 每条 AC 包含可判定的 Given/When/Then，并可映射到本地单元测试。
- [x] 边界、异常、非功能需求、接口、数据模型和约束均已填写或明确不涉及。
- [x] 残留澄清标记为 0。
- [x] 变更历史已更新，未创建平行版本文件。
