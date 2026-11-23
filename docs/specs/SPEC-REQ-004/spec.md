# 审批版本绑定、change-set 与 impact 规格说明书（Spec）

## 1. 元数据

| 项 | 内容 |
|---|---|
| Spec ID | SPEC-REQ-004 |
| 工作项 ID | SDD-GOV-001 |
| FEAT ID | FEAT-006 |
| 原始需求来源 | https://github.com/RyanBrainNew/sdd-kit/issues/20 |
| 作者 | SDD Agent |
| 创建日期 | 2026-11-23 |
| 状态 | Draft |
| 版本号 | 1.0.0 |
| 产品类型 | 传统产品 |
| 模板适配 | 标准 21 节模板；UI、AI 与多智能体章节标注不适用 |
| 关联人 | 产品负责人：RyanBrainNew；技术负责人：sdd-kit 平台维护者 |
| 原型版本 | 不涉及 |

## 2. 范围声明

- In-Scope：把“人类确认过的需求”与具体 Spec 版本绑定，并让审批后的范围变化显式可见。
  1. `approve` 成功时在 `state.json` 记录 `approved_spec_digest`、`approved_at`、
     `approved_by` 和 `approval_evidence`，G0/G1 报告记录同一摘要。
  2. 审批后 `spec.md` 内容变化时，`check`、`complete`、`verify`、`merge`
     和 CI 均阻断，并给出可执行的修复提示。
  3. 新增人工专用 `reapprove`，再次校验 G0/G1 后更新审批摘要，并在
     `approvals` 中保留旧摘要、新摘要、原因、证据、审批人和时间。
  4. 新增只读 `sdd impact --json`，输出 FEAT、FR、AC、Task、测试选择器、
     代码路径和是否需要审批。
  5. 新增 `sdd change`，创建或追加 `change-set.md`，记录变更 ID、原因、
     关联对象、风险、回滚和审批状态。
  6. 存在未批准的 change-set 时，代码提交和 CI 被阻断；人类 `reapprove`
     后 change-set 自动标记为 approved，代码提交放行。
  7. 纯文档/配置变更可用 `--docs-only` 显式登记豁免，不允许静默跳过。
  8. 同步 CLI、MCP 边界、README、执行手册、Agent 契约、版本和 manifest。
- Out-of-Scope：不把 SDD 扩展为外部审批平台。
  1. 不实现 issue #21 的全量 commit 审计与 `sdd trace`。
  2. 不新增服务端、数据库、常驻进程、第三方运行时依赖或可视化审批台。
  3. 不改变 `sdd/scripts/sdd.py` 作为唯一状态机的架构。
  4. 不允许 MCP 暴露 `reapprove`、`approve`、`merge`、`unblock`、`rewind`、`waive`。
  5. 不为历史 MERGED Spec 回填或重写 `state.json` 与 Gate 报告。
  6. 不解析自然语言判断“需求语义是否变化”；只以 Spec 摘要和显式 change-set 为准。
  7. 不替代 Git 分支保护、PR 审核和代码评审。

## 3. 业务上下文

### 3.1 干系人与角色

| 角色 | 诉求 | 使用场景 | 责任边界 |
|---|---|---|---|
| 业务负责人 | 确认过的需求不能被静默改写 | 审批 Spec、范围变化时重新确认 | 执行 `approve` / `reapprove` 并承担决策责任 |
| 执行 Agent | 能判断当前 Spec 是否仍是被批准的版本 | 提交设计、任务、代码和验证证据 | 不得代替人类 `reapprove` |
| 平台维护者 | 审批、变更、代码提交之间有可机器校验的链路 | 维护 Gate、hook 和 CI | 维护规则与兼容性，不替业务做审批 |
| 审计人员 | 能还原每次范围变化的原因、影响和批准人 | 审计 change-set、审批记录和 Gate 报告 | 只读审计，不修改状态 |

### 3.2 业务流程

1. 人类执行 `approve`，引擎运行 G0/G1，通过后把当前 `spec.md` 摘要写入
   `state.json`，并在 G0/G1 报告记录同一摘要。
2. Agent 按已批准 Spec 产出 design、tasks 和代码；此时摘要一致，
   change-set 不是必需项。
3. 若审批后需要调整范围，Agent 先执行 `sdd change` 生成 pending
   change-set，再修改 Spec/Design/Tasks。
4. 人类检查变更内容后执行 `reapprove`；引擎重跑 G0/G1，更新审批摘要，
   并把 pending change-set 标记为 approved。
5. 只有 approved 状态或无 pending change-set 时，代码提交和 CI 才放行。
6. 纯文档或配置变更由 Agent 执行 `sdd change --docs-only` 显式登记；
   该记录不要求 `reapprove`，但任何代码提交都会被阻断。

### 3.3 业务规则

- BR-001：`sdd/scripts/sdd.py` 仍是唯一状态机；CLI、MCP、hook 和 CI 只调用它。
- BR-002：`approve` 与 `reapprove` 只能由人类执行，必须带 `--human`。
- BR-003：审批摘要只对 `spec.md` 的规范化文本计算，沿用 CRLF/LF 规范化规则。
- BR-004：审批后摘要不一致必须阻断，不得用普通 `complete` 或 `verify` 绕过。
- BR-005：旧 Spec 缺少 `approved_spec_digest` 时必须阻断并给出迁移命令，不能静默放行。
- BR-006：change-set 必须包含变更 ID、原因、FEAT/FR/AC、Task、测试、代码路径、
  风险、回滚和审批状态；引用不存在对象时命令失败。
- BR-007：pending change-set 阻断代码提交；docs-only change-set 显式豁免
  文档变更，但阻断代码提交。
- BR-008：`reapprove` 必须保留历史审批记录，不得覆盖旧摘要。
- BR-009：MERGED 历史 Spec 不因新增字段缺失而失败；新 Spec 不享受该兼容分支。
- BR-010：只使用 Python 标准库；MCP 适配器继续保持薄适配。

## 4. 功能需求与验收条件

### FR-001 审批版本绑定与人工重审

- 功能描述：`approve` 把人类批准与当前 Spec 摘要绑定；摘要变化后阻断，
  并由人类通过 `reapprove` 重新确认。
- 用户场景：需求审批后有人修改 AC 文本，团队需要在改代码前重新获得确认。
- 验收条件：
  - AC-001-1：Given 人类对 DRAFT Spec 执行 `approve` 且 G0/G1 通过，When 读取 `state.json` 和 G0/G1 报告，Then state 记录 `approved_spec_digest`、`approved_at`、`approved_by`、`approval_evidence`，报告记录同一摘要。【执行路径：本地单元测试】
  - AC-001-2：Given Spec 已审批，When 修改 `spec.md` 文本后执行 `check`、`complete` 或 `verify`，Then 返回 `G1-08` 阻断，提示先登记 change-set 再执行 `reapprove`，状态不推进。【执行路径：本地单元测试】
  - AC-001-3：Given 人类执行 `reapprove --human --reason ... --evidence ...` 且 G0/G1 通过，When 查看 state 和审批记录，Then 审批摘要更新为当前 Spec，旧摘要、新摘要、原因、证据、审批人和时间均保留。【执行路径：本地单元测试】
  - AC-001-4：Given 缺少 `--human`、理由为空或旧 Spec 没有 `approved_spec_digest`，When 执行 `reapprove` 或 `check`，Then 命令被拒绝或阻断，并输出包含 Spec ID 和迁移命令的可执行提示。【执行路径：本地单元测试】

### FR-002 只读影响视图

- 功能描述：`sdd impact --json` 从 Spec、tasks 和 design 中提取关联对象与代码路径，
  只读输出稳定的影响视图。
- 用户场景：Agent 和人类在变更前确认会触及哪些 FEAT、FR、AC、Task、测试和代码。
- 验收条件：
  - AC-002-1：Given 有效的 Spec、Design 和 Tasks，When 执行 `sdd impact --json`，Then 返回 `feat_ids`、`fr_ids`、`ac_ids`、`task_ids`、`test_selectors`、`code_paths` 和 `approval_required`。【执行路径：本地单元测试】
  - AC-002-2：Given Spec 或 change-set 引用了不存在的 FR、AC、Task 或 FEAT，When 执行 `impact` 或 `change`，Then `impact` 输出 `missing` 列表，`change` 失败且不写入半成品。【执行路径：本地单元测试】
  - AC-002-3：Given 审批摘要一致且没有 pending change-set，When 执行 `impact`，Then `approval_required=false`；给定摘要不一致或存在 pending change-set，Then `approval_required=true`。【执行路径：本地单元测试】

### FR-003 change-set 先行与提交阻断

- 功能描述：审批后的范围变化必须先登记 change-set，再经人类 `reapprove`，
  之后才允许代码提交；纯文档/配置变更必须显式声明。
- 用户场景：开发者先改代码后补文档时，hook/CI 在本地或流水线阻断。
- 验收条件：
  - AC-003-1：Given 已审批 Spec，When 执行 `sdd change --reason "..."`，Then 创建或追加 `change-set.md`，包含变更 ID、原因、FEAT/FR/AC、Task、测试、代码路径、风险、回滚和 pending 审批状态。【执行路径：本地单元测试】
  - AC-003-2：Given 存在 pending change-set，When 人类执行 `reapprove`，Then change-set 标记为 approved，记录审批人、时间和 Spec 摘要，后续代码提交放行。【执行路径：本地单元测试】
  - AC-003-3：Given 存在 pending change-set 且暂存了代码文件，When 运行 pre-commit 或 CI 检查，Then 返回 `G1-09` 阻断并提示先完成 `reapprove`。【执行路径：本地单元测试】
  - AC-003-4：Given 纯文档/配置变更，When 执行 `sdd change --docs-only --reason "..."`，Then change-set 显式记录 docs-only 豁免且不要求 reapprove；若随后提交代码，Then 仍被阻断。【执行路径：本地单元测试】
  - AC-003-5：Given change-set 缺少必填字段或引用不存在的对象，When 执行 `sdd change`，Then 命令失败、返回具体字段或对象，且不写入新记录。【执行路径：本地单元测试】

### FR-004 边界、兼容与发布

- 功能描述：新动作保持人工边界和架构不变量，历史 Spec 可兼容读取，发布元数据同步。
- 用户场景：平台维护者升级 sdd-kit 后，既有仓库不被历史数据误伤，新仓库获得完整治理。
- 验收条件：
  - AC-004-1：Given `reapprove`、`change` 和 `impact` 命令，When 检查 CLI 与 MCP 暴露面，Then `reapprove` 仅存在于 CLI 且强制 `--human`，MCP 不暴露任何人工动作。【执行路径：本地单元测试】
  - AC-004-2：Given MERGED 历史 Spec 或旧格式 Gate 报告，When 执行 `check --all --stage ci`，Then 不因缺少 `approved_spec_digest` 失败；新 Spec 缺少该字段仍按 AC-001-4 阻断。【执行路径：本地单元测试 + `check --all`】
  - AC-004-3：Given 修改受保护核心与发布元数据，When 执行全量测试、`verify-core`、`verify-agent` 和 CI 检查，Then 版本、manifest、文档与测试一致且全部通过。【执行路径：本地单元测试 + CI】

## 5. 边界与异常

| 场景类型 | 场景描述 | 关联FR/AC | 预期行为（错误码/降级策略/提示信息） |
|---|---|---|---|
| 边界场景 | 审批后只改 AC 文案，不改编号 | FR-001；AC-001-2 | Spec 摘要不一致，`G1-08` 阻断并提示 reapprove |
| 边界场景 | 旧 Spec 无 `approved_spec_digest` | FR-001；AC-001-4 | 阻断并输出 `sdd reapprove --spec ... --human --reason legacy-migration` |
| 边界场景 | 纯文档变更 | FR-003；AC-003-4 | `docs-only` 显式登记后放行文档提交，代码提交仍阻断 |
| 异常场景 | change-set 引用不存在的 AC | FR-002；AC-002-2 | `change` 返回缺失对象并保持原文件不变 |
| 异常场景 | 未带 `--human` 调用 reapprove | FR-001；AC-001-4 | 退出码非 0，不修改 state |
| 异常场景 | 多个 Spec 同时活跃且存在 pending change-set | FR-003；AC-003-3 | 任一活跃 Spec 的 pending 记录均可阻断代码提交 |

## 6. 非功能需求

| 类型 | 要求 | 指标/验收方式 | 关联FR/AC |
|---|---|---|---|
| 性能 | 单次 `impact` 在 1 秒内完成 | 本地单元测试观察 | FR-002；AC-002-1 |
| 安全 | 人工动作强制 `--human`，MCP 不暴露 | CLI/MCP 边界测试 | FR-004；AC-004-1 |
| 可用性 | 错误提示包含 Spec ID、缺失项和下一步命令 | 负向单元测试 | FR-001；AC-001-4 |
| 兼容性 | MERGED 历史 Spec 不被新规则误伤 | `check --all` 回归 | FR-004；AC-004-2 |

## 7. 外部接口

| 方法 | 路径 | 用途 | 归属AC |
|---|---|---|---|
| CLI | `sdd impact --spec <spec> --json` | 只读输出影响视图 | AC-002-1 |
| CLI | `sdd change --spec <spec> --reason <text>` | 创建或追加 change-set | AC-003-1 |
| CLI | `sdd reapprove --spec <spec> --human` | 人工重新确认 Spec 版本 | AC-001-3 |

- 请求/响应示例：`impact` 返回稳定 JSON，字段见 AC-002-1。
- 契约文件：不新增外部网络契约。

## 8. 数据模型

- 核心实体定义：`state.json` 增加 `approved_spec_digest`、`approved_at`、
  `approved_by`、`approval_evidence`；`approvals` 增加 reapprove 记录。
- `change-set.md` 是 Markdown 审计工件，每个 `CHG-NNN` 记录包含审批状态。
- 数据流说明：Spec 文本 -> 规范化 SHA-256 -> state/报告 -> check/hook/CI 比对。

## 9. 约束与假设

- 技术约束：只使用 Python 标准库；状态机仍在 `sdd/scripts/sdd.py`。
- 业务约束：人工动作不得由 Agent 或 MCP 代替。
- 假设条件：审批后的语义变化会体现在 `spec.md` 文本或显式 change-set 中。

## 10. 变更历史

| 日期 | 版本 | 变更内容 | 作者 |
|---|---|---|---|
| 2026-11-23 | 1.0.0 | 初始版本 | SDD Agent |

> 本文件原地修改，以 Git 历史作为物理版本、元数据版本号作为语义版本；禁止创建平行版本文件。

## 11. AI能力规格

不适用（传统产品）。

## 12. 上下文与知识规格

不涉及。

## 13. 统计性验收标准

不涉及。

## 14. AI安全合规

不适用。

## 15. 成本与性能

不涉及。

## 16. 运行监控与效果度量

不涉及。

## 17. 自主程度与人机分工

不适用（仅 AI 原生·L4 产品填写）。

## 18. Agent行为规格

不适用（仅 AI 原生·L4 产品填写）。

## 19. 审计与回放

不适用（仅 AI 原生·L4 产品填写）。

## 20. 多智能体协同

不涉及。

## 21. 自检清单（评审辅助，不作Gate依据）

- [x] Spec ID 格式正确，并与目录名一致。
- [x] 工作项 ID 存在且不含前导 `%`。
- [x] In-Scope 和 Out-of-Scope 均已明确填写。
- [x] FR/AC 编号唯一、稳定，每个 FR 至少包含一条 AC。
- [x] 每条 AC 包含可判定的 Given/When/Then，并可映射到本地单元测试。
- [x] 边界、异常、非功能需求、接口、数据模型和约束均已填写或明确不涉及。
- [x] 残留澄清标记为 0。
- [x] 变更历史已更新，未创建平行版本文件。
