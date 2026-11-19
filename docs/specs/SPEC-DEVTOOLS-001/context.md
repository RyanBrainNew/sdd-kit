# 需求上下文

- Work item: `SDD-GH-001`

## 原始需求

参照主流开源项目，为 sdd-kit 建立 GitHub Pages 介绍站，并重写 README

## 调研事实

- 本仓库是 `sdd-kit` 源仓库，当前核心版本 `0.6.1`（`sdd/VERSION`），定位是公司 SDD-L2 的仓库自带工作流；业务仓库通过 `bootstrap.py` 一次性接入，不直接修改核心。
- 仓库只使用 Python 标准库；MCP 依赖隔离在 `sdd/mcp/requirements.txt`。验证命令为 `python -m unittest discover -s tests -v`、`python -m sdd verify-core`、`python -m sdd verify-agent`、`python -m sdd check --all --stage ci --check-git`。
- 当前 GitHub 远端为 `RyanBrainNew/sdd-kit`，默认分支 `main`，仓库可见性为 `PRIVATE`，`homepageUrl` 为空，尚未启用 Pages。
- 仓库根目录没有 `LICENSE`，没有 `.github/` 目录；现有 CI 模板位于 `ci/kit-tests.yml` 和 `sdd/ci/github-actions.yml`。
- 现有 `README.md` 约 31 KB，内容覆盖架构、接入、CLI 全链路、MCP、FAQ，属于长篇执行手册，缺少开源项目常见的短首页结构（徽章、Quickstart、文档导航、贡献入口）。
- 现有可复用文档：`ARCHITECTURE.md`、`ADOPTION.md`、`LANDSCAPE.md`、`sdd/README.md`、`sdd/agent-contract.md`、`dsh/README.md`、`deploy/README.md`。
- 站点不能把 `docs/specs/` 一并发布：Spec、Context、Gate 报告属于内部工件，公开站点只能包含面向访客的营销与文档内容。
- GitHub Pages 对私有仓库需要付费计划；对公开仓库可直接使用 GitHub Actions 发布静态站点。仓库是否转公开由人决定，不在 Agent 权限内。
- 当前登录的 `gh` 账号为 `RyanBrainNew`，具备 `repo` 与 `workflow` scope，可创建 Pages workflow 和修改仓库 homepage 字段。

## 未决问题

- 是否将仓库转为公开、以及是否采用某种开源许可证，属于人的决策；本次交付按“站点可发布、README 可公开阅读”设计，不替代人做可见性与许可证决定。
