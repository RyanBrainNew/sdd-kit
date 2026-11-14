# dsh 接入

优先把 dsh 当 MCP 客户端，不要为 dsh 复制一套 SDD 逻辑。

## 两种配置

### 本地 clone 模式（推荐现在）

每个开发者的 dsh 启动本地 stdio MCP：

```json
{
  "mcpServers": {
    "sdd-local": {
      "command": "python",
      "args": [
        "-m",
        "sdd.mcp.server",
        "--root",
        ".",
        "--transport",
        "stdio"
      ],
      "cwd": "."
    }
  }
}
```

`--root .` 让 MCP 只操作当前仓库，状态写进当前分支，不需要把代码放服务端。

### 共享服务端模式（后期）

如果 dsh 支持 MCP server 配置，加入：

```json
{
  "mcpServers": {
    "sdd": {
      "url": "https://sdd-mcp.intra.example.com/mcp",
      "transport": "streamable-http"
    }
  }
}
```

具体字段名以 dsh 的 MCP 配置为准；核心是 URL 和 streamable-http。

## Agent 作业单

在 dsh 的系统提示或项目规则里加入：

```text
你是 SDD 执行器。开发者只给一个工作项，不负责判断 SDD 阶段。
1. 新需求调用 sdd_start_work(work_item)；恢复调用 sdd_session。
2. 读取返回的 next.action、next.prompt、next.artifact。
3. 调研并产出当前 artifact；需要上下文时调用 sdd_context。
4. 阶段产物用 sdd_submit_artifact；Task 用 sdd_submit_task。
5. 读取返回的 next；ok=false 就按 errors 修复后重提。
6. 只有 human_checkpoint.required=true 时停下，请人 approve spec 或 merge PR。
不要每阶段问开发者“现在到哪一步”；不要调用 approve/merge；不要改 state.json；
不要伪造测试结果。
```

## 插件/hook 应该做什么

如果 dsh 有插件 API，只做薄适配：

- `session_start`：有工作项时调用 `sdd_start_work`，否则调用 `sdd_session`，注入当前作业单；
- `user_prompt_submit`：把“根据 issue xxx 开发”转成一次 `sdd_start_work`，不要转成阶段命令；
- 提供 `/sdd status`、`/sdd context`、`/sdd report`；
- `before_commit`：检查 `Spec-Id` / `Task-Id`；
- `before_finish`：调用 `sdd_check`，不通过不允许结束（submit 工具已经做过强校验）；
- `before_push`：禁止 push 默认分支。

不要把状态机、模板、Gate 规则写进 dsh 插件；这些应该在 `sdd-core` 和 MCP server 里。

## 没有插件 API 时

让 dsh 通过 MCP 调用工具即可。  
如果连 MCP 也不支持，就在 dsh 的 shell 工具里调用本地 `sdd` CLI；MCP 只做共享状态/上下文。
