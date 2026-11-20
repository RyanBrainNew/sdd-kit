# 验证

1. 读 spec、tasks、verification 模板和项目测试说明。
2. 确认 `config.json` 的 `test_commands` 非空，运行 `python -m sdd verify`。
   空 `test_commands` 会被标记为 manual/unverified，不能进入 PR_READY。
3. 在 `verification.md` 写清：
   - `sdd verify` 自动写入的 Command / CWD / Exit / Head / Plan-Hash / At；
   - 每条 AC 的预期与实际；
   - 没跑什么、为什么；
   - AC -> 测试/证据映射。
4. 不要写“应该通过”；只写实际结果。手写 PASS 不能替代 exit=0 的命令证据。
5. 用 `[AC-xxx-y]` 标记让测试函数与 AC 建立关联；函数体外的裸标签不算覆盖。
6. 运行 `python -m sdd check --stage verify`。
7. 通过后运行 `sdd complete --evidence "..."`，脚本会生成 `PR_BODY.md`、`gate5-report.md` 并进入 PR_READY。
