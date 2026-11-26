<div align="center">

<img src="site/assets/logo.svg" alt="SDD Kit" width="420">

# 把 SDD 装进仓库

**SDD Kit 把 SDD-L2 的工件、Gate 和证据链做成仓库里的状态机，而不是一份需要人执行的规范。**
Agent 按 `next.action` 推进，CLI 在每次提交时校验，CI 做最终硬校验；人在 SDD 流程内只做两个决定：确认 Spec，确认交付。

[![tests](https://github.com/RyanBrainNew/sdd-kit/actions/workflows/tests.yml/badge.svg)](https://github.com/RyanBrainNew/sdd-kit/actions/workflows/tests.yml)
![version](https://img.shields.io/badge/version-0.9.9-5ee7a8)
![python](https://img.shields.io/badge/python-3.11%2B-3776AB)
![license](https://img.shields.io/badge/license-Apache--2.0-5ee7a8)
[![site](https://img.shields.io/badge/site-GitHub%20Pages-5ee7a8)](https://ryanbrainnew.github.io/sdd-kit/)

[官网](https://ryanbrainnew.github.io/sdd-kit/) · [完整指南](docs/GUIDE.md) · [架构](ARCHITECTURE.md) · [Agent 协议](sdd/agent-contract.md) · [Runner 契约](deploy/runner/CONTRACT.md) · [Issues](https://github.com/RyanBrainNew/sdd-kit/issues)

</div>

---

SDD 的核心不是写出一份规范，而是让规范在每次提交时都能被验证。SDD Kit 把阶段、工件、Gate 和证据收进仓库：

- **一个状态机。** 阶段、工件校验、Gate 和审计事件只在 `sdd/scripts/sdd.py` 定义；MCP、Hook、CI 都只是薄适配，没有 MCP 也能跑完整流程。
- **一条命令。** 平台 bootstrap 一次，开发者 clone 即用；任何能执行 shell 的 Agent 都走 `python -m sdd`，不绑定 IDE。
- **两个人工检查点。** SDD 流程内只有 Spec 确认和交付确认，其余由 `next.action` 推进；PR 审核与合并仍按仓库原有规则完成。
- **证据随 Git。** Spec、Gate 报告、测试证据、审批记录和事件哈希链都随代码提交，可复查、可追溯。

[![SDD Kit 官网首屏](docs/assets/site-preview.png)](https://ryanbrainnew.github.io/sdd-kit/)

## 它怎么工作

```mermaid
flowchart LR
  D[DRAFT<br/>写 Spec] -->|submit| S[SPEC_READY]
  S -->|人 approve| DS[DESIGN_READY]
  DS -->|submit| T[TASKS_READY]
  T -->|逐 Task 实现| I[IMPLEMENTING]
  I -->|全部任务完成| V[VERIFYING]
  V -->|Gate 通过| P[PR_READY]
  P -->|人确认交付| M[MERGED]
  M -->|Agent 开 PR| R[管理员合并]

  classDef gate fill:#2b2110,stroke:#ffc46b,color:#ffc46b;
  class S,P gate;
```

Agent 每次会话先运行 `python -m sdd resume --json`，读取唯一的 `next.action`、`next.submit_with` 和 `next.human_checkpoint`。它不需要猜阶段，也不应该问开发者“现在是什么阶段”。

| 检查点 | 人执行 | 之后发生什么 |
|---|---|---|
| Spec 确认 | `python -m sdd approve --spec <spec> --human` | Agent 继续设计和拆任务 |
| 交付确认 | `python -m sdd merge --spec <spec> --human` | 状态机进入 `MERGED`；Agent 创建 PR，由管理员合并 |

> `merge` 是交付确认，不执行 Git 合并。PR 的审核与合并仍在 GitHub 完成。

工作流在创建 Spec 时固定，之后仓库预设升级不会改变旧 Spec：

| 预设 | 适用场景 | 关键差异 |
|---|---|---|
| `l2-standard` | 默认 L2 需求 | G0 人工；G2 仅高风险人工；其余自动 |
| `l2-hotfix` | 紧急修复，低/中风险 | 轻量设计；高风险和 `risk_stop` 标签直接拒绝 |
| `l2-strict` | 安全、迁移、破坏性变更 | G0–G5 全部人工；验证需要独立审查人 |
| `l2-refactor` | 行为保持型存量改造 | schema 2；强调改动边界、回归证据与可回滚 |

## 快速开始

### 1. 平台团队：每个仓库接入一次

```powershell
cd D:\repos\order-api
python D:\tools\sdd-kit\bootstrap.py
```

默认目标是当前目录，项目 ID 取目录名。它复制 `sdd/` 核心、合并 `AGENTS.md` 托管块、写入 manifest、安装 Git Hook 与 CI 模板；已有 `AGENTS.md` 不会被覆盖。
也可以在 sdd-kit 目录内执行 `python bootstrap.py --target <repo>`。

```powershell
# 项目使用 pytest 或需要 GitLab CI 时
python D:\tools\sdd-kit\bootstrap.py --test-command "python -m pytest -q" --ci gitlab
```

### 2. 开发者：每次会话恢复

```powershell
git clone <repo>
cd <repo>
python -m sdd resume --json
```

没有当前需求时，只问一次工作项，然后运行 `python -m sdd start-work --work-item <id> --json`。

### 3. 合并前：跑同一组校验

```powershell
python -m unittest discover -s tests -v
python -m sdd verify-core
python -m sdd verify-agent
python -m sdd check --all --stage ci --check-git
```

CI 执行同一组命令。核心被改、托管块漂移、工件缺失或证据不真实都会失败。

## 常用命令

完整命令见 [sdd/README.md](sdd/README.md)。`--json` 方便 Agent 解析；人看时可以去掉。

| 目的 | 命令 | 执行者 |
|---|---|---|
| 恢复 / 开始 | `sdd resume` · `sdd start-work` | Agent |
| 提交阶段工件 | `sdd submit --artifact <name> --file <path>` | Agent |
| 完成一个任务 | `sdd submit-task --task T-xxx --evidence "..."` | Agent |
| 生成 PR 正文 | `sdd report` | Agent |
| 确认 Spec | `sdd approve --human` | 人 |
| 确认交付 | `sdd merge --human` | 人 |
| 预设升级 | `sdd upgrade-workflow --to <name>@<version> --human` | 人 |
| 范围变化 / 回退 / 解阻 / 豁免 | `sdd reapprove` · `sdd rewind` · `sdd unblock` · `sdd waive` | 人 |
| 校验 | `sdd check --all --stage ci` | CI |
| 观察与追溯 | `sdd board` · `sdd inbox` · `sdd metrics` · `sdd events` · `sdd trace` · `sdd view` | 人 / Agent |

## 当前版本 0.9.9

0.9.9 加入固定预设升级 `upgrade-workflow`。0.9.8 的只读 HTML 视图、外部 runner 契约、按测试/AC/commit 追溯的 `trace`、人工豁免、审批后 `change-set` 与全量 commit 审计均已在 0.9.x 交付。

| 状态 | 内容 |
|---|---|
| 已交付 | [只读 HTML 视图 #1](https://github.com/RyanBrainNew/sdd-kit/issues/1) · [外部 Runner 契约 #2](https://github.com/RyanBrainNew/sdd-kit/issues/2) · [固定预设升级 #3](https://github.com/RyanBrainNew/sdd-kit/issues/3) · [治理闭环 #8](https://github.com/RyanBrainNew/sdd-kit/issues/8) |
| 总纲 | [轻量、可自定义、全链路可溯源的执行内核 #7](https://github.com/RyanBrainNew/sdd-kit/issues/7) |

未开发能力不会出现在命令表里，也不会在站点上冒充已交付。

## 文档

| 文档 | 内容 |
|---|---|
| [docs/GUIDE.md](docs/GUIDE.md) | 完整接入、架构、MCP、全部命令与 FAQ |
| [ARCHITECTURE.md](ARCHITECTURE.md) | 设计取舍、模块边界与分阶段落地 |
| [ADOPTION.md](ADOPTION.md) | 从单仓库试点到多仓库推广 |
| [docs/STANDARD-CONFORMANCE.md](docs/STANDARD-CONFORMANCE.md) | P0–P5 / G0–G5 的实现、证据与缺口 |
| [sdd/agent-contract.md](sdd/agent-contract.md) | Agent 自动循环与人类检查点契约 |
| [sdd/README.md](sdd/README.md) | 业务仓库内的执行手册 |
| [sdd/mcp/README.md](sdd/mcp/README.md) | 可选 MCP 适配器与部署 |
| [deploy/README.md](deploy/README.md) | 共享 MCP 的容器部署 |
| [docs/GITHUB-ABOUT.md](docs/GITHUB-ABOUT.md) | 仓库 About 文案、Topics 与 Homepage |

## 仓库结构

```text
AGENTS.md                  # 项目规则 + SDD 托管块
bootstrap.py               # 业务仓库一次性接入
docs/
  GUIDE.md
  prd-index.md             # 工作项 → FEAT → Spec 追溯
  specs/<Spec ID>/         # 需求工件；阅读顺序见下一节
sdd/
  scripts/sdd.py           # 唯一状态机
  core.py                  # 会话指针与 CLI 编排
  cli.py                   # python -m sdd
  workflows/               # l2-standard / l2-hotfix / l2-strict / l2-refactor
  templates/               # 六个阶段骨架
  prompts/                 # Agent 方法层
  context/                 # 服务卡、契约、ADR、术语
  reports/<Spec ID>/       # gate0-report.md ... gate5-report.md
  mcp/                     # 可选 MCP 适配器
site/                      # GitHub Pages 官网
tests/                     # 单元、CLI、站点与集成测试
```

## 怎么看 docs/ 产物

`docs/` 是随代码提交的审计面，不是官网，也不是临时输出。入口是 `docs/prd-index.md`：先按工作项或 FEAT 找到 Spec ID，再进入 `docs/specs/<Spec ID>/`。

`docs/` 顶层：`GUIDE.md` 是完整指南，`prd-index.md` 是追溯入口，`STANDARD-CONFORMANCE.md` 是 P0–P5 / G0–G5 基线，`specs/` 是每个需求的审计工件。

如果只看三份：`spec.md` 看范围，`gates.md` 看结论，`verification.md` 看证据。

| 顺序 | 文件 | 回答什么问题 | 谁维护 |
|---|---|---|---|
| 1 | `spec.md` | 做什么、不做什么、FR/AC 是否闭合 | Agent 写，`sdd submit` 校验 |
| 2 | `design.md` | 怎么做、模块边界、接口契约、风险与回滚 | Agent 写，CLI 校验 |
| 3 | `tasks.md` | 怎么拆、依赖顺序、每条 AC 由哪个 Task/测试覆盖 | Agent 写，CLI 校验 |
| 4 | `verification.md` | 每条 AC 怎么验、跑了什么命令、结果如何 | Agent 写，`sdd verify` 追加证据 |
| 5 | `gates.md` | G0–G5 是否通过、人工还是自动、证据和时间 | CLI 追加 |
| 6 | `context.md` / `unknowns.md` / `decisions.md` | 调研事实、未决问题、关键取舍 | Agent 维护 |
| 7 | `workflow.json` | 本次 Spec 固定了哪套工作流 | 创建 Spec 时快照 |
| 8 | `state.json` / `events.jsonl` | 当前状态、审批、产物哈希、审计事件链 | 只能由 CLI 写 |
| 9 | `verification-evidence.jsonl` / `PR_BODY.md` | 原始测试证据 / 生成的 PR 正文 | `sdd verify` / `sdd report` |

按角色看：

- **产品 / 负责人**：`spec.md` → `gates.md` → `verification.md`，重点看范围、AC、未决问题和 Gate 结论。
- **开发**：`design.md` → `tasks.md` → `context.md` / `decisions.md`，重点看边界、依赖和取舍。
- **审计 / 复盘**：`verification-evidence.jsonl` → `gates.md` → `events.jsonl` → `state.json`，重点看命令、退出码、产物哈希和审批链。

不想直接读 JSON 时，用 `python -m sdd view --spec <spec>` 看只读 HTML；`python -m sdd board` 看整体进度；`python -m sdd events --spec <spec>` 看审计链；`python -m sdd trace --test/--ac/--commit ...` 反查 test、AC、commit 到 Spec 的链路。

`gates.md` 是摘要；详细检查在 `sdd/reports/<Spec ID>/gateN-report.md`。`change-set.md`、`review-findings.json`、`history/` 只在变更审批、独立审查或回退时出现。

不要手改 `state.json`、`events.jsonl`、`gates.md`、`workflow.json` 或 `verification-evidence.jsonl`；它们由 CLI 写入，手改会破坏哈希链或 Gate 证据。`docs/` 只随代码提交，`site/` 才是公开发布的官网；Pages 工作流只上传 `site/`。

## 适合与不适合

**适合**

- 多个业务仓库，需要统一 L2 流程与审计证据
- 团队混用不同 Agent 或 IDE
- 已有 `AGENTS.md`，希望增量接入
- Git 与 CI 已是默认基础设施

**不适合**

- 单人一次性脚本，没有 Spec、Gate 或合并流程
- 没有 Git 或 CI，无法留下可校验证据
- 需要集中式 Web 审批台；当前只有 CLI 与 MCP
- 希望工具替代需求判断或代码评审

## 开发

只使用 Python 标准库；MCP 依赖隔离在 `sdd/mcp/requirements.txt`。

```powershell
$env:PYTHONIOENCODING='utf-8'
python -m unittest discover -s tests -v
python -m sdd verify-core
python -m sdd verify-agent
python -m sdd check --all --stage ci --check-git
```

修改受保护文件后，更新 `sdd/VERSION` 并重新生成 manifest：

```powershell
python -m sdd manifest --write
```

`sdd/manifest.json` 与 `sdd/VERSION` 必须提交，不能加入 `.gitignore`。

贡献时先在 Issue 说明工作项与影响面，从 `main` 切分支并保持 diff 聚焦。修改核心需同步测试、README、`sdd/agent-contract.md` 和相关提示词；`approve`、`reapprove`、`merge`、`unblock`、`rewind`、`waive` 只能由人执行。

## 许可证

本项目采用 [Apache License 2.0](LICENSE)。允许商用、修改和分发；分发时需保留版权与许可声明，在修改过的文件中标注修改，并保留随附的 `NOTICE`（如有）。

Copyright 2026 RyanBrainNew

---

<div align="center">

**SDD Kit 0.9.9** · 把 SDD 装进仓库

</div>
