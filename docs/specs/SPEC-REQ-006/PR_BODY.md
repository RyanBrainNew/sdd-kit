# SPEC-REQ-006 外部 runner 接入契约

## Spec 文件

- `docs/specs/SPEC-REQ-006/spec.md`
- Issue: `https://github.com/RyanBrainNew/sdd-kit/issues/2`

## Spec Item 列表

- AC-001-1
- AC-001-2
- AC-001-3
- AC-002-1
- AC-002-2
- AC-002-3
- AC-003-1
- AC-003-2
- AC-003-3
- T-001 编写 `deploy/runner/CONTRACT.md` 七阶段契约、失败语义、人工边界、职责与示例，并新增结构测试
- T-002 在 `README.md` 与 `sdd/README.md` 增加契约入口，并新增入口链接测试
- T-003 回归 MCP 人工动作边界与发布元数据一致性，确认未修改受保护核心

## 变更说明

- 高层方案：契约文档作为唯一入口，按“准备 -> 启动 -> 读取 -> 执行 -> 提交 ->
  检查点 -> 归档”线性组织；每一步只引用现有 CLI 和 `next` 字段，不复制
  Gate 规则，也不定义第二套状态枚举。
- 关键决策：
  1. 契约只描述 runner 如何消费 CLI 输出，阶段名称、`next.action` 和检查点判断
     全部以 `sdd resume --json` 返回值为准。
  2. 用一张“返回类型 -> runner 行为 -> 退出语义”表格覆盖成功、`ok=false`、
     `decision_required`、`awaiting_human_approval` 四类结果。
  3. 人工动作边界以显式清单列出六个命令，并引用 `sdd/agent-block.md` 的托管规则。
  4. Docker、沙箱、网络、密钥、资源限制和日志归档明确归 runner，核心只提供
     Python 标准库 CLI。
  5. 示例使用 `sdd start-work`、`sdd resume`、`sdd submit`、`sdd submit-task`、
     `sdd complete`，不出现内部模块调用。
  6. 文档一致性测试直接读取 Markdown，断言章节、关键词和命令存在，避免契约漂移。
- 方案对比：
  - 把契约写进 `sdd/agent-contract.md`：该文件面向 Agent 且受 manifest 保护，
    每次改文档都要升版本，职责也不匹配，放弃。
  - 生成 HTML 或站点页面：离线不可评审，且与 issue 要求的 Markdown 契约不符，放弃。
  - 只写 README 段落：无法承载失败语义和伪代码，放弃。

## AC 验证清单

| AC | Task | Evidence |
| --- | --- | --- |
| AC-001-1 | T-001 | 见 `docs/specs/SPEC-REQ-006/verification.md` |
| AC-001-2 | T-001 | 见 `docs/specs/SPEC-REQ-006/verification.md` |
| AC-001-3 | T-001 | 见 `docs/specs/SPEC-REQ-006/verification.md` |
| AC-002-1 | T-001 | 见 `docs/specs/SPEC-REQ-006/verification.md` |
| AC-002-2 | T-001 | 见 `docs/specs/SPEC-REQ-006/verification.md` |
| AC-002-3 | T-001 | 见 `docs/specs/SPEC-REQ-006/verification.md` |
| AC-003-1 | T-002 | 见 `docs/specs/SPEC-REQ-006/verification.md` |
| AC-003-2 | T-003 | 见 `docs/specs/SPEC-REQ-006/verification.md` |
| AC-003-3 | T-003 | 见 `docs/specs/SPEC-REQ-006/verification.md` |

## 命令与结果

- 全量测试命令：`python -m unittest discover -s tests -v`
- 核心与 Agent 校验：`python -m sdd verify-core`、`python -m sdd verify-agent`
- 结构化证据：`docs/specs/SPEC-REQ-006/verification-evidence.jsonl`

- Evidence recorded: Command: python -m unittest discover -s tests -v

## 未运行 / Not run

None。未执行容器化 runner、外部 CI 厂商接入或客户端浏览器人工评审，
这些均不在本 Spec 范围内。

## 风险与回滚

| 风险 | 影响 | 缓解 | 负责人 |
|---|---|---|---|
| 契约与 CLI 后续演进不一致 | runner 按旧顺序调用失败 | 文档测试断言关键命令；改 CLI 时同步契约 | 平台维护者 |
| 读者把契约当第二套状态机 | 出现自造阶段判断 | 每阶段强调以 `next` 为准，禁止硬编码状态 | 平台维护者 |
| 示例复制到 Windows 以外环境 | 命令不可执行 | 注明 PowerShell 与等价 shell 的替换方式 | 平台维护者 |
| 文档膨胀成 runner 实现教程 | 维护成本上升 | 明确非目标，容器细节只列职责不展开 | 平台维护者 |

## Gate 记录

# Gate 记录

| Gate | State | Mode | Result | Evidence | At |
| --- | --- | --- | --- | --- | --- |
| G0 | SPEC_READY | manual | PASS | 需求已确认 | 2026-11-24T11:24:39+08:00 |
| G1 | SPEC_READY | auto | PASS | spec check passed | 2026-11-24T11:24:39+08:00 |
| G2 | DESIGN_READY | auto | PASS | design.md submitted via CLI and checked | 2026-11-24T11:30:37+08:00 |
| G3 | TASKS_READY | auto | PASS | tasks.md submitted via CLI and checked | 2026-11-24T11:32:52+08:00 |
| G4 | VERIFYING | auto | PASS | all tasks completed | 2026-11-24T11:36:11+08:00 |
| G5 | PR_READY | auto | PASS | verification.md submitted via CLI and checked | 2026-11-24T12:10:21+08:00 |

## 证据

- `docs/specs/SPEC-REQ-006/verification.md`
- `docs/specs/SPEC-REQ-006/gates.md`
- `sdd/reports/SPEC-REQ-006/gate1-report.md`
- `sdd/reports/SPEC-REQ-006/gate2-report.md`
- `sdd/reports/SPEC-REQ-006/gate3-report.md`
- `sdd/reports/SPEC-REQ-006/gate4-report.md`
- `sdd/reports/SPEC-REQ-006/gate5-report.md`
