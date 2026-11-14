# 拆任务

目标：把 design 拆成 agent 能逐个完成、每个都能独立验证并形成 Commit 的任务，满足公司 Gate 3。

1. 使用公司任务表，不要退回 checklist：

```text
| Task ID | 任务描述 | 关联FR/AC | 依赖Task | 并行标识 | 验收标准 | 单元测试类/方法 | 单Task测试命令 | 状态 | Commit SHA |
```

2. 每个 Task 是纵向切片：数据、逻辑、接口、测试一起完成；避免“改 model / 改 service / 改 controller”的横向拆分。
3. 每个 Task 至少关联一个有效 FR 和一个有效 AC；全部 AC 必须被至少一个 Task 覆盖。
4. 每个 Task 写具体验收标准、具体测试类/方法、真实可执行命令和 `P`/`S` 并行标识。
5. 依赖为空写 `None`；依赖必须真实存在，DAG 不能有环。
6. 任务要能在一个上下文窗口内完成；太大就拆，太小就合并。
7. 填完 AC—Task—单元测试映射和依赖图，删除 TODO，运行 `python sdd/scripts/sdd.py check --stage tasks`，再 `sdd complete --evidence "..."`。
