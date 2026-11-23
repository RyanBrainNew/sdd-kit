# 决策记录

> 记录实现过程中做出的关键取舍。没有就保持为空。

## Decisions

- D-001：采用 `sdd/scripts/sdd_ext.py` 承载无状态纯函数，状态迁移仍只在
  `sdd/scripts/sdd.py`。详见 `adrs/ADR-002-extension-boundary.md`。
- D-002：Profile v2 允许选择已注册检查项，但不能定义任意脚本、阶段或 DAG；
  安全红线检查不能被 Profile 移除。
- D-003：命令证据使用当前 Spec 下的追加式 JSONL，不引入数据库；
  Gate 报告继续绑定产物哈希，证据记录绑定命令与输出摘要。

## Blocked
