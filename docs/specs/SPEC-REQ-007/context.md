# 需求上下文

- Work item: `SDD-VIEW-001`
- Issue: https://github.com/RyanBrainNew/sdd-kit/issues/1

## 原始需求

issue #1 要求新增只读单文件 HTML 运行视图：

```powershell
python -m sdd view --spec SPEC-ORDER-001 --out .sdd/runtime/view/SPEC-ORDER-001.html
```

- 头部：Spec、状态、工作流、风险、PR URL；
- 时间线：`events.jsonl` 追加事件；
- Gate 表：状态、模式、证据、产物哈希；
- Task 表：状态、AC、commit；
- 工件列表：链接到 Spec 目录内文件；
- 只读，不写 `state.json`、`events.jsonl` 或 Gate 报告；
- 单文件 HTML，无外部 CSS/JS，离线可打开；
- 不复制状态机规则，只消费 `sdd status/events/board --json`；
- 不做拖拽、编辑、运行或服务端。

## 调研事实

- `sdd/cli.py` 已注册 `status`、`events`、`board`、`report` 等只读命令，
  通过 `sdd/core.py` 的 `Workspace` 调用 `sdd/scripts/sdd.py`。
- `sdd/core.py` 的 JSON 输出包含 `state`、`next`、`events` 和任务看板数据；
  `sdd/reports/<spec>/gate*-report.md` 提供 Gate 状态、模式、证据和产物哈希。
- `docs/specs/<spec>/` 下有 spec/design/tasks/verification/gates/state/events 等工件。
- 现有 `sdd board` 只有文本/JSON；没有 HTML 输出。
- `.sdd/runtime/` 已被 `.gitignore` 忽略，适合放生成的视图文件。
- `sdd/manifest.json` 只覆盖受保护核心文件；新增 `sdd/view.py` 与 `sdd/cli.py`
  变更需要版本递增和 manifest 重写。

## 影响范围

- 核心：新增 `sdd/view.py`，`sdd/cli.py` 注册 `view` 子命令。
- API：`Workspace` 增加只读视图数据收集方法，仍通过子进程调用状态机。
- 测试：新增 `tests/test_view.py` 覆盖正常 Spec、空 Spec、rewind 事件和只读性。
- 文档：README、`sdd/README.md`、`sdd/agent-contract.md`、版本与 manifest。

## 约束与排除

- 不新增 Web 服务、前端构建链、JavaScript 或第三方依赖。
- 不复制 Gate 规则；所有阶段和状态来自现有 CLI JSON。
- 不通过视图执行任何人工或写入动作。
