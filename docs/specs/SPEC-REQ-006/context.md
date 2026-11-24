# 需求上下文

- Work item: `SDD-RUNNER-001`
- Issue: https://github.com/RyanBrainNew/sdd-kit/issues/2

## 原始需求

issue #2 要求新增 `deploy/runner/CONTRACT.md`，给外部 runner 一个明确契约：

- 说明准备环境、`start-work`、读取 `next`、运行 Agent、`submit` / `submit-task`、
  人工检查点、收集日志与证据的完整生命周期；
- 覆盖成功、`ok=false`、`decision_required`、`awaiting_human_approval` 的处理；
- 明确 runner 不得调用 `approve`、`reapprove`、`merge`、`unblock`、`rewind`、`waive`；
- 明确 Docker/沙箱属于 runner，不属于 `sdd-kit` 核心；
- 提供最小伪代码或命令序列示例；
- README 或 `sdd/README.md` 有入口链接。

## 调研事实

- `sdd resume --json` 返回 `next`（`action`、`artifact`、`submit_with`、
  `context_bundle`、`human_checkpoint`）和 `autopilot` 边界说明。
- `sdd start-work`、`sdd submit`、`sdd submit-task`、`sdd complete` 是 Agent
  可调用的推进命令；状态机在 `sdd/scripts/sdd.py`。
- 人工动作由 CLI 强制 `--human`，MCP 不暴露；`sdd/inbox --json` 汇总等待项。
- 现有部署目录 `deploy/` 只有共享 MCP 示例，没有 runner 契约文档。
- `sdd/agent-contract.md` 面向 Agent；外部 runner 需要一个面向 harness 的独立契约。

## 影响范围

- 新增 `deploy/runner/CONTRACT.md`。
- `README.md` 与 `sdd/README.md` 增加入口链接。
- 新增文档一致性测试，校验契约必需章节和人工动作边界。
- 受保护文件变更时同步版本与 manifest。

## 约束与排除

- 不改状态机、不新增 MCP 写工具、不实现具体 Docker runner 或 CI 厂商接入。
- 文档不复制 Gate 规则，只引用 CLI 输出和 `sdd/agent-contract.md`。
