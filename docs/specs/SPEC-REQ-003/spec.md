# Gate 检查项分级、人工豁免与按 ID 度量规格说明书（Spec）

## 1. 元数据

| 项 | 内容 |
|---|---|
| Spec ID | SPEC-REQ-003 |
| 工作项 ID | SDD-GATE-002 |
| FEAT ID | FEAT-005 |
| 原始需求来源 | https://github.com/RyanBrainNew/sdd-kit/issues/7 |
| 作者 | SDD Agent |
| 创建日期 | 2026-11-23 |
| 状态 | Draft |
| 版本号 | 1.0.0 |
| 产品类型 | 传统产品 |
| 模板适配 | 标准 21 节模板；UI、统计、多智能体与 AI 专属章节标注不适用 |
| 关联人 | 产品负责人：RyanBrainNew；技术负责人：sdd-kit 平台维护者 |
| 原型版本 | 不涉及 |

## 2. 范围声明

- In-Scope：把现有检查项注册表和 Gate 报告扩展为可分级治理模型。
  1. 注册表覆盖 G0–G5 的稳定检查 ID，并声明触发方式、级别、是否可豁免、
     安全红线属性、证据要求和责任角色。
  2. Gate 检查结果为 `pass`、`warn`、`block`；强制项失败为 `block`，
     建议项失败为 `warn`，安全红线失败不可降级。
  3. 建议项告警写入 Gate 报告和 `inbox`，但不阻断正常状态推进。
  4. 新增人类专用 `waive` 动作，记录检查 ID、范围、原因、审批人、到期时间和证据。
  5. 豁免绑定当前 Spec 与相关产物哈希；产物变化或豁免到期后自动重新校验。
  6. `metrics` 按检查 ID 输出 pass、warn、block、waived 次数和通过率、告警率。
  7. 同步 CLI、README、执行手册、Agent 契约、版本和 manifest。
- Out-of-Scope：不把 Gate 扩展为独立审批平台。
  1. 不新增服务端、数据库、常驻进程、第三方运行时依赖或可视化编排。
  2. 不允许 MCP 暴露 `waive`、`approve`、`merge`、`unblock`、`rewind`。
  3. 不允许 profile 关闭 required 检查或把 security 红线降级。
  4. 不实现 P1-3 的 Review Skill / 技术栈 overlay。
  5. 不实现 P2 的知识索引、BAR/Fix Pattern 或逃逸缺陷回流指标。
  6. 不重新定义 G0–G5 的业务含义，只改变检查结果分级、豁免和度量。
  7. 不迁移或重写历史 Gate 报告；旧报告继续按现有 PASS/FAILED 语义读取。

## 3. 业务上下文

### 3.1 干系人与角色

| 角色 | 诉求 | 使用场景 | 责任边界 |
|---|---|---|---|
| 平台维护者 | 每项检查有稳定 ID、级别和明确执行条件 | 新增检查、调整建议项、排查 Gate 失败 | 维护注册表和检查实现 |
| 业务负责人 | 建议项可见但不阻断交付，例外有可审计的人工豁免 | 紧急交付、纯文档变更、已知低风险缺口 | 批准豁免并承担到期责任 |
| 执行 Agent | 只根据 `next.action` 和结构化结果判断能否继续 | 提交产物、重跑 Gate、读取 inbox | 不得调用人工豁免 |
| 审计与合规 | 能按检查 ID 追溯通过、告警、阻断和豁免 | 审计 Gate 报告、统计告警率 | 只读审计，不代替人工批准 |

### 3.2 业务流程

1. 引擎运行当前 Gate 的注册检查，每项得到 `pass`、`warn` 或 `block`。
2. 仅当存在 `block` 时 Gate 总体结果为 `FAILED`，正常 `complete` 或 `approve`
   不能绕过；只有 `warn` 时 Gate 总体结果仍为 `PASS`，但报告保留告警。
3. 若 required 检查失败且该项允许豁免，人类可执行 `waive`；有效豁免把该项
   降为 `warn`，并写入审批记录、产物范围和到期时间。
4. 每次重新执行 Gate、`check`、`inbox` 或 `metrics` 时，引擎重新计算豁免
   有效期与产物哈希；过期或范围变化后原豁免失效，检查恢复为 `block`。
5. `inbox` 展示未关闭告警；`metrics` 按检查 ID 汇总各状态次数和比率。

### 3.3 业务规则

- BR-001：`sdd/scripts/sdd.py` 仍是唯一状态机；CLI、MCP 和报告不得复制状态规则。
- BR-002：检查 ID 一旦发布不得复用；新增检查使用同 Gate 的下一个稳定编号。
- BR-003：required 失败输出 `block`；advisory 失败输出 `warn`。
- BR-004：`redline=true` 的检查失败永远输出 `block`，不可豁免或降级。
- BR-005：豁免只影响指定检查 ID、当前 Spec 和绑定产物哈希，不扩大为 Spec 级放行。
- BR-006：豁免必须有人类审批、非空范围、原因、证据和未来到期时间。
- BR-007：`warn` 不阻断状态推进，但必须写入 Gate 报告并可从 `inbox` 发现。
- BR-008：历史 Gate 报告和既有 Spec 的状态、摘要、digest 不因本能力改变。
- BR-009：只使用 Python 标准库；MCP 适配器继续保持薄适配。

## 4. 功能需求与验收条件

### FR-001 全 Gate 检查项注册表

- 功能描述：注册表覆盖 G0–G5，每项包含稳定 ID、Gate、名称、级别、触发方式、
  是否可豁免、是否安全红线、证据要求和责任角色，并由核心统一校验。
- 用户场景：维护者新增或审查检查项时，可从注册表枚举 Gate 的全部检查与边界。
- 验收条件：
  - AC-001-1：Given 当前核心注册表，When 执行注册表校验，Then G0–G5 均至少存在一项注册检查，ID 唯一且字段合法。【执行路径：本地单元测试】
  - AC-001-2：Given 注册表包含重复 ID、非法 Gate、非法级别、非法触发方式或非布尔 redline，When 执行注册表校验，Then 返回可定位错误。【执行路径：本地单元测试】
  - AC-001-3：Given 既有 G0/G1 检查 ID，When 升级到新注册表，Then 原 ID 和检查含义保持不变，历史报告仍可解析。【执行路径：本地单元测试】

### FR-002 pass/warn/block 判定与阻断

- 功能描述：核心按检查级别和 redline 属性生成 `pass`、`warn`、`block`；
  只有 `block` 阻止 Gate 通过，`warn` 保留在报告中。
- 用户场景：建议项失败时团队能看到风险并继续交付；强制项失败时任何普通流程动作都不能绕过。
- 验收条件：
  - AC-002-1：Given required 检查失败且无有效豁免，When 执行 Gate，Then 该项为 `block`，Gate 总体结果为 `FAILED`，状态不推进。【执行路径：本地单元测试】
  - AC-002-2：Given 仅 advisory 检查失败，When 执行 Gate，Then 该项为 `warn`，Gate 总体结果为 `PASS` 且状态可正常推进。【执行路径：本地单元测试】
  - AC-002-3：Given redline 检查失败，When 检查是否可豁免或执行普通 `complete`，Then 仍为 `block`，且错误说明安全红线不可降级。【执行路径：本地单元测试】
  - AC-002-4：Given Gate 报告含 warn 或 block，When 读取报告与 `gates.md`，Then 每项显示稳定检查 ID、级别、结果、证据和问题说明。【执行路径：本地单元测试】

### FR-003 人类豁免与到期重校验

- 功能描述：新增人类专用 `waive` 动作，只为允许豁免的非红线检查记录有范围、
  有期限、有审批人和证据的豁免；引擎在每次校验时重新确认范围与有效期。
- 用户场景：已知低风险证据缺口可由负责人限期接受，到期或代码变化后自动恢复阻断。
- 验收条件：
  - AC-003-1：Given required 检查、合法范围和未来到期时间，When 人类执行 `waive`，Then state 记录检查 ID、Gate、范围、原因、审批人、时间、到期时间和证据。【执行路径：本地单元测试】
  - AC-003-2：Given 有效豁免且绑定产物未变化，When 重新执行失败检查，Then 结果为 `warn`，Gate 不阻断且报告标记 waived。【执行路径：本地单元测试】
  - AC-003-3：Given 豁免已过期或绑定产物哈希变化，When 重新执行检查，Then 原豁免失效，required 失败恢复为 `block`。【执行路径：本地单元测试】
  - AC-003-4：Given 检查不可豁免、属于 redline、缺少 --human、缺少证据或到期时间不合法，When 执行 `waive`，Then 命令失败且不写入豁免。【执行路径：本地单元测试】

### FR-004 inbox 告警与按检查 ID 度量

- 功能描述：`inbox` 展示未关闭的 Gate 告警，`metrics --json` 按检查 ID 汇总
  pass、warn、block、waived 次数、通过率和告警率。
- 用户场景：负责人能从待办中发现被接受的建议项缺口，平台维护者能定位高频告警检查。
- 验收条件：
  - AC-004-1：Given 某 Spec 的 Gate 报告存在 warn，When 运行 `inbox --json`，Then 该项告警可见并带 Spec、Gate、检查 ID 和结果。【执行路径：本地单元测试】
  - AC-004-2：Given 多个 Spec 的 Gate 报告包含不同检查结果，When 运行 `metrics --json`，Then `checks` 按检查 ID 输出各状态计数、通过率和告警率。【执行路径：本地单元测试】
  - AC-004-3：Given 历史报告只有 pass/block 或旧格式检查行，When 计算 inbox 和 metrics，Then 不报错并保持旧结果可读。【执行路径：本地单元测试 + `check --all`】

### FR-005 人工边界、兼容性与文档同步

- 功能描述：`waive` 仅在 CLI 暴露且强制 `--human`，MCP 不提供；同步版本、manifest
  和文档，保证旧 Spec 与现有 CI 全部通过。
- 用户场景：平台发布新能力后，现有仓库和历史 Spec 不需要迁移或重跑。
- 验收条件：
  - AC-005-1：Given MCP 工具清单和 CLI 帮助，When 检查人工动作边界，Then `waive` 只在 CLI 且要求 `--human`，MCP 不可调用。【执行路径：本地单元测试 + 文档评审】
  - AC-005-2：Given 版本升级后的仓库，When 执行全量测试、`verify-core`、`verify-agent` 和 `check --all --stage ci --check-git`，Then 全部通过。【执行路径：本地单元测试 + CI 集成测试】

## 4.1 UI规格（涉及前端UI时必填）

不涉及。

## 5. 边界与异常

| 场景类型 | 场景描述 | 关联FR/AC | 预期行为（错误码/降级策略/提示信息） |
|---|---|---|---|
| 边界场景 | 同一检查同时是 advisory 和 redline 且失败 | FR-002；AC-002-3 | 以 `block` 为准，不因 advisory 降级 |
| 边界场景 | 豁免检查 ID 不存在或不属于当前 Gate | FR-003；AC-003-4 | 拒绝，列出可用 Gate 与检查 ID |
| 边界场景 | `--expires` 等于或早于当前时间 | FR-003；AC-003-4 | 拒绝，提示必须是未来 ISO 时间 |
| 边界场景 | Spec 产物在豁免后发生变化 | FR-003；AC-003-3 | 豁免失效，检查重新计算 |
| 异常场景 | 旧 Gate 报告没有 warn/waived 列 | FR-004；AC-004-3 | 按旧 pass/block 行读取，不补写历史 |
| 异常场景 | MCP 或 Agent 尝试调用 waive | FR-005；AC-005-1 | 工具不存在；CLI 缺少 `--human` 时失败 |
| 异常场景 | 豁免到期但立刻重新运行 Gate | FR-003；AC-003-3 | 过期记录保留审计，但不再参与判定 |

## 6. 非功能需求

| 类型 | 要求 | 指标/验收方式 | 关联FR/AC |
|---|---|---|---|
| 性能 | 豁免与指标计算只读取本地状态和报告 | 单元测试；无网络和额外进程 | FR-003；FR-004 |
| 安全 | 红线检查不可豁免，MCP 不暴露人工动作 | 负向测试与工具清单审查 | FR-002；FR-005 |
| 兼容性 | 旧 Gate 报告、旧 Spec 和旧 CLI 用法不受影响 | `check --all` 与历史 Spec 回归 | FR-001；FR-004；FR-005 |
| 可审计性 | 豁免包含审批人、范围、原因、到期时间和证据 | state 审批记录断言 | FR-003；AC-003-1 |
| 可维护性 | 检查结果和状态解析集中在一个核心模块 | 代码评审与单元测试 | FR-001；FR-002 |

## 7. 外部接口

| 方法 | 路径 | 用途 | 归属AC |
|---|---|---|---|
| CLI | `python -m sdd waive --spec <spec> --check <id> --scope <text> --reason <text> --expires <iso> --evidence <text> --human` | 记录人工豁免 | AC-003-1；AC-003-4 |
| CLI | `python -m sdd inbox --json` | 展示 Gate 告警与待人工处理事项 | AC-004-1 |
| CLI | `python -m sdd metrics --json` | 按检查 ID 汇总结果 | AC-004-2 |
| CLI | `python -m sdd check --all --stage ci --check-git` | 验证兼容性和阻断规则 | AC-002-1；AC-005-2 |

- 请求/响应示例：`waive --json` 返回
  `{"ok": true, "kind": "waiver", "spec": "...", "check": "G2-01", "expires_at": "..."}`。
- 契约文件：不涉及外部网络契约；检查项字段和 Gate 报告格式由本 Spec 定义。

## 8. 数据模型

- 检查项注册表字段：

| 字段 | 类型 | 必填 | 规则 |
|---|---|---|---|
| `id` | string | 是 | `G[0-5]-NN`，全局唯一且发布后不复用 |
| `gate` | string | 是 | G0–G5 |
| `name` | string | 是 | 非空中文说明 |
| `level` | string | 是 | `required` 或 `advisory` |
| `trigger` | string | 是 | `doc_pr`、`code_pr`、`local`、`ci`、`pipeline` 之一 |
| `waivable` | bool | 是 | 仅 required 检查可考虑豁免 |
| `redline` | bool | 是 | 为 true 时永不豁免且失败必为 block |
| `evidence` | string | 是 | 非空证据要求 |
| `owner` | string | 是 | 非空责任角色 |

- 检查结果字段：`id`、`level`、`result`（`pass/warn/block`）、`detail`、
  `errors`，以及可选 `waiver`（审批人、到期时间、范围摘要）。
- 豁免记录：`check_id`、`gate`、`scope`、`artifacts`、`reason`、`approver`、
  `at`、`expires_at`、`evidence`。
- 数据流：注册表 → Gate 检查结果 → Gate 报告与审计 → inbox / metrics。
- 迁移方案：不迁移历史报告；新字段只对新生成报告生效。

## 9. 约束与假设

- 技术约束：只使用 Python 标准库；报告仍是 Markdown，状态仍是 JSON。
- 业务约束：人工动作只能由人执行；建议项不能成为静默忽略项。
- 假设条件：所有现有 Gate 检查都能映射到稳定 ID，且不需要改变业务含义。
- 假设条件：豁免只对当前 Spec 生效，不支持跨 Spec 或全仓库豁免。

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

不涉及；所有验收条件均为确定性本地测试或 CI 检查。

## 14. AI安全合规

不适用；但安全检查红线属于本 Spec 的强制业务规则。

## 15. 成本与性能

不涉及。

## 16. 运行监控与效果度量

本 Spec 的度量对象是 Gate 检查，不涉及 AI 效果指标。

## 17. 自主程度与人机分工

不适用。

## 18. Agent行为规格

不适用；Agent 仍只能执行 CLI 暴露的非人工动作。

## 19. 审计与回放

不适用；本 Spec 的审计由现有 `events.jsonl`、Gate 报告和豁免记录承担。

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
