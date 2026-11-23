# 需求上下文

- Work item: `SDD-HASH-001`
- Issue: https://github.com/RyanBrainNew/sdd-kit/issues/15

## 原始需求

修复文本工件哈希对 CRLF/LF 敏感的问题，兼容历史哈希，并让 GitHub Actions 执行 SDD 三项检查。

## 调研事实

- `.gitattributes` 规定 `* text=auto eol=lf`；仓库文本的规范行尾是 LF。
- `sdd/scripts/sdd.py` 的 `sha256_file()` 直接对 `path.read_bytes()` 计算 SHA-256，未规范化行尾。
- `artifact_digest()`、`check_gates()`、审批记录和 rewind 归档都复用该哈希逻辑。
- `SPEC-DEVTOOLS-002/state.json` 记录的是 Windows CRLF 内容哈希：
  - `spec.md` 记录 `4ba6e8d3...`，CRLF 工作区匹配，LF 工作区不匹配。
  - `design.md` 记录 `c4ca0d02...`，CRLF 工作区匹配，LF 工作区不匹配。
  - `verification.md` 记录 `342152cb...`，CRLF 工作区匹配，LF 工作区不匹配。
- `tasks.md#plan` 使用结构化 `task_plan_hash()`，不受行尾影响，因此 G3/G4 未报错。
- `python -m sdd check --all --stage ci --check-git` 在 `main` 的 LF 工作区失败，在同一提交的 CRLF 工作区通过。
- `.github/workflows/tests.yml` 当前只运行 `python -m unittest discover -s tests -v`，没有执行 `verify-core`、`verify-agent` 或 `check --all`。
- `AGENTS.md`、`README.md` 和 `sdd/agent-contract.md` 已声明 CI 应执行上述 SDD 门禁，但实际工作流未对齐。
- 项目只允许 Python 标准库；核心修改必须同步测试、README、`sdd/agent-contract.md`、版本和 manifest。

## 影响范围

- 核心：`sdd/scripts/sdd.py` 的文本工件哈希与兼容校验。
- 测试：`tests/test_sdd.py` 的 Gate 哈希回归测试。
- CI：`.github/workflows/tests.yml` 增加 SDD 门禁步骤。
- 文档：`README.md`、`sdd/README.md`、`sdd/agent-contract.md` 说明跨平台哈希和 CI 行为。
- 发布：`sdd/VERSION`、`sdd/__init__.py`、`sdd/manifest.json`。

## 约束与排除

- 不手改 `state.json` 或 `events.jsonl`。
- 不改变唯一状态机和人工动作边界。
- 不对二进制工件做文本规范化。
- 不重新执行历史 Spec 的 Gate。
