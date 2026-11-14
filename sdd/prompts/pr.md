# 交付 PR

1. 运行 `python sdd/scripts/sdd.py report`，确认 `PR_BODY.md` 包含：
   - Spec 文件；
   - Spec Item 列表；
   - 变更说明；
   - AC 验证清单；
   - 命令、结果、Not run。
2. 用 `PR_BODY.md` 开 PR。标题建议 `<type>(<scope>): <summary>`，正文第一行引用 Spec。
3. 运行 `python sdd/scripts/sdd.py pr --url <PR_URL>` 记录 URL。
4. 不要合并，不要 push 默认分支。
5. 如果平台支持 draft PR，优先开 draft；等人审后再转 ready。
