# 标准符合性与核心优势基线

> 适用版本：`sdd-kit 0.9.9`  
> 对齐依据：集团《SDD 开发规范 v1.0.3》培训口径、P0–P5 / G0–G5 六阶段门禁，
> 以及面向全国专业公司培训中的 SDD In Action v7 实践。  
> 结论边界：本文证明 `sdd-kit` 已覆盖 SDD-L2 执行内核的强制路径与证据链；
> 不宣称替代公司的正式认证，也不宣称已完成 L3 四层校验或 L4 Agentic Engineering。

## 1. 阅读规则

状态只使用以下四个值：

| 状态 | 含义 |
|---|---|
| 已自动 | CLI 或 Agent 能自动执行，并产生可复核证据；需要人工签署时会单独标出 |
| 已人工 | 最终动作按规范必须由人执行，CLI 只做前置校验和留痕 |
| 部分实现 | L2 强制路径可用，但更深层的语义校验、平台能力或增强项尚未实现 |
| 未实现 | 当前版本没有对应能力 |

每一项都写出内部动作、证据位置、责任角色和缺口。  
“已自动”不等于“Agent 可以代替人审批”；`approve`、`merge`、`unblock`、
`rewind` 和 Gate 豁免始终是人工动作。

## 2. P0–P5 官方阶段映射

| 条目 | 官方阶段/Gate | 实现方式 | 证据位置 | 缺口 | 状态 |
|---|---|---|---|---|---|
| P0 | REQUIREMENT / 需求侧准入 | `start-work` 建 Spec；G0 自动校验工作项、FEAT、PRD 来源和澄清标记，人执行 `approve --human` | `docs/prd-index.md`、`spec.md`、`gate0-report.md`、`events.jsonl` | 无；业务判断仍由产品负责人完成 | 已人工 |
| P1 | SPECIFY / Spec 准入 | `approve` 内执行 G1；检查章节、FR/AC 闭合、AC 可测试性、占位符和审批摘要绑定 | `spec.md`、G1-01–G1-09、`gate1-report.md` | 无 | 已自动 |
| P2 | PLAN / 设计评审 | `complete` 设计阶段执行 G2；检查 Design 章节、AC 落点、风险与回滚 | `design.md`、`decisions.md`、G2-01–G2-04、`gate2-report.md` | ADR/OpenAPI 未做语义级自动审查 | 部分实现 |
| P3 | DECOMPOSE / 任务拆解 | `DESIGN_READY → TASKS_READY` 校验任务表、依赖 DAG、测试定位和知识资产 | `tasks.md`、G3-01–G3-06、`gate3-report.md` | 任务粒度仍由人设定 | 已自动 |
| P4 | IMPLEMENT / 代码审查 | `start`/`submit-task` 逐 Task 推进；最后一个 Task 完成时执行 G4，校验证据、测试定位与独立 Review | `verification.md`、`verification-evidence.jsonl`、G4-01–G4-05、`gate4-report.md` | 人工 Review 质量仍取决于 Reviewer | 已自动 |
| P5 | VALIDATE / 规格验证 | `verify` 记录真实命令；G5 校验退出码、AC 覆盖、Gate 链、事件哈希与豁免 | `verification.md`、`verification-evidence.jsonl`、G5-01–G5-10、`gate5-report.md` | 未实现自动语义漂移判定 | 部分实现 |
| G0 | REQUIREMENT / 需求侧准入 | `approve --human` 前执行 G0 注册项，任一 required 失败即阻断 | G0-01–G0-07、`gate0-report.md` | 无 | 已人工 |
| G1 | SPECIFY / Spec 准入 | 自动执行 G1 注册项，失败时不允许进入设计阶段；审批后摘要变化由 G1-08/G1-09 阻断 | G1-01–G1-09、`gate1-report.md` | 无 | 已自动 |
| G2 | PLAN / 设计评审 | 设计阶段执行章节、AC 覆盖、方案与回滚检查；风险决定是否人工 | G2-01–G2-04、`gate2-report.md` | Review overlay 主要在 G4/G5 生效，G2 仍以设计文档为主 | 部分实现 |
| G3 | DECOMPOSE / 任务拆解 | 任务阶段执行字段、AC 覆盖、依赖无环与测试映射检查 | G3-01–G3-06、`gate3-report.md` | 工时估算与并行冲突检查未实现 | 已自动 |
| G4 | IMPLEMENT / 代码审查 | 校验测试名、AC 覆盖、可复验测试证据与必要的独立 review 证据 | G4-01–G4-05、`gate4-report.md`、`review-findings.json` | Review 结论仍需人判断 | 已自动 |
| G5 | VALIDATE / 规格验证 | `sdd verify` 写结构化证据；G5 校验 exit=0、AC 覆盖、豁免与审计事件链 | G5-01–G5-10、`gate5-report.md`、`verification-evidence.jsonl` | Plan-Hash 已记录，但尚未用于自动漂移比对 | 部分实现 |

### 2.1 阶段与门禁详细视图

| 官方阶段 | 官方核心产出 | 状态 | `sdd-kit` 内部动作 | 证据 | 责任角色 | 缺口说明 |
|---|---|---|---|---|---|---|
| P0 Requirement 需求分析 | `prd-index`、FEAT、澄清标记清零 | 已人工 | `start-work` 建 Spec；G0 校验工作项、FEAT、PRD 来源和 `[NEEDS CLARIFICATION]` | `docs/prd-index.md`、`spec.md`、G0 报告、`events.jsonl` | 产品负责人 + 执行 Agent | 无；业务判断仍由产品负责人完成 |
| P1 Specify 规格定义 | Spec、FR、AC、FEAT 映射 | 已自动 | Agent 生成 `spec.md`；`submit`/`approve` 执行 G0/G1；AC 必须可测试并闭合到 FR | `spec.md`、G1 报告、AC 追溯检查 | 需求负责人 + 独立评审者 | 无 |
| P2 Plan 方案制定 | Design、ADR、接口契约 | 部分实现 | `submit design.md` 执行 G2；模板检查章节、AC 覆盖、风险与回滚；契约文件从上下文读取 | `design.md`、`decisions.md`、`sdd/context/contracts/`、G2 报告 | 技术负责人 + 执行 Agent | ADR/OpenAPI 目前以模板和文件落位，未做接口语义级自动校验 |
| P3 Decompose 任务拆解 | Task 清单、依赖、测试映射 | 已自动 | `submit tasks.md` 执行 G3；检查字段、AC 覆盖、依赖 DAG、测试定位和知识资产 | `tasks.md`、G3 报告、任务测试定位结果 | 技术负责人 + 执行 Agent | 任务粒度仍由人设定；经验值不是强制门槛 |
| P4 Implement 代码实现 | 业务代码、测试代码、提交记录 | 已自动 | `start`/`submit-task` 逐 Task 推进；代码类变更必须有成功测试证据；G4 检查 Review | Task 状态、`verification-evidence.jsonl`、G4 报告、Commit trailer | 执行 Agent + 独立评审者 | 不代替人做业务取舍；最终合并仍由人完成 |
| P5 Validate 规格验证 | 验证报告、Spec 漂移清单 | 部分实现 | `verify` 记录真实命令；G5 检查证据、AC 覆盖、Gate 链和事件哈希 | `verification.md`、`verification-evidence.jsonl`、G5 报告、`events.jsonl` | 质量负责人 + 执行 Agent | 已覆盖可执行证据与人工 Review，但没有自动语义 diff 引擎判断所有 Spec 漂移 |

| 官方 Gate | 官方含义 | 状态 | `sdd-kit` 执行动作 | 检查与证据 | 人工节点 | 缺口说明 |
|---|---|---|---|---|---|---|
| G0 需求侧准入 | P0 出口 | 已人工 | 人执行 `approve --human`；CLI 先自动校验 PRD、FEAT、工作项和澄清标记 | `G0-01`–`G0-07`、`gate0-report.md`、approval 记录 | Spec 确认 | 无（需要产品负责人给出业务判断） |
| G1 Spec 准入 | P1 出口 | 已自动 | `approve` 内执行 G1；检查章节、FR/AC 闭合、可测试性、占位符和审批摘要绑定 | `G1-01`–`G1-09`、`gate1-report.md` | 与 G0 同一人工检查点；范围变化时另有 `reapprove` | 无（正常流程不额外增加人工停止点） |
| G2 设计评审 | P2 出口 | 部分实现 | `submit design.md` 执行 G2；检查 Design、AC 落点、风险与回滚 | `G2-01`–`G2-04`、`gate2-report.md` | 高风险或 `l2-strict` 时人工 | ADR 与 OpenAPI 尚未做语义级自动审查 |
| G3 任务拆解 | P3 出口 | 已自动 | `submit tasks.md` 执行 G3；检查字段、DAG、测试映射和知识资产 | `G3-01`–`G3-06`、`gate3-report.md` | 无额外计划内节点 | 任务规模经验值由团队自行约束 |
| G4 代码审查 | P4 出口 | 已自动 | 最后一个 Task 完成时执行 G4；检查 Task 证据、Review finding 和测试定位 | `G4-01`–`G4-05`、`gate4-report.md`、`review-findings.json` | PR Review / 合并 | 人工 Review 质量仍取决于 Reviewer；工具只校验证据结构 |
| G5 规格验证 | P5 出口 | 部分实现 | `verify` 写 JSONL；`complete` 执行 G5；检查真实退出码、AC 覆盖、Gate 链与事件哈希 | `G5-01`–`G5-10`、`gate5-report.md`、`verification-evidence.jsonl` | PR 合并 | 未实现自动语义漂移判定；漂移清单仍需 Review 和人工判断 |

## 3. G0–G5 官方门禁映射

每个 Gate 都有稳定检查 ID、结构化 `pass/warn/block/waived` 结果、产物哈希和
`gate_result` 审计事件。`l2-standard` 的两个计划内人工检查点是 Spec 确认与 PR 合并；
`l2-strict` 可把 G0–G5 全部设为人工签署。

### 3.1 六个公司骨架的落点

| 公司骨架 | 对应阶段 | 实现位置 | 当前状态 |
|---|---|---|---|
| `spec.md` | P0/P1 | `sdd/templates/spec.md` | 已自动 |
| `design.md` / `design-lite.md` | P2 | `sdd/templates/design.md`、`design-lite.md` | 已自动 |
| `tasks.md` | P3 | `sdd/templates/tasks.md` | 已自动 |
| `decisions.md` | P2 | `sdd/templates/decisions.md` | 已人工 |
| `gates.md` | G0–G5 | `sdd/templates/gates.md` + CLI 自动追加 | 已自动 |
| `verification.md` / `verification-strict.md` | P5 | `sdd/templates/verification*.md` | 已自动 |

## 4. 三项核心优势基线

| 核心优势 | 指标 | 目标值 | 采集方式 | 当前结果（0.9.9） |
|---|---|---|---|---|
| 轻量、使用简单 | 核心第三方依赖数 | 0 | 检查 `sdd/scripts/*.py` 只导入标准库；MCP 依赖只在可选目录 | 0 |
| 轻量、使用简单 | 核心常驻服务/数据库 | 0 | 架构检查：CLI 直接读写仓库内文件 | 0 |
| 轻量、使用简单 | 每仓库 bootstrap 次数 | 1 次 | 平台团队执行一次 `bootstrap.py` 后，开发者 clone 即用 | 1 次 |
| 轻量、使用简单 | 开发者必记命令数 | 2 个 | Spec 确认 `approve`、PR 合并 `merge`；其余由 Agent 执行 | 2 个 |
| 可轻松自定义 | 声明式工作流数量 | ≥ 4 | 统计 `sdd/workflows/*.json` | 4 个：`l2-standard`、`l2-hotfix`、`l2-strict`、`l2-refactor` |
| 可轻松自定义 | 新增工作流所需核心代码改动 | 0 行 | 只用 Profile JSON + `workflow validate` | 0 行；`l2-refactor` 已验证 |
| 可轻松自定义 | Profile 校验覆盖 | 100% 未知字段/阶段/检查 ID/空检查集显式失败 | `python -m sdd workflow validate --file ... --json` | 100% |
| 可轻松自定义 | 旧 Spec 快照稳定性 | 100% | 创建 Spec 后修改预设，旧 Spec 仍读 `workflow.json` | 100% |
| 合规可溯源 | P0–P5 / G0–G5 映射覆盖 | 12/12 | 本文两张映射表 | 12/12 |
| 合规可溯源 | Gate 结构化结果 | 100% 带稳定检查 ID | `python -m sdd check ... --json`、Gate 报告 | 100% |
| 合规可溯源 | 新事件哈希链 | 100% 新事件可验证 | `python -m sdd events --spec <spec> --json` 的 `audit.valid` | 100%（旧事件标记为 `legacy_events`） |
| 合规可溯源 | 验证证据字段 | 命令、目录、时间、退出码、耗时、输出哈希、产物哈希 | `verification-evidence.jsonl` | 全部字段已记录 |
| 合规可溯源 | 质量回流指标 | 豁免率、逃逸缺陷、重开率、Gate 一次通过率 | `python -m sdd metrics --json` | 4 项均有口径与来源 |

“当前结果”由 0.9.9 的自动测试与 CLI 输出得出；人员能力、业务判断和
组织审批效率不在工具可承诺的范围内。

## 5. 可复核证据索引

| 能力 | 证据入口 | 复核方式 |
|---|---|---|
| 唯一状态机与 Gate | `sdd/scripts/sdd.py` | `python -m sdd verify-core` |
| Gate 检查注册表 | `sdd/scripts/sdd_ext.py` | `python -m unittest tests.test_evolution.GateRegistryTests -v` |
| 上下文包 | `resume --json` / `next --json` | `python -m unittest tests.test_evolution.ContextBundleTests -v` |
| 可复验测试证据 | `verification-evidence.jsonl` | `python -m unittest tests.test_evolution.EvidenceTests -v` |
| 声明式工作流 | `sdd/workflows/` | `python -m unittest tests.test_evolution.ProfileTests -v` |
| 检查分级与人工豁免 | `state.json.waivers`、`events.jsonl` | `python -m unittest tests.test_evolution.WaiverTests -v` |
| 审批版本绑定与 change-set | `state.json.approved_spec_digest`、`change-set.md` | `python -m unittest tests.test_governance.ApprovalBindingTests tests.test_governance.ChangeSetTests -v` |
| 全量 commit 审计与 trace | `check --check-git`、`sdd trace --json` | `python -m unittest tests.test_trace.CommitAuditTests tests.test_trace.TraceTests -v` |
| Review overlay | `sdd/prompts/review/` | `python -m unittest tests.test_evolution.ReviewTests -v` |
| 知识基线与 Fix Pattern | `docs/knowledge/` | `python -m unittest tests.test_evolution.KnowledgeTests -v` |
| 指标与审计回放 | `metrics --json`、`events --json` | `python -m unittest tests.test_evolution.MetricsTests.test_metrics_and_audit -v` |
| Agent 单动作循环 | `sdd/agent-contract.md`、`sdd/prompts/` | `python -m sdd resume --json` 与 CI 校验 |

`docs/specs/SPEC-DEVTOOLS-002/workflow.json` 保留创建时的 `l2-standard@1` schema 1
快照，用于验证“旧 Spec 不随预设漂移”；`sdd/workflows/l2-refactor.json` 是 schema 2
的示例，不代表历史 Spec 会被自动升级。

在 G5-03 引入前已经完成合并的旧 Spec，如果没有 `verification-evidence.jsonl`，
CI 保留其历史结论，不追溯补证；新 Spec 和所有未合并 Spec 仍强制执行 G5-03。

## 6. 已知缺口与非目标

以下能力没有在本版本中冒充“已实现”：

1. 不提供企业级 Ontology、全量 SSOT 平台或自动业务决策；当前使用最小知识索引。
2. 不自动生成或语义校验所有 ADR/OpenAPI；当前通过模板、上下文文件和 Review 约束。
3. 不提供完整的 Spec 漂移语义 diff 引擎；当前提供验证证据、AC 覆盖和人工 Review。
4. 不提供数据库、服务端控制面、Web 审批台或常驻守护进程。
5. 不实现 L3 四层校验、L4 自主生成 Spec 和沙箱规范引擎。
6. 旧版本 `events.jsonl` 可能没有哈希字段；读取时标记为 legacy，新事件必须进入哈希链。
   如果旧文件中段在已有哈希事件之后出现无哈希事件（例如被手工删改），整条链会判
   `invalid`，必须从审计事件源头修复，不能把该情况当作可忽略的 legacy 前缀。

这些缺口在 `l2-standard` 下不会静默通过：需要人工判断的事项会明确进入
`inbox`、Review 或 PR 合并检查点。
