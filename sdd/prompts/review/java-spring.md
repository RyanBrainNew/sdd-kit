# Java / Spring Review Overlay

- 适用范围：允许路径包含 `.java` 或 `.kt` 文件。
- 通用契约：`sdd/prompts/review/contract.md`。
- 权威依据：Spring Framework / Spring Boot 官方文档、项目构建配置、接口契约与现有测试。

## 重点检查

- Controller、Service、Repository 边界是否清晰，事务是否覆盖正确的业务边界。
- 空值、异常映射、幂等、并发和重复提交是否处理。
- 输入校验、鉴权、越权访问、SQL/JPQL 注入和敏感信息日志。
- 配置项是否有安全默认值；生产配置是否误用调试或开放策略。
- 测试是否验证 HTTP 契约、事务回滚和真实持久化行为，而非只验证 mock。

## Finding 规则

- `location` 精确到类、方法、配置键或接口路径。
- `authority` 至少引用一条：官方文档、接口契约、项目规范或可复现测试。
- 事务边界错误、鉴权缺失、数据损坏风险标记为 `high` 或 `critical` 并阻断。
- 只影响内部实现且不改变行为的问题可以标记为 `low` 或 `medium`。
