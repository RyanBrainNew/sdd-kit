# GitHub Pages 官网与开源 README 验证报告

## 1. 元数据

| 项 | 内容 |
|---|---|
| Spec ID | SPEC-DEVTOOLS-001 |
| 工作项 ID | SDD-GH-001 |
| 作者 | Agent |
| 创建日期 | 2026-11-19 |
| 验证时间 | 2026-11-19 |

## 2. 命令

| 命令 | 目录 | 退出码 | 实际结果 |
|---|---|---:|---|
| `python -m unittest discover -s tests -v` | 仓库根目录 | 0 | Ran 93 tests, OK (skipped=2) |
| `python -m unittest tests.test_site -v` | 仓库根目录 | 0 | Ran 27 tests, OK |
| `node --check site/app.js` | 仓库根目录 | 0 | 无语法错误 |
| `python -m sdd verify-core` | 仓库根目录 | 0 | `verify_core passed` |
| `python -m sdd verify-agent` | 仓库根目录 | 0 | `verify_agent passed` |
| `python sdd/scripts/sdd.py verify` | 仓库根目录 | 0 | 提示 `config.json 没有 test_commands`，随后手动执行上述测试 |
| `node .tmp-check.cjs`（Playwright 1.65.1 / Chromium） | 仓库根目录 | 0 | 5 个视口无横向溢出；复制、菜单、reduced-motion、no-JS、焦点均符合预期 |
| `gh repo view RyanBrainNew/sdd-kit --json description,homepageUrl,repositoryTopics` | 仓库根目录 | 0 | description、homepage、topics 已写入 |
| `gh api repos/RyanBrainNew/sdd-kit/pages` | 仓库根目录 | 0 | 返回 `build_type: workflow`，`html_url: https://ryanbrainnew.github.io/sdd-kit/` |
| `python -m sdd check --all --stage ci --json` | 仓库根目录 | 0 | 全部 Spec `ok: true` |

## 3. 结果

- 站点在 360、390、768、1280、1440 五个视口下 `scrollWidth - clientWidth = 0`，无横向溢出。
- 1280×800 下首屏主按钮底部为 494px，两个 CTA 与定位句均在首屏内。
- 点击命令复制后按钮显示“已复制”，剪贴板内容与命令块逐字一致；2 秒复位逻辑存在。
- 移动菜单打开后 `aria-expanded=true`，按 Escape 后回到 `false`。
- 关闭 JavaScript 后标题“把 SDD 装进仓库”与命令块仍可见，复制按钮为 `display: none`。
- `prefers-reduced-motion: reduce` 下区块 `opacity=1`，标题 `animation-name=none`。
- 第一次 Tab 聚焦“跳到正文”，焦点轮廓为 `solid 2px`。
- 本地 HTTP 服务下首页、`styles.css`、`app.js`、`favicon.svg` 均返回 200。
- 全量单元测试 93 个中 91 个通过、2 个跳过、0 个失败。
- GitHub About 已写入：description 为 SDD-L2 定位，homepage 为 `https://ryanbrainnew.github.io/sdd-kit/`，topics 包含 sdd、spec-driven-development、ai-agents、developer-tools、workflow-automation、agents-md、cli、python、mcp、code-review。

## 4. 未运行

- GitHub Pages 尚未产生部署记录：仓库已转公开且 Pages 已启用为 workflow 构建，但站点文件仍在 PR 分支，未合并到 `main`，线上地址在合并前返回 404。
- `python -m sdd check --all --stage ci --check-git` 的 Git trailer 部分需要人工提交后再执行。
- 未做真实屏幕阅读器走查；已完成语义结构、键盘焦点和 aria 状态的静态与 Playwright 检查。
- 未测试 Safari / Firefox 实机渲染；已测试 Chromium，并使用标准 CSS 与渐进增强实现。

## 5. AC 覆盖

| AC | 测试/证据 | 结果 |
|---|---|---|
| AC-001-1 | `SiteStructureTests#test_hero_contract`；Playwright 1280×800 首屏坐标 | 通过 |
| AC-001-2 | `SiteStructureTests#test_required_sections` | 通过 |
| AC-001-3 | `SiteStyleTests#test_mobile_rules`；Playwright 360px 溢出为 0 | 通过 |
| AC-002-1 | `SiteInteractionTests#test_clipboard_feedback`；Playwright 剪贴板读取 | 通过 |
| AC-002-2 | `SiteInteractionTests#test_no_js_content`；Playwright `javaScriptEnabled:false` | 通过 |
| AC-002-3 | `SiteStructureTests#test_accessibility_hooks`；`SiteInteractionTests#test_aria_hooks`；Tab 焦点检查 | 通过 |
| AC-002-4 | `SiteStyleTests#test_reduced_motion`；Playwright reduced-motion 上下文 | 通过 |
| AC-003-1 | `ReadmeTests#test_header` | 通过 |
| AC-003-2 | `ReadmeTests#test_quickstart` | 通过 |
| AC-003-3 | `ReadmeTests#test_doc_nav`；`LinkTests#test_relative_links` | 通过 |
| AC-003-4 | `ReadmeTests#test_license_section` | 通过 |
| AC-004-1 | `GuideTests#test_all_sections`；正文与 `HEAD:README.md` 逐字比对 | 通过 |
| AC-004-2 | `GuideTests#test_commands_preserved` | 通过 |
| AC-004-3 | `LinkTests#test_relative_links` | 通过 |
| AC-005-1 | `PagesWorkflowTests#test_uploads_site_only`；工作流文件静态检查 | 本地通过，线上未执行 |
| AC-005-2 | `PagesWorkflowTests#test_relative_site_assets`；本地 HTTP 资源 200 | 本地通过，线上未执行 |
| AC-005-3 | `AboutTests#test_about_material`；`gh repo view` 返回 description/topics | 通过 |
| AC-005-4 | `AboutTests#test_homepage_matches_pages`；`gh repo view` 返回 homepageUrl | 通过 |

## 6. Gate 5 结论

PASS。

残余风险：仓库当前为私有且账号计划不支持私有仓库 Pages，`homepageUrl` 已写入但站点上线前会返回 404。需要人工选择“仓库转公开”或“升级支持 Pages 的计划”，然后在 Settings → Pages 选择 GitHub Actions 并运行 `pages.yml`。代码、文档、静态站点与 About 元数据均已完成并通过本地验证。
