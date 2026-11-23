# ADR-002: 状态机与纯函数扩展的边界

## Status

Accepted

## Context

本 Spec 需要增加 Profile 校验、检查注册表、证据解析、Review finding、
知识索引、Fix Pattern 和指标。若把这些逻辑继续堆入 `sdd/scripts/sdd.py`，
会放大单文件复杂度；若拆成独立工作流引擎，又会形成第二套阶段规则。

## Decision

- 阶段迁移、Gate 编排、人工动作和 CLI 命令继续只存在于 `sdd/scripts/sdd.py`。
- 新增 `sdd/scripts/sdd_ext.py`，只接收文本或 JSON 并返回结构化结果。
- `sdd_ext.py` 不读取或写入 `state.json`，不调用 `transition`，不决定下一状态。
- Profile 只能从注册表选择检查项，不能注入脚本或新增阶段。

## Consequences

- 扩展逻辑可以独立单元测试，状态机仍只有一个权威实现。
- 新增纯函数模块必须加入 manifest 和 `verify-core` 保护范围。
- 任何需要修改阶段规则的变更仍必须回到 `sdd.py` 评审，不能藏在 Profile 中。
