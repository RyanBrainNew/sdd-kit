# 验证

1. 读 spec、tasks、verification 模板、`verification-evidence.jsonl` 和项目测试说明。
2. 运行 `python -m sdd verify --spec <spec>`；它会把命令、目录、时间、退出码、
   耗时、输出哈希和产物哈希写入 JSONL。不要手工伪造 PASS。
3. 如果 `config.json` 没有配置 `test_commands`，先补真实测试命令；纯文档变更
   需要人工豁免时必须限范围、说明原因并设置到期时间。
4. 在 `verification.md` 写清：
   - 命令、目录、退出码；
   - 每条 AC 的预期与实际；
   - 没跑什么、为什么；
   - AC -> 测试/证据映射。
5. 不要写“应该通过”；只写实际结果。失败、错误、跳过、未执行都必须如实记录。
6. 用 `[AC-xxx-y]` 标记让测试文件与 AC 建立关联。
7. 中高风险变更必须写“独立审查”章节，并按 `sdd/prompts/review/` 的 overlay
   输出九字段 finding；未关闭的阻断 finding 不得通过 G5。
8. 运行 `python -m sdd check --spec <spec> --stage verify --json`，确认审计链有效。
9. 通过后运行 `python -m sdd complete --spec <spec> --evidence "..." --json`，
   生成 `PR_BODY.md`、`gate5-report.md` 并进入 PR_READY。
