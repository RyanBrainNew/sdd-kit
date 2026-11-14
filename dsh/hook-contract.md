# dsh hook 契约

这些 hook 是可选增强；没有它们，CI 仍然是最终门禁。

## before_commit

```text
必须有且只有一个 Spec-Id trailer。
代码 commit 必须有且只有一个 Task-Id trailer。
文档 commit 不得带 Task-Id。
工作项前缀必须与 spec.md 元数据一致。
```

## before_finish

```text
调用 sdd_check(project, spec, stage="auto")。
如果 ok=false，把 errors 原样返回给模型，让它继续修。
不允许模型自行宣布完成。
如果本轮还没有提交当前阶段产物，先调用 sdd_submit_artifact/sdd_submit_task，
不要用 sdd_complete 手工推进。
```

## before_push

```text
拒绝 push 到默认分支。
只允许 push 当前 sdd/<spec>-<slug> 分支。
```

## session_start

```text
如果用户提供了工作项/issue，调用 sdd_start_work(project, work_item=...)。
否则调用 sdd_session。
把返回的 work_order、next.action、next.submit_with、AC、相关 service card/ADR 注入上下文。
如果返回 action=select_spec，先让人类选择 Spec，或用工作项调用 sdd_start_work 恢复。
不要注入整个仓库。
```

## user_prompt_submit

```text
识别“根据 issue/work item 开发”的意图，只调用一次 sdd_start_work。
不要把用户的话拆成“先写 spec、再写 design”等阶段命令。
后续阶段由 next.action 驱动。
```
