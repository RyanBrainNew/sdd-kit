# 工作流 Profile v2：可声明扩展与 workflow validate 规格说明书（Spec）

## 1. 元数据

| 项 | 内容 |
|---|---|
| Spec ID | SPEC-REQ-002 |
| 工作项 ID | SDD-PROFILE-001 |
| FEAT ID | FEAT-004 |
| 原始需求来源 | https://github.com/RyanBrainNew/sdd-kit/issues/7 |
| 作者 | SDD Agent |
| 创建日期 | 2026-11-23 |
| 状态 | Draft |
| 版本号 | 1.0.0 |
| 产品类型 | 传统产品 |
| 模板适配 | 标准 21 节模板；UI、统计与多智能体章节标注不适用 |
| 关联人 | 产品负责人：RyanBrainNew；技术负责人：sdd-kit 平台维护者 |
| 原型版本 | 不涉及 |

## 2. 范围声明

- In-Scope：把工作流预设从“固定 8 阶段 + 固定 Gate”扩展为可声明、可校验的
  Profile v2，并保证唯一状态机继续解释配置，而不是把规则复制到 profile。
  1. 新增 schema 2 声明模型；schema 1 预设和旧 Spec 快照继续原样可用。
  2. 声明 `stages`、`artifacts`、`gates`、`required_gates`、`gate_checks`、
     `human_checkpoints`、`design_mode`、`review_required`、`risk_stop`、
     `context_rules`。
  3. 阶段允许是规范阶段序列的严格递增子序列；被省略的阶段由引擎安全跳过，
     但不得跳过强制 Gate 或人工检查点。
  4. 新增 `python -m sdd workflow validate --file <profile>`，逐字段报错。
  5. 新增示范 profile `l2-refactor`，不改核心代码即可运行。
  6. 引擎实际消费 `gate_checks`、`human_checkpoints`、`risk_stop` 和
     `context_rules`，而不是只接受字段。
- Out-of-Scope：不把 `sdd-kit` 扩成通用工作流平台。
  1. 不支持任意 DAG、条件脚本、循环或运行时插件。
  2. 不改变 `sdd/scripts/sdd.py` 作为唯一状态机的地位。
  3. 不允许重命名 `spec.md`、`design.md`、`tasks.md`、`verification.md`、
     `PR_BODY.md`；v2 只声明阶段与产物的对应关系。
  4. 不实现 issue #3 的 `upgrade-workflow`。
  5. 不实现 P1-2 的 `warn/waiver`、P1-3 的 Review overlay、P2 的知识索引和
     BAR/Fix Pattern。
  6. 不新增服务端、数据库、常驻进程或第三方运行时依赖。
  7. 不改变 `approve`、`merge`、`unblock`、`rewind` 的人工属性和 MCP 边界。

## 3. 业务上下文

### 3.1 干系人与角色

| 角色 | 诉求 | 使用场景 | 责任边界 |
|---|---|---|---|
| 平台维护者 | 新流程只用声明文件定义，升级不复制状态机规则 | 新增团队流程、修正 Gate 组合、发布示范 profile | 维护核心解释器和 schema |
| 业务团队负责人 | 不改核心即可约束本团队的阶段、Gate 与上下文范围 | 重构、存量改造、合规专项流程 | 维护本仓库 profile 与说明 |
| 执行 Agent | 只读 `resume` 和 profile 快照就能知道下一步与约束 | 按 `next.action` 推进、读取 `context_bundle` | 不手改快照或状态文件 |
| 审计与合规 | 每次运行都能回答用了哪个 profile 版本和检查组合 | 复核 Gate 报告、追溯配置变更 | 只读审计，不代替人工确认 |

### 3.2 业务流程

1. 平台维护者新增或修改 `sdd/workflows/<name>.json`，本地运行
   `python -m sdd workflow validate --file <profile>`。
2. 创建 Spec 时 `--workflow <name>` 选择 profile；引擎校验后把完整 profile
   快照到 `docs/specs/<Spec>/workflow.json`，并把 name、version、digest 写入
   `state.json.workflow`。
3. 引擎按 profile 决定阶段推进、Gate 策略、检查项组合、人工检查点、风险停止
   规则和上下文范围；每一步仍由唯一状态机执行。
4. 旧 Spec 只读自己的快照；仓库 profile 升级不改变旧 Spec 的 digest、Gate
   结果或阶段序列。
5. `resume --json` 返回的 `context_bundle` 遵守当前 profile 的上下文规则。

### 3.3 业务规则

- BR-001：`sdd/scripts/sdd.py` 仍是唯一状态机；profile 只声明数据，不包含脚本。
- BR-002：profile 必须版本化、快照化、可计算 digest；旧 Spec 不随仓库预设漂移。
- BR-003：未知字段、未知检查 ID、非法阶段、非法人工动作必须显式失败，不能静默忽略。
- BR-004：强制级检查项不可被 profile 关闭；安全检查不可降级。
- BR-005：`approve` 和 `merge` 仍是所有人可读流程中固定的人工动作，profile 不能移除。
- BR-006：`schema: 1` 的旧快照必须继续通过校验，行为不变。
- BR-007：上下文规则只能缩小范围，不能让 Agent 读取其他 Spec、绝对路径或仓库外文件。
- BR-008：只使用 Python 标准库；不引入 YAML 解析器，profile 继续使用 JSON。

## 4. 功能需求与验收条件

### FR-001 Profile schema v2 与严格校验

- 功能描述：新增 schema 2 声明模型，覆盖阶段、产物、Gate、检查项、人工检查点、
  设计模式、审查要求、风险停止和上下文规则，并对未知字段逐路径报错。
- 用户场景：平台维护者新增团队流程时，只改一个 JSON 文件即可，不修改核心代码。
- 验收条件：
  - AC-001-1：Given 一个包含全部 v2 字段的合法 profile，When 执行校验，Then 返回 `ok=true` 并给出规范化 digest。【执行路径：本地单元测试】
  - AC-001-2：Given profile 含未知顶层或嵌套字段，When 执行校验，Then 返回 `ok=false`，错误包含字段路径且退出码非 0。【执行路径：本地单元测试】
  - AC-001-3：Given `schema: 1` 的既有快照，When 执行校验与 `check --all`，Then 行为与升级前一致，旧 Spec 的 digest 和 Gate 结果不变。【执行路径：本地单元测试】

### FR-002 阶段子序列与安全跳过

- 功能描述：允许 `stages` 是规范阶段序列的严格递增子序列，但必须从 `DRAFT`
  开始、以 `MERGED` 结束；引擎在推进时跳过未声明阶段，且不得跳过强制 Gate
  或人工检查点。
- 用户场景：某团队不需要独立的设计阶段时，可在 profile 中省略
  `DESIGN_READY`，但仍保留 G0/G1 与 Spec 人工确认。
- 验收条件：
  - AC-002-1：Given 省略 `DESIGN_READY` 的 profile，When 完成 Spec 并推进，Then 状态直接进入下一个已声明阶段，历史中不出现被省略阶段。【执行路径：本地单元测试】
  - AC-002-2：Given profile 试图跳过强制 Gate 或 `approve`/`merge` 检查点，When 执行校验，Then 明确拒绝并指出冲突字段。【执行路径：本地单元测试】
  - AC-002-3：Given 非法阶段顺序（重复、逆序、缺 `DRAFT` 或 `MERGED`），When 执行校验，Then 返回带索引的错误。【执行路径：本地单元测试】

### FR-003 gate_checks、human_checkpoints、risk_stop 与 context_rules 生效

- 功能描述：引擎按 profile 选择 Gate 检查项、声明人工检查点、合并风险停止标签，
  并把上下文规则应用到 `context_bundle`。
- 用户场景：重构流程只启用与行为保持相关的检查，并把知识目录纳入上下文，
  同时排除其他 Spec。
- 验收条件：
  - AC-003-1：Given profile 省略某条 advisory 检查但保留全部 required 检查，When 执行 Gate，Then 只运行声明的检查；若省略 required 检查则校验失败。【执行路径：本地单元测试】
  - AC-003-2：Given profile 声明额外人工检查点，When 到达该 Gate，Then `resume` 返回 `human_checkpoint.required=true` 且 Agent 不能自动完成。【执行路径：本地单元测试】
  - AC-003-3：Given profile 的 `risk_stop` 命中或 `context_rules` 包含/排除规则，When 生成 `context_bundle` 或评估风险，Then 标签合并、范围裁剪且不越界读取。【执行路径：本地单元测试】

### FR-004 workflow validate 命令

- 功能描述：新增 `python -m sdd workflow validate --file <profile>`，支持文本和
  `--json` 输出，错误定位到具体字段，成功时返回 name、version 和 digest。
- 用户场景：平台维护者在提交 profile 前本地校验，CI 也可直接调用。
- 验收条件：
  - AC-004-1：Given 合法 profile，When 运行 `python -m sdd workflow validate --file <path> --json`，Then 输出 `ok=true`、`name`、`version`、`digest`，退出码为 0。【执行路径：本地单元测试】
  - AC-004-2：Given 不存在或非 JSON 文件，When 运行命令，Then 输出可定位错误并以非 0 退出，不写入任何状态。【执行路径：本地单元测试】

### FR-005 l2-refactor 示范 profile 与兼容性

- 功能描述：新增 `sdd/workflows/l2-refactor.json`（schema 2），用于行为保持型
  改造；它声明与默认流程不同的检查组合和上下文规则，但不改核心代码。
- 用户场景：存量系统重构时选择 `--workflow l2-refactor`，得到更聚焦的检查与
  上下文，同时保留两个固定人工检查点。
- 验收条件：
  - AC-005-1：Given `l2-refactor` profile，When 创建 Spec，Then 快照写入该 profile，`state.workflow` 记录 name/version/digest，且流程可推进到 `PR_READY`。【执行路径：本地单元测试】
  - AC-005-2：Given 仓库新增 `l2-refactor` 并升级版本，When 校验旧 `SPEC-DEVTOOLS-002` 与 `SPEC-REQ-001`，Then 旧快照与 Gate 结果不变。【执行路径：本地单元测试 + `check --all`】
  - AC-005-3：Given profile 通过 `--workflow l2-refactor` 使用，When 运行 `check --all --stage ci --check-git`，Then 全部 Spec 通过。【执行路径：本地单元测试 + CI 集成测试】

## 4.1 UI规格（涉及前端UI时必填）

不涉及。

## 5. 边界与异常

| 场景类型 | 场景描述 | 关联FR/AC | 预期行为（错误码/降级策略/提示信息） |
|---|---|---|---|
| 边界场景 | profile 文件是合法 JSON 但不是对象 | FR-001；AC-001-2 | 报错 `$ 必须是 JSON 对象` |
| 边界场景 | 未知字段出现在 `gates` 或 `context_rules` 内 | FR-001；AC-001-2 | 报错到 `gates.<字段>` 或 `context_rules.<字段>` |
| 边界场景 | 阶段子序列跳过 `SPEC_READY` 但仍声明 `approve` 检查点 | FR-002；AC-002-2 | 报错人工检查点无法绑定到被省略阶段 |
| 边界场景 | `gate_checks` 漏掉 required 检查 | FR-003；AC-003-1 | 报错缺少的检查 ID，拒绝 profile |
| 边界场景 | `context_rules` 使用绝对路径或 `..` | FR-003；AC-003-3 | 报错并拒绝，防止越界读取 |
| 异常场景 | profile 文件不存在或 JSON 解析失败 | FR-004；AC-004-2 | 非 0 退出，输出路径和解析错误，不写状态 |
| 异常场景 | 旧 Spec 快照是 `schema: 1` | FR-001；AC-001-3 | 按 v1 规则校验，不强制迁移 |
| 异常场景 | 仓库 profile 内容变化但 version 未升级 | FR-005；AC-005-2 | 拒绝启动，提示升级 version 并重生成 manifest |

## 6. 非功能需求

| 类型 | 要求 | 指标/验收方式 | 关联FR/AC |
|---|---|---|---|
| 性能 | 单次 profile 校验只读一个 JSON 文件，不启动子进程 | 单元测试与代码评审；本地校验开销可忽略 | FR-001；FR-004 |
| 安全 | 不执行 profile 中的任何代码；上下文规则不能越出仓库 | 路径校验与负向测试 | FR-003；AC-003-3 |
| 可用性 | 错误信息包含字段路径和期望值，可直接修复 | 校验测试断言错误文本 | FR-001；FR-004 |
| 兼容性 | schema 1 快照继续可用，旧 Spec 不漂移 | 旧 Spec `check --all` 回归 | FR-001；AC-001-3 |
| 可维护性 | 新流程只改 profile，不改 `sdd/scripts/sdd.py` | `l2-refactor` 示范与代码评审 | FR-005；AC-005-1 |

## 7. 外部接口

| 方法 | 路径 | 用途 | 归属AC |
|---|---|---|---|
| CLI | `python -m sdd workflow validate --file <profile>` | 校验 profile 并输出结构化结果 | AC-004-1；AC-004-2 |
| CLI | `python -m sdd start-work --workflow <name>` | 选择并快照 profile | AC-005-1 |
| CLI | `python -m sdd resume --json` | 返回受 profile 约束的下一步与上下文包 | AC-003-2；AC-003-3 |
| CLI | `python -m sdd check --all --stage ci --check-git` | CI 校验全部 Spec 与 profile 快照 | AC-005-3 |

- 请求/响应示例：`workflow validate --json` 返回
  `{"ok": true, "name": "...", "version": 2, "digest": "..."}`。
- 契约文件：`sdd/workflows/*.json` 的 schema 2 由本 Spec 定义。

## 8. 数据模型

- 核心实体：Profile 仍是一个 JSON 对象，`schema` 从 1 扩展为 1 或 2。
- schema 2 顶层字段：

| 字段 | 类型 | 必填 | 规则 |
|---|---|---|---|
| `schema` | int | 是 | 必须为 2 |
| `name` | string | 是 | 小写字母、数字、短横线，且与文件名一致 |
| `version` | int | 是 | 正整数；内容变化必须升级 |
| `description` | string | 是 | 非空说明 |
| `stages` | string[] | 是 | 规范阶段的严格递增子序列，首 `DRAFT`、尾 `MERGED` |
| `artifacts` | object | 是 | 每个已声明阶段只能映射到该阶段规范产物名 |
| `gates` | object | 是 | G0–G5 全部存在，值为 `human/auto/auto_if_no_risk` |
| `required_gates` | object | 是 | 每个已声明阶段对应累计 Gate 列表 |
| `gate_checks` | object | 否 | Gate → 检查 ID 列表；必须包含该 Gate 的全部 required 检查 |
| `human_checkpoints` | object[] | 是 | 必须包含 `approve_spec` 与 `confirm_delivery`；可加 `complete_gate` |
| `design_mode` | string | 是 | `full` 或 `lite` |
| `review_required` | bool | 是 | 是否强制独立审查 |
| `risk_stop` | string[] | 否 | 追加的风险停止标签，与 `config.risk_stop` 取并集 |
| `context_rules` | object | 否 | `include`/`exclude` 相对 glob，禁止绝对路径与 `..` |

- 数据流：profile 校验 → 快照 `docs/specs/<Spec>/workflow.json` →
  `state.json.workflow` 记录 name/version/digest → 引擎按快照解释。
- 迁移方案：不迁移旧快照；schema 1 按原规则校验。

## 9. 约束与假设

- 技术约束：只使用 Python 标准库；profile 使用 JSON，不引入 YAML。
- 业务约束：正常流程仍只有 Spec 确认与交付确认两个计划内人工检查点；
  profile 只能增加 gate 级人工确认，不能移除这两个动作。
- 假设条件：规范阶段序列固定为
  `DRAFT → SPEC_READY → DESIGN_READY → TASKS_READY → IMPLEMENTING →
  VERIFYING → PR_READY → MERGED`。
- 假设条件：强制检查项以现有检查项注册表为准，profile 只能裁剪 advisory 项。

## 10. 变更历史

| 日期 | 版本 | 变更内容 | 作者 |
|---|---|---|---|
| 2026-11-23 | 1.0.0 | 初始版本 | SDD Agent |

> 本文件原地修改，以 Git 历史作为物理版本、元数据版本号作为语义版本；禁止创建平行版本文件。

## 11. AI能力规格

不适用。

## 12. 上下文与知识规格

- `context_rules` 是 profile 对 `context_bundle` 的附加约束，只做范围裁剪。
- 默认排除其他 Spec、全量 PRD、历史聊天和仓库外路径。
- 规则为空或未声明时沿用现有 `context_bundle` 行为，不新增必填文档。

## 13. 统计性验收标准

不涉及。

## 14. AI安全合规

不适用。

## 15. 成本与性能

不涉及。

## 16. 运行监控与效果度量

不涉及。

## 17. 自主程度与人机分工

- Agent 可编辑和校验 profile，但不能代替人执行 `approve`、`merge`、
  `unblock`、`rewind`。
- profile 声明的人工检查点由 CLI 强制返回 `human_checkpoint`，Agent 必须停止。

## 18. Agent行为规格

- Agent 新增流程时只新增或修改 `sdd/workflows/*.json`，不得复制阶段规则到脚本。
- Agent 必须用 `workflow validate` 校验 profile，再创建 Spec。
- Agent 不得手改 `workflow.json` 快照或 `state.json.workflow`。

## 19. 审计与回放

- 每个 Spec 的快照固定本次运行的 profile 内容；`state.json.workflow` 记录
  name、version、digest。
- Gate 报告继续绑定产物哈希；profile digest 变化必须伴随 version 升级。
- 旧 Spec 的快照和 digest 不因仓库 profile 升级而变化。

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
