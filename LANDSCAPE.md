# 开源方案速览（2026-11-14）

这不是“谁最强”的排行榜，而是选型时的对照表。Star 数和项目状态会变，接入前应以仓库 README、Release 和实际试点为准。

## 1. 先分类，避免拿不同层的东西比较

| 类别 | 代表项目 | 主要解决 |
|---|---|---|
| 仓库内 SDD 工作流 | cc-sdd、Conductor、Agent OS、Spec Kitty、BMAD、Trellis、GSD | Spec → Plan → Tasks → 实现 → 评审 |
| 任务管理 | Taskmaster | 把需求拆成可跟踪任务 |
| Agent 编排/harness | MoAI-ADK、OpenHands、Goose、Claude Flow | 多 Agent、工具调用、执行环境 |
| 通用编码助手 | Aider、Cline、Roo Code、Continue | 改代码、补全、对话 |
| 强审计流程 | aidlc（用户已有实践） | 完整证据链和阶段审计 |

同一行里才适合直接比较。拿 Trellis 和 aidlc 比“快慢”，本质上是在比“开发体验”和“审计强度”。

## 2. 值得看的项目

### 2.1 cc-sdd

- 仓库：https://github.com/gotalab/cc-sdd
- 定位：把 Spec-Driven Development 装成 Agent Skills，覆盖 discovery、requirements、design、tasks、autonomous implementation。
- 特点：明确对标 Kiro 风格；支持多个 coding agent；强调 per-task review。
- 适合：希望“一个命令装进现有 Agent”，又想要较长自主实现链路的团队。
- 注意：它更偏“Agent Skills 工作流”，公司要求的 Gate 报告、commit trailer、CI 硬校验仍需另补。

### 2.2 Conductor

- 仓库：https://github.com/gemini-cli-extensions/conductor
- 定位：Antigravity / Claude Code 等 Agent 的插件，按 `Context -> Spec & Plan -> Implement` 推进。
- 特点：把 context 当作与代码同等重要的工件；协议严格，体验连贯。
- 适合：已经使用 Antigravity 或 Claude Code，想要现成插件的团队。
- 注意：插件形态意味着入口与宿主绑定；跨仓库统一治理要额外做。

### 2.3 Agent OS

- 仓库：https://github.com/buildermethods/agent-os
- 定位：从代码库提取标准，按任务注入相关规范，再辅助写 Spec。
- 特点：强在“把团队规范注入 Agent”，而不是强在状态机。
- 适合：已有较成熟代码规范、希望 Agent 少跑偏的团队。
- 注意：它不会自动产生公司 L2 所需的 Gate 证据链。

### 2.4 BMAD Method

- 仓库：https://github.com/bmad-code-org/BMAD-METHOD
- 定位：敏捷式 AI 驱动开发方法，覆盖 Clarify / Plan / Build / Learn 的完整循环。
- 特点：方法论文档和角色分工较完整；可按任务大小伸缩。
- 适合：愿意接受一套“方法”而不只是“工具”的团队。
- 注意：方法越完整，落地培训和流程摩擦越高；需要裁剪到公司 L2。

### 2.5 Spec Kitty

- 仓库：https://github.com/spec-kitty/spec-kitty
- 定位：repo-native 的 `spec -> plan -> tasks -> next -> review -> accept -> merge` CLI，强调治理和多 Agent 工作树。
- 特点：**这是目前与本 kit 控制面最接近的同类产品**。它已经有：
  - CLI-first 的确定性入口，`spec-kitty next --json` 可以返回下一步动作；
  - `planned / in_progress / for_review / approved / done` 的 work package lane；
  - `.worktrees/` 隔离并行 Agent；
  - review / accept / merge / retrospective 的审计链；
  - built-in / org / project 三层 Charter/Doctrine，适合平台团队统一治理；
  - Claude Code、Codex、Cursor、Gemini、Copilot、Windsurf、OpenCode 等多宿主接入。
- 与本 kit 重合的部分：仓库内状态、任务/评审阶段、`next` 调度、worktree 并行、CLI-first。
- 关键缺口：
  - 公司要求的 6 个骨架、Gate 0–5 报告格式、commit trailer、PR 四要素、
    `docs/prd-index.md`、AC → Task → 测试文件追溯，仍需另做公司适配层；
  - 截至 2026-11-14，官方 `mission-gates.md` 明确写着 gate mechanism 仍是
    “accepted design, not yet shipped behaviour”；当前只有 pre-review gate，
    且 gate fault 会 fail open，不能直接当作公司硬门禁；
  - 没有开箱即用的“业务仓库必须通过 SDD 校验”的消费端 CI job 模板；
  - 仍需 `spec-kitty init` / `verify-setup` 和项目级 `.kittify` 配置，
    与“团队只 clone、不初始化”的目标有距离；
  - 项目处于 4.0.0rc8 快速迭代期，接入必须锁版本、做试点。
- 适合：愿意接受项目级 init、需要强治理和多 Agent worktree 的团队。
- 结论：可以作为“控制面”的优先候选，但不能直接替代公司 L2 合规层。

### 2.6 GSD / GSD Pi

- 仓库：https://github.com/open-gsd/gsd-pi
- 定位：meta-prompting、context engineering 和 spec-driven development，让 Agent 长时间自主工作而不丢大图。
- 特点：强调长任务、上下文保持和自主推进。
- 适合：issue agent、长时间无人值守任务。
- 注意：原 `gsd-build/gsd-2` 已归档并迁移到 `open-gsd/gsd-pi`，选型时注意仓库迁移。

### 2.7 MoAI-ADK

- 仓库：https://github.com/modu-ai/moai-adk
- 定位：面向 Claude Code 的验证驱动 Agent 编排 harness，带 SPEC 流程、质量门禁和模型路由。
- 特点：单一 Go 二进制、强调 verification 和 TRUST 5 质量门禁。
- 适合：想要“harness 级”统一控制、愿意绑定 Claude Code 的团队。
- 注意：它已经是 harness，不只是仓库内工作流；和公司现有 Agent 的关系要先理清。

### 2.8 Trellis

- 仓库：https://github.com/mindfold-ai/trellis
- 定位：开箱即用的 AI 编码工程框架，把 specs、tasks、memory 持久化进仓库。
- 特点：初始化后体验接近无感，这正是用户同事反馈好的原因。
- 适合：追求开发体验、希望 Agent 自动读项目记忆的团队。
- 注意：公司 L2 的 Gate 报告、trailer、CI 校验需要额外补；它的“无感”来自把复杂度藏在初始化之后。

### 2.9 Taskmaster

- 仓库：https://github.com/eyaltoledano/claude-task-master
- 定位：AI 开发的任务管理系统，和任意 AI chat 配合。
- 特点：任务拆解和跟踪强，但不负责完整 SDD 工件和 Gate。
- 适合：已有 Spec/Design 流程，只缺任务编排的团队。

### 2.10 OSpec

- 仓库：https://github.com/clawplays/ospec
- 定位：轻量 SDD + Loop Engineering，支持 Claude Code、Codex、Gemini、OpenCode 和 MCP。
- 特点：有 `init -> change -> verify/finalize` 的日常快流程，也有面向大任务的 Goal loop；
  支持 session hook、worktree、独立 review、证据和归档。
- 适合：希望比 Kiro 更轻、又想要“一个目标自动跑到验证”的团队。
- 注意：它是 npm CLI + 每个项目 `ospec init`，并且是 change/goal 双流程；
  公司 L2 的固定骨架、Gate 报告和 CI 规则仍要另补。

### 2.11 speclaw

- 仓库：https://github.com/esneiderbravo/speclaw
- 定位：把项目规则写成 `LAWS.md`，用 CLI + MCP + 多 Agent Cortex 执行。
- 特点：理念与本 kit 很接近：laws、gates、CODEOWNERS、lock 摘要、自适应 ceremony、
  多角色（explorer/planner/implementer/reviewer/tester/archiver）。
- 适合：作为“规则即代码 + 多 Agent 评审”的设计参考。
- 注意：项目体量和生态仍小，不适合直接作为公司基础设施；可借鉴它的 law lock 和
  role hand-off，而不是整体替换。

### 2.12 Stratum

- 仓库：https://github.com/smartmemory/stratum
- 定位：面向 AI Agent 的状态机 dispatch server，强调 typed spec、postcondition、human gate 和审计 trace。
- 特点：它解决的是“执行内核”，不是完整 SDD 产品；适合作为 MCP/状态机的实现参考。
- 注意：没有公司工件、模板和 CI 规则，单独使用不会自动满足 L2。

### 2.13 Spectra / rstack

- Spectra：https://github.com/kaochenlong/spectra-app
  - 桌面 App + CLI + skills，覆盖 propose/apply/verify/review/archive；
  - 适合个人和小团队可视化管 Spec，不是公司级强制门禁。
- rstack：https://github.com/michaelshimeles/rstack
  - `AGENTS.md` + 7 个 skills，强调 worktree、evidence、PR 和自动 review；
  - 适合作为“Agent 工作方法”和“证据驱动交付”的参考，不含公司 L2 合规层。

## 3. 对照表

“仓库内真相”指 Spec、状态、评审记录是否跟代码一起进 Git；“CI 硬校验”指不依赖 Agent 自觉。

| 方案 | 仓库内真相 | 状态机 | Gate/评审 | CI 硬校验 | 多 Agent | 接入摩擦 | vibecoding 感 |
|---|---|---|---|---|---|---|---|
| 本 kit | 强 | 强 | 强（L2） | 强 | 中 | 低 | 中高 |
| Trellis | 强 | 中 | 中 | 需补 | 中 | 低 | 高 |
| cc-sdd | 强 | 中 | 中 | 需补 | 强 | 低 | 高 |
| Conductor | 强 | 中 | 中 | 需补 | 中 | 低 | 高 |
| Agent OS | 中 | 弱 | 弱 | 需补 | 中 | 低 | 高 |
| BMAD | 强 | 中 | 中 | 需补 | 中 | 中高 | 中 |
| Spec Kitty | 强 | 强 | 强 | 中 | 强 | 中 | 中高 |
| MoAI-ADK | 强 | 强 | 强 | 中 | 强 | 中高 | 中 |
| aidlc | 强 | 强 | 强 | 可接 | 中 | 高 | 低 |

这张表是选型起点，不是结论。真正的判断标准是：**你的约束是什么**。

## 4. 有没有“比 Trellis 更优秀”的替代品

没有无条件更优秀的。按约束选：

- **要开发体验、初始化后无感**：Trellis、cc-sdd、Conductor。
- **要仓库内治理、多 Agent 工作树**：Spec Kitty。
- **要方法论完整、角色分工**：BMAD。
- **要把团队规范注入 Agent**：Agent OS。
- **要 harness 级统一控制**：MoAI-ADK、GSD Pi。
- **要公司 L2 的 Gate/证据/CI 硬校验**：本 kit，或 Spec Kitty + 自建 Gate/CI。

如果“公司要求 SDD-L2”是硬约束，那么 Trellis 的体验优势不能直接兑换成合规；需要补的正是本 kit 已经做掉的部分。

## 4.1 Build vs Adopt：不要为了“用开源”再补一遍同样的合规层

把候选方案拆成两层看：

| 层 | 解决的问题 | 谁做得较好 | 公司 L2 是否可直接复用 |
|---|---|---|---|
| 控制面 | 当前任务、阶段、下一步、暂停/恢复、worktree、评审状态 | Spec Kitty、Trellis、OSpec | 部分可以 |
| 合规层 | 6 个骨架、AC 追溯、Gate 0–5、trailer、PR 四要素、PRD index、CI 硬校验 | 本 kit | 是 |

因此有三个选项：

1. **保留本 kit，借鉴 Spec Kitty/Trellis 的控制面设计**：当前最稳，改动最小，已经能落地。
2. **以 Spec Kitty 为底座，再做公司 L2 适配包**：适合愿意接受项目级 init、并且能维护
   Charter Pack + Gate 脚本 + CI job 的团队；但适配量并不小，还要承担 RC 迭代风险。
3. **直接用 Trellis/OSpec 替换**：开发体验可能更好，但公司要求的工件、证据和 CI
   仍要补，最后会得到“开源控制面 + 自研合规层”的混合体。

当前建议是 1，保留 2 作为中期评估。判断标准不是“谁 star 多”，而是：

- 开发者是否只需要提供工作项；
- 克隆后是否不需要个人初始化；
- 阶段是否由确定性状态机推进；
- 不合格工件是否能被 CI 拦住；
- 公司证据是否能跟着代码进 Git。

## 5. 开源项目维护者通常用什么

没有一个统一答案。成熟开源项目更常见的组合是：

- Issue / PR 模板；
- CI（测试、lint、构建、安全扫描）；
- `CODEOWNERS` 和 maintainer review；
- ADR / RFC / design doc；
- Conventional Commits 或项目自定义 commit 规范；
- `AGENTS.md` / `CLAUDE.md` / `CONTRIBUTING.md` 给 Agent 和新人提供上下文。

Agent 密集的项目会额外加 Spec 目录、任务文件和自动 review，但“用某个统一 SDD 框架”并不是行业默认。把它们共同的做法抽象出来，就是：**把约定写进仓库，把校验放进 CI，把判断留给人**。

## 6. 对本项目的建议

1. 不替换现有 Agent，不绑定 IDE。
2. 以本 kit 的仓库内状态机为默认路径。
3. 只把 MCP 当共享控制面和上下文入口。
4. 用 Spec Kitty / cc-sdd / Trellis 的体验设计反过来优化本 kit 的 onboarding。
5. 高风险变更再引入 aidlc 式 strict 模式。

这样既满足公司要求，又不会让每个研发先学一套新工具。
