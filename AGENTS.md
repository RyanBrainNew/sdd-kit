# sdd-kit 维护约束

本仓库是公司 SDD-L2 工作流的源仓库。业务仓库通过 `bootstrap.py` 引入本仓库的
`sdd/` 核心；业务项目不要直接修改核心。

## 1. 架构不变量

- `sdd/scripts/sdd.py` 是唯一状态机；不要在其他地方复制阶段规则。
- `sdd/core.py` 负责会话指针和 CLI 高层编排；必须继续通过子进程调用 `sdd.py`。
- `sdd/mcp/` 只是薄适配器；MCP 工具不得包含独立的 Gate 或状态规则。
- `approve`、`merge`、`unblock`、`rewind` 是人工动作；CLI 强制 `--human`，MCP 不暴露。
- `sdd/agent-block.md` 只能通过 `python -m sdd sync-agent` 合并进 `AGENTS.md`；
  不要生成 `AGENTS.sdd.md`。

## 2. 目录职责

```text
sdd/scripts/sdd.py     # 状态机、工件校验、Gate
sdd/core.py            # Workspace、会话指针、submit/report 编排
sdd/cli.py             # python -m sdd
sdd/agents.py          # AGENTS.md 托管块
sdd/templates/         # 公司六个骨架
sdd/workflows/         # 命名工作流预设
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

- `README.md`：项目首页、快速接入与文档导航。
- `docs/GUIDE.md`：完整接入、架构图、人类步骤、两种开发模式。
- `site/`：GitHub Pages 官网静态站点，由 `.github/workflows/pages.yml` 发布。
- `docs/GITHUB-ABOUT.md`：仓库 About 区文案、Topics 与 Homepage。
- `sdd/README.md`：仓库内执行手册。
- `sdd/agent-contract.md`：Agent 自动循环和人类检查点。
- `ARCHITECTURE.md`：设计取舍。
- `ADOPTION.md`：推广步骤。

<!-- SDD:MANAGED:START -->
# SDD Agent 执行协议

你是本仓库的 SDD 执行 Agent。开发者只需要给一个工作项；**不要问“现在是什么阶段”**，
也不要让开发者选择 `DRAFT`、`SPEC_READY` 等状态。阶段、下一步和是否停下由仓库内 CLI 决定。

## 0. 硬规则

- 所有命令都在仓库根目录执行。
- 唯一状态机是 `sdd/scripts/sdd.py`。不要手改 `state.json` 或 `events.jsonl`。
- 不要跳过 `submit` / `submit-task`；`ok=false` 时按 `errors` 修复后重试。
- `approve`、`reapprove`、`merge`、`unblock`、`rewind`、`waive` 只能由人执行，Agent 不得代替。
- `l2-standard` 正常流程只有两个人工检查点：Spec 确认、交付确认；
  交付确认后才创建 PR，PR 的审核合并由管理员在 GitHub 完成；
  `l2-strict` 的 G0–G5 全部需要人工确认。
- 首次接入由平台团队执行一次 `sdd init`；旧入口 `bootstrap.py` 保留为兼容 shim。

## 1. 每次会话先恢复

每次新会话、切分支、接手需求或继续上次工作时，第一步必须运行：

```powershell
python -m sdd resume --json
```

读取返回的 `next`：

- 有 `spec` 和 `next.action`：直接执行 `next.action`，不要重新创建 Spec。
- `action=create_spec`：没有当前需求，只问一次工作项，然后运行：

```powershell
python -m sdd start-work --work-item <work-item> --issue-url "<url>" --json
```

- `action=select_spec`：只问一次恢复哪个 Spec，然后运行：

```powershell
python -m sdd resume --spec <spec> --json
```

需要紧急修复、严格流程或存量重构时，由创建需求的人加 `--workflow l2-hotfix`、
`--workflow l2-strict` 或 `--workflow l2-refactor`；Agent 不要自行选择或修改工作流。

## 2. 自动循环

1. 读取 `next.action`、`next.step_id`、`next.kind`、`next.prompt_file`、
   `next.artifact`、`next.done_when`、`next.submit_with` 和 `next.context_bundle`。
2. 只按 `context_bundle` 的范围调研代码、测试、契约、ADR、知识索引和
   `sdd/context/`；把事实写进 `context.md`，把未决问题写进 `unknowns.md`。
3. 产出 `next.artifact` 要求的内容。
4. 调用 `next.submit_with` 提交：
   - 阶段产物：`python -m sdd submit --artifact <name> --file <path> --json`
   - 实现任务：`python -m sdd submit-task --task T-xxx --evidence "..." --json`
   - 状态迁移：`python -m sdd complete --evidence "..." --json`
5. `ok=false`：按 `errors` 修复后重新提交。
6. `decision_required=true`：停止，只把 `question` 和 `options` 交给人类。
7. `human_checkpoint.required=true`：停止，并告诉人类执行 `human_checkpoint.command`。
8. 否则继续读取新的 `next.action`，直到 `done` 或人工检查点。

每个阶段只执行一个动作、用一个提交命令；不要绕过 CLI 批量推进。

## 3. 人类检查点与例外动作

正常流程只有两个人工检查点：

1. Spec 确认：人执行
   `python -m sdd approve --spec <spec> --human --evidence "需求已确认"`。
2. PR 合并：人执行
   `python -m sdd merge --spec <spec> --human --evidence "PR merged"`。

例外动作：

- 审批后范围变化：人执行
  `python -m sdd reapprove --spec <spec> --human --reason "..." --evidence "..."`。
  Agent 必须先执行 `python -m sdd change --spec <spec> --reason "..."` 登记变更；
  存在 pending change-set 时不得提交代码。
- 回退/返工：人执行
   `python -m sdd rewind --spec <spec> --to <stage> --reason "..." --human`。
- 解除阻塞：人执行
   `python -m sdd unblock --spec <spec> --human --evidence "..."`。
- 范围化豁免：人执行
   `python -m sdd waive --spec <spec> --check <id> --scope "..." --reason "..." --expires <iso> --evidence "..." --human`。
   豁免只对可豁免的非红线 required 检查有效，并绑定 Gate 产物哈希。

人可以用 `python -m sdd inbox --json` 查看所有等待处理的事项；
用 `python -m sdd events --spec <spec> --json` 和 `python -m sdd metrics --json`
查看审计链与质量指标。Agent 不代替人创建豁免。

## 4. 优先级

- 技术栈、目录、构建、测试和代码风格：以本文件其他章节为准；缺失时先检查仓库再记录，不得编造。
- SDD 阶段、提交方式、人工检查点和证据要求：以本托管块和 `sdd/agent-contract.md` 为准。
- 底层状态机和 Gate 规则：以 `sdd/scripts/sdd.py` 和 `sdd/config.json` 为准。

CI 会执行 `python -m sdd verify-core`、`python -m sdd verify-agent` 和
`python -m sdd check --all --stage ci --check-git`。不要试图绕过。

`verification-evidence.jsonl` 是真实测试证据；`events.jsonl` 是带哈希链的审计流。
只在 Markdown 写 PASS、伪造退出码或手工重写事件都会失败。
<!-- SDD:MANAGED:END -->
