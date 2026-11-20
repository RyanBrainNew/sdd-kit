# `context_bundle` 上下文包

`python -m sdd resume --json` 和 `python -m sdd next --json` 的 `next.context_bundle`
是执行 Task 时的最小只读上下文。它由 `sdd/scripts/sdd.py` 按需计算，不落盘，
不修改 `state.json` 或 `events.jsonl`。

## 字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `task` | object \| null | 当前 Task：`id`、`description`、`status` |
| `frs` | string[] | 当前 Task 关联的 FR |
| `acs` | string[] | 当前 Task 关联的 AC |
| `design_sections` | object[] | 需要阅读的 Design 章节：`heading`、`reason` |
| `contracts` | string[] | Design 声明的契约文件与 `sdd/context/contracts/` 下的文件 |
| `project_constraints` | object[] | 仓库约束文件：`path`、`scope`，至少包含 `AGENTS.md` |
| `fix_patterns` | object[] | 历史修复模式；P0 固定为空数组 |
| `allowed_paths` | string[] | 由 Design 影响范围、契约文件和 Task 测试/命令派生的允许范围 |
| `exclude` | string[] | 明确不注入的内容：其他 Spec、全量 PRD、运行时目录、历史聊天 |

固定字段集合为上述 9 个。新增字段属于契约变更，必须同步本文、测试和版本。

## 空结构

非 Task 步骤（写 Spec、写 Design、写 Tasks、验证、开 PR、已合并等）返回：

```json
{
  "task": null,
  "frs": [],
  "acs": [],
  "design_sections": [],
  "contracts": [],
  "project_constraints": [],
  "fix_patterns": [],
  "allowed_paths": [],
  "exclude": []
}
```

`next.action`、`next.step_id`、`next.artifact`、`next.submit_with` 等原有字段语义不变。

## 范围语义

- `allowed_paths` 为空数组表示“范围未知”，不等于“全仓库可改”。
- `allowed_paths` 不应包含其他 Spec 的文件，也不包含 `docs/prd.md`。
- `contracts` 只读取 Design 声明和 `sdd/context/contracts/`，不扫描全仓库。
- `exclude` 固定包含 `docs/prd.md`、`docs/specs/*（其他 Spec）`、`.sdd/runtime/**`
  和 `历史聊天`。

## 示例

```json
{
  "task": {"id": "T-001", "description": "实现取消接口", "status": "Todo"},
  "frs": ["FR-001"],
  "acs": ["AC-001-1"],
  "design_sections": [
    {"heading": "4. Spec覆盖关系", "reason": "覆盖 AC-001-1"}
  ],
  "contracts": ["docs/specs/SPEC-ORDER-001/api/order.yaml"],
  "project_constraints": [{"path": "AGENTS.md", "scope": "."}],
  "fix_patterns": [],
  "allowed_paths": ["tests/test_status.py"],
  "exclude": [
    "docs/prd.md",
    "docs/specs/*（其他 Spec）",
    ".sdd/runtime/**",
    "历史聊天"
  ]
}
```
