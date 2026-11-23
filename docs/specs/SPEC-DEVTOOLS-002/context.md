# 需求上下文

- Work item: `SDD-GH-007`
- FEAT: `FEAT-002`
- Issue: https://github.com/RyanBrainNew/sdd-kit/issues/7

## 原始需求

实现 Issue #7：在不扩展为重平台的前提下，补齐标准符合性、G0/FEAT 追溯、
最小上下文包、G4/G5 可复验证据、声明式工作流、检查分级与豁免、
按需 Review overlay、最小知识基线和 BAR/Fix Pattern 闭环。

## 调研事实

- 集团培训材料强调输入可信、生成受控、验证可证、错误能回流；阶段数量不是主要难点。
- 专业公司 v7 提供了 P0–P5、G0–G5、FEAT/FR/AC、Gate 证据、技能库和技术栈 Review 参考，
  但其模板与工具包体量不适合原样复制。
- `sdd/scripts/sdd.py` 当前已是唯一状态机；`approve` 已校验 Spec 与 PRD 索引登记，
  但尚未把 FEAT 写入 Spec 元数据，也未把 G0/G1 拆成独立检查项报告。
- `sdd/config.json` 的 `test_commands` 当前为空；G4/G5 仍允许主要依赖任务表和 AC 文本，
  不能证明测试真实执行。
- `resume --json` 当前返回 `next`、`context`、`specs` 等状态，没有面向当前 Task 的
  `context_bundle`。
- 现有 workflows 是 `l2-standard`、`l2-hotfix`、`l2-strict` 预设；Profile 尚无独立
  校验命令、检查项组合和上下文规则。
- 现有 MCP 边界不暴露 `approve` 等人工动作；新增豁免能力必须保持同一隔离。
- 现有事件、Gate 报告和 manifest 可作为审计基础；不新增数据库或服务端。

## 设计约束

- 核心运行时只使用 Python 标准库。
- 不改变 `sdd/scripts/sdd.py` 的唯一状态机地位。
- `l2-standard` 保持两个计划内人工检查点。
- 旧 Spec 必须继续使用创建时的 Profile 快照。
