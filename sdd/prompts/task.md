# 实现一个任务

1. 读当前 Task、对应 FR/AC、design、tasks 中的测试映射和相关源码。
2. 运行 `sdd start --task T-xxx`，把 Task 标记为 In Progress。
3. 先写一个会失败的回归测试；测试名或注释里带 `[AC-xxx-y]`。
4. 运行目标测试，确认它因预期原因失败。
5. 写满足测试的最小生产代码；不要顺手重构无关代码。
6. 跑 Task 指定的测试命令、模块测试和必要的静态检查。
7. 更新 `decisions.md`（如果有新取舍）和 `verification.md`（命令/结果）。
8. 创建只包含本 Task 的本地 Commit，然后运行：

```bash
python sdd/scripts/sdd.py complete --task T-xxx --commit <SHA> --evidence "<命令、目录、结果>"
```

9. 如果失败 3 次仍无法推进，运行 `sdd block --reason "..."` 并停止。
