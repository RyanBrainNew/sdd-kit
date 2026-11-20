# SDD-L2 执行内核 P0：标准符合性、上下文包与可复验证据规格说明书（Spec）

## 1. 元数据

| 项 | 内容 |
|---|---|
| Spec ID | SPEC-DEVTOOLS-002 |
| 工作项 ID | SDD-EPIC-007 |
| FEAT ID | FEAT-002 |
| 原始需求来源 | https://github.com/RyanBrainNew/sdd-kit/issues/7 |
| 作者 | SDD Agent |
| 创建日期 | 2026-11-20 |
| 状态 | Draft |
| 版本号 | 1.0.0 |
| 产品类型 | 传统产品 |
| 模板适配 | 标准 21 节模板；AI 能力相关章节标注不适用 |
| 关联人 | 产品负责人：RyanBrainNew；技术负责人：sdd-kit 平台维护者 |
| 原型版本 | 不涉及 |

## 2. 范围声明

- In-Scope：交付 issue #7 的 P0 阶段，补齐“合规可证”的三块能力，并保持现有轻量、CLI-first、两个计划内人工检查点的优势。
  1. 新增官方标准符合性映射，逐条说明 P0–P5 / G0–G5 在 sdd-kit 中的实现、证据、缺口和实现状态。
  2. 打通 FEAT 追溯链：Spec 元数据带 FEAT，PRD 索引提供可解析的“工作项 → FEAT → Spec → FR/AC”映射，G0 与 G1 分别输出稳定检查项。
  3. `resume --json` 的 `next` 增加按需生成的最小上下文包，让 Agent 只加载当前任务需要的 Spec、Design、契约和约束。
  4. G4/G5 只接受可复验证据：真实测试命令、退出码、测试名可定位、AC 不是裸标签、中高风险 Spec 有独立 review 证据。
  5. 同步核心测试、README、`sdd/README.md`、`sdd/agent-contract.md`、提示词、版本和 manifest。
- Out-of-Scope：不实现 issue #7 的 P1/P2，也不改变现有状态机阶段图、人工动作边界或部署形态。
  1. 不实现 Profile v2、`l2-refactor`、`workflow validate` 的完整自定义能力（P1-1）。
  2. 不实现 `warn`/人工豁免（waiver）分级治理和按检查 ID 的通过率统计（P1-2）；P0 只要求 `pass`/`block` 与稳定检查 ID。
  3. 不实现按需加载的技术栈 Review overlay（P1-3）。
  4. 不实现知识索引 `docs/knowledge/index.md`、BAR/Fix Pattern 闭环和回流指标（P2）。
  5. 不引入服务端、数据库、常驻守护进程、任意 DAG 编辑器或新的第三方运行时依赖。
  6. 不新增或改变 `approve`、`merge`、`unblock`、`rewind` 的人工属性，也不让 MCP 暴露这些动作。
  7. 不追溯重验已合并的历史 Spec；历史 Spec 不得因本次升级而漂移或失败。

## 3. 业务上下文

### 3.1 干系人与角色

| 角色 | 诉求 | 使用场景 | 责任边界 |
|---|---|---|---|
| 平台维护者 | 用一份可核对的映射回答“公司 P0–P5 / G0–G5 在 sdd-kit 里到底实现到什么程度” | 对外说明、内部审计、版本规划 | 维护核心、标准映射和发布 |
| 业务仓库开发者 | 用最少命令完成 Spec、实现和验证，不被新增检查拖慢 | clone 后直接 `resume`，按 `next.action` 执行 | 只维护业务配置、上下文和 Spec |
| 执行 Agent | 只读当前任务所需上下文，产出可被 CLI 复验的证据 | 每次会话恢复、实现 Task、提交验证 | 不越过人工检查点，不伪造证据 |
| 审计与合规 | 每个官方 Gate 都能定位到自动检查、人工动作、证据和缺口 | 版本验收、过程审计 | 只读审计，不代替业务确认 |

### 3.2 业务流程

1. 开发者给出工作项；Agent 运行 `resume`，拿到 `next.action` 和最小上下文包。
2. 写 Spec 时，Agent 从 PRD 索引取得 FEAT，并把 FEAT、FR、AC 写进 Spec 元数据和结构化映射。
3. 人类确认 Spec；G0 检查工作项、FEAT、澄清标记和映射，G1 检查 Spec 结构与 FR/AC；两组检查分别留痕。
4. Agent 按 `context_bundle` 实现 Task，只加载当前任务关联的 AC、Design 章节、契约、项目约束和允许范围。
5. Agent 提交 Task 时附真实测试命令与结果；G4 校验测试名可定位、AC 不是裸标签。
6. Agent 提交验证时，G5 校验命令退出码、证据哈希和风险对应的独立 review；没有成功命令证据不得 PASS。
7. 人类合并 PR；全过程仍只有 Spec 确认和 PR 合并两个计划内人工检查点。

### 3.3 业务规则

- BR-001：唯一状态机是 `sdd/scripts/sdd.py`；新增 Gate 检查、FEAT 规则和上下文生成都必须落在该状态机内，MCP 与文档不得复制规则。
- BR-002：`approve`、`merge`、`unblock`、`rewind` 只能由人执行；P0 不新增人工动作，也不改变人工检查点数量。
- BR-003：强制检查失败必须阻断流转；P0 不引入可降级的安全检查，也不允许用普通 `complete` 绕过。
- BR-004：没有新配置或新字段时，旧 Spec 的校验、Gate 报告和工作流快照保持可用；不得静默改变已合并 Spec 的结论。
- BR-005：证据必须来自真实执行或真实文件；文档中的 PASS 文本不能替代退出码、测试定位或 review finding。
- BR-006：上下文按需生成、默认排除无关材料；范围不明时显式提示，不静默扩大到其他 Spec、全量 PRD 或历史聊天。

## 4. 功能需求与验收条件

### FR-001 官方标准符合性映射

- 功能描述：提供一份可核对的《标准符合性映射》，把官方 P0–P5 阶段与 G0–G5 Gate 逐条映射到 sdd-kit 的实现方式、证据位置、缺口和实现状态。
- 用户场景：平台维护者对外说明合规程度，审计人员核对某个官方 Gate 是否已自动、已人工、部分实现或未实现。
- 验收条件：
  - AC-001-1：Given 标准符合性文档已交付，When 读者查看任一官方 Gate 条目，Then 该条目同时给出实现方式、证据位置、缺口和“已自动/已人工/部分实现/未实现”四选一状态。【执行路径：本地单元测试 + 人工评审】
  - AC-001-2：Given 标准符合性文档已交付，When 自动检查 P0–P5 与 G0–G5 条目，Then 12 个官方条目全部存在、无重复，且阶段说明与状态机当前映射一致。【执行路径：本地单元测试】
  - AC-001-3：Given 文档引用了自动检查 ID，When 运行校验，Then 每个 ID 都能在检查项注册表中找到；未知 ID 阻断。【执行路径：本地单元测试】

### FR-002 FEAT 追溯链

- 功能描述：让 FEAT 成为工作项、Spec、FR/AC 之间的稳定锚点；Spec 元数据声明 FEAT，PRD 索引提供结构化映射，检查逻辑解析表格而不是做全文包含判断。
- 用户场景：审计人员从任一 FR/AC 反查 FEAT 与工作项；平台维护者在多个 Spec 之间发现 FEAT 冲突或孤儿需求。
- 验收条件：
  - AC-002-1：Given 创建或更新 Spec，When 读取其元数据与 PRD 索引，Then Spec 含 FEAT ID 且与索引中该 Spec 行的 FEAT 完全一致。【执行路径：本地单元测试】
  - AC-002-2：Given Spec 缺少 FEAT、索引缺少对应行或 FEAT 与 Spec 不一致，When 运行 G0 检查，Then 返回 block 并指出缺失字段和不一致值。【执行路径：本地单元测试】
  - AC-002-3：Given 两个 Spec 行声明同一 FEAT，When 运行全量检查，Then 阻断并列出冲突的 FEAT 与两个 Spec。【执行路径：本地单元测试】
  - AC-002-4：Given Spec 中某个 FR 或 AC 未出现在该 FEAT 的结构化映射中，When 运行 G0/G1 检查，Then 阻断并列出孤儿 FR/AC 编号。【执行路径：本地单元测试】
  - AC-002-5：Given PRD 索引存在非零澄清标记、缺少 source/updated 元数据或表格不可解析，When 运行 G0 检查，Then 阻断并给出可定位到行或字段的错误。【执行路径：本地单元测试】
  - AC-002-6：Given FEAT 或 Spec ID 只出现在正文而不在结构化映射表，When 运行检查，Then 视为未登记并阻断。【执行路径：本地单元测试】
  - AC-002-7：Given 已合并（MERGED）且元数据没有 FEAT 的历史 Spec，When 运行全量检查，Then 以 legacy 模式通过并在报告中显式标注未启用 FEAT 映射，不阻断历史交付。【执行路径：本地单元测试】
  - AC-002-8：Given 新建或未合并的 Spec，When 元数据缺少 FEAT 或 PRD 索引未登记，Then 在 G0 阻断，不允许用 legacy 模式绕过。【执行路径：本地单元测试】

### FR-003 G0/G1 独立检查项与稳定 ID

- 功能描述：把 G0 与 G1 的检查项从固定文案升级为可枚举、可引用的注册项；即使同闸执行，也分别输出两组结果。
- 用户场景：审计人员按检查 ID 追踪某个阻断项；平台维护者在不改状态机阶段图的前提下新增或调整检查。
- 验收条件：
  - AC-003-1：Given 生成 G0 报告，When 查看检查项表，Then 每项包含稳定检查 ID、级别（强制/建议）、结果（pass/block）和证据。【执行路径：本地单元测试】
  - AC-003-2：Given G0 与 G1 在同一次人工确认中执行，When 查看两份报告，Then G0-xx 与 G1-xx 分别列出，不因合闸而省略任一组。【执行路径：本地单元测试】
  - AC-003-3：Given 任一强制检查项失败，When 记录 Gate，Then 总体结果为 block/FAILED，Spec 状态不推进。【执行路径：本地单元测试】
  - AC-003-4：Given 检查项注册表，When 校验注册项，Then 检查 ID 全局唯一，且每项都声明所属 Gate、触发方式、级别、可豁免性、证据要求和责任角色；重复 ID 或未知 Gate 阻断。【执行路径：本地单元测试】

### FR-004 最小上下文包

- 功能描述：在 `resume --json` 的 `next` 中返回 `context_bundle`，由当前状态按需生成，只包含当前任务所需的最小材料，不写状态、不新增必填文档。
- 用户场景：Agent 在实现 Task 时不再拉全量 PRD、其他 Spec 或历史聊天，只按包内路径和约束工作。
- 验收条件：
  - AC-004-1：Given 当前 Step 是实现 Task，When 运行 resume --json，Then next.context_bundle 包含 task、frs、acs、design_sections、contracts、project_constraints、fix_patterns、allowed_paths、exclude 九个字段。【执行路径：本地单元测试】
  - AC-004-2：Given 当前 Step 不是实现 Task，When 运行 resume --json，Then context_bundle 返回字段齐全的空结构且不报错。【执行路径：本地单元测试】
  - AC-004-3：Given 改动前的 next 已含 action、step_id、artifact、submit_with，When 对比改动后输出，Then 这些字段的名称与语义不变，且 resume 前后 state.json 与 events.jsonl 字节不变。【执行路径：本地单元测试 + 集成测试】
  - AC-004-4：Given 任务所需文件超出自定义允许范围，When 读取 context_bundle，Then 返回空 allowed_paths 或显式越界提示，不静默加载其他 Spec、全量 PRD 或历史聊天。【执行路径：本地单元测试】
  - AC-004-5：Given context_bundle 的 schema 文档，When 对照实际输出，Then 字段名、类型、空值表示和默认排除规则逐项一致，并有固定字段集合的快照测试。【执行路径：本地单元测试】

### FR-005 G4/G5 可复验证据

- 功能描述：让 G4/G5 只认可复验的测试与 review 证据；没有真实命令、成功退出码、可定位测试名或必要独立审查时，不得自动 PASS。
- 用户场景：审计人员复跑命令即可重现结论；平台维护者识别“文档写 PASS、实际没跑测试”的交付。
- 验收条件：
  - AC-005-1：Given 代码类变更的 test_commands 为空，When 运行 verify 或提交 verification，Then Gate 结果标记为 manual/unverified，Spec 不能自动进入 PR_READY。【执行路径：本地单元测试】
  - AC-005-2：Given 执行一条测试命令，When 命令结束，Then verification 证据记录命令、工作目录、退出码、关键输出和对应产物哈希。【执行路径：本地单元测试】
  - AC-005-3：Given verification 写了 PASS 但没有退出码为 0 的真实命令证据，When 运行 check 或 submit，Then 阻断并指出缺失的命令或退出码。【执行路径：本地单元测试】
  - AC-005-4：Given Task 表写了测试文件中不存在的测试类或方法，When 运行 G4/G5 检查，Then 阻断并列出无法定位的测试名。【执行路径：本地单元测试】
  - AC-005-5：Given 测试文件只有 AC 标签而没有对应测试用例，When 计算 AC 覆盖，Then 该 AC 视为未覆盖并阻断。【执行路径：本地单元测试】
  - AC-005-6：Given 中风险或高风险 Spec，When 缺少结构化独立 review 证据，Then G5 阻断并指出缺失的 finding 字段。【执行路径：本地单元测试】
  - AC-005-7：Given 低风险 Spec 按 l2-standard 完成真实测试，When 提交 verification，Then 流程与现状一致，不新增人工检查点或额外日常命令。【执行路径：本地单元测试 + 集成测试】
  - AC-005-8：Given 任一 test_command 退出码非 0，When 提交 verification，Then G5 阻断，文档中的 PASS 文本不能让结果通过。【执行路径：本地单元测试】
  - AC-005-9：Given 已合并（MERGED）的历史 Spec，When 运行全量检查，Then 不被新增证据规则追溯阻断，并保留原有 Gate 报告结论。【执行路径：本地单元测试】
  - AC-005-10：Given 新建或未合并的 Spec，When 提交 verification，Then 必须满足新增证据规则，不能用历史 Spec 的 legacy 模式绕过。【执行路径：本地单元测试】

## 5. 边界与异常

| 场景类型 | 场景描述 | 关联FR/AC | 预期行为（错误码/降级策略/提示信息） |
|---|---|---|---|
| 边界场景 | 已合并的历史 Spec 没有 FEAT 元数据 | FR-002；AC-002-7 | 以 legacy 模式通过，报告显式标注；不修改历史 Spec，不重开 Gate |
| 边界场景 | 旧 PRD 索引只有扁平表、没有 FR/AC 映射 | FR-002；AC-002-5 | 对新建 Spec 阻断并给出迁移提示；对已合并 Spec 保留 legacy 校验 |
| 边界场景 | 当前 Step 不是实现 Task | FR-004；AC-004-2 | 返回字段齐全的空 `context_bundle`，不报错，不推断任务 |
| 边界场景 | design 没有可解析的“影响范围”或 Task 未给出文件 | FR-004；AC-004-4 | `allowed_paths` 返回空数组并附范围提示；不把空数组解释为“可改全仓库” |
| 边界场景 | 低风险 Spec 使用 l2-standard | FR-005；AC-005-7 | 不增加人工检查点；只要求真实测试与可定位测试名 |
| 异常场景 | test_commands 为空且没有手工命令证据 | FR-005；AC-005-1 | Gate 标记 manual/unverified；不得推进到 PR_READY |
| 异常场景 | 测试命令退出码非 0 | FR-005；AC-005-8 | G5 阻断；记录失败命令、目录、退出码和输出 |
| 异常场景 | Task 表写了不存在的测试名 | FR-005；AC-005-4 | 阻断并列出无法定位的测试名；不得用裸 AC 标签代替 |
| 异常场景 | 中高风险 Spec 缺少独立 review | FR-005；AC-005-6 | G5 阻断并列出缺失字段；不能以“无发现”空白代替 |
| 异常场景 | PRD 索引表格格式损坏 | FR-002；AC-002-5 | 阻断并给出首个不可解析行；不得退化为全文包含判断 |

## 6. 非功能需求

| 类型 | 要求 | 指标/验收方式 | 关联FR/AC |
|---|---|---|---|
| 依赖 | 只使用 Python 标准库，MCP 依赖继续隔离 | 核心导入检查；不新增运行时依赖 | FR-001；AC-001-2 |
| 兼容 | 旧 Spec、旧 Gate 报告、旧工作流快照继续可读 | `check --all --stage ci` 在历史 Spec 上保持通过 | FR-002；AC-002-7 |
| 性能 | `resume` 只读且快速；`context_bundle` 不读取全量 PRD | 在仓库测试夹具上不执行测试命令；不新增网络访问 | FR-004；AC-004-3 |
| 安全 | 不把 Token、内网地址、其他 Spec 或历史聊天注入上下文包 | 上下文包路径白名单与排除列表测试 | FR-004；AC-004-4 |
| 可维护性 | 检查 ID 稳定、注册项集中、报告可引用 | 注册表唯一性与报告快照测试 | FR-003；AC-003-4 |
| 可操作性 | 新增阻断项给出可执行的修复提示 | 阻断错误包含字段、行或修复动作 | FR-005；AC-005-3 |

## 7. 外部接口

| 接口 | 方向 | 用途 | 归属AC |
|---|---|---|---|
| `resume --json` 的 `next.context_bundle` | CLI → Agent | 返回当前任务最小上下文包 | AC-004-1 |
| Gate 报告检查项表 | CLI → 审计 | 输出稳定检查 ID、结果与证据 | AC-003-1 |
| PRD 索引结构化映射表 | 仓库文件 → CLI | 提供工作项、FEAT、Spec、FR/AC 映射 | AC-002-1 |
| verification 命令证据 | CLI → 仓库文件 | 记录命令、目录、退出码、输出与哈希 | AC-005-2 |

- 请求/响应示例：不涉及网络接口；上述接口均为 CLI JSON 或仓库内 Markdown 表格。
- 契约文件：`sdd/context/contracts/` 保持只读输入；本次不新增外部契约。

## 8. 数据模型

- `context_bundle` 是只读 JSON 对象，字段固定为：`task`（对象或 null）、`frs`（字符串数组）、`acs`（字符串数组）、`design_sections`（章节标题数组）、`contracts`（路径数组）、`project_constraints`（约束数组）、`fix_patterns`（数组，P0 固定为空）、`allowed_paths`（路径数组，空数组表示范围未知）、`exclude`（路径与类别数组）。
- 检查项注册表每条记录包含：检查 ID、所属 Gate、触发方式、级别、是否可豁免、证据要求、责任角色。P0 只使用强制/建议与 pass/block，不实现豁免动作。
- PRD 索引保留现有扁平行，并新增可解析的 `FEAT 映射` 表：工作项、FEAT、Spec、FR、AC。FEAT 与 Spec 在映射中必须唯一；FR/AC 必须能在 Spec 中找到。
- verification 证据记录包含：命令、工作目录、退出码、关键输出摘要、执行时间和绑定的产物哈希。
- 不新增持久化数据库；所有新事实仍以 Markdown、JSON 和 Git 历史为权威源。

## 9. 约束与假设

- 技术约束：只使用 Python 标准库；不引入服务端、数据库、常驻进程或第三方包。
- 技术约束：`sdd/scripts/sdd.py` 仍是唯一状态机；`sdd/core.py` 只做编排，MCP 只做适配。
- 业务约束：人工动作与两个计划内人工检查点不变；中高风险 Spec 的独立 review 是 Gate 证据，不是新的人工仪式。
- 兼容约束：新增 FEAT 与证据规则只对新建或未合并 Spec 强制；已合并历史 Spec 走 legacy 校验并在报告中显式标注。
- 兼容约束：旧的 Gate 报告、工作流快照、`state.json` 字段保持可读；不要求业务仓库迁移既有 Spec。
- 假设条件：issue #7 的 P0 范围已由人类确认；P1/P2 另立 Spec，不在本 PR 中实现。
- 假设条件：`docs/prd-index.md` 是工作项与 FEAT 的权威索引；PRD 全文仍留在工作项系统。

## 10. 变更历史

| 日期 | 版本 | 变更内容 | 作者 |
|---|---|---|---|
| 2026-11-20 | 1.0.0 | 初始版本，承接 issue #7 的 P0 范围 | SDD Agent |

> 本文件原地修改，以 Git 历史作为物理版本、元数据版本号作为语义版本；禁止创建平行版本文件。

## 11. AI能力规格

不适用（传统产品）；本次不调用大模型，只调整执行内核的校验与上下文生成。

## 12. 上下文与知识规格

本次交付 `context_bundle` 的最小上下文协议，但不建设知识库或 RAG；P2 的知识索引与 Fix Pattern 不在范围内。

## 13. 统计性验收标准

不涉及（全部验收条件为确定性行为，可用单元测试或人工评审判定）。

## 14. AI安全合规

不适用（传统产品）；上下文包仍需遵守“不加载其他 Spec、全量 PRD 和历史聊天”的边界。

## 15. 成本与性能

不涉及按 Token 计费；性能约束见第 6 节，重点是 `resume` 保持只读、快速、无网络访问。

## 16. 运行监控与效果度量

本期以 Gate 报告、`inbox` 和 `metrics` 的现有字段作为可观测信号；warn/waiver 统计属于 P1-2。

## 17. 自主程度与人机分工

不适用（仅 AI 原生·L4 产品填写）；本仓库的人机分工仍以 `sdd/agent-contract.md` 为准。

## 18. Agent行为规格

不适用（仅 AI 原生·L4 产品填写）；Agent 仍按 `next.action` 执行，遇到人工检查点停止。

## 19. 审计与回放

不适用（仅 AI 原生·L4 产品填写）；审计信息由 Gate 报告、事件流和产物哈希承载。

## 20. 多智能体协同

不涉及（本次为单 Agent 执行内核改造，不引入多智能体编排）。

## 21. 自检清单（评审辅助，不作Gate依据）

- [x] Spec ID 格式正确，并与目录名一致。
- [x] 工作项 ID 存在且不含前导 `%`。
- [x] FEAT ID 已声明，并与 `docs/prd-index.md` 的 FEAT-002 一致。
- [x] In-Scope 和 Out-of-Scope 均已明确填写。
- [x] FR/AC 编号唯一、稳定，每个 FR 至少包含一条 AC。
- [x] 每条 AC 包含可判定的 Given/When/Then 和执行路径。
- [x] 边界、异常、非功能需求、接口、数据模型和约束均已填写或明确不涉及。
- [x] 残留澄清标记为 0。
- [x] 变更历史已更新，未创建平行版本文件。
