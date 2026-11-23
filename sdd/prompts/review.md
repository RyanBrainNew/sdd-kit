# PR 前审查

通用输出契约和 finding 九字段以
`sdd/prompts/review/contract.md` 为准。技术栈规则按改动路径加载：

- Python：`sdd/prompts/review/python.md`
- Java/Spring：`sdd/prompts/review/java-spring.md`
- 前端：`sdd/prompts/review/frontend.md`

审查结论写入 `verification.md` 的“独立审查”章节；发现问题时同时写
`review-findings.json`。未关闭的阻断 finding 会阻止 G4/G5。
