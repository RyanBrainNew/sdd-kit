# 创建 PR

人类已经确认交付（`MERGED`），现在才创建 PR。

1. 提交 `sdd merge` 写入的 `state.json` / `events.jsonl`，commit message 带
   `Spec-Id: <spec>` trailer。
2. push 当前功能分支，用 `PR_BODY.md` 开 PR。标题建议
   `<type>(<scope>): <summary>`，正文第一行引用 Spec。
3. 运行 `python -m sdd pr --url <PR_URL>` 记录 URL。
4. 不要合并，不要 push 默认分支；由管理员审阅并合并 PR。
