# 知识索引

本索引只保存稳定 ID、结论摘要、权威位置和适用范围。Spec、Design 和 Agent
上下文应引用知识 ID，不复制权威正文。

## 1. 类型

| Type | 含义 | ID 示例 |
|---|---|---|
| `SRC` | 权威来源及其版本 | `SRC-001` |
| `FACT` | 可由代码、契约或测试证明的事实 | `FACT-001` |
| `BR` | 已确认的业务规则 | `BR-001` |
| `CONFLICT` | 来源之间的冲突及裁决状态 | `CONFLICT-001` |
| `GAP` | 尚缺 Owner 确认或权威来源的知识缺口 | `GAP-001` |

## 2. 记录

| ID | Type | Statement | Source | Version | Scope | Owner | Status | Links |
|---|---|---|---|---|---|---|---|---|
| SRC-001 | SRC | SDD-Kit 下一阶段能力以当前 Spec 为权威需求来源 | docs/specs/SPEC-DEVTOOLS-002/spec.md | 1.0.0 | sdd-kit | repo-maintainer | CONFIRMED | FEAT-002；FR-001 |
| FACT-001 | FACT | `sdd/scripts/sdd.py` 是唯一状态机 | sdd/scripts/sdd.py | 0.9.x | sdd/scripts | repo-maintainer | CONFIRMED | FEAT-002；FR-010 |
| BR-001 | BR | 中风险和高风险 Spec 必须提供独立 Review 证据 | docs/specs/SPEC-DEVTOOLS-002/spec.md#FR-007 | 1.0.0 | sdd/scripts/sdd.py | repo-maintainer | CONFIRMED | FEAT-002；AC-007-3 |
| CONFLICT-001 | CONFLICT | 纯文档变更的测试豁免必须显式、限范围且可到期 | docs/specs/SPEC-DEVTOOLS-002/spec.md#BR-012 | 1.0.0 | sdd/scripts/sdd.py | repo-maintainer | RESOLVED | FEAT-002；AC-004-6 |
| GAP-001 | GAP | 公司培训材料尚未分配稳定 SRC ID，暂不复制正文 | N/A | N/A | docs/knowledge | repo-maintainer | OPEN | FEAT-002；FR-008 |

## 3. 状态约定

- `CONFIRMED` 表示有权威来源且 Owner 已确认。
- 没有权威来源的记录只能使用 `OPEN`、`CANDIDATE` 或 `GAP`，不得标记为 `CONFIRMED`。
- 未解决的 `CONFLICT` 会阻断相关任务的 `context_bundle`，直到 Owner 裁决。
- `GAP` 只说明缺口，不自动构成业务规则或阻断依据。
