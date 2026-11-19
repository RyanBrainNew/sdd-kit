# SPEC-DEVTOOLS-001 GitHub Pages 官网与开源 README

## Spec 文件

- `docs/specs/SPEC-DEVTOOLS-001/spec.md`
- Issue: `N/A`

## Spec Item 列表

- AC-001-1
- AC-001-2
- AC-001-3
- AC-002-1
- AC-002-2
- AC-002-3
- AC-002-4
- AC-003-1
- AC-003-2
- AC-003-3
- AC-003-4
- AC-004-1
- AC-004-2
- AC-004-3
- AC-005-1
- AC-005-2
- AC-005-3
- AC-005-4
- T-001 实现官网页面结构、文案与视觉系统（`site/index.html`、`site/styles.css`、`site/assets/`）
- T-002 实现站点交互（`site/app.js`）：移动菜单、锚点状态、命令复制、滚动揭示与降级
- T-003 新增 GitHub Pages 发布工作流（`.github/workflows/pages.yml`）
- T-004 重写根 `README.md` 为开源项目首页结构
- T-005 将原 README 迁入 `docs/GUIDE.md` 并修正入口与相对链接
- T-006 新增 `docs/GITHUB-ABOUT.md`，写入仓库 homepage，并执行全量验收

## 变更说明

- 高层方案：新增只含静态资源的 `site/` 目录，使用原生 HTML/CSS/JS 实现单页官网；GitHub Actions 将 `site/` 作为 Pages 制品上传，避免 `docs/specs/` 被发布。根 README 重写为开源项目首页，原 README 正文原样迁入 `docs/GUIDE.md`，只替换文档标题并补充归档说明与入口。
- 关键决策：
  1. 站点独立目录 + Actions 制品发布，而不是 `docs/` 分支发布。理由是 `docs/` 含 Spec 与内部工件，直接发布会造成信息泄露。
  2. 零构建、零外部依赖。理由是 Pages 环境稳定、断网可读、与仓库“只用标准库”的调性一致。
  3. 视觉采用深色开发者工具风格，单一强调色 + 中性灰阶，用状态流动画作为记忆点，不使用紫蓝渐变、emoji 图标或虚构指标。
  4. README 采用“短首页 + 深文档”结构，长文不删除，迁入 `docs/GUIDE.md` 并在 README 首屏给入口。
- 方案对比：
  - 方案 A（采用）：`site/` + Actions Pages。隔离性好、无需构建、可控。
  - 方案 B：把官网放进 `docs/` 并用 Pages 的 `/docs` 发布。配置最少，但会公开 Spec、Gate 报告和上下文，否决。
  - 方案 C：引入 Vite/Astro 构建。视觉上限更高，但新增 Node 依赖与构建链，违背仓库约束，否决。

## AC 验证清单

| AC | Task | Evidence |
| --- | --- | --- |
| AC-001-1 | T-001 | 见 `docs/specs/SPEC-DEVTOOLS-001/verification.md` |
| AC-001-2 | T-001 | 见 `docs/specs/SPEC-DEVTOOLS-001/verification.md` |
| AC-001-3 | T-001 | 见 `docs/specs/SPEC-DEVTOOLS-001/verification.md` |
| AC-002-1 | T-002 | 见 `docs/specs/SPEC-DEVTOOLS-001/verification.md` |
| AC-002-2 | T-001 | 见 `docs/specs/SPEC-DEVTOOLS-001/verification.md` |
| AC-002-3 | T-001 | 见 `docs/specs/SPEC-DEVTOOLS-001/verification.md` |
| AC-002-4 | T-001 | 见 `docs/specs/SPEC-DEVTOOLS-001/verification.md` |
| AC-003-1 | T-004 | 见 `docs/specs/SPEC-DEVTOOLS-001/verification.md` |
| AC-003-2 | T-004 | 见 `docs/specs/SPEC-DEVTOOLS-001/verification.md` |
| AC-003-3 | T-004 | 见 `docs/specs/SPEC-DEVTOOLS-001/verification.md` |
| AC-003-4 | T-004 | 见 `docs/specs/SPEC-DEVTOOLS-001/verification.md` |
| AC-004-1 | T-005 | 见 `docs/specs/SPEC-DEVTOOLS-001/verification.md` |
| AC-004-2 | T-005 | 见 `docs/specs/SPEC-DEVTOOLS-001/verification.md` |
| AC-004-3 | T-005 | 见 `docs/specs/SPEC-DEVTOOLS-001/verification.md` |
| AC-005-1 | T-003 | 见 `docs/specs/SPEC-DEVTOOLS-001/verification.md` |
| AC-005-2 | T-003 | 见 `docs/specs/SPEC-DEVTOOLS-001/verification.md` |
| AC-005-3 | T-006 | 见 `docs/specs/SPEC-DEVTOOLS-001/verification.md` |
| AC-005-4 | T-006 | 见 `docs/specs/SPEC-DEVTOOLS-001/verification.md` |

## 命令与结果

| 命令 | 目录 | 退出码 | 实际结果 |
|---|---|---:|---|
| `python -m unittest discover -s tests -v` | 仓库根目录 | 0 | Ran 74 tests, OK (skipped=2) |
| `python -m unittest tests.test_site -v` | 仓库根目录 | 0 | Ran 27 tests, OK |
| `node --check site/app.js` | 仓库根目录 | 0 | 无语法错误 |
| `python -m sdd verify-core` | 仓库根目录 | 0 | `verify_core passed` |
| `python -m sdd verify-agent` | 仓库根目录 | 0 | `verify_agent passed` |
| `python sdd/scripts/sdd.py verify` | 仓库根目录 | 0 | 提示 `config.json 没有 test_commands`，随后手动执行上述测试 |
| `node .tmp-check.cjs`（Playwright 1.65.1 / Chromium） | 仓库根目录 | 0 | 5 个视口无横向溢出；复制、菜单、reduced-motion、no-JS、焦点均符合预期 |
| `gh repo view RyanBrainNew/sdd-kit --json description,homepageUrl,repositoryTopics` | 仓库根目录 | 0 | description、homepage、topics 已写入 |
| `gh api -X POST repos/RyanBrainNew/sdd-kit/pages -f build_type=workflow` | 仓库根目录 | 1 | HTTP 422：当前计划不支持私有仓库 Pages |
| `python -m sdd check --all --stage ci --check-git --json` | 仓库根目录 | 1 | 运行时尚在 IMPLEMENTING，缺 verification.md、PR_BODY.md 与 commit trailer；`--check-git` 等待人工提交 |

## 未运行 / Not run

- GitHub Actions 的 `pages.yml` 与 `tests.yml` 未在远端实际运行：本次会话不推送、不合并，且仓库为私有、当前计划不支持 Pages。
- `python -m sdd check --all --stage ci --check-git` 的 Git trailer 部分未通过：本会话按约束不创建 Git Commit，需人工提交带 `Spec-Id: SPEC-DEVTOOLS-001` 的 commit 后再执行。
- 未做真实屏幕阅读器走查；已完成语义结构、键盘焦点和 aria 状态的静态与 Playwright 检查。
- 未测试 Safari / Firefox 实机渲染；已测试 Chromium，并使用标准 CSS 与渐进增强实现。

## 风险与回滚

| 风险/依赖 | 影响 | 缓解措施 | 负责人 |
|---|---|---|---|
| 仓库当前为私有，Pages 可能无法启用 | About 链接暂时 404 | 交付时明确两种解锁方式；站点文件可本地直接打开；工作流先合入 | 仓库管理员 |
| 旧 README 迁移后出现链接或命令走样 | 团队查阅受阻 | 文件级复制、命令抽样 diff、链接检查 | Agent |
| 重写 README 丢失关键事实 | 新成员误解流程 | 保留 GUIDE 全文，README 只做摘要并链接 | Agent |
| Pages 默认地址包含仓库名，资源写死绝对路径会 404 | 站点样式丢失 | 全部资源相对路径，避免根路径 `/` | Agent |
| 视觉动效影响低端设备或晕动症用户 | 可访问性下降 | 仅 transform/opacity，提供 reduced-motion 关闭 | Agent |

## Gate 记录

# Gate 记录

| Gate | State | Mode | Result | Evidence | At |
| --- | --- | --- | --- | --- | --- |
| G0 | SPEC_READY | manual | PASS | 需求已确认 | 2026-11-19T15:54:12+08:00 |
| G1 | SPEC_READY | auto | PASS | spec check passed | 2026-11-19T15:54:12+08:00 |
| G2 | DESIGN_READY | auto | PASS | design.md submitted via CLI and checked | 2026-11-19T15:55:47+08:00 |
| G3 | TASKS_READY | auto | PASS | tasks.md submitted via CLI and checked | 2026-11-19T15:57:20+08:00 |
| G4 | VERIFYING | auto | PASS | all tasks completed | 2026-11-19T16:22:18+08:00 |
| G5 | PR_READY | auto | PASS | verification.md submitted via CLI and checked | 2026-11-19T16:24:09+08:00 |

## 证据

- `docs/specs/SPEC-DEVTOOLS-001/verification.md`
- `docs/specs/SPEC-DEVTOOLS-001/gates.md`
- `sdd/reports/SPEC-DEVTOOLS-001/gate1-report.md`
- `sdd/reports/SPEC-DEVTOOLS-001/gate2-report.md`
- `sdd/reports/SPEC-DEVTOOLS-001/gate3-report.md`
- `sdd/reports/SPEC-DEVTOOLS-001/gate4-report.md`
- `sdd/reports/SPEC-DEVTOOLS-001/gate5-report.md`
