# Python Review Overlay

- 适用范围：允许路径包含 `.py` 文件。
- 通用契约：`sdd/prompts/review/contract.md`。
- 权威依据：PEP 8、PEP 257、项目 `pyproject.toml` / lint 配置、现有测试与 `AGENTS.md`。

## 重点检查

- 异常路径是否保留原始上下文，是否吞掉 `BaseException` 或错误状态。
- 资源是否通过上下文管理器释放；文件、锁、子进程是否在失败时清理。
- 可变默认参数、共享状态、隐式编码和路径拼接是否引入跨环境问题。
- 安全边界：命令执行、反序列化、路径穿越、密钥和日志中的敏感数据。
- 测试是否真实覆盖 AC，是否只验证 mock 调用而没有验证结果。

## Finding 规则

- `location` 精确到文件、函数或行号。
- `authority` 至少引用一条：PEP、项目配置、现有契约或可复现测试。
- 任何可能改变公开行为但缺少回归测试的问题，至少标记为 `medium`。
- 未处理的注入、越权、密钥泄漏或不可信反序列化，标记为 `high` 或 `critical` 并阻断。
