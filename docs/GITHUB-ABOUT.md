# GitHub About 配置

> 本文件是仓库 About 区的配置素材，修改后按下方命令写入 GitHub。
> 官网内容位于 `site/`，由 `.github/workflows/pages.yml` 发布。

## Description

把公司 SDD-L2 流程装进仓库：一个 CLI、一套状态机、任何 Agent 都能接入。

## Topics

```text
sdd
spec-driven-development
ai-agents
developer-tools
workflow-automation
agents-md
cli
python
mcp
code-review
```

## Homepage

```text
https://ryanbrainnew.github.io/sdd-kit/
```

## License

```text
Apache-2.0
```

许可证全文见仓库根目录 `LICENSE`。GitHub 会在仓库首页自动识别并展示。

## 写入命令

```powershell
gh repo edit RyanBrainNew/sdd-kit `
  --description "把公司 SDD-L2 流程装进仓库：一个 CLI、一套状态机、任何 Agent 都能接入。" `
  --homepage "https://ryanbrainnew.github.io/sdd-kit/" `
  --add-topic sdd `
  --add-topic spec-driven-development `
  --add-topic ai-agents `
  --add-topic developer-tools `
  --add-topic workflow-automation `
  --add-topic agents-md `
  --add-topic cli `
  --add-topic python `
  --add-topic mcp `
  --add-topic code-review
```

## 前置条件

- 仓库已转公开。
- Pages 已启用为 `GitHub Actions` 构建（`build_type: workflow`，源分支 `main`）。
- 站点文件合并到 `main` 并触发 `pages.yml` 后，Homepage 才会返回 200；在此之前访问为 404。

## Social preview

GitHub 的 Social preview 需要 1280×640 的 PNG/JPG/SVG。站点 logo 不能直接作为 Social preview；
如需完整门面，可在 `Settings -> Social preview` 上传一张同主题的 1280×640 图片。
