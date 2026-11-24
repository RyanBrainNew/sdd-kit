# 外部 Runner 接入契约

本契约面向所有外部 runner（自研 harness、CI job、调度器）。核心原则只有一条：
**阶段、下一步和人工检查点都以 `sdd resume --json` 返回的 `next` 为准**。
Runner 不维护第二套状态机，也不判断 Gate 规则。

## 1. 准备隔离工作区

- 命令：检出目标仓库和分支，确认 `python -m sdd --version` 可执行。
- 输入：仓库 URL、分支、工作项 ID、隔离目录或容器镜像。
- 输出：干净工作区、Python 3.9+ 环境、可写的 `.sdd/runtime/` 目录。
- 失败：克隆失败、Python 缺失或工作区不干净时立即退出，不启动 Agent。

```powershell
git clone <repo-url> work
cd work
python -m sdd --version
```

容器、网络、密钥和资源限制由 runner 负责，见第 9 节。

## 2. 启动或恢复工作项

- 命令：新工作项用 `sdd start-work`；已有会话用 `sdd resume`。
- 输入：工作项 ID、issue URL、标题或已有 Spec ID。
- 输出：`spec`、`state`、`next` 和 `human_checkpoint`。
- 失败：`ok=false` 时把 `errors` 交给 Agent 或人，不自行创建 Spec。

```powershell
python -m sdd start-work --work-item <id> --issue-url <url> --json
python -m sdd resume --json
```

已有 active Spec 时只调用 `resume`，不要重复 `start-work`。

## 3. 读取 next

- 命令：解析 `sdd resume --json` 的 `next` 对象。
- 输入：`next.action`、`next.artifact`、`next.submit_with`、
  `next.context_bundle`、`next.human_checkpoint`。
- 输出：本轮要执行的动作和允许读取的上下文范围。
- 失败：字段缺失或 `next` 为空时停止并报告，不猜测阶段。

```powershell
python -m sdd resume --json
```

Runner 只按 `next.context_bundle` 提供上下文，不额外扩大读取范围。

## 4. 运行 Agent

- 命令：把 `next`、`next.context_bundle` 和 `next.prompt_file` 交给 Agent。
- 输入：提示词、当前 Spec 工件、允许的代码与文档范围。
- 输出：`next.artifact` 要求的文件或代码改动。
- 失败：Agent 超时或产出不符合 `done_when` 时记录日志并重试或退出。

```powershell
python -m sdd resume --json
```

Agent 只能产出当前 `next` 要求的内容；runner 不替 Agent 改 state。

## 5. 提交阶段产物与任务证据

- 命令：阶段产物用 `sdd submit`，实现任务用 `sdd submit-task`。
- 输入：产物路径、任务 ID、测试命令、退出码和 Commit SHA。
- 输出：`ok=true` 与新 `next`，或 `ok=false` 与 `errors`。
- 失败：`ok=false` 时回到第 4 步修复；不得跳过提交直接进入下一阶段。

```powershell
python -m sdd submit --artifact design.md --file docs/specs/<spec>/design.md --json
python -m sdd submit-task --task T-001 --evidence "<test command>: passed" --json
python -m sdd complete --evidence "<summary>" --json
```

## 6. 处理人工检查点

- 命令：读取 `human_checkpoint.required`，为 true 时停止自动循环。
- 输入：`human_checkpoint.type`、`command`、`message`。
- 输出：通知人执行 `human_checkpoint.command` 的记录。
- 失败：不得轮询代替人执行；不得伪造 `--human`。

```powershell
python -m sdd inbox --json
```

Runner 遇到检查点应退出并把命令原文交给人，等待人重新触发。

## 7. 归档运行证据

- 命令：保存每轮 `next`、提交结果、命令输出、退出码和产物哈希。
- 输入：stdout、stderr、退出码、时间戳、`sdd events --json`。
- 输出：可按工作项检索的运行日志和证据目录。
- 失败：日志写入失败时停止任务，避免产生无证据的“成功”。

```powershell
python -m sdd events --spec <spec> --json
```

## 8. 返回类型与退出语义

| 返回 | Runner 行为 | 退出语义 |
|---|---|---|
| 成功且 `next.action=done` | 归档证据，正常结束 | 退出码 0 |
| `ok=false` | 把 `errors` 交回 Agent 修复后重试 | 重试耗尽退出码 20 |
| `decision_required=true` | 停止循环，把 `question` 和 `options` 交给人 | 退出码 10 |
| `awaiting_human_approval=true` 或 `human_checkpoint.required=true` | 停止循环，通知人执行检查点命令 | 退出码 10 |
| 环境或 IO 错误 | 记录错误并停止 | 退出码 30 |

退出码由 runner 定义，核心 CLI 只返回 JSON；runner 可映射到自身平台，
但不得把人工检查点映射成“成功”。

## 9. Runner 职责与禁止动作

Runner 自己负责：

- Docker、容器镜像、沙箱和进程隔离；
- 网络访问、密钥注入、资源限额和超时；
- 日志落盘、证据归档、重试策略和告警。

这些能力**不属于** `sdd-kit` 核心；核心只提供 Python 标准库 CLI。

Runner **不得调用**以下人工动作，也不得通过环境变量或包装脚本伪造：

- `approve`
- `reapprove`
- `merge`
- `unblock`
- `rewind`
- `waive`

遇到 `human_checkpoint` 时只能停机通知人；人工动作由人在本地执行。

## 10. 最小命令序列

```powershell
python -m sdd start-work --work-item SDD-DEMO-001 --issue-url "<url>" --json
python -m sdd resume --json
python -m sdd submit --artifact spec.md --file docs/specs/SPEC-DEMO-001/spec.md --json
python -m sdd submit --artifact design.md --file docs/specs/SPEC-DEMO-001/design.md --json
python -m sdd submit --artifact tasks.md --file docs/specs/SPEC-DEMO-001/tasks.md --json
python -m sdd submit-task --task T-001 --evidence "<test command>: passed" --json
python -m sdd complete --evidence "all tasks done" --json
python -m sdd events --spec SPEC-DEMO-001 --json
```

每一次调用后都重新读取 `next`，不要缓存上一轮的阶段判断。
