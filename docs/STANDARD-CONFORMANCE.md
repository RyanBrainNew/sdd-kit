# SDD-L2 标准符合性映射

本文把官方 P0–P5 阶段与 G0–G5 Gate 映射到 sdd-kit 的当前实现。每个条目都给出
实现方式、证据位置、缺口和状态，便于平台维护者对外说明与审计核对。

## 1. 状态枚举

| 状态 | 含义 |
|---|---|
| 已自动 | 主要由 CLI 自动检查和推进，不需要额外人工动作 |
| 已人工 | 该阶段或 Gate 按当前工作流要求由人确认 |
| 部分实现 | 核心能力已落地，但官方条目中的部分能力仍缺失 |
| 未实现 | 当前没有对应实现 |

## 2. 映射表

| 条目 | 官方阶段/Gate | 实现方式 | 证据位置 | 缺口 | 状态 |
|---|---|---|---|---|---|
| P0 | REQUIREMENT / 需求侧准入 | `DRAFT → SPEC_READY`：G0 自动检查后由人执行 `approve --human` | `sdd/scripts/sdd.py` 的 G0-01…G0-07；`sdd/reports/<Spec>/gate0-report.md` | 无 | 已人工 |
| P1 | SPECIFY / Spec 准入 | G1 自动校验 Spec 章节、FR/AC 映射、AC 可测试性与占位符；Profile v2 可声明检查组合 | `sdd/scripts/sdd.py` 的 G1-01…G1-04；`gate1-report.md`；`workflow validate` | 技术栈 overlay 未实现 | 已自动 |
| P2 | PLAN / 设计评审 | `complete` 设计阶段执行 `check_design`；`auto_if_no_risk`，高风险转人工 | G2-01；`gate2-report.md` | Review overlay、按技术栈扩展的设计检查未实现 | 部分实现 |
| P3 | DECOMPOSE / 任务拆解 | `DESIGN_READY → TASKS_READY` 校验任务表、依赖 DAG、AC 与测试映射 | G3-01；`gate3-report.md` | 工时估算、并行调度冲突检查未实现 | 已自动 |
| P4 | IMPLEMENT / 代码审查 | 全部 Task 完成后校验任务完成、测试名可定位、AC 来自 `test_*` 函数体、中高风险 review | `submit-task` / `complete`；`verification.md` 的 Task 证据；G4-01…G4-03；`gate4-report.md` | Review overlay 未实现 | 部分实现 |
| P5 | VALIDATE / 规格验证 | `VERIFYING → PR_READY` 校验结构化命令证据、退出码、AC 覆盖和 Gate 报告 | `command_verify`；`verification.md` 的 Command/CWD/Exit/Head/Plan-Hash/At；G5-01…G5-03；`gate5-report.md` | Plan-Hash 尚未用于 Gate 比对 | 部分实现 |
| G0 | REQUIREMENT / 需求侧准入 | `approve --human` 前执行 G0 注册项，任一 required 失败即阻断 | G0-01…G0-07；`gate0-report.md` | 无 | 已人工 |
| G1 | SPECIFY / Spec 准入 | 自动执行 G1 注册项，失败时不允许进入设计阶段 | G1-01…G1-04；`gate1-report.md` | 技术栈专用检查未实现 | 已自动 |
| G2 | PLAN / 设计评审 | 设计阶段执行章节、AC 覆盖、方案与回滚检查；风险决定是否人工 | G2-01；`gate2-report.md` | 独立 Review overlay 未实现 | 部分实现 |
| G3 | DECOMPOSE / 任务拆解 | 任务阶段执行字段、AC 覆盖、依赖无环与测试映射检查 | G3-01；`gate3-report.md` | 工时估算与并行冲突检查未实现 | 已自动 |
| G4 | IMPLEMENT / 代码审查 | 全部 Task 完成后校验任务完成、Task 证据、测试名与 AC 映射；可豁免项支持范围化人工 waiver | G4-01…G4-03；`verification.md`；`gate4-report.md` | Review overlay 未实现 | 部分实现 |
| G5 | VALIDATE / 规格验证 | `sdd verify` 写结构化证据；校验 exit=0、空 test_commands、AC 覆盖与前置 Gate；G5-01 为不可豁免红线 | G5-01…G5-03；`verification.md`；`gate5-report.md` | Plan-Hash 尚未用于 Gate 比对 | 部分实现 |

## 3. 维护约定

- 文档引用的自动检查 ID 必须存在于 `sdd/scripts/sdd.py` 的 `CHECK_REGISTRY`。
- 新增或调整 Gate 检查时，同步更新本表、`sdd/agent-contract.md` 和测试。
- 状态变化必须基于代码事实；不能把“计划实现”写成“已自动”。
