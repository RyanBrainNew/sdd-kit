import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from sdd.core import Workspace
from sdd.scripts import sdd as engine


KIT_ROOT = Path(__file__).resolve().parents[1]
SPEC_ID = "SPEC-ORDER-001"

SPEC_TEXT = """# 订单取消规格说明书（Spec）

## 1. 元数据

| 项 | 内容 |
|---|---|
| Spec ID | SPEC-ORDER-001 |
| 工作项 ID | srdcloud-553377 |
| FEAT ID | FEAT-001 |
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
| T-001 | 实现订单取消接口和状态校验 | FR-001；AC-001-1 | None | P | 待支付订单可取消，其他状态拒绝 | `StatusTest#test_cancel_pending_order` | `python -m unittest tests.test_status` | Todo | — |

字段规则：

- Task ID 采用 `T-xxx`，在当前 Spec 内唯一。
- 状态仅允许 Todo、In Progress、Done。

## 3. AC—Task—单元测试映射

| AC ID | 覆盖Task | 测试类/方法 | 测试命令/选择器 | 预期结果 | Gate 4实际结果 |
|---|---|---|---|---|---|
| AC-001-1 | T-001 | `StatusTest#test_cancel_pending_order` | `python -m unittest tests.test_status` | 订单状态变为已取消 | 未执行 |

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

- Command: `python -m unittest tests.test_status`
- CWD: `C:/repo`
- Exit: `0`
- Head: `abc1234`
- Plan-Hash: `sha256:0123456789abcdef`
- At: `2026-11-14T10:00:00+08:00`

```text
test_cancel_pending_order (tests.test_status.StatusTest) ... ok
```

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

DESIGN_LITE_TEXT = """# 订单取消设计文档（Design Lite）

## 1. 元数据

| 项 | 内容 |
|---|---|
| Spec ID | SPEC-ORDER-001 |
| 工作流 | l2-hotfix |

## 2. 根因

- 现象：待支付订单取消时偶发状态未更新。
- 根因：取消方法没有校验订单状态和归属。
- 证据：复现测试 `test_cancel_pending_order`。

## 3. 修复策略

- 修复方案：在 OrderService 增加状态与归属校验。
- 备选方案：在 Controller 校验；不采用，避免规则分散。
- 不修的影响：用户可以取消已支付订单。

## 4. 影响范围

| 模块/服务 | 影响 | 兼容性 | 回滚风险 |
|---|---|---|---|
| OrderService | 取消接口增加校验 | 向后兼容 | 低 |

## 5. 回滚方案

- 回滚条件：取消接口错误率上升。
- 回滚步骤：回退本次提交。
- 数据回滚：不涉及。

## 6. 验收标准

| AC | 验证方式 | 证据 |
|---|---|---|
| AC-001-1 | 单元测试 | test_cancel_pending_order |
"""

VERIFY_STRICT_SUFFIX = """

## 7. 独立审查

| 项 | 内容 |
|---|---|
| Reviewer | 独立评审员 |
| Session | reviewer-session-1 |
| Model | review-model |
| Findings | 未发现阻断问题。 |
| Blocking issues | none |
"""


class SddFlowBase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        shutil.copytree(KIT_ROOT / "sdd", self.root / "sdd")
        (self.root / "tests").mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def run_sdd(self, *args, expect=0, env=None):
        result = subprocess.run(
            [sys.executable, str(self.root / "sdd" / "scripts" / "sdd.py"), *args],
            cwd=self.root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
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

    def new_spec(
        self,
        spec_id=SPEC_ID,
        risk="low",
        labels=None,
        workflow=None,
    ):
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
        if workflow:
            args.extend(["--workflow", workflow])
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

class SddFlowTest(SddFlowBase):
    def test_full_flow(self):
        self.new_spec()
        self.assertEqual(self.state()["state"], "DRAFT")
        self.assertEqual(self.next_action()["action"], "write_spec")
        self.run_sdd("check", "--spec", SPEC_ID, "--stage", "spec", expect=1)

        self.write("docs/specs/SPEC-ORDER-001/spec.md", SPEC_TEXT)
        self.run_sdd("index", "--spec", SPEC_ID)
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
        self.assertEqual(self.next_action()["action"], "confirm_merge")
        self.run_sdd(
            "merge",
            "--spec",
            SPEC_ID,
            "--human",
            "--evidence",
            "交付已确认",
        )
        self.assertEqual(self.state()["state"], "MERGED")
        self.assertIsNone(self.state().get("pr_url"))
        test_file = self.root / "tests" / "test_status.py"
        original_test = test_file.read_text(encoding="utf-8")
        test_file.write_text(
            original_test.replace("# [AC-001-1]", ""), encoding="utf-8"
        )
        self.run_sdd("check", "--spec", SPEC_ID, "--stage", "ci", expect=1)
        test_file.write_text(original_test, encoding="utf-8")
        self.assertEqual(self.next_action()["action"], "open_pr")
        resumed = Workspace(self.root, session_key="agent-resume").session()
        self.assertEqual(resumed["spec"], SPEC_ID)
        self.assertEqual(resumed["next"]["action"], "open_pr")
        self.run_sdd("pr", "--spec", SPEC_ID, "--url", "https://example.invalid/pr/1")
        self.assertEqual(self.next_action()["action"], "done")
        metrics = json.loads(self.run_sdd("metrics", "--json").stdout)
        spec_metrics = metrics["specs"][0]
        self.assertIsNotNone(spec_metrics["lead_time_hours"])
        self.assertGreaterEqual(spec_metrics["human_interventions"], 2)
        self.assertEqual(spec_metrics["ac_coverage"], 1.0)

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

    def test_pr_url_requires_delivery_confirmation(self):
        self.new_spec()
        self.approve_valid_spec()
        self.complete_design()
        self.complete_tasks()
        self.run_sdd("complete", "--spec", SPEC_ID, "--evidence", "开始实现")
        self.finish_implementation()
        self.finish_verification()
        self.assertEqual(self.state()["state"], "PR_READY")
        result = self.run_sdd(
            "pr",
            "--spec",
            SPEC_ID,
            "--url",
            "https://example.invalid/pr/1",
            expect=2,
        )
        self.assertIn("MERGED", result.stderr)
        self.run_sdd(
            "merge",
            "--spec",
            SPEC_ID,
            "--human",
            "--evidence",
            "交付已确认",
        )
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        result = self.run_sdd(
            "pr",
            "--spec",
            SPEC_ID,
            "--url",
            "https://example.invalid/pr/1",
            expect=2,
        )
        self.assertIn("尚未提交", result.stderr)
        subprocess.run(
            ["git", "add", f"docs/specs/{SPEC_ID}"],
            cwd=self.root,
            check=True,
        )
        subprocess.run(
            [
                "git",
                "-c",
                "user.name=Test",
                "-c",
                "user.email=test@example.com",
                "commit",
                "-q",
                "-m",
                "chore(sdd): record delivery",
            ],
            cwd=self.root,
            check=True,
        )
        self.run_sdd(
            "pr",
            "--spec",
            SPEC_ID,
            "--url",
            "https://example.invalid/pr/1",
        )

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

    def test_hotfix_workflow_uses_lite_design_and_auto_g2(self):
        self.new_spec(risk="medium", workflow="l2-hotfix")
        state = self.state()
        self.assertEqual(state["workflow"]["name"], "l2-hotfix")
        self.assertTrue(
            (self.root / "docs/specs/SPEC-ORDER-001/workflow.json").is_file()
        )
        design = (
            self.root / "docs/specs/SPEC-ORDER-001/design.md"
        ).read_text(encoding="utf-8")
        self.assertIn("Design Lite", design)

        self.approve_valid_spec()
        self.write(
            "docs/specs/SPEC-ORDER-001/design.md",
            DESIGN_LITE_TEXT,
        )
        self.run_sdd(
            "complete",
            "--spec",
            SPEC_ID,
            "--evidence",
            "hotfix design 完成",
        )
        self.assertEqual(self.state()["state"], "DESIGN_READY")
        report = (
            self.root / "sdd/reports/SPEC-ORDER-001/gate2-report.md"
        ).read_text(encoding="utf-8")
        self.assertIn("| 执行模式 | auto |", report)

    def test_hotfix_workflow_rejects_high_risk(self):
        result = self.run_sdd(
            "new",
            "SPEC-HOT-001",
            "--title",
            "高风险热修复",
            "--work-item",
            "srdcloud-553378",
            "--workflow",
            "l2-hotfix",
            "--risk",
            "high",
            expect=2,
        )
        self.assertIn("risk<=medium", result.stderr)
        self.assertFalse(
            (self.root / "docs/specs/SPEC-HOT-001").exists()
        )

    def test_legacy_spec_without_workflow_uses_standard(self):
        self.new_spec()
        state_path = self.root / "docs/specs/SPEC-ORDER-001/state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state.pop("workflow", None)
        state_path.write_text(
            json.dumps(state, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (self.root / "docs/specs/SPEC-ORDER-001/workflow.json").unlink()
        self.run_sdd("status", "--spec", SPEC_ID, "--json")

    def test_spec_keeps_workflow_snapshot_when_preset_changes(self):
        self.new_spec()
        preset_path = self.root / "sdd/workflows/l2-standard.json"
        preset = json.loads(preset_path.read_text(encoding="utf-8"))
        preset["version"] = 2
        preset["description"] = "changed for test"
        preset_path.write_text(
            json.dumps(preset, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        self.run_sdd("status", "--spec", SPEC_ID, "--json")
        self.assertEqual(
            self.state()["workflow"]["version"],
            1,
        )

    def test_strict_workflow_requires_human_gates_and_review(self):
        self.new_spec(workflow="l2-strict")
        self.assertEqual(self.state()["workflow"]["name"], "l2-strict")
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
            "--human",
            "--evidence",
            "设计评审通过",
        )
        self.assertEqual(self.state()["state"], "DESIGN_READY")

        self.write("docs/specs/SPEC-ORDER-001/tasks.md", TASKS_TEXT)
        self.run_sdd(
            "complete",
            "--spec",
            SPEC_ID,
            "--evidence",
            "tasks 完成",
            expect=2,
        )
        self.run_sdd(
            "complete",
            "--spec",
            SPEC_ID,
            "--human",
            "--evidence",
            "任务拆解评审通过",
        )
        self.assertEqual(self.state()["state"], "TASKS_READY")

        self.run_sdd("complete", "--spec", SPEC_ID, "--evidence", "开始实现")
        self.write(
            "tests/test_status.py",
            """import unittest


class StatusTest(unittest.TestCase):
    def test_cancel_pending_order(self):
        # [AC-001-1]
        self.assertTrue(True)
""",
        )
        self.run_sdd("start", "--spec", SPEC_ID, "--task", "T-001")
        self.run_sdd(
            "complete",
            "--spec",
            SPEC_ID,
            "--task",
            "T-001",
            "--commit",
            "abc1234",
            "--evidence",
            "python -m unittest tests.test_status: 1 passed",
        )
        self.assertEqual(self.state()["state"], "IMPLEMENTING")
        self.run_sdd(
            "complete",
            "--spec",
            SPEC_ID,
            "--human",
            "--evidence",
            "代码评审通过",
        )
        self.assertEqual(self.state()["state"], "VERIFYING")
        self.set_config(
            test_commands=["python -m unittest discover -s tests -p test_status.py"]
        )

        session = next(
            str(item["session"])
            for item in reversed(self.state()["history"])
            if item.get("role") == "implementer" and item.get("session")
        )
        self.write(
            "docs/specs/SPEC-ORDER-001/verification.md",
            VERIFY_TEXT + VERIFY_STRICT_SUFFIX.replace(
                "reviewer-session-1", session
            ),
        )
        same_session = self.run_sdd(
            "check",
            "--spec",
            SPEC_ID,
            "--stage",
            "verify",
            expect=1,
        )
        self.assertIn("Session 与实现会话相同", same_session.stdout)

        self.write(
            "docs/specs/SPEC-ORDER-001/verification.md",
            VERIFY_TEXT + VERIFY_STRICT_SUFFIX,
        )
        self.run_sdd("check", "--spec", SPEC_ID, "--stage", "verify")
        self.run_sdd(
            "complete",
            "--spec",
            SPEC_ID,
            "--evidence",
            "验证完成",
            expect=2,
        )
        self.run_sdd(
            "complete",
            "--spec",
            SPEC_ID,
            "--human",
            "--evidence",
            "规格验证通过",
        )
        self.assertEqual(self.state()["state"], "PR_READY")

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

    def set_config(self, **values):
        path = self.root / "sdd" / "config.json"
        config = json.loads(path.read_text(encoding="utf-8"))
        config.update(values)
        path.write_text(
            json.dumps(config, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def test_gate_hash_detects_tampering(self):
        self.new_spec()
        self.approve_valid_spec()
        self.complete_design()
        self.complete_tasks()
        self.run_sdd("complete", "--spec", SPEC_ID, "--evidence", "开始实现")
        self.finish_implementation()

        spec_path = self.root / "docs/specs/SPEC-ORDER-001/spec.md"
        spec_path.write_text(
            spec_path.read_text(encoding="utf-8") + "\n<!-- tampered -->\n",
            encoding="utf-8",
        )
        self.set_config(
            test_commands=["python -m unittest discover -s tests -p test_status.py"]
        )
        self.run_sdd("verify", "--spec", SPEC_ID)
        self.write(
            "docs/specs/SPEC-ORDER-001/verification.md", VERIFY_TEXT
        )
        result = self.run_sdd(
            "complete", "--spec", SPEC_ID, "--evidence", "验证完成", expect=2
        )
        self.assertIn("已被修改", result.stderr)
        self.assertEqual(self.state()["state"], "VERIFYING")

    def test_check_failed_and_event_schema_v2(self):
        self.new_spec()
        self.run_sdd("check", "--spec", SPEC_ID, "--stage", "spec", expect=1)
        events = [
            json.loads(line)
            for line in (
                self.root / "docs/specs/SPEC-ORDER-001/events.jsonl"
            ).read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertTrue(events)
        self.assertTrue(all(event.get("schema") == 2 for event in events))
        failed = [event for event in events if event.get("event") == "check_failed"]
        self.assertTrue(failed)
        self.assertEqual(failed[-1]["role"], "planner")
        self.assertTrue(failed[-1].get("session"))
        self.assertTrue(failed[-1].get("session_source"))

        self.approve_valid_spec()
        events = [
            json.loads(line)
            for line in (
                self.root / "docs/specs/SPEC-ORDER-001/events.jsonl"
            ).read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        approval = [
            event
            for event in events
            if event.get("to_state") == "SPEC_READY"
        ][-1]
        self.assertEqual(approval["role"], "approver")
        self.assertTrue(approval.get("artifacts"))
        self.assertEqual(approval["artifacts"][0]["path"].endswith("spec.md"), True)

    def test_manual_gates_require_human_complete(self):
        self.set_config(
            gates={"G0": "human", "G1": "auto", "G2": "human", "G3": "human", "G4": "auto", "G5": "human"},
            require_approver=True,
        )
        self.new_spec()
        self.write("docs/specs/SPEC-ORDER-001/spec.md", SPEC_TEXT)
        self.run_sdd(
            "approve",
            "--spec",
            SPEC_ID,
            "--human",
            "--approver",
            "张三 <zhang@example.com>",
            "--evidence",
            "需求已确认",
        )
        self.write("docs/specs/SPEC-ORDER-001/design.md", DESIGN_TEXT)
        self.run_sdd(
            "complete", "--spec", SPEC_ID, "--evidence", "design 完成", expect=2
        )
        self.run_sdd(
            "complete",
            "--spec",
            SPEC_ID,
            "--evidence",
            "design 已评审",
            "--human",
            "--approver",
            "李四 <li@example.com>",
        )
        self.assertEqual(self.state()["state"], "DESIGN_READY")
        self.assertEqual(self.state()["approvals"][-1]["gate"], "G2")

        self.write("docs/specs/SPEC-ORDER-001/tasks.md", TASKS_TEXT)
        self.run_sdd(
            "complete", "--spec", SPEC_ID, "--evidence", "tasks 完成", expect=2
        )
        self.run_sdd(
            "complete",
            "--spec",
            SPEC_ID,
            "--evidence",
            "tasks 已评审",
            "--human",
            "--approver",
            "李四 <li@example.com>",
        )
        self.assertEqual(self.state()["state"], "TASKS_READY")
        self.assertEqual(self.state()["approvals"][-1]["gate"], "G3")

        self.run_sdd("complete", "--spec", SPEC_ID, "--evidence", "开始实现")
        self.finish_implementation()
        self.set_config(
            test_commands=["python -m unittest discover -s tests -p test_status.py"]
        )
        self.run_sdd("verify", "--spec", SPEC_ID)
        self.write("docs/specs/SPEC-ORDER-001/verification.md", VERIFY_TEXT)
        self.run_sdd(
            "complete", "--spec", SPEC_ID, "--evidence", "验证完成", expect=2
        )
        self.run_sdd(
            "complete",
            "--spec",
            SPEC_ID,
            "--evidence",
            "验证已确认",
            "--human",
            "--approver",
            "王五 <wang@example.com>",
        )
        self.assertEqual(self.state()["state"], "PR_READY")
        self.assertEqual(self.state()["approvals"][-1]["gate"], "G5")

    def test_manual_approver_required_when_config_enabled(self):
        self.set_config(require_approver=True)
        self.new_spec()
        self.write("docs/specs/SPEC-ORDER-001/spec.md", SPEC_TEXT)
        env = os.environ.copy()
        env["GIT_CONFIG_GLOBAL"] = str(self.root / "missing-global-config")
        env["GIT_CONFIG_SYSTEM"] = str(self.root / "missing-system-config")
        result = self.run_sdd(
            "approve",
            "--spec",
            SPEC_ID,
            "--human",
            "--evidence",
            "需求已确认",
            expect=2,
            env=env,
        )
        self.assertIn("--approver", result.stderr)
        self.assertEqual(self.state()["state"], "DRAFT")

    def test_last_task_manual_gate_is_retryable(self):
        self.set_config(gates={"G4": "human"})
        self.new_spec()
        self.approve_valid_spec()
        self.complete_design()
        self.complete_tasks()
        self.run_sdd("complete", "--spec", SPEC_ID, "--evidence", "开始实现")
        self.write(
            "tests/test_status.py",
            "import unittest\n\n"
            "class StatusTest(unittest.TestCase):\n"
            "    def test_cancel_pending_order(self):\n"
            "        # [AC-001-1]\n"
            "        self.assertTrue(True)\n",
        )
        self.run_sdd("start", "--spec", SPEC_ID, "--task", "T-001")
        self.run_sdd(
            "complete",
            "--spec",
            SPEC_ID,
            "--task",
            "T-001",
            "--commit",
            "abc1234",
            "--evidence",
            "python -m unittest tests.test_status: 1 passed",
        )
        tasks = (self.root / "docs/specs/SPEC-ORDER-001/tasks.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("| Done |", tasks)
        self.assertEqual(self.state()["state"], "IMPLEMENTING")
        inbox = json.loads(self.run_sdd("inbox", "--json").stdout)
        self.assertEqual(inbox["items"][0]["action"], "manual_gate")
        self.assertEqual(inbox["items"][0]["gate"], "G4")
        self.run_sdd(
            "complete",
            "--spec",
            SPEC_ID,
            "--evidence",
            "代码评审通过",
            "--human",
        )
        self.assertEqual(self.state()["state"], "VERIFYING")

    def test_inbox_lists_draft_blocked_and_manual_gate(self):
        self.new_spec()
        inbox = json.loads(self.run_sdd("inbox", "--json").stdout)
        self.assertEqual(inbox["items"][0]["action"], "approve_spec")
        self.assertIn("approve", inbox["items"][0]["command"])

        self.run_sdd("block", "--spec", SPEC_ID, "--reason", "缺少测试环境")
        inbox = json.loads(self.run_sdd("inbox", "--json").stdout)
        self.assertEqual(inbox["items"][0]["action"], "unblock")
        self.assertEqual(inbox["items"][0]["priority"], 0)

        self.run_sdd(
            "unblock", "--spec", SPEC_ID, "--human", "--evidence", "环境已恢复"
        )
        self.set_config(gates={"G2": "human"})
        self.approve_valid_spec()
        self.write("docs/specs/SPEC-ORDER-001/design.md", DESIGN_TEXT)
        inbox = json.loads(self.run_sdd("inbox", "--json").stdout)
        self.assertEqual(inbox["items"][0]["action"], "manual_gate")
        self.assertEqual(inbox["items"][0]["gate"], "G2")
        self.assertIn("complete", inbox["items"][0]["command"])
        self.assertIn("--human", inbox["items"][0]["command"])

    def test_rewind_from_verifying_resumes_to_pr_ready(self):
        self.new_spec()
        self.approve_valid_spec()
        self.complete_design()
        self.complete_tasks()
        self.run_sdd("complete", "--spec", SPEC_ID, "--evidence", "开始实现")
        self.finish_implementation()
        self.assertEqual(self.state()["state"], "VERIFYING")

        design_before = (
            self.root / "docs/specs/SPEC-ORDER-001/design.md"
        ).read_text(encoding="utf-8")
        result = self.run_sdd(
            "rewind",
            "--spec",
            SPEC_ID,
            "--to",
            "DESIGN_READY",
            "--reason",
            "验证发现设计遗漏",
            "--human",
            "--approver",
            "张三 <zhang@example.com>",
            "--json",
        )
        payload = json.loads(result.stdout)
        self.assertEqual(payload["from"], "VERIFYING")
        self.assertEqual(payload["to"], "DESIGN_READY")
        self.assertTrue(payload["archived"])
        self.assertEqual(self.state()["state"], "DESIGN_READY")
        self.assertEqual(
            (self.root / "docs/specs/SPEC-ORDER-001/design.md").read_text(
                encoding="utf-8"
            ),
            design_before,
        )
        self.assertIn(
            "| Todo |",
            (self.root / "docs/specs/SPEC-ORDER-001/tasks.md").read_text(
                encoding="utf-8"
            ),
        )
        history = self.root / "docs/specs/SPEC-ORDER-001/history"
        self.assertTrue(any(history.rglob("manifest.json")))
        self.assertFalse(
            (self.root / "sdd/reports/SPEC-ORDER-001/gate3-report.md").exists()
        )
        events = [
            json.loads(line)
            for line in (
                self.root / "docs/specs/SPEC-ORDER-001/events.jsonl"
            ).read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertEqual(events[-1]["event"], "rewind")
        self.assertEqual(events[-1]["rewind"]["to"], "DESIGN_READY")

        self.complete_tasks()
        self.run_sdd("complete", "--spec", SPEC_ID, "--evidence", "开始实现")
        self.finish_implementation()
        self.finish_verification()
        self.assertEqual(self.state()["state"], "PR_READY")

        metrics = json.loads(self.run_sdd("metrics", "--json").stdout)
        spec_metrics = metrics["specs"][0]
        self.assertEqual(spec_metrics["reworks"], 1)
        self.assertIn("DESIGN_READY", spec_metrics["stage_hours"])
        self.assertGreaterEqual(spec_metrics["human_interventions"], 2)

    def test_rewind_to_implementing_reopens_last_done_task(self):
        self.new_spec()
        self.approve_valid_spec()
        self.complete_design()
        self.complete_tasks()
        self.run_sdd("complete", "--spec", SPEC_ID, "--evidence", "开始实现")
        self.finish_implementation()
        self.assertEqual(self.state()["state"], "VERIFYING")

        self.run_sdd(
            "rewind",
            "--spec",
            SPEC_ID,
            "--to",
            "IMPLEMENTING",
            "--reason",
            "返工最后一个任务",
            "--human",
        )
        self.assertEqual(self.state()["state"], "IMPLEMENTING")
        tasks = (self.root / "docs/specs/SPEC-ORDER-001/tasks.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("| Todo |", tasks)
        self.assertEqual(self.next_action()["task"], "T-001")

    def test_rewind_requires_human(self):
        self.new_spec()
        result = self.run_sdd(
            "rewind",
            "--spec",
            SPEC_ID,
            "--to",
            "DRAFT",
            "--reason",
            "重做",
            expect=2,
        )
        self.assertIn("--human", result.stderr)
        self.assertEqual(self.state()["state"], "DRAFT")


class CheckRegistryTests(SddFlowBase):
    def test_registry_ids_are_unique(self):
        # [AC-003-4]
        self.assertEqual(engine.validate_check_registry(), [])
        ids = [str(item["id"]) for item in engine.CHECK_REGISTRY]
        self.assertEqual(len(ids), len(set(ids)))
        for item in engine.CHECK_REGISTRY:
            self.assertIn(item["gate"], engine.GATE_STAGES)
            self.assertIn(item["level"], {"required", "advisory"})

    def test_gate_reports_include_stable_ids(self):
        # [AC-003-1] [AC-003-2]
        self.new_spec()
        self.approve_valid_spec()
        g0 = (
            self.root / "sdd/reports/SPEC-ORDER-001/gate0-report.md"
        ).read_text(encoding="utf-8")
        g1 = (
            self.root / "sdd/reports/SPEC-ORDER-001/gate1-report.md"
        ).read_text(encoding="utf-8")
        for report in (g0, g1):
            self.assertIn("| 检查 ID | 检查项 | 级别 | 结果 | 证据 |", report)
            self.assertIn("| required |", report)
        self.assertIn("| G0-01 |", g0)
        self.assertIn("| G1-01 |", g1)
        self.assertNotIn("| G1-01 |", g0)
        self.assertNotIn("| G0-01 |", g1)

    def test_required_item_failure_blocks(self):
        # [AC-003-3]
        self.new_spec()
        self.write(
            "docs/specs/SPEC-ORDER-001/spec.md",
            SPEC_TEXT.replace(
                "- Out-of-Scope：不支持已支付订单退款。",
                "- Out-of-Scope：待补充",
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
        g0 = (
            self.root / "sdd/reports/SPEC-ORDER-001/gate0-report.md"
        ).read_text(encoding="utf-8")
        self.assertIn("| 总体结果 | FAILED |", g0)
        self.assertIn("| G0-06 |", g0)
        self.assertIn("| BLOCK |", g0)
        g1 = (
            self.root / "sdd/reports/SPEC-ORDER-001/gate1-report.md"
        ).read_text(encoding="utf-8")
        self.assertIn("| 总体结果 | PASS |", g1)


class FeatTraceTests(SddFlowBase):
    def config(self):
        return json.loads(
            (self.root / "sdd" / "config.json").read_text(encoding="utf-8")
        )

    def prepare_feat_spec(self):
        self.new_spec()
        self.write("docs/specs/SPEC-ORDER-001/spec.md", SPEC_TEXT)
        self.run_sdd("index", "--spec", SPEC_ID)
        return (
            self.root / "docs/specs/SPEC-ORDER-001/spec.md"
        ).read_text(encoding="utf-8")

    def test_feat_metadata_must_match_index(self):
        # [AC-002-1] [AC-002-2] [AC-002-8]
        spec_text = self.prepare_feat_spec()
        self.assertEqual(
            engine.feat_identity_errors(
                self.root, self.config(), self.state(), spec_text
            ),
            [],
        )
        self.assertEqual(
            engine.feat_coverage_errors(
                self.root, self.config(), self.state(), spec_text
            ),
            [],
        )
        mismatched = spec_text.replace("| FEAT ID | FEAT-001 |", "| FEAT ID | FEAT-999 |")
        errors = engine.feat_identity_errors(
            self.root, self.config(), self.state(), mismatched
        )
        self.assertTrue(any("不一致" in error for error in errors))
        missing = spec_text.replace("| FEAT ID | FEAT-001 |\n", "")
        errors = engine.feat_identity_errors(
            self.root, self.config(), self.state(), missing
        )
        self.assertTrue(any("缺少有效 FEAT ID" in error for error in errors))

    def test_duplicate_feat_is_blocked(self):
        # [AC-002-3]
        spec_text = self.prepare_feat_spec()
        index = self.root / "docs" / "prd-index.md"
        text = index.read_text(encoding="utf-8")
        marker = text.index("## FEAT 映射")
        duplicate = (
            "| srdcloud-999999 | N/A | current | FEAT-001 | SPEC-ORDER-002 | 重复 | 0 |\n"
        )
        index.write_text(text[:marker] + duplicate + "\n" + text[marker:], encoding="utf-8")
        errors = engine.feat_identity_errors(
            self.root, self.config(), self.state(), spec_text
        )
        self.assertTrue(any("被多个 Spec 使用" in error for error in errors))

    def test_orphan_fr_ac_is_blocked(self):
        # [AC-002-4]
        spec_text = self.prepare_feat_spec()
        index = self.root / "docs" / "prd-index.md"
        text = index.read_text(encoding="utf-8")
        text = text.replace(
            "| FR-001 | AC-001-1 |",
            "| FR-001 | AC-001-2 |",
        )
        index.write_text(text, encoding="utf-8")
        errors = engine.feat_coverage_errors(
            self.root, self.config(), self.state(), spec_text
        )
        self.assertTrue(any("缺少 AC：AC-001-1" in error for error in errors))
        self.assertTrue(any("不存在的 AC：AC-001-2" in error for error in errors))

    def test_body_only_feat_is_not_registered(self):
        # [AC-002-5] [AC-002-6]
        spec_text = self.prepare_feat_spec()
        index = self.root / "docs" / "prd-index.md"
        text = index.read_text(encoding="utf-8")
        marker = text.index("## FEAT 映射")
        body_only = text[:marker] + "正文提到 FEAT-001 / SPEC-ORDER-001 / FR-001 / AC-001-1。\n"
        index.write_text(body_only, encoding="utf-8")
        errors = engine.feat_coverage_errors(
            self.root, self.config(), self.state(), spec_text
        )
        self.assertTrue(any("缺少当前 Spec 的 FEAT 映射表行" in error for error in errors))

    def test_merged_legacy_spec_skips_feat_mapping(self):
        # [AC-002-7]
        self.new_spec()
        legacy_spec = SPEC_TEXT.replace("| FEAT ID | FEAT-001 |\n", "")
        legacy_state = dict(self.state())
        legacy_state["state"] = "MERGED"
        self.assertEqual(
            engine.check_feat_trace(
                self.root, self.config(), legacy_state, legacy_spec
            ),
            [],
        )
        self.assertTrue(
            engine.check_feat_trace(
                self.root, self.config(), self.state(), legacy_spec
            )
        )


class EvidenceTests(SddFlowBase):
    def config(self, commands=None):
        return {"test_commands": commands or []}

    def check(self, text, commands=None, state_name="VERIFYING"):
        return engine.check_verification(
            text,
            ["AC-001-1"],
            None,
            {"state": state_name},
            self.config(commands),
        )

    def plain_pass(self):
        return (
            VERIFY_TEXT.split("## 2. 命令")[0]
            + "## 2. 命令\n\n"
            + "`python -m unittest tests.test_status`，退出码 0。\n\n"
            + "## 3. 结果"
            + VERIFY_TEXT.split("## 3. 结果", 1)[1]
        )

    def test_empty_commands_block_pr_ready(self):
        # [AC-005-1]
        errors = self.check(VERIFY_TEXT)
        self.assertTrue(any("test_commands 为空" in error for error in errors))

    def test_success_evidence_passes(self):
        # [AC-005-2]
        errors = self.check(
            VERIFY_TEXT, ["python -m unittest tests.test_status"]
        )
        self.assertEqual(errors, [])

    def test_nonzero_exit_blocks(self):
        # [AC-005-8]
        text = VERIFY_TEXT.replace("Exit: `0`", "Exit: `1`")
        errors = self.check(text, ["python -m unittest tests.test_status"])
        self.assertTrue(any("退出码非 0" in error for error in errors))

    def test_pass_without_evidence_blocks(self):
        # [AC-005-3]
        errors = self.check(
            self.plain_pass(), ["python -m unittest tests.test_status"]
        )
        self.assertTrue(
            any("缺少结构化命令证据" in error for error in errors)
        )

    def test_merged_spec_skips_new_evidence_rules(self):
        # [AC-005-9]
        errors = self.check(self.plain_pass(), [], "MERGED")
        self.assertEqual(errors, [])

    def test_delivery_confirmed_merged_spec_keeps_evidence_rules(self):
        errors = engine.check_verification(
            self.plain_pass(),
            ["AC-001-1"],
            None,
            {
                "state": "MERGED",
                "delivery_confirmed_at": "2026-11-20T00:00:00+08:00",
            },
            self.config([]),
        )
        self.assertTrue(any("test_commands 为空" in error for error in errors))

    def test_unmerged_spec_cannot_use_legacy_escape(self):
        # [AC-005-10]
        errors = self.check(self.plain_pass(), [], "PR_READY")
        self.assertTrue(any("test_commands 为空" in error for error in errors))
        self.assertTrue(
            any("缺少结构化命令证据" in error for error in errors)
        )

    def test_verify_records_structured_evidence(self):
        # [AC-005-2]
        self.new_spec()
        self.approve_valid_spec()
        self.complete_design()
        self.complete_tasks()
        self.run_sdd("complete", "--spec", SPEC_ID, "--evidence", "开始实现")
        self.finish_implementation()
        self.set_config(
            test_commands=["python -m unittest tests.test_status"]
        )
        self.run_sdd("verify", "--spec", SPEC_ID)
        text = (
            self.root / "docs/specs/SPEC-ORDER-001/verification.md"
        ).read_text(encoding="utf-8")
        for field in ("Command:", "CWD:", "Exit: `0`", "Head:", "Plan-Hash:", "At:"):
            self.assertIn(field, text)
        self.assertEqual(
            engine.verification_evidence_errors(
                text,
                {"test_commands": ["python -m unittest tests.test_status"]},
                {"state": "VERIFYING"},
            ),
            [],
        )

    def set_config(self, **values):
        path = self.root / "sdd" / "config.json"
        config = json.loads(path.read_text(encoding="utf-8"))
        config.update(values)
        path.write_text(
            json.dumps(config, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


class TestCoverageTests(SddFlowBase):
    def config(self):
        return json.loads(
            (self.root / "sdd" / "config.json").read_text(encoding="utf-8")
        )

    def workflow(self):
        return json.loads(
            (self.root / "sdd" / "workflows" / "l2-standard.json").read_text(
                encoding="utf-8"
            )
        )

    def write_status_test(self, tag_inside=True):
        tag = "        # [AC-001-1]\n" if tag_inside else ""
        self.write(
            "tests/test_status.py",
            "import unittest\n\n\n"
            "class StatusTest(unittest.TestCase):\n"
            "    def test_cancel_pending_order(self):\n"
            f"{tag}"
            "        self.assertTrue(True)\n",
        )

    def test_task_test_name_must_exist(self):
        # [AC-005-4]
        self.write_status_test()
        tasks = engine.parse_tasks(TASKS_TEXT)
        self.assertEqual(
            engine.task_test_name_errors(self.root, self.config(), tasks), []
        )
        missing = TASKS_TEXT.replace(
            "StatusTest#test_cancel_pending_order",
            "MissingTest#test_not_written",
        )
        errors = engine.task_test_name_errors(
            self.root, self.config(), engine.parse_tasks(missing)
        )
        self.assertTrue(
            any("测试名无法定位" in error for error in errors)
        )
        self.assertTrue(any("test_not_written" in error for error in errors))

    def test_bare_ac_tag_does_not_count(self):
        # [AC-005-5]
        self.write("tests/test_bare.py", "# [AC-001-1]\n")
        errors = engine.check_test_coverage(
            self.root, self.config(), ["AC-001-1"]
        )
        self.assertTrue(any("函数体内" in error for error in errors))

        self.write(
            "tests/test_bare.py",
            "import unittest\n\n\n"
            "class BareTest(unittest.TestCase):\n"
            "    def test_ac(self):\n"
            "        # [AC-001-1]\n"
            "        self.assertTrue(True)\n",
        )
        self.assertEqual(
            engine.check_test_coverage(
                self.root, self.config(), ["AC-001-1"]
            ),
            [],
        )

    def test_medium_risk_requires_review(self):
        # [AC-005-6]
        state = {"risk": "medium", "risk_labels": [], "history": []}
        errors = engine.check_verification(
            VERIFY_TEXT,
            ["AC-001-1"],
            self.workflow(),
            state,
            self.config(),
        )
        self.assertTrue(
            any("独立审查" in error for error in errors)
        )
        errors = engine.check_verification(
            VERIFY_TEXT + VERIFY_STRICT_SUFFIX,
            ["AC-001-1"],
            self.workflow(),
            state,
            self.config(),
        )
        self.assertFalse(
            any("独立审查" in error for error in errors)
        )

    def test_low_risk_flow_unchanged(self):
        # [AC-005-7]
        state = {"risk": "low", "risk_labels": [], "history": []}
        workflow = self.workflow()
        self.assertEqual(
            engine.check_verification(
                VERIFY_TEXT,
                ["AC-001-1"],
                workflow,
                state,
                self.config(),
            ),
            [],
        )
        self.assertEqual(
            engine.gate_mode(self.config(), "G4", state, False, workflow),
            "auto",
        )
        self.assertEqual(
            engine.gate_mode(self.config(), "G5", state, False, workflow),
            "auto",
        )


class ContextBundleTests(SddFlowBase):
    def prepare_implementing(self, design_text=None):
        self.new_spec()
        self.approve_valid_spec()
        self.write(
            "docs/specs/SPEC-ORDER-001/design.md",
            design_text if design_text is not None else DESIGN_TEXT,
        )
        self.run_sdd("complete", "--spec", SPEC_ID, "--evidence", "design 完成")
        self.write("docs/specs/SPEC-ORDER-001/tasks.md", TASKS_TEXT)
        self.run_sdd("complete", "--spec", SPEC_ID, "--evidence", "tasks 完成")
        self.run_sdd("complete", "--spec", SPEC_ID, "--evidence", "开始实现")
        return self.next_action()

    def test_task_step_returns_all_fields(self):
        # [AC-004-1]
        action = self.prepare_implementing()
        bundle = action["context_bundle"]
        self.assertEqual(
            set(bundle),
            {
                "task",
                "frs",
                "acs",
                "design_sections",
                "contracts",
                "project_constraints",
                "fix_patterns",
                "allowed_paths",
                "exclude",
            },
        )
        self.assertEqual(
            bundle["task"],
            {
                "id": "T-001",
                "description": "实现订单取消接口和状态校验",
                "status": "Todo",
            },
        )
        self.assertEqual(bundle["frs"], ["FR-001"])
        self.assertEqual(bundle["acs"], ["AC-001-1"])
        self.assertTrue(
            any(
                "Spec覆盖关系" in item["heading"]
                and "AC-001-1" in item["reason"]
                for item in bundle["design_sections"]
            )
        )
        self.assertIn(
            "docs/specs/SPEC-ORDER-001/api/order.yaml", bundle["contracts"]
        )
        self.assertIn(
            {"path": "AGENTS.md", "scope": "."}, bundle["project_constraints"]
        )
        self.assertEqual(bundle["fix_patterns"], [])
        self.assertIn("tests/test_status.py", bundle["allowed_paths"])
        self.assertEqual(
            bundle["exclude"],
            [
                "docs/prd.md",
                "docs/specs/*（其他 Spec）",
                ".sdd/runtime/**",
                "历史聊天",
            ],
        )
        self.assertEqual(action["action"], "implement_task")
        self.assertEqual(action["task"], "T-001")
        self.assertEqual(
            action["artifact"], "docs/specs/SPEC-ORDER-001/tasks.md"
        )
        self.assertEqual(action["prompt_file"], "sdd/prompts/task.md")

    def test_non_task_step_returns_empty_bundle(self):
        # [AC-004-2]
        self.new_spec()
        action = self.next_action()
        bundle = action["context_bundle"]
        self.assertIsNone(bundle["task"])
        for field in (
            "frs",
            "acs",
            "design_sections",
            "contracts",
            "project_constraints",
            "fix_patterns",
            "allowed_paths",
            "exclude",
        ):
            self.assertEqual(bundle[field], [])
        self.assertEqual(action["action"], "write_spec")
        self.assertEqual(action["artifact"], "docs/specs/SPEC-ORDER-001/spec.md")

    def test_bundle_is_read_only(self):
        # [AC-004-3]
        self.prepare_implementing()
        state_path = self.root / "docs/specs/SPEC-ORDER-001/state.json"
        events_path = self.root / "docs/specs/SPEC-ORDER-001/events.jsonl"
        state_before = state_path.read_bytes()
        events_before = events_path.read_bytes()
        self.next_action()
        self.next_action()
        self.assertEqual(state_path.read_bytes(), state_before)
        self.assertEqual(events_path.read_bytes(), events_before)

    def test_allowed_paths_from_design_impact(self):
        # [AC-004-4]
        design = DESIGN_TEXT.replace(
            "## 5. 系统架构",
            """## 4.1 影响范围

| 模块/服务 | 影响 | 兼容性 | 回滚风险 |
|---|---|---|---|
| `sdd/scripts/sdd.py` | 增加取消逻辑 | 向后兼容 | 低 |
| `tests/test_status.py` | 新增单测 | 无 | 低 |

## 5. 系统架构""",
        )
        action = self.prepare_implementing(design)
        allowed = action["context_bundle"]["allowed_paths"]
        self.assertIn("sdd/scripts/sdd.py", allowed)
        self.assertIn("tests/test_status.py", allowed)

        self.write(
            "docs/specs/SPEC-ORDER-001/design.md",
            DESIGN_TEXT.replace(
                "- 请求/响应结构：见 `api/order.yaml`。\n", ""
            ).replace(
                "- 契约文件：`docs/specs/SPEC-ORDER-001/api/order.yaml`\n", ""
            ),
        )
        task = {
            "id": "T-999",
            "description": "无范围任务",
            "status": "Todo",
            "frs": ["FR-001"],
            "acs": ["AC-001-1"],
            "test": "",
            "command": "",
        }
        bundle = engine.build_context_bundle(
            self.root,
            self.root / "docs/specs/SPEC-ORDER-001",
            self.state(),
            task,
        )
        self.assertEqual(bundle["allowed_paths"], [])

    def test_bundle_excludes_other_specs(self):
        # [AC-004-5]
        self.write(
            "docs/specs/SPEC-OTHER-001/spec.md",
            SPEC_TEXT.replace("SPEC-ORDER-001", "SPEC-OTHER-001"),
        )
        self.write(
            "docs/specs/SPEC-OTHER-001/api/other.yaml",
            "openapi: 3.0.0\n",
        )
        action = self.prepare_implementing()
        bundle = action["context_bundle"]
        rendered = json.dumps(bundle, ensure_ascii=False)
        self.assertNotIn("SPEC-OTHER-001", rendered)
        self.assertNotIn("api/other.yaml", rendered)
        self.assertIn("docs/specs/*（其他 Spec）", bundle["exclude"])
        self.assertEqual(bundle["fix_patterns"], [])


def valid_v2_profile(name="l2-refactor"):
    return {
        "schema": 2,
        "name": name,
        "version": 1,
        "description": "行为保持型改造流程",
        "stages": list(engine.STAGE_ORDER),
        "artifacts": {
            "DRAFT": "spec.md",
            "SPEC_READY": "design.md",
            "DESIGN_READY": "tasks.md",
            "TASKS_READY": "tasks.md",
            "IMPLEMENTING": "tasks.md",
            "VERIFYING": "verification.md",
            "PR_READY": "PR_BODY.md",
        },
        "gates": {
            "G0": "human",
            "G1": "auto",
            "G2": "auto",
            "G3": "auto",
            "G4": "auto",
            "G5": "auto",
        },
        "required_gates": {
            stage: engine.required_gates(stage) for stage in engine.STAGE_ORDER
        },
        "gate_checks": {
            "G0": ["G0-01", "G0-02", "G0-03", "G0-04", "G0-05", "G0-06"],
            "G1": ["G1-01", "G1-02", "G1-03", "G1-04"],
        },
        "human_checkpoints": [
            {"type": "approve_spec"},
            {"type": "confirm_delivery"},
        ],
        "design_mode": "full",
        "review_required": False,
        "risk_stop": ["data-loss"],
        "context_rules": {
            "include": ["docs/knowledge/**"],
            "exclude": ["docs/prd.md"],
        },
        "allow_rewind_to": [
            "DRAFT",
            "SPEC_READY",
            "DESIGN_READY",
            "TASKS_READY",
            "IMPLEMENTING",
            "VERIFYING",
        ],
    }


class WorkflowProfileTests(unittest.TestCase):
    def test_valid_v2_profile(self):
        # [AC-001-1]
        preset = valid_v2_profile()
        self.assertEqual(
            engine.validate_workflow_preset(preset, "l2-refactor.json"), []
        )
        digest = engine.workflow_digest(preset)
        self.assertRegex(digest, r"^[0-9a-f]{64}$")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copytree(KIT_ROOT / "sdd", root / "sdd")
            path = root / "sdd" / "workflows" / "l2-refactor.json"
            path.write_text(
                json.dumps(preset, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            loaded = engine.load_workflow_preset(root, "l2-refactor")
            self.assertEqual(loaded["schema"], 2)
            self.assertEqual(
                engine.workflow_digest(loaded), engine.workflow_digest(preset)
            )

    def test_unknown_fields_report_paths(self):
        # [AC-001-2]
        preset = valid_v2_profile()
        preset["unexpected"] = True
        preset["context_rules"]["bogus"] = []
        errors = engine.validate_workflow_preset(preset, "profile.json")
        rendered = "\n".join(errors)
        self.assertIn("$.unexpected", rendered)
        self.assertIn("context_rules.bogus", rendered)

    def test_schema1_snapshot_unchanged(self):
        # [AC-001-3]
        self.assertEqual(engine.WORKFLOW_SCHEMA, 1)
        for name in ("l2-standard", "l2-hotfix", "l2-strict"):
            preset = json.loads(
                (KIT_ROOT / "sdd" / "workflows" / f"{name}.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(
                engine.validate_workflow_preset(preset, f"{name}.json"), []
            )
        standard = json.loads(
            (KIT_ROOT / "sdd" / "workflows" / "l2-standard.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            engine.workflow_digest(standard),
            "ae89c532988018c3f6d3c222c4a66da2a44981f33c8401d62a632bef66a8e910",
        )
        standard["legacy_extension"] = True
        self.assertEqual(
            engine.validate_workflow_preset(standard, "l2-standard.json"), []
        )


class ArtifactHashTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def write_artifact(self, name: str, text: str, newline: str) -> Path:
        path = self.root / name
        path.write_bytes(text.replace("\n", newline).encode("utf-8"))
        return path

    def test_text_hash_is_line_ending_stable(self):
        # [AC-001-1]
        text = "# title\n\ncontent\n"
        lf_path = self.write_artifact("lf.md", text, "\n")
        crlf_path = self.write_artifact("crlf.md", text, "\r\n")
        self.assertEqual(
            engine.artifact_sha256(lf_path),
            engine.artifact_sha256(crlf_path),
        )

    def test_check_ignores_line_ending_only_change(self):
        # [AC-001-2]
        text = "# title\n\ncontent\n"
        lf_path = self.write_artifact("lf.md", text, "\n")
        crlf_path = self.write_artifact("crlf.md", text, "\r\n")
        expected = engine.artifact_sha256(crlf_path)
        self.assertTrue(engine.artifact_hash_matches(lf_path, expected))

    def test_check_rejects_text_change(self):
        # [AC-001-3]
        original = self.write_artifact(
            "original.md", "# title\n\noriginal\n", "\r\n"
        )
        changed = self.write_artifact(
            "changed.md", "# title\n\nchanged\n", "\n"
        )
        expected = engine.artifact_sha256(original)
        self.assertFalse(engine.artifact_hash_matches(changed, expected))

    def test_check_accepts_legacy_crlf_hash(self):
        # [AC-002-1]
        text = "# title\n\ncontent\n"
        crlf_path = self.write_artifact("crlf.md", text, "\r\n")
        lf_path = self.write_artifact("lf.md", text, "\n")
        legacy_expected = hashlib.sha256(crlf_path.read_bytes()).hexdigest()
        self.assertTrue(engine.artifact_hash_matches(lf_path, legacy_expected))

    def test_check_rejects_content_change_with_legacy_hash(self):
        # [AC-002-2]
        original = self.write_artifact(
            "legacy-original.md", "# title\n\noriginal\n", "\r\n"
        )
        changed = self.write_artifact(
            "legacy-changed.md", "# title\n\nchanged\n", "\n"
        )
        legacy_expected = hashlib.sha256(original.read_bytes()).hexdigest()
        self.assertFalse(engine.artifact_hash_matches(changed, legacy_expected))

    def test_new_gate_hash_uses_lf(self):
        # [AC-002-3]
        text = "# title\n\ncontent\n"
        crlf_path = self.write_artifact("gate-crlf.md", text, "\r\n")
        relative, digest, _ = engine.artifact_digest(
            self.root, self.root, "gate-crlf.md"
        )
        self.assertEqual(relative, "gate-crlf.md")
        self.assertEqual(
            digest,
            hashlib.sha256(text.encode("utf-8")).hexdigest(),
        )
        self.assertNotEqual(
            digest,
            hashlib.sha256(crlf_path.read_bytes()).hexdigest(),
        )


class GitTrailerTests(unittest.TestCase):
    def test_recent_trailer_only_applies_to_active_specs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(
                ["git", "config", "user.email", "test@example.invalid"],
                cwd=root,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "SDD Test"],
                cwd=root,
                check=True,
            )
            (root / "note.txt").write_text("no trailer\n", encoding="utf-8")
            subprocess.run(["git", "add", "note.txt"], cwd=root, check=True)
            subprocess.run(
                ["git", "commit", "-q", "-m", "init"],
                cwd=root,
                check=True,
            )

            self.assertTrue(engine.check_git(root, SPEC_ID, "DRAFT"))
            self.assertEqual(engine.check_git(root, SPEC_ID, "MERGED"), [])


if __name__ == "__main__":
    unittest.main()
