# Gate 记录

| Gate | State | Mode | Result | Evidence | At |
| --- | --- | --- | --- | --- | --- |
| G0 | SPEC_READY | manual | PASS | 需求已确认 | 2026-11-23T11:01:13+08:00 |
| G1 | SPEC_READY | auto | PASS | spec check passed | 2026-11-23T11:01:13+08:00 |
| G2 | DESIGN_READY | auto | PASS | design.md submitted via CLI and checked | 2026-11-23T11:18:31+08:00 |
| G3 | TASKS_READY | auto | PASS | tasks.md submitted via CLI and checked | 2026-11-23T11:22:10+08:00 |
| G4 | VERIFYING | auto | FAILED | 标准符合性、文档/协议/版本/manifest 收口完成；独立审查 HIGH 问题已修复并回归通过；全量 134 项测试 132 通过、2 跳过；补充 python -m sdd verify CLI 入口。 | 2026-11-23T14:04:43+08:00 |
| G4 | VERIFYING | auto | FAILED | T-001 至 T-010 全部完成；G4 复核通过；补充追加章节回归测试和 python -m sdd verify CLI 入口。 | 2026-11-23T14:05:41+08:00 |
| G4 | VERIFYING | auto | PASS | T-001 至 T-010 全部完成；G4 复核通过；补充章节追加与 Python AST 测试扫描回归。 | 2026-11-23T14:06:52+08:00 |
| G5 | PR_READY | auto | PASS | 全量 138 项测试 136 通过、2 跳过；sdd verify 证据与 AC 覆盖通过；独立审查和事件链有效。 | 2026-11-23T14:14:49+08:00 |
