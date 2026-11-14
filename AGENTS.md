# sdd-kit 维护约束

本仓库是公司 SDD-L2 工作流的源仓库。业务仓库通过 `bootstrap.py` 引入本仓库的
`sdd/` 核心；业务项目不要直接修改核心。

## 1. 架构不变量

- `sdd/scripts/sdd.py` 是唯一状态机；不要在其他地方复制阶段规则。
- `sdd/core.py` 负责会话指针和 CLI 高层编排；必须继续通过子进程调用 `sdd.py`。
- `sdd/mcp/` 只是薄适配器；MCP 工具不得包含独立的 Gate 或状态规则。
- `approve`、`merge`、`unblock` 是人工动作；CLI 强制 `--human`，MCP 不暴露。
- `sdd/agent-block.md` 只能通过 `python -m sdd sync-agent` 合并进 `AGENTS.md`；
  不要生成 `AGENTS.sdd.md`。

## 2. 目录职责

```text
sdd/scripts/sdd.py     # 状态机、工件校验、Gate
sdd/core.py            # Workspace、会话指针、submit/report 编排
sdd/cli.py             # python -m sdd
sdd/agents.py          # AGENTS.md 托管块
sdd/templates/         # 公司六个骨架
sdd/prompts/           # Agent 方法层
sdd/context/           # 多微服务上下文模板
sdd/mcp/               # 可选 MCP 适配器
bootstrap.py           # 业务仓库一次性接入
tests/                 # 单元与集成测试
deploy/                # 共享 MCP 部署示例
dsh/                   # dsh/harness 薄适配约定
```

## 3. 开发与验证

只使用 Python 标准库；MCP 依赖只在 `sdd/mcp/requirements.txt`。

```powershell
$env:PYTHONIOENCODING='utf-8'
python -m unittest discover -s tests -v
python -m sdd verify-core
python -m sdd verify-agent
```

修改受保护文件后，必须更新版本并重新生成 manifest：

```powershell
python -m sdd manifest --write
```

`sdd/manifest.json` 和 `sdd/VERSION` 必须提交，不能加入 `.gitignore`。

## 4. 变更规则

- 不修改公司真实项目，只在 `sdd-kit` 和测试临时目录里工作。
- 改核心时同步更新测试、README、`sdd/agent-contract.md` 和相关提示词。
- 不扩大无关 diff；不做与当前任务无关的重构。
- 新增人工动作必须同时更新 CLI、MCP 边界、README 和测试。
- 新增 MCP 工具必须确认它不复制状态机规则。

## 5. 关键文档

- `README.md`：完整接入、架构图、人类步骤、两种开发模式。
- `sdd/README.md`：仓库内执行手册。
- `sdd/agent-contract.md`：Agent 自动循环和人类检查点。
- `ARCHITECTURE.md`：设计取舍。
- `ADOPTION.md`：推广步骤。

<!-- SDD:MANAGED:START -->
## SDD Workflow

本仓库使用 SDD。所有命令都在仓库根目录执行。

### 会话入口

```powershell
python -m sdd resume --json
```

没有当前工作项时，只问一次工作项，然后运行：

```powershell
python -m sdd start-work --work-item <work-item> --json
```

### 自动循环

- 读取返回的 `next.action`、`next.artifact`、`next.prompt`、`next.done_when`。
- 先调研代码、测试、契约和 `sdd/context/`，把事实写进 `context.md`，把未决问题写进 `unknowns.md`。
- 产出 `next.artifact` 后，用 `next.submit_with` 提交：
  - 阶段产物：`python -m sdd submit --artifact <name> --file <path> --json`
  - 实现任务：`python -m sdd submit-task --task T-xxx --evidence "..." --json`
- `ok=false` 时按 `errors` 修复后重新提交；不要跳步，不要直接编辑 `state.json`。
- `decision_required=true` 时停止，把 `question` / `options` 交给人类，不要继续编码。
- 只有 `human_checkpoint.required=true` 时才停下来找人。

### 人类检查点

正常流程只有两个：

1. Spec 确认：人执行 `python -m sdd approve --spec <spec> --human --evidence "需求已确认"`。
2. PR 合并：人执行 `python -m sdd merge --spec <spec> --human --evidence "PR merged"`。

`approve`、`merge`、`unblock` 只能由人执行，Agent 不得代替。

### 优先级

- 技术栈、目录、构建、测试和代码风格：以本文件其他章节为准；缺失时先检查仓库再记录，不得编造。
- SDD 阶段、提交方式、人工检查点和证据要求：以本托管块和 `sdd/agent-contract.md` 为准。
- 底层状态机和 Gate 规则：以 `sdd/scripts/sdd.py` 和 `sdd/config.json` 为准。

CI 会执行 `python -m sdd verify-core`、`python -m sdd verify-agent` 和
`python -m sdd check --all --stage ci --check-git`。不要试图绕过。
<!-- SDD:MANAGED:END -->
