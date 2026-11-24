# 只读 sdd view HTML 运行视图规格说明书（Spec）

## 1. 元数据

| 项 | 内容 |
|---|---|
| Spec ID | SPEC-REQ-007 |
| 工作项 ID | SDD-VIEW-001 |
| FEAT ID | FEAT-009 |
| 原始需求来源 | https://github.com/RyanBrainNew/sdd-kit/issues/1 |
| 作者 | SDD Agent |
| 创建日期 | 2026-11-24 |
| 状态 | Draft |
| 版本号 | 1.0.0 |
| 产品类型 | 传统产品 |
| 模板适配 | 标准 21 节模板；UI、AI 与多智能体章节标注不适用 |
| 关联人 | 产品负责人：RyanBrainNew；技术负责人：sdd-kit 平台维护者 |
| 原型版本 | 不涉及 |

## 2. 范围声明

- In-Scope：提供一个离线可打开的只读运行视图。
  1. 新增 CLI `python -m sdd view --spec <spec> [--out <path>] [--json]`。
  2. 生成单文件 HTML，包含头部、事件时间线、Gate 表、Task 表和 Spec 工件列表。
  3. 页面数据只来自现有 `status`、`events`、`board` 与 Gate 报告 JSON/Markdown。
  4. 未指定 `--out` 时默认写入 `.sdd/runtime/view/<spec>.html`。
  5. 视图严格只读：不写 `state.json`、`events.jsonl`、Gate 报告或任何审计文件。
  6. 空 Spec、无事件 Spec 和包含 rewind 事件的 Spec 都能生成合法页面。
  7. 同步 README、`sdd/README.md`、`sdd/agent-contract.md`、版本和 manifest。
- Out-of-Scope：不把视图扩展为在线平台。
  1. 不新增 Web 服务、数据库、前端构建链或常驻进程。
  2. 不使用外部 CSS/JS、CDN 或网络请求；HTML 必须离线可用。
  3. 不实现拖拽、编辑、审批、运行或任何写入动作。
  4. 不在视图中复制 Gate 规则或自行推导状态。
  5. 不新增 MCP 写工具，不改变现有 `next` JSON schema。
  6. 不重新设计 `sdd board` 的文本/JSON 输出。

## 3. 业务上下文

### 3.1 干系人与角色

| 角色 | 诉求 | 使用场景 | 责任边界 |
|---|---|---|---|
| 开发者 | 一眼看到 Spec 当前状态、卡点和等待项 | 本地排查或站会 | 只读查看，不通过页面执行动作 |
| 平台维护者 | 视图与 CLI 状态一致，可离线分享 | 评审、审计、演示 | 维护渲染逻辑，不复制状态机 |
| 审计人员 | 能还原时间线、Gate 证据和产物 | 交付后审计 | 只读查看和归档 |
| 业务负责人 | 了解谁在等谁 | 审批前后查看进度 | 仍通过 CLI 执行人工动作 |

### 3.2 业务流程

1. 开发者执行 `sdd view --spec <spec>`。
2. CLI 读取当前 Spec 的 state、events、board 和 Gate 报告。
3. 渲染器把数据转义后写入单文件 HTML。
4. 开发者用浏览器离线打开页面，查看状态、时间线、Gate、Task 和工件。
5. 页面不提供任何写操作；需要推进时仍执行标准 CLI。

### 3.3 业务规则

- BR-001：`sdd/scripts/sdd.py` 仍是唯一状态机；视图只消费其 JSON 输出。
- BR-002：生成视图前后，Spec 目录下所有审计文件字节不变。
- BR-003：HTML 必须转义所有动态文本，禁止注入脚本或外部资源。
- BR-004：单文件 HTML 不依赖网络、构建工具或浏览器扩展。
- BR-005：默认输出目录不存在时自动创建，但不得覆盖 Spec 审计文件。
- BR-006：数据缺失时展示明确空态，不猜测或补造事件。
- BR-007：只使用 Python 标准库；MCP 适配器保持薄适配。

## 4. 功能需求与验收条件

### FR-001 单文件视图生成

- 功能描述：`sdd view` 生成包含五个核心区块的离线 HTML。
- 用户场景：开发者需要快速查看 Spec 进度和等待项。
- 验收条件：
  - AC-001-1：Given 一个有效 Spec，When 执行 `sdd view --spec <spec> --out <path>`，Then 生成 HTML，包含头部、事件时间线、Gate 表、Task 表和工件列表五个区块。【执行路径：本地单元测试】
  - AC-001-2：Given 未指定 `--out`，When 执行 `sdd view --spec <spec>`，Then 输出写入 `.sdd/runtime/view/<spec>.html`，父目录自动创建，命令打印输出路径。【执行路径：本地单元测试】
  - AC-001-3：Given 空 Spec 或没有事件的 Spec，When 生成视图，Then HTML 合法可打开，并为时间线、Gate、Task 和工件展示明确空态。【执行路径：本地单元测试】

### FR-002 只读数据来源与时间线

- 功能描述：视图只读取现有 JSON/报告，完整展示事件与证据，不产生副作用。
- 用户场景：审计人员需要确认 rewind 等关键事件和 Gate 证据。
- 验收条件：
  - AC-002-1：Given 生成视图前后，When 比较 `state.json`、`events.jsonl` 和 `sdd/reports/<spec>/`，Then 文件字节完全不变。【执行路径：本地单元测试】
  - AC-002-2：Given `events.jsonl` 包含 rewind 事件，When 生成视图，Then 时间线按事件顺序展示事件名、时间、证据和 from/to 状态。【执行路径：本地单元测试】
  - AC-002-3：Given 视图实现，When 检查数据来源与 MCP 暴露面，Then 页面数据只来自 status/events/board/Gate 报告，未复制状态机规则，未新增 MCP 写工具。【执行路径：本地单元测试 + 人工评审】

### FR-003 边界、安全与发布

- 功能描述：错误输入、特殊字符和发布元数据都有确定行为。
- 用户场景：平台维护者升级版本时，需要视图安全且文档一致。
- 验收条件：
  - AC-003-1：Given 不存在的 Spec 或非法 `--out` 路径，When 执行 `sdd view`，Then 退出码非 0、输出明确错误，且不留下半成品文件。【执行路径：本地单元测试】
  - AC-003-2：Given Spec 标题或证据包含 `<script>` 等特殊字符，When 生成视图，Then 文本被 HTML 转义，页面不包含可执行脚本或外部资源引用。【执行路径：本地单元测试】
  - AC-003-3：Given 修改受保护核心文件，When 执行发布校验，Then `sdd/VERSION` 已递增、`sdd/manifest.json` 已重写并通过 `verify-core`，README 与执行手册已同步。【执行路径：本地单元测试 + `verify-core`】

## 5. 边界与异常

| 场景类型 | 场景描述 | 关联FR/AC | 预期行为（错误码/降级策略/提示信息） |
|---|---|---|---|
| 边界场景 | Spec 刚创建、没有事件 | FR-001；AC-001-3 | 生成空态页面，时间线显示“暂无事件” |
| 边界场景 | `--out` 所在目录不存在 | FR-001；AC-001-2 | 自动创建目录后写入 |
| 边界场景 | Spec 已 MERGED | FR-001；AC-001-1 | 正常渲染最终状态与 PR 链接 |
| 异常场景 | `--spec` 不存在 | FR-003；AC-003-1 | 退出码 1，提示 Spec ID，不写文件 |
| 异常场景 | `--out` 指向目录或不可写路径 | FR-003；AC-003-1 | 退出码 1，保留原文件不变 |
| 异常场景 | 标题含 HTML/脚本片段 | FR-003；AC-003-2 | 转义输出，页面无 `<script>` |
| 异常场景 | `events.jsonl` 含损坏行 | FR-002；AC-002-2 | 跳过损坏行并在页面标注告警，不中断渲染 |

## 6. 非功能需求

| 类型 | 要求 | 指标/验收方式 | 关联FR/AC |
|---|---|---|---|
| 性能 | 单 Spec 视图生成小于 1 秒 | 本地单元测试观察 | FR-001；AC-001-1 |
| 安全 | 无脚本、无外部资源、动态文本全部转义 | HTML 断言 | FR-003；AC-003-2 |
| 可用性 | 浏览器直接打开，窄屏可读 | 人工评审 | FR-001；AC-001-1 |
| 只读性 | 不修改任何审计文件 | 前后哈希比较 | FR-002；AC-002-1 |
| 兼容性 | 只使用 Python 标准库与现有 JSON | `verify-core` 回归 | FR-003；AC-003-3 |

## 7. 外部接口

| 方法 | 路径 | 用途 | 归属AC |
|---|---|---|---|
| CLI | `sdd view --spec <spec> --out <path>` | 生成单文件 HTML 视图 | AC-001-1 |
| CLI | `sdd view --spec <spec>` | 使用默认输出路径 | AC-001-2 |
| CLI | `sdd view --spec <spec> --json` | 返回生成结果 JSON | AC-001-1 |
| 数据 | `status` / `events` / `board` / Gate 报告 | 视图数据来源 | AC-002-3 |

- 请求/响应示例：`--json` 返回 `ok`、`spec`、`out`、`bytes` 和 `sections`。
- 契约文件：不新增网络契约；HTML 本身是交付物。

## 8. 数据模型

- 核心实体定义：不新增持久化数据；视图消费现有 `state.json`、
  `events.jsonl`、`tasks.md`、`gates.md` 和 `sdd/reports/<spec>/gate*-report.md`。
- 数据流说明：CLI JSON -> 渲染模型 -> HTML 字符串 -> 单文件输出。
- 持久化：仅写用户指定的 HTML 文件；不写 state、events 或报告。

## 9. 约束与假设

- 技术约束：只使用 Python 标准库；HTML/CSS 内联，无 JavaScript。
- 业务约束：视图不执行任何人工动作或状态迁移。
- 假设条件：浏览器支持现代 HTML5/CSS；输出目录可写。

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
