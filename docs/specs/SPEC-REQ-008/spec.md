# 固定预设升级 upgrade-workflow 规格说明书（Spec）

## 1. 元数据

| 项 | 内容 |
|---|---|
| Spec ID | SPEC-REQ-008 |
| 工作项 ID | SDD-WORKFLOW-001 |
| FEAT ID | FEAT-010 |
| 原始需求来源 | https://github.com/RyanBrainNew/sdd-kit/issues/3 |
| 作者 | SDD Agent |
| 创建日期 | 2026-11-24 |
| 状态 | Draft |
| 版本号 | 1.0.0 |
| 产品类型 | 传统产品 |
| 模板适配 | 标准 21 节模板；UI、AI 与多智能体章节标注不适用 |
| 关联人 | 产品负责人：RyanBrainNew；技术负责人：sdd-kit 平台维护者 |
| 原型版本 | 不涉及 |

## 2. 范围声明

- In-Scope：允许人类在保留审计的前提下把现有 Spec 升级到仓库中的固定预设。
  1. 新增人工命令 `sdd upgrade-workflow --spec <spec> --to <name>@<version>
     --reason "..." --human`。
  2. 原子替换 Spec 的 `workflow.json`，同步 `state.json.workflow`。
  3. 在 `state.workflow_history` 追加 from/to name、version、digest、
     审批人、原因、时间和待补 Gate。
  4. 默认只允许同预设升到更高 version；跨预设允许但必须给出 reason；
     降级默认拒绝，仅在 `--allow-downgrade --design-change <ref>` 时允许并留痕。
  5. 升级后按新预设的 `required_gates` 重新校验现有 Gate，未 PASS 的 Gate
     进入 `inbox`。
  6. 旧 spec/design/tasks/verification/gates 工件不被重写。
  7. 同步 CLI、MCP 边界、README、执行手册、Agent 契约、版本和 manifest。
- Out-of-Scope：不做工作流编辑器。
  1. 不实现任意 DAG 编辑、拖拽流程或运行时修改 Gate 规则。
  2. 不批量升级多个 Spec，不自动升级历史 MERGED Spec。
  3. 不通过 MCP 暴露升级动作。
  4. 不自动批准、伪造或重写 Gate 报告；缺失 Gate 只提示人处理。
  5. 不新增服务端、数据库或第三方依赖。
  6. 不改变 `sdd/scripts/sdd.py` 作为唯一状态机的架构。

## 3. 业务上下文

### 3.1 干系人与角色

| 角色 | 诉求 | 使用场景 | 责任边界 |
|---|---|---|---|
| 平台维护者 | 发布新预设后让活跃 Spec 受控升级 | 统一门禁、修补流程缺口 | 执行升级并承担审计责任 |
| 业务负责人 | 升级不破坏已批准范围和历史证据 | 审批升级原因 | 通过 reason/evidence 确认 |
| 执行 Agent | 知道升级后哪些 Gate 需要补 | 继续推进实现 | 不得执行升级或伪造 Gate |
| 审计人员 | 能还原每次升级的前后版本与批准人 | 交付后审计 | 只读检查历史与 inbox |

### 3.2 业务流程

1. 平台维护者发布或更新 `sdd/workflows/<name>.json` 的 version。
2. 人类对活跃 Spec 执行 `upgrade-workflow`，指定 `--to name@version` 与 reason。
3. 引擎校验目标预设、版本方向、跨预设/降级规则和人工身份。
4. 引擎原子替换快照并更新 state，追加 `workflow_history` 与事件。
5. 引擎按新预设重新检查当前状态要求的 Gate，把未 PASS 的 Gate 写入历史与 inbox。
6. Agent 继续按新工作流推进；人工通过 `sdd inbox` 处理缺失 Gate。

### 3.3 业务规则

- BR-001：升级只能人工执行，CLI 与状态机双重强制 `--human`。
- BR-002：目标必须是仓库中存在且 version 匹配的合法预设。
- BR-003：同版本升级拒绝；降级默认拒绝，例外必须记录 design-change。
- BR-004：跨预设升级必须填写 reason，并在历史中保留来源预设。
- BR-005：快照与 state 必须同步更新；任一失败都不能留下半升级状态。
- BR-006：历史工件只读；升级只改 `workflow.json`、`state.json` 和 `events.jsonl`。
- BR-007：缺失 Gate 只进入 inbox，不自动生成报告或推进状态。
- BR-008：MERGED 或 BLOCKED Spec 不得直接升级。
- BR-009：只使用 Python 标准库；MCP 适配器保持薄适配。

## 4. 功能需求与验收条件

### FR-001 人工升级与版本方向

- 功能描述：提供人工专用升级命令，并严格执行版本方向规则。
- 用户场景：平台发布 `l2-standard@2` 后，活跃 Spec 需要切换到新门禁。
- 验收条件：
  - AC-001-1：Given 活跃 Spec 固定在 `l2-standard@1` 且仓库存在 `l2-standard@2`，When 人类执行 `upgrade-workflow --to l2-standard@2 --reason "..." --human`，Then 快照与 `state.workflow` 均变为 2，命令返回 from/to 与 history 摘要。【执行路径：本地单元测试】
  - AC-001-2：Given 当前已是目标版本，When 再次升级到同版本，Then 命令失败且不修改快照、state 或事件。【执行路径：本地单元测试】
  - AC-001-3：Given 目标预设不存在或请求 version 与预设 version 不一致，When 执行升级，Then 命令失败，输出可用预设/版本，状态保持不变。【执行路径：本地单元测试】
  - AC-001-4：Given 升级目标是更低 version，When 未提供 `--allow-downgrade --design-change`，Then 拒绝；提供后允许并把 design-change 写入历史。【执行路径：本地单元测试】
  - AC-001-5：Given 缺少 `--human`、reason 为空或 Spec 已 MERGED/BLOCKED，When 执行升级，Then 拒绝且不写任何文件。【执行路径：本地单元测试】

### FR-002 审计历史与工件保护

- 功能描述：升级全过程可追溯，旧证据不被重写。
- 用户场景：审计人员需要还原升级前后的工作流和批准人。
- 验收条件：
  - AC-002-1：Given 一次成功升级，When 读取 `state.workflow_history[-1]`，Then 记录 from/to name、version、digest、approver、reason、at 和 pending_gates。【执行路径：本地单元测试】
  - AC-002-2：Given 升级前后，When 比较 spec/design/tasks/verification/gates 文件，Then 字节完全不变；只有 `workflow.json`、`state.json`、`events.jsonl` 变化。【执行路径：本地单元测试】
  - AC-002-3：Given 目标预设无效或写入失败，When 升级中止，Then `workflow.json` 与 `state.json` 保持升级前字节一致（无半升级状态）。【执行路径：本地单元测试】

### FR-003 Gate 重校验与 inbox

- 功能描述：升级后按新预设复核 Gate，并把缺口交给人工处理。
- 用户场景：跨预设升级后新增的 Gate 需要有人跟进。
- 验收条件：
  - AC-003-1：Given 新预设对当前状态要求更多 Gate，When 升级成功，Then 重新校验 `required_gates`，未 PASS 的 Gate 写入 `workflow_history[-1].pending_gates` 并出现在命令返回中。【执行路径：本地单元测试】
  - AC-003-2：Given 升级后存在 pending gates，When 执行 `sdd inbox --json`，Then 每个 Gate 以独立 item 出现，包含 action、gate、reason 和下一步命令。【执行路径：本地单元测试】
  - AC-003-3：Given pending gate 后续获得 PASS 报告，When 再次执行 `inbox`，Then 该 item 消失；升级本身不写 Gate 报告。【执行路径：本地单元测试】

### FR-004 边界与发布

- 功能描述：保持人工边界、MCP 薄适配和发布元数据一致。
- 用户场景：平台维护者升级 sdd-kit 后，命令可发现且文档一致。
- 验收条件：
  - AC-004-1：Given `upgrade-workflow`，When 检查 CLI 与 MCP 暴露面，Then 仅 CLI 注册且强制 `--human`，MCP 不暴露该动作。【执行路径：本地单元测试】
  - AC-004-2：Given 修改受保护核心与文档，When 执行发布校验，Then 版本递增、manifest 重写、README/执行手册/Agent 契约同步并通过 `verify-core`。【执行路径：本地单元测试 + `verify-core`】
  - AC-004-3：Given 升级后再次执行 `status`/`check`，When 解析工作流，Then 快照 digest/version 与 state 一致，命令不因升级而误报手工修改。【执行路径：本地单元测试 + `status`】

## 5. 边界与异常

| 场景类型 | 场景描述 | 关联FR/AC | 预期行为（错误码/降级策略/提示信息） |
|---|---|---|---|
| 边界场景 | 同预设升到更高 version | FR-001；AC-001-1 | 允许，记录 from/to 历史 |
| 边界场景 | 跨预设升级 | FR-001；AC-001-4 | 允许但必须 reason，记录来源预设 |
| 异常场景 | 同版本/降级 | FR-001；AC-001-2/4 | 拒绝；降级需显式 design-change |
| 异常场景 | 目标预设或 version 不存在 | FR-001；AC-001-3 | 退出码非 0，列出可用预设与版本 |
| 异常场景 | 缺少 --human 或 reason | FR-001；AC-001-5 | 退出码非 0，不修改任何文件 |
| 异常场景 | MERGED/BLOCKED Spec | FR-001；AC-001-5 | 拒绝升级并提示后续处理 |
| 边界场景 | 新预设增加 Gate | FR-003；AC-003-1/2 | 升级成功，缺口进入 inbox |
| 边界场景 | 写入中断 | FR-002；AC-002-3 | 恢复旧快照与旧 state |

## 6. 非功能需求

| 类型 | 要求 | 指标/验收方式 | 关联FR/AC |
|---|---|---|---|
| 一致性 | 快照、state、history、inbox 使用同一版本与 digest | 单元测试断言 | FR-001/FR-002/FR-003 |
| 安全性 | 人工动作强制 --human，MCP 不暴露 | CLI/MCP 边界测试 | FR-004；AC-004-1 |
| 原子性 | 失败时不留半升级状态 | 负向写入测试 | FR-002；AC-002-3 |
| 可读性 | 错误提示包含当前版本、目标版本和可用预设 | 负向测试 | FR-001；AC-001-3 |
| 兼容性 | 旧快照 Spec 不受影响 | 回归测试 | FR-004；AC-004-3 |

## 7. 外部接口

| 方法 | 路径 | 用途 | 归属AC |
|---|---|---|---|
| CLI | `sdd upgrade-workflow --spec <spec> --to <name>@<version> --reason "..." --human` | 人工升级固定预设 | AC-001-1 |
| CLI | `sdd upgrade-workflow ... --allow-downgrade --design-change <ref>` | 有设计变更证据的降级 | AC-001-4 |
| CLI | `sdd inbox --json` | 查看升级后缺失的 Gate | AC-003-2 |

- 请求/响应示例：升级返回 `from`、`to`、`pending_gates`、`history` 和 `next`。
- 契约文件：不新增网络契约。

## 8. 数据模型

- `state.workflow`：更新为 `{name, version, digest, snapshot}`。
- `state.workflow_history`：新增数组，条目包含：
  - `from` / `to`：name、version、digest；
  - `approver`、`reason`、`at`、`design_change`（可选）；
  - `pending_gates`：升级时未 PASS 的 Gate。
- `workflow.json`：替换为目标预设快照。
- `events.jsonl`：由状态机追加 `workflow_upgraded` 事件。
- 不新增数据库或旁路 JSON。

## 9. 约束与假设

- 技术约束：只使用 Python 标准库；升级逻辑位于 `sdd/scripts/sdd.py`。
- 业务约束：人工动作不得由 Agent 或 MCP 代替。
- 假设条件：平台团队通过发布新预设文件/version 提供升级目标。

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
