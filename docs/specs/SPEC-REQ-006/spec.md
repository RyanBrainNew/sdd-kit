# 外部 runner 接入契约定稿（Spec）

## 1. 元数据

| 项 | 内容 |
|---|---|
| Spec ID | SPEC-REQ-006 |
| 工作项 ID | SDD-RUNNER-001 |
| FEAT ID | FEAT-008 |
| 原始需求来源 | https://github.com/RyanBrainNew/sdd-kit/issues/2 |
| 作者 | SDD Agent |
| 创建日期 | 2026-11-24 |
| 状态 | Draft |
| 版本号 | 1.0.0 |
| 产品类型 | 传统产品 |
| 模板适配 | 标准 21 节模板；UI、AI 与多智能体章节标注不适用 |
| 关联人 | 产品负责人：RyanBrainNew；技术负责人：sdd-kit 平台维护者 |
| 原型版本 | 不涉及 |

## 2. 范围声明

- In-Scope：为外部 runner 定义一份可执行、可校验的接入契约。
  1. 新增 `deploy/runner/CONTRACT.md`，覆盖环境准备、`start-work`、读取 `next`、
     运行 Agent、`submit` / `submit-task`、人工检查点、证据收集七个阶段。
  2. 契约列出成功、`ok=false`、`decision_required`、`awaiting_human_approval`
     四类返回的处理方式与退出语义。
  3. 契约明确 runner 不得调用 `approve`、`reapprove`、`merge`、`unblock`、
     `rewind`、`waive`，遇人工检查点必须停止并通知人。
  4. 契约明确 Docker、沙箱、日志落盘和资源隔离属于 runner 责任，不属于核心。
  5. 契约提供最小伪代码或命令序列示例，只使用 `sdd resume` / `sdd submit` 等公开命令。
  6. `README.md` 或 `sdd/README.md` 提供入口链接。
  7. 新增文档一致性测试，校验契约必需章节、人工动作边界和示例命令存在。
- Out-of-Scope：不在本需求内交付运行器实现。
  1. 不实现具体 Docker runner、守护进程或任务编排服务。
  2. 不接入任何 CI 厂商或外部工作项 API。
  3. 不修改 `sdd/scripts/sdd.py` 的状态机规则，不新增 MCP 写工具。
  4. 不复制 Gate 规则；契约只引用 CLI 输出与 `sdd/agent-contract.md`。
  5. 不定义新的 JSON schema 或修改现有 `next` 结构。

## 3. 业务上下文

### 3.1 干系人与角色

| 角色 | 诉求 | 使用场景 | 责任边界 |
|---|---|---|---|
| Runner 开发者 | 知道按什么顺序调用 SDD、如何判断停止 | 接入新 harness 或 CI | 实现容器、重试和日志；不代替人审批 |
| Agent 执行器 | 稳定读取 `next` 并提交产物 | 自动循环推进 Spec | 只调用 Agent 允许的命令 |
| 平台维护者 | 契约与真实 CLI 行为一致 | 升级 CLI 后回归契约 | 维护测试与文档，不实现具体 runner |
| 业务负责人 | 人工检查点不会被 runner 绕过 | 审批 Spec、确认交付 | 执行人工命令并承担决策 |

### 3.2 业务流程

1. Runner 准备隔离工作区并检出目标分支。
2. Runner 调用 `sdd start-work` 或 `sdd resume --json`，读取 `next`。
3. Runner 把 `next`、`context_bundle` 和提示词交给 Agent。
4. Agent 产出 `next.artifact` 后用 `next.submit_with` 提交；Runner 只转发结果。
5. 返回 `ok=false` 时 Runner 把 `errors` 交回 Agent 修复并重试。
6. 返回 `decision_required` 或 `human_checkpoint.required=true` 时 Runner 停止，
   通知人执行对应命令。
7. Runner 收集命令日志、退出码、产物哈希和 `sdd events --json` 作为运行证据。

### 3.3 业务规则

- BR-001：`sdd/scripts/sdd.py` 仍是唯一状态机；契约文档不得定义第二套阶段规则。
- BR-002：Runner 不得调用人工动作，也不得伪造 `--human`。
- BR-003：`ok=false` 不是可忽略的警告，必须交回 Agent 修复后重试。
- BR-004：人工检查点必须停机等待，不得轮询代替人执行命令。
- BR-005：容器、网络、密钥、资源限制和日志归档由 Runner 负责。
- BR-006：契约示例只使用公开 CLI，不依赖内部模块或私有 API。
- BR-007：文档一致性测试必须能在无网络、无容器环境下运行。

## 4. 功能需求与验收条件

### FR-001 契约文档结构与生命周期

- 功能描述：`deploy/runner/CONTRACT.md` 按固定章节描述 runner 的完整生命周期，
  足以让新 harness 在不读源码的情况下接入。
- 用户场景：新团队要把 SDD 接入自研 runner，需要一份权威步骤说明。
- 验收条件：
  - AC-001-1：Given 仓库包含 `deploy/runner/CONTRACT.md`，When 检查章节，Then 文档包含环境准备、启动工作项、读取 `next`、运行 Agent、提交产物、人工检查点、证据收集七个阶段。【执行路径：本地单元测试】
  - AC-001-2：Given 读者阅读契约，When 查看命令说明，Then 每个阶段标注对应命令、输入、期望输出和失败处理，并引用 `next.submit_with` 而不是自造调用顺序。【执行路径：本地单元测试 + 人工评审】
  - AC-001-3：Given 契约包含示例，When 复制示例命令执行，Then 只使用 `sdd start-work`、`sdd resume`、`sdd submit`、`sdd submit-task`、`sdd complete` 等公开 CLI。【执行路径：本地单元测试】

### FR-002 失败语义与人工边界

- 功能描述：契约明确四类返回的处理方式和 runner 的禁止动作，避免自动流程绕过人。
- 用户场景：流水线遇到 `decision_required` 时，runner 需要知道应停止而不是猜测。
- 验收条件：
  - AC-002-1：Given 契约文档，When 检查失败语义章节，Then 成功、`ok=false`、`decision_required`、`awaiting_human_approval` 四类均有处理方式和退出行为。【执行路径：本地单元测试】
  - AC-002-2：Given 契约文档，When 检索人工动作，Then 明确列出 `approve`、`reapprove`、`merge`、`unblock`、`rewind`、`waive` 为 runner 禁止调用，并要求检查点停机通知人。【执行路径：本地单元测试】
  - AC-002-3：Given 契约文档，When 检查职责边界，Then 明确 Docker、沙箱、日志与资源隔离属于 runner，核心不提供容器运行时。【执行路径：本地单元测试】

### FR-003 入口链接与发布一致性

- 功能描述：契约可从仓库首页或执行手册发现，文档与发布元数据保持一致。
- 用户场景：平台维护者升级文档后，需要确认入口、版本和 manifest 未漂移。
- 验收条件：
  - AC-003-1：Given 仓库文档，When 打开 `README.md` 或 `sdd/README.md`，Then 存在指向 `deploy/runner/CONTRACT.md` 的入口链接。【执行路径：本地单元测试】
  - AC-003-2：Given 本需求变更，When 运行 `verify-core` 与 `check --stage spec`，Then 状态机与 MCP 暴露面未新增写操作或人工动作。【执行路径：本地单元测试 + `verify-core`】
  - AC-003-3：Given 受保护文件发生变更，When 检查 `sdd/VERSION` 与 `sdd/manifest.json`，Then 版本已递增且 manifest 重新生成并通过校验。【执行路径：本地单元测试 + `verify-core`】

## 5. 边界与异常

| 场景类型 | 场景描述 | 关联FR/AC | 预期行为（错误码/降级策略/提示信息） |
|---|---|---|---|
| 边界场景 | `next` 只包含 `action=done` | FR-001；AC-001-2 | Runner 归档证据并正常退出，不继续调用 submit |
| 边界场景 | 提交返回 `ok=false` | FR-002；AC-002-1 | 把 `errors` 交回 Agent 修复后重试，记录重试次数 |
| 边界场景 | 返回 `decision_required=true` | FR-002；AC-002-1 | 停止自动循环，把 `question` 与 `options` 交给人类 |
| 异常场景 | 到达 Spec 审批或交付确认检查点 | FR-002；AC-002-2 | 退出码非 0，通知人执行 `human_checkpoint.command` |
| 异常场景 | Runner 尝试调用人工动作 | FR-002；AC-002-2 | 契约禁止；CLI 缺少 `--human` 时拒绝执行 |
| 异常场景 | 文档新增但未更新版本或 manifest | FR-003；AC-003-3 | `verify-core` 失败并提示重新生成 manifest |

## 6. 非功能需求

| 类型 | 要求 | 指标/验收方式 | 关联FR/AC |
|---|---|---|---|
| 可读性 | 新 harness 开发者可在 15 分钟内读完并按示例接入 | 人工评审 | FR-001；AC-001-2 |
| 一致性 | 契约命令与 `sdd --help` 及 `sdd/agent-contract.md` 一致 | 文档一致性测试 | FR-001；AC-001-3 |
| 安全性 | 人工动作边界明确且不可被 runner 绕过 | 单元测试断言 | FR-002；AC-002-2 |
| 可维护性 | 文档变更不修改状态机代码 | `verify-core` 回归 | FR-003；AC-003-2 |

## 7. 外部接口

| 方法 | 路径 | 用途 | 归属AC |
|---|---|---|---|
| 文档 | `deploy/runner/CONTRACT.md` | 外部 runner 接入契约 | AC-001-1 |
| 文档 | `README.md` / `sdd/README.md` | 契约入口链接 | AC-003-1 |
| CLI | `sdd resume --json` | 读取 `next` 与检查点 | AC-001-2 |
| CLI | `sdd submit` / `sdd submit-task` | 提交阶段产物与任务证据 | AC-001-2 |

- 请求/响应示例：契约中给出 JSON 字段摘录与命令序列，不新增网络接口。
- 契约文件：本需求交付的 Markdown 文档即契约本身。

## 8. 数据模型

- 核心实体定义：不新增数据结构；契约消费现有 `next`、`human_checkpoint`、
  `autopilot` 和 `inbox` JSON。
- 数据流说明：Runner 读取 CLI JSON -> 交给 Agent -> 回传提交结果 -> 归档日志与证据。
- 持久化：不新增数据库；运行日志由 runner 自行落盘。

## 9. 约束与假设

- 技术约束：只使用现有公开 CLI；文档与测试不引入第三方依赖。
- 业务约束：人工动作只能由人执行，runner 不得代替或伪造。
- 假设条件：外部 runner 能执行 PowerShell 或等价 shell 命令并保存退出码。

## 10. 变更历史

| 日期 | 版本 | 变更内容 | 作者 |
|---|---|---|---|
| 2026-11-24 | 1.0.0 | 初始版本 | SDD Agent |

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
