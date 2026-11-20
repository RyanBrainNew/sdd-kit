# 实现一个任务

1. 读 `next.context_bundle` 中的 Task、FR/AC、Design 章节、契约、约束和
   `allowed_paths`；只在允许范围内读源码和测试。
2. 先写一个会失败的回归测试；测试名可定位，AC 标签 `[AC-xxx-y]` 放在
   `def test_*` 函数体内。
3. 运行目标测试，确认它因预期原因失败。
4. 写满足测试的最小生产代码；不要顺手重构无关代码。
5. 跑 Task 指定的测试命令、模块测试和必要的静态检查。
6. 更新 `decisions.md`（如果有新取舍）和 `verification.md`（命令/结果）。
7. 创建只包含本 Task 的本地 Commit，然后运行 `submit-task`（会自动 start + complete）：

```bash
python -m sdd submit-task --task T-xxx --commit <SHA> --evidence "<命令、目录、结果>"
```

8. 如果失败 3 次仍无法推进，运行 `sdd block --reason "..."` 并停止。
