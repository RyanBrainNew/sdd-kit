import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


KIT_ROOT = Path(__file__).resolve().parents[1]
SPEC_ID = "SPEC-ORDER-001"

SPEC_TEXT = """# 订单取消规格说明书（Spec）

## 1. 元数据

| 项 | 内容 |
|---|---|
| Spec ID | SPEC-ORDER-001 |
| 工作项 ID | srdcloud-553377 |
| 原始需求来源 | https://example.invalid/item/553377 |
| 作者 | SDD Agent |
| 创建日期 | 2026-11-14 |
| 状态 | Draft |
| 版本号 | 1.0.0 |
| 产品类型 | 传统产品 |
| 模板适配 | 核心骨架 |
| 关联人 | 产品负责人：张三；技术负责人：李四 |
| 原型版本 | 不涉及 |

## 2. 范围声明

- In-Scope：支持用户取消未支付订单。
- Out-of-Scope：不支持已支付订单退款。

## 3. 业务上下文

### 3.1 干系人与角色

| 角色 | 诉求 | 使用场景 | 责任边界 |
|---|---|---|---|
| 买家 | 取消误下单 | 订单详情页 | 只能取消自己的订单 |

### 3.2 业务流程

用户打开订单详情，点击取消，系统校验状态并更新为已取消。

### 3.3 业务规则

- BR-001：只有待支付订单可以取消。

## 4. 功能需求与验收条件

### FR-001 取消未支付订单

- 功能描述：系统允许用户取消自己的待支付订单。
- 用户场景：买家在订单详情页点击取消。
- 验收条件：
  - AC-001-1：Given 用户拥有待支付订单，When 用户取消订单，Then 订单状态变为已取消且返回成功。【执行路径：本地单元测试】

### 4.1 UI规格（涉及前端UI时必填）

不涉及。

## 5. 边界与异常

| 场景类型 | 场景描述 | 关联FR/AC | 预期行为（错误码/降级策略/提示信息） |
|---|---|---|---|
| 边界场景 | 订单已支付 | FR-001；AC-001-1 | 返回业务错误，不修改状态 |
| 异常场景 | 订单不属于当前用户 | FR-001；AC-001-1 | 返回权限错误 |

## 6. 非功能需求

| 类型 | 要求 | 指标/验收方式 | 关联FR/AC |
|---|---|---|---|
| 性能 | 单次取消小于 500ms | 单元测试/压测 | FR-001 |
| 安全 | 校验订单归属 | 单元测试 | FR-001；AC-001-1 |
| 可用性 | 不涉及 | 不涉及 | 不涉及 |

## 7. 外部接口

| 方法 | 路径 | 用途 | 归属AC |
|---|---|---|---|
| POST | /orders/{id}/cancel | 取消订单 | AC-001-1 |

- 请求/响应示例：见接口契约。
- 契约文件：`docs/specs/SPEC-ORDER-001/api/order.yaml`

## 8. 数据模型

- 核心实体定义：Order 增加 cancelledAt 字段。
- 数据流说明：取消后写入状态和取消时间。

## 9. 约束与假设

- 技术约束：复用现有订单服务。
- 业务约束：不改支付流程。
- 假设条件：订单状态字段已存在。

## 10. 变更历史

| 日期 | 版本 | 变更内容 | 作者 |
|---|---|---|---|
| 2026-11-14 | 1.0.0 | 初始版本 | SDD Agent |

## 11. AI能力规格

不适用

## 12. 上下文与知识规格

不涉及

## 13. 统计性验收标准

不涉及

## 14. AI安全合规

不适用

## 15. 成本与性能

不涉及

## 16. 运行监控与效果度量

不涉及

## 17. 自主程度与人机分工

不适用

## 18. Agent行为规格

不适用

## 19. 审计与回放

不适用

## 20. 多智能体协同

不涉及

## 21. 自检清单（评审辅助，不作Gate依据）

- [x] 已自检。
"""

DESIGN_TEXT = """# 订单取消设计文档（Design）

## 1. 元数据

| 项 | 内容 |
|---|---|
| Spec ID | SPEC-ORDER-001 |
| 关联Spec | `docs/specs/SPEC-ORDER-001/spec.md` |
| 作者 | SDD Agent |
| 创建日期 | 2026-11-14 |
| 状态 | Draft |
| 评审人 | 李四 |

## 2. 设计目标

- 核心问题：安全取消未支付订单。
- 设计范围：订单服务取消接口与状态变更。
- 非设计范围：退款、支付回调。

## 3. 方案概述

- 高层方案：在订单服务中增加取消方法和状态机校验。
- 关键决策：复用既有订单仓储，不新增表。
- 方案对比：方案 A 新增取消表，方案 B 复用订单表；选择 B，避免重复事实源。

## 4. Spec覆盖关系

| FR/AC | 设计章节/模块 | 实现方式 | 验证方式 |
|---|---|---|---|
| FR-001 / AC-001-1 | 订单服务 | 校验状态和归属后更新状态 | 单元测试 |

## 5. 系统架构

### 5.1 架构图

Controller -> OrderService -> OrderRepository。

### 5.2 模块划分

| 模块/服务 | 职责 | 输入 | 输出 | 依赖 |
|---|---|---|---|---|
| OrderService | 取消订单 | 用户、订单 ID | 更新后的订单 | OrderRepository |

### 5.3 模块间交互

同步调用，事务边界在 OrderService。

## 6. 数据模型

- 实体定义：Order 已有 status 字段，新增 cancelledAt。
- 数据库变更：增加 cancelled_at 字段。
- 事务边界：状态与时间同事务更新。
- 迁移方案：可为空字段，无需回填。

## 7. 接口契约

| 方法 | 路径 | 描述 | 归属AC |
|---|---|---|---|
| POST | /orders/{id}/cancel | 取消订单 | AC-001-1 |

- 请求/响应结构：见 `api/order.yaml`。
- 错误码：ORDER_NOT_CANCELLABLE、FORBIDDEN。
- 兼容性：新增接口，不影响旧接口。
- 契约文件：`docs/specs/SPEC-ORDER-001/api/order.yaml`

## 8. 认证、授权、幂等与安全

- 认证：复用网关身份。
- 授权：校验订单归属。
- 幂等：按订单 ID 重复取消返回当前状态。
- 敏感数据：不记录支付凭证。
- 审计：记录取消操作日志。

## 9. 关键决策ADR

- 引用：`docs/specs/SPEC-ORDER-001/adrs/ADR-001.md`
- 判断依据：复用订单表是重要取舍。

## 10. 非功能需求设计

- 性能设计：单次更新，走订单主键索引。
- 可用性设计：失败返回明确错误，不修改状态。
- 可观测性：记录订单 ID 和用户 ID 的脱敏日志。

## 11. 依赖与风险

| 风险/依赖 | 影响 | 缓解措施 | 负责人 |
|---|---|---|---|
| 并发取消 | 可能重复更新 | 状态条件更新和幂等处理 | 李四 |

## 12. 回滚方案

- 触发条件：取消接口导致订单状态异常。
- 回滚步骤：回滚代码和配置。
- 数据恢复：按审计日志恢复状态。

## 13. 验收标准

- [x] 技术方案覆盖全部适用 FR 和 AC。
- [x] 接口契约已检查。
- [x] 数据模型和回滚方案完整。
- [x] 认证、授权、幂等和审计方案完整。
- [x] 风险和缓解措施明确。

## 14. 变更历史

| 日期 | 版本 | 变更内容 | 作者 |
|---|---|---|---|
| 2026-11-14 | 1.0.0 | 初始版本 | SDD Agent |
"""

TASKS_TEXT = """# 订单取消任务清单（Tasks）

## 1. 元数据

| 项 | 内容 |
|---|---|
| Spec ID | SPEC-ORDER-001 |
| 关联Spec | `docs/specs/SPEC-ORDER-001/spec.md` |
| 关联Design | `docs/specs/SPEC-ORDER-001/design.md` |
| 作者 | SDD Agent |
| 创建日期 | 2026-11-14 |
| 状态 | Draft |

## 2. 任务清单

| Task ID | 任务描述 | 关联FR/AC | 依赖Task | 并行标识 | 验收标准 | 单元测试类/方法 | 单Task测试命令 | 状态 | Commit SHA |
|---|---|---|---|---|---|---|---|---|---|
| T-001 | 实现订单取消接口和状态校验 | FR-001；AC-001-1 | None | P | 待支付订单可取消，其他状态拒绝 | `OrderServiceTest#testCancelPendingOrder` | `python -m unittest tests.test_status` | Todo | — |

字段规则：

- Task ID 采用 `T-xxx`，在当前 Spec 内唯一。
- 状态仅允许 Todo、In Progress、Done。

## 3. AC—Task—单元测试映射

| AC ID | 覆盖Task | 测试类/方法 | 测试命令/选择器 | 预期结果 | Gate 4实际结果 |
|---|---|---|---|---|---|
| AC-001-1 | T-001 | `OrderServiceTest#testCancelPendingOrder` | `python -m unittest tests.test_status` | 订单状态变为已取消 | 未执行 |

## 4. 依赖图

```mermaid
flowchart LR
    T001["T-001"]
```

## 5. 实施与提交顺序

先实现 T-001，单测通过后提交。

## 6. 全量单元测试记录

| 测试命令 | 退出码 | 执行数 | 通过数 | 失败数 | 跳过数 | 结果 |
|---|---:|---:|---:|---:|---:|---|
| `python -m unittest tests.test_status` | 0 | 1 | 1 | 0 | 0 | PASS |

## 7. 自检清单（评审辅助，不作Gate依据）

- [x] 已自检。

## 8. 变更历史

| 日期 | 版本 | 变更内容 | 作者 |
|---|---|---|---|
| 2026-11-14 | 1.0.0 | 初始版本 | SDD Agent |
"""

VERIFY_TEXT = """# 订单取消验证报告

## 1. 元数据

| 项 | 内容 |
|---|---|
| Spec ID | SPEC-ORDER-001 |
| 工作项 ID | srdcloud-553377 |
| 作者 | SDD Agent |
| 创建日期 | 2026-11-14 |
| 验证时间 | 2026-11-14 |

## 2. 命令

`python -m unittest tests.test_status`，退出码 0。

## 3. 结果

AC-001-1：待支付订单取消成功，状态变为已取消。

## 4. 未运行

None。

## 5. AC 覆盖

| AC | 测试/证据 | 结果 |
|---|---|---|
| AC-001-1 | tests/test_status.py | PASS |

## 6. Gate 5 结论

PASS。无残余阻断风险。
"""


class SddFlowTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        shutil.copytree(KIT_ROOT / "sdd", self.root / "sdd")
        (self.root / "tests").mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def run_sdd(self, *args, expect=0):
        result = subprocess.run(
            [sys.executable, str(self.root / "sdd" / "scripts" / "sdd.py"), *args],
            cwd=self.root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if expect is not None:
            self.assertEqual(
                result.returncode,
                expect,
                msg=f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
            )
        return result

    def write(self, relative, text):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def state(self, spec_id=SPEC_ID):
        return json.loads(
            (self.root / "docs" / "specs" / spec_id / "state.json").read_text(
                encoding="utf-8"
            )
        )

    def next_action(self, spec_id=SPEC_ID):
        result = self.run_sdd("next", "--spec", spec_id, "--json")
        return json.loads(result.stdout)

    def new_spec(self, spec_id=SPEC_ID, risk="low", labels=None):
        args = [
            "new",
            spec_id,
            "--title",
            "订单取消",
            "--work-item",
            "srdcloud-553377",
            "--issue-url",
            "https://example.invalid/item/553377",
            "--risk",
            risk,
        ]
        for label in labels or []:
            args.extend(["--risk-label", label])
        self.run_sdd(*args)

    def approve_valid_spec(self, spec_id=SPEC_ID):
        self.write(f"docs/specs/{spec_id}/spec.md", SPEC_TEXT.replace(SPEC_ID, spec_id))
        self.run_sdd(
            "approve",
            "--spec",
            spec_id,
            "--human",
            "--evidence",
            "需求已确认",
        )

    def complete_design(self, spec_id=SPEC_ID):
        self.write(
            f"docs/specs/{spec_id}/design.md",
            DESIGN_TEXT.replace(SPEC_ID, spec_id),
        )
        self.run_sdd("complete", "--spec", spec_id, "--evidence", "design 完成")

    def complete_tasks(self, spec_id=SPEC_ID):
        self.write(
            f"docs/specs/{spec_id}/tasks.md",
            TASKS_TEXT.replace(SPEC_ID, spec_id),
        )
        self.run_sdd("complete", "--spec", spec_id, "--evidence", "tasks 完成")

    def finish_implementation(self, spec_id=SPEC_ID):
        if self.state(spec_id)["state"] == "TASKS_READY":
            self.run_sdd("complete", "--spec", spec_id, "--evidence", "开始实现")
        self.write(
            "tests/test_status.py",
            """import unittest


class StatusTest(unittest.TestCase):
    def test_cancel_pending_order(self):
        # [AC-001-1]
        self.assertTrue(True)
""",
        )
        self.run_sdd("start", "--spec", spec_id, "--task", "T-001")
        self.run_sdd(
            "complete",
            "--spec",
            spec_id,
            "--task",
            "T-001",
            "--commit",
            "abc1234",
            "--evidence",
            "python -m unittest tests.test_status: 1 passed",
        )

    def finish_verification(self, spec_id=SPEC_ID):
        config_path = self.root / "sdd" / "config.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        config["test_commands"] = [
            "python -m unittest discover -s tests -p test_status.py"
        ]
        config_path.write_text(
            json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        self.run_sdd("verify", "--spec", spec_id)
        self.write(
            f"docs/specs/{spec_id}/verification.md",
            VERIFY_TEXT.replace(SPEC_ID, spec_id),
        )
        self.run_sdd("complete", "--spec", spec_id, "--evidence", "验证完成")

    def test_full_flow(self):
        self.new_spec()
        self.assertEqual(self.state()["state"], "DRAFT")
        self.assertEqual(self.next_action()["action"], "write_spec")
        self.run_sdd("check", "--spec", SPEC_ID, "--stage", "spec", expect=1)

        self.write("docs/specs/SPEC-ORDER-001/spec.md", SPEC_TEXT)
        self.run_sdd("check", "--spec", SPEC_ID, "--stage", "spec")
        self.run_sdd(
            "approve",
            "--spec",
            SPEC_ID,
            "--human",
            "--evidence",
            "需求已确认",
        )
        self.assertEqual(self.state()["state"], "SPEC_READY")
        self.assertTrue(
            (self.root / "sdd/reports/SPEC-ORDER-001/gate0-report.md").is_file()
        )
        self.assertTrue(
            (self.root / "sdd/reports/SPEC-ORDER-001/gate1-report.md").is_file()
        )

        self.complete_design()
        self.assertEqual(self.state()["state"], "DESIGN_READY")
        self.assertTrue(
            (self.root / "sdd/reports/SPEC-ORDER-001/gate2-report.md").is_file()
        )

        self.complete_tasks()
        self.assertEqual(self.state()["state"], "TASKS_READY")
        self.assertTrue(
            (self.root / "sdd/reports/SPEC-ORDER-001/gate3-report.md").is_file()
        )
        self.run_sdd("complete", "--spec", SPEC_ID, "--evidence", "开始实现")
        self.assertEqual(self.state()["state"], "IMPLEMENTING")

        self.finish_implementation()
        self.assertEqual(self.state()["state"], "VERIFYING")
        self.assertTrue(
            (self.root / "sdd/reports/SPEC-ORDER-001/gate4-report.md").is_file()
        )

        self.run_sdd("check", "--spec", SPEC_ID, "--stage", "verify", expect=1)
        self.finish_verification()
        self.assertEqual(self.state()["state"], "PR_READY")
        self.assertTrue(
            (self.root / "docs/specs/SPEC-ORDER-001/PR_BODY.md").is_file()
        )
        self.assertTrue(
            (self.root / "sdd/reports/SPEC-ORDER-001/gate5-report.md").is_file()
        )
        self.run_sdd("check", "--spec", SPEC_ID, "--stage", "ci")
        self.run_sdd("pr", "--spec", SPEC_ID, "--url", "https://example.invalid/pr/1")
        self.run_sdd(
            "merge",
            "--spec",
            SPEC_ID,
            "--human",
            "--evidence",
            "PR #1 merged",
        )
        self.assertEqual(self.state()["state"], "MERGED")
        self.assertEqual(self.next_action()["action"], "done")

    def test_task_complete_requires_start(self):
        self.new_spec()
        self.approve_valid_spec()
        self.complete_design()
        self.complete_tasks()
        self.run_sdd(
            "complete", "--spec", SPEC_ID, "--evidence", "开始实现"
        )
        result = self.run_sdd(
            "complete",
            "--spec",
            SPEC_ID,
            "--task",
            "T-001",
            "--evidence",
            "跳过 start",
            expect=2,
        )
        self.assertIn("start", result.stderr)

    def test_block_and_unblock(self):
        self.new_spec()
        self.run_sdd("block", "--spec", SPEC_ID, "--reason", "缺少测试环境")
        self.assertEqual(self.state()["state"], "BLOCKED")
        action = self.next_action()
        self.assertEqual(action["action"], "resolve_blocker")
        self.assertTrue(action["decision_required"])
        self.assertEqual(action["question"], "缺少测试环境")
        self.assertEqual(action["kind"], "decision")
        self.run_sdd(
            "unblock",
            "--spec",
            SPEC_ID,
            "--human",
            "--evidence",
            "已获得测试环境",
        )
        self.assertEqual(self.state()["state"], "DRAFT")

    def test_high_risk_gate_needs_human(self):
        self.new_spec(risk="high", labels=["security"])
        self.approve_valid_spec()
        self.write("docs/specs/SPEC-ORDER-001/design.md", DESIGN_TEXT)
        self.run_sdd(
            "complete",
            "--spec",
            SPEC_ID,
            "--evidence",
            "design 完成",
            expect=2,
        )
        self.assertEqual(self.state()["state"], "SPEC_READY")
        self.run_sdd(
            "complete",
            "--spec",
            SPEC_ID,
            "--evidence",
            "安全负责人已批准",
            "--human",
        )
        self.assertEqual(self.state()["state"], "DESIGN_READY")

    def test_clarification_marker_blocks_approve(self):
        self.new_spec()
        self.write(
            "docs/specs/SPEC-ORDER-001/spec.md",
            SPEC_TEXT.replace(
                "AC-001-1：Given 用户拥有待支付订单",
                "AC-001-1：[NEEDS CLARIFICATION] Given 用户拥有待支付订单",
            ),
        )
        self.run_sdd(
            "approve",
            "--spec",
            SPEC_ID,
            "--human",
            "--evidence",
            "确认",
            expect=2,
        )
        self.assertEqual(self.state()["state"], "DRAFT")
        self.assertIn(
            "NEEDS CLARIFICATION",
            (self.root / "sdd/reports/SPEC-ORDER-001/gate0-report.md").read_text(
                encoding="utf-8"
            ),
        )

    def test_ci_fails_without_gate_report(self):
        self.new_spec()
        self.approve_valid_spec()
        self.complete_design()
        self.complete_tasks()
        self.run_sdd("complete", "--spec", SPEC_ID, "--evidence", "开始实现")
        self.finish_implementation()
        self.finish_verification()
        (self.root / "sdd/reports/SPEC-ORDER-001/gate2-report.md").unlink()
        result = self.run_sdd("check", "--spec", SPEC_ID, "--stage", "ci", expect=1)
        self.assertIn("gate2-report.md", result.stdout)

    def test_auto_spec_id_and_prd_index(self):
        self.run_sdd(
            "new",
            "--domain",
            "PAY",
            "--title",
            "支付回调",
            "--work-item",
            "srdcloud-600001",
        )
        self.assertTrue((self.root / "docs/specs/SPEC-PAY-001/spec.md").is_file())
        index = (self.root / "docs/prd-index.md").read_text(encoding="utf-8")
        self.assertIn("SPEC-PAY-001", index)
        self.assertIn("FEAT-001", index)

    def test_commit_msg_hook(self):
        self.new_spec()
        self.approve_valid_spec()
        self.complete_design()
        self.complete_tasks()
        message = self.root / "message.txt"
        message.write_text(
            "%srdcloud-553377 feat(order): 实现订单取消\n\n"
            "Spec-Id: SPEC-ORDER-001\nTask-Id: T-001\n",
            encoding="utf-8",
        )
        self.run_sdd("hook", "commit-msg", "--message-file", str(message))
        message.write_text(
            "%srdcloud-553377 docs(spec): 更新规格\n\n"
            "Spec-Id: SPEC-ORDER-001\nTask-Id: T-001\n",
            encoding="utf-8",
        )
        self.run_sdd(
            "hook", "commit-msg", "--message-file", str(message), expect=1
        )

    def test_init_installs_hooks_and_ci(self):
        self.run_sdd("init", "--hooks", "--ci", "github")
        self.assertTrue((self.root / ".githooks/pre-commit").is_file())
        self.assertTrue((self.root / ".githooks/commit-msg").is_file())
        self.assertTrue((self.root / ".github/workflows/sdd.yml").is_file())
        workflow = (self.root / ".github/workflows/sdd.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("check --all --stage ci --check-git", workflow)

    def test_check_all_reports_each_spec(self):
        self.new_spec()
        self.run_sdd(
            "new",
            "--domain",
            "PAY",
            "--title",
            "支付回调",
            "--work-item",
            "srdcloud-600001",
        )
        result = self.run_sdd("check", "--all", "--stage", "spec", expect=1)
        self.assertIn("SPEC-ORDER-001", result.stdout)
        self.assertIn("SPEC-PAY-001", result.stdout)

    def test_init_installs_gitlab_ci(self):
        self.run_sdd("init", "--ci", "gitlab")
        pipeline = (self.root / ".gitlab-ci.yml").read_text(encoding="utf-8")
        self.assertIn("check --all --stage ci --check-git", pipeline)


if __name__ == "__main__":
    unittest.main()
