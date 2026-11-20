# 交付确认

当前状态是 `PR_READY`：实现、验证和 `PR_BODY.md` 都已完成，但**还没有创建 PR**。

1. 检查 `PR_BODY.md` 是否包含 Spec、变更说明、AC 验证清单、命令与结果。
2. 不要创建 PR，不要 push 默认分支，不要调用 `sdd merge`。
3. 把 `PR_BODY.md` 和验证结果交给人类，等人类运行：

```powershell
python -m sdd merge --spec <spec> --human --evidence "交付已确认"
```

4. 人类确认后，状态变为 `MERGED`，再按 `next.action=open_pr` 创建 PR。
