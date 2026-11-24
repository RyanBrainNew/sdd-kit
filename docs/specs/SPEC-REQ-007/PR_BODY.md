# SPEC-REQ-007 只读 sdd view HTML 运行视图

## Spec 文件

- `docs/specs/SPEC-REQ-007/spec.md`
- Issue: `https://github.com/RyanBrainNew/sdd-kit/issues/1`

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
- T-001 新增 `sdd/view.py` 渲染器、`sdd view` CLI 与 board 的 commit/test 字段
- T-002 加固只读性、HTML 转义、错误路径与数据来源边界
- T-003 同步 README、执行手册、Agent 契约、版本与 manifest

## 变更说明

- 高层方案：新增 `sdd/view.py` 渲染模块，`sdd/cli.py` 注册 `view` 子命令。
  渲染器通过 `Workspace` 调用现有 `status`、`events`、`board` JSON，读取
  `gates.md` 表格和 Spec 目录文件列表，拼接 HTML 字符串后写入 `--out`。
- 关键决策：
  1. 数据获取全部复用 `Workspace`（内部子进程调用状态机），不导入 Gate 规则。
  2. `board` JSON 增加只读字段 `commit`、`test`，避免视图重复解析 tasks.md。
  3. Gate 表从 `gates.md` 的固定表头解析，产物哈希来自 `status.state.artifact_hashes`。
  4. HTML 使用一个内联 `<style>`，无 `<script>`、无 `<link>`、无 `src` 外链。
  5. 所有动态文本经 `html.escape()`；工件链接用 `os.path.relpath` 从输出文件计算。
  6. 默认输出 `.sdd/runtime/view/<spec>.html`，父目录不存在时创建。
  7. `sdd/view.py` 加入受保护文件清单，版本升到 0.9.8 并重写 manifest。
- 方案对比：
  - 在 `sdd/scripts/sdd.py` 内直接渲染 HTML：把展示逻辑塞进状态机，放弃。
  - 引入 Jinja2 或前端框架：违反标准库与离线约束，放弃。
  - 用 JavaScript 动态加载 JSON：离线打开受浏览器安全限制，放弃。

## AC 验证清单

| AC | Task | Evidence |
| --- | --- | --- |
| AC-001-1 | T-001 | 见 `docs/specs/SPEC-REQ-007/verification.md` |
| AC-001-2 | T-001 | 见 `docs/specs/SPEC-REQ-007/verification.md` |
| AC-001-3 | T-001 | 见 `docs/specs/SPEC-REQ-007/verification.md` |
| AC-002-1 | T-002 | 见 `docs/specs/SPEC-REQ-007/verification.md` |
| AC-002-2 | T-001 | 见 `docs/specs/SPEC-REQ-007/verification.md` |
| AC-002-3 | T-002 | 见 `docs/specs/SPEC-REQ-007/verification.md` |
| AC-003-1 | T-002 | 见 `docs/specs/SPEC-REQ-007/verification.md` |
| AC-003-2 | T-002 | 见 `docs/specs/SPEC-REQ-007/verification.md` |
| AC-003-3 | T-003 | 见 `docs/specs/SPEC-REQ-007/verification.md` |

## 命令与结果

- 全量测试命令：`python -m unittest discover -s tests -v`
- 视图定向测试：`python -m unittest tests.test_view -v`
- 核心与 Agent 校验：`python -m sdd verify-core`、`python -m sdd verify-agent`
- 结构化证据：`docs/specs/SPEC-REQ-007/verification-evidence.jsonl`

- Evidence recorded: Command: python -m unittest discover -s tests -v

## 未运行 / Not run

None。未执行浏览器人工评审、容器化 runner 或外部 CI 厂商接入，均不在本 Spec 范围。

## 风险与回滚

| 风险 | 影响 | 缓解 | 负责人 |
|---|---|---|---|
| Gate 表格式变化 | 页面缺行 | 按表头解析并对缺列给出告警 | 平台维护者 |
| 事件文件很大 | 页面体积过大 | 只渲染文本，不嵌资源；后续可加分页 | 平台维护者 |
| HTML 注入 | XSS 或页面破坏 | 统一转义并测试 `<script>` 输入 | 平台维护者 |
| 输出路径指向审计文件 | 覆盖 state/events | 默认路径限定 `.sdd/runtime`，显式路径由用户负责 | 平台维护者 |
| board 字段变更 | Task 表缺 commit | 加入兼容测试并保持字段可选 | 平台维护者 |

## Gate 记录

# Gate 记录

| Gate | State | Mode | Result | Evidence | At |
| --- | --- | --- | --- | --- | --- |
| G0 | SPEC_READY | manual | PASS | 需求已确认 | 2026-11-24T14:36:35+08:00 |
| G1 | SPEC_READY | auto | PASS | spec check passed | 2026-11-24T14:36:35+08:00 |
| G2 | DESIGN_READY | auto | PASS | design.md submitted via CLI and checked | 2026-11-24T14:39:30+08:00 |
| G3 | TASKS_READY | auto | PASS | tasks.md submitted via CLI and checked | 2026-11-24T14:41:16+08:00 |
| G4 | VERIFYING | auto | PASS | all tasks completed | 2026-11-24T14:47:49+08:00 |
| G5 | PR_READY | auto | PASS | verification.md submitted via CLI and checked | 2026-11-24T15:24:09+08:00 |

## 证据

- `docs/specs/SPEC-REQ-007/verification.md`
- `docs/specs/SPEC-REQ-007/gates.md`
- `sdd/reports/SPEC-REQ-007/gate1-report.md`
- `sdd/reports/SPEC-REQ-007/gate2-report.md`
- `sdd/reports/SPEC-REQ-007/gate3-report.md`
- `sdd/reports/SPEC-REQ-007/gate4-report.md`
- `sdd/reports/SPEC-REQ-007/gate5-report.md`
