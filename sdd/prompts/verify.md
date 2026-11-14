# 验证

1. 读 spec、tasks、verification 模板和项目测试说明。
2. 运行 `python sdd/scripts/sdd.py verify`；如果 `config.json` 没配置 `test_commands`，手动运行项目测试命令。
3. 在 `verification.md` 写清：
   - 命令、目录、退出码；
   - 每条 AC 的预期与实际；
   - 没跑什么、为什么；
   - AC -> 测试/证据映射。
4. 不要写“应该通过”；只写实际结果。失败、错误、跳过、未执行都必须如实记录。
5. 用 `[AC-xxx-y]` 标记让测试文件与 AC 建立关联。
6. 运行 `python sdd/scripts/sdd.py check --stage verify`。
7. 通过后运行 `sdd complete --evidence "..."`，脚本会生成 `PR_BODY.md`、`gate5-report.md` 并进入 PR_READY。
