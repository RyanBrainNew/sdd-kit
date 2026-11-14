# SDD Context

这个目录放“AI 需要知道、但代码里不一定显式写出来”的系统事实。  
`sdd_context` MCP 工具会读取这里的 Markdown/YAML/JSON，并和当前 spec 的 `context.md` 一起返回。

最小内容：

- `services.yaml`：服务目录、负责人、依赖、测试/启动命令；
- `services/*.md`：每个服务一页服务卡；
- `contracts/`：OpenAPI、protobuf、事件 schema；
- `adr/`：仍然约束代码的 ADR；
- `glossary.md`：领域术语。

`services.example.yaml`、`adr/ADR-0001.example.md` 和 `glossary.example.md` 是填写样例，接入时改成真实文件。

不要为历史而写历史。只记录仍会影响下一次改动的边界、契约和决策。
