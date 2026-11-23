# 工件哈希 CRLF/LF 规范化与 SDD CI 门禁对齐验证报告

## 1. 元数据

| 项 | 内容 |
|---|---|
| Spec ID | SPEC-REQ-001 |
| 工作项 ID | SDD-HASH-001 |
| 作者 | SDD Agent |
| 创建日期 | 2026-11-23T11:10:05+08:00 |
| 验证时间 | 2026-11-23T11:10:05+08:00 |

## 2. 命令

<!-- TODO: 记录实际执行的命令、目录和退出码；sdd verify 会自动追加命令证据。 -->

- 待填写

## 3. 结果

- Evidence recorded: Task T-003

### Task T-003

- At: 2026-11-23T11:46:34+08:00

python -m unittest tests.test_ci_contract -v -> Ran 1 test OK; python -m sdd verify-core -> passed; python -m sdd verify-agent -> passed; GitHub Actions 已包含 verify-core、verify-agent、check --all --stage ci --check-git，版本升至 0.9.2，manifest 43 files

### Task T-002

- At: 2026-11-23T11:42:42+08:00

python -m unittest tests.test_sdd.ArtifactHashTests -v -> Ran 6 tests OK; 历史 CRLF 哈希可在 LF 文件通过，正文变化仍阻断，新 Gate 记录使用 LF 哈希

### Task T-001

- At: 2026-11-23T11:40:55+08:00

python -m unittest tests.test_sdd.ArtifactHashTests -v -> Ran 3 tests OK; python -m unittest tests.test_sdd -v -> Ran 54 tests OK; CRLF/LF 哈希一致，行尾变化不报修改，正文变化仍阻断

## 4. 未运行

None。

## 5. AC 覆盖

<!-- TODO: 每个 AC 一行，写 AC -> 测试/证据映射。 -->

| AC | 测试/证据 | 结果 |
|---|---|---|
| AC-001-1 | 待填写 | 待填写 |

## 6. Gate 5 结论

<!-- TODO: 填 PASS 或 FAILED，并说明残余风险。 -->

待填写。
