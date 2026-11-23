# 通用 Review 契约

## 1. 适用条件

- Spec 风险为 `medium` 或 `high` 时必须执行独立审查。
- `low` 风险是否强制由 Profile 的 `review_policy.required_for_risk` 决定。
- 只加载当前改动路径命中的技术栈 overlay；没有匹配 overlay 时，只使用本通用契约。

## 2. 输入范围

审查前先确认：

- 当前 Spec、Task、关联 FR/AC 和允许改动路径。
- 实际 diff、测试命令与 `verification-evidence.jsonl`。
- 适用的 overlay、契约文件和项目约束。

不得审查当前 Task 之外的无关文件，也不得把历史聊天或未确认知识当成权威依据。

## 3. 输出位置

结论写入 `verification.md` 的“独立审查”章节，至少包含：

| 项 | 内容 |
|---|---|
| Reviewer | 审查人或审查 Agent |
| Session | 独立会话标识 |
| Model | 使用的模型 |
| Scope | 本次审查覆盖的文件、模块和 AC |
| Findings | 问题摘要；无问题时必须写明“未发现可执行问题” |
| Blocking issues | `none`，或未关闭阻断 finding 的 ID |

发现问题时，同时写入 `review-findings.json`。该文件必须是 finding 数组。

## 4. Finding 九字段

| 字段 | 要求 |
|---|---|
| `id` | 本 Spec 内唯一，例如 `RV-001` |
| `location` | 文件、行号、接口或测试位置 |
| `evidence` | 可复核的事实、命令输出或代码引用 |
| `impact` | 对正确性、安全、兼容性或可维护性的影响 |
| `recommendation` | 可执行的修复建议 |
| `authority` | 规范、项目约束、测试或 Owner 确认等权威依据 |
| `severity` | `low`、`medium`、`high` 或 `critical` |
| `verification` | `open`、`fixed`、`verified`、`closed` 或 `resolved` |
| `blocking` | 布尔值；阻断项只有进入 `verified`、`closed` 或 `resolved` 后才算关闭 |

字段缺失、取值非法、ID 重复或存在未关闭阻断 finding 时，G4/G5 必须失败。

## 5. 审查结论

- 无问题时不得留空，必须写“未发现可执行问题”，并给出 `Scope`。
- 有问题时必须列出 finding ID，并与 `review-findings.json` 保持一致。
- Review 只输出结构化事实，最终结论由现有 Gate 读取证据后判定。
