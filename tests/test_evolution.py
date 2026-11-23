import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from sdd.scripts import sdd as sdd_module


KIT_ROOT = Path(__file__).resolve().parents[1]
try:
    from tests.test_sdd import DESIGN_TEXT, TASKS_TEXT, VERIFY_TEXT
except ImportError:  # pragma: no cover - direct test discovery fallback
    from test_sdd import DESIGN_TEXT, TASKS_TEXT, VERIFY_TEXT


SPEC_TEMPLATE = """# 演进内核规格说明书（Spec）

## 1. 元数据

| 项 | 内容 |
|---|---|
| Spec ID | {spec_id} |
| 工作项 ID | SDD-GH-900 |
| FEAT ID | {feat} |
| 原始需求来源 | https://example.invalid/issues/900 |
| 作者 | Test Agent |
| 创建日期 | 2026-11-23 |
| 状态 | Draft |
| 版本号 | 1.0.0 |
| 产品类型 | 传统产品 |
| 模板适配 | 核心骨架 |
| 关联人 | 产品负责人：仓库维护者；技术负责人：仓库维护者 |
| 原型版本 | 不涉及 |

## 2. 范围声明

- In-Scope：验证追溯链。
- Out-of-Scope：不验证真实业务。

## 3. 业务上下文

### 3.1 干系人与角色

| 角色 | 诉求 | 使用场景 | 责任边界 |
|---|---|---|---|
| 开发者 | 追溯需求 | 日常开发 | 不改核心 |

### 3.2 业务流程

工作项进入 FEAT，再进入 Spec。

### 3.3 业务规则

- BR-001：FEAT 必须唯一。

## 4. 功能需求与验收条件

### FR-001 可追溯需求

- 功能描述：需求可被追溯。
- 用户场景：审计。
- 验收条件：
  - AC-001-1：Given 需求已登记，When 校验追溯链，Then 返回通过。【执行路径：本地单元测试】

### 4.1 UI规格（涉及前端UI时必填）

不涉及。

## 5. 边界与异常

| 场景类型 | 场景描述 | 关联FR/AC | 预期行为（错误码/降级策略/提示信息） |
|---|---|---|---|
| 异常场景 | FEAT 重复 | FR-001；AC-001-1 | 阻断 |

## 6. 非功能需求

| 类型 | 要求 | 指标/验收方式 | 关联FR/AC |
|---|---|---|---|
| 可用性 | 错误可定位 | 单元测试 | FR-001；AC-001-1 |

## 7. 外部接口

| 方法 | 路径 | 用途 | 归属AC |
|---|---|---|---|
| 不涉及 | 不涉及 | 不涉及 | AC-001-1 |

- 请求/响应示例：不涉及。
- 契约文件：不涉及。

## 8. 数据模型

- 核心实体定义：FEAT 记录。
- 数据流说明：工作项到 Spec。

## 9. 约束与假设

- 技术约束：只用标准库。
- 业务约束：不改旧 Spec。
- 假设条件：PRD 索引存在。

## 10. 变更历史

| 日期 | 版本 | 变更内容 | 作者 |
|---|---|---|---|
| 2026-11-23 | 1.0.0 | 初始版本 | Test Agent |
"""


class EvolutionTestBase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        shutil.copytree(KIT_ROOT / "sdd", self.root / "sdd")
        (self.root / "tests").mkdir()
        (self.root / "sdd" / "context").mkdir(exist_ok=True)

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

    def run_json(self, *args, expect=0):
        return json.loads(self.run_sdd(*args, expect=expect).stdout)

    def write(self, relative, text):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def new_spec(self, spec_id="SPEC-EVOL-001", risk="low"):
        self.run_sdd(
            "new",
            spec_id,
            "--title",
            "演进内核",
            "--work-item",
            "SDD-GH-900",
            "--issue-url",
            "https://example.invalid/issues/900",
            "--risk",
            risk,
        )
        return spec_id

    def write_spec(self, spec_id="SPEC-EVOL-001", feat="FEAT-001"):
        self.write(
            f"docs/specs/{spec_id}/spec.md",
            SPEC_TEMPLATE.format(spec_id=spec_id, feat=feat),
        )

    def prd_index(self):
        return (
            self.root / "docs" / "prd-index.md"
        ).read_text(encoding="utf-8")

    def spec_dir(self, spec_id="SPEC-EVOL-001"):
        return self.root / "docs" / "specs" / spec_id


class TraceabilityTests(EvolutionTestBase):
    def test_feat_and_prd_chain(self):
        spec_id = self.new_spec()
        self.write_spec(spec_id)
        checked = self.run_json(
            "check", "--spec", spec_id, "--stage", "spec", "--json"
        )
        self.assertTrue(checked["ok"], checked)

        self.write_spec(spec_id, feat="FEAT-999")
        checked = self.run_json(
            "check", "--spec", spec_id, "--stage", "spec", "--json", expect=1
        )
        self.assertTrue(
            any("FEAT" in error for error in checked["errors"]),
            checked["errors"],
        )

        index = self.prd_index()
        extra = (
            "| SDD-GH-900 | https://example.invalid/issues/900 | current | "
            "FEAT-001 | SPEC-EVOL-001 | duplicate | 1 |\n"
        )
        self.write("docs/prd-index.md", index + extra)
        self.write_spec(spec_id, feat="FEAT-001")
        checked = self.run_json(
            "check", "--spec", spec_id, "--stage", "spec", "--json", expect=1
        )
        self.assertTrue(
            any("FEAT" in error and "重复" in error for error in checked["errors"]),
            checked["errors"],
        )

    def test_orphans_and_duplicate_feat(self):
        spec_id = self.new_spec()
        text = SPEC_TEMPLATE.format(spec_id=spec_id, feat="FEAT-001")
        text = text.replace(
            "  - AC-001-1：Given 需求已登记，When 校验追溯链，Then 返回通过。"
            "【执行路径：本地单元测试】\n",
            "  - AC-001-1：Given 需求已登记，When 校验追溯链，Then 返回通过。"
            "【执行路径：本地单元测试】\n"
            "  - AC-009-1：Given 孤儿条件，When 校验，Then 被阻断。"
            "【执行路径：本地单元测试】\n",
        )
        self.write(f"docs/specs/{spec_id}/spec.md", text)
        checked = self.run_json(
            "check", "--spec", spec_id, "--stage", "spec", "--json", expect=1
        )
        self.assertTrue(
            any("AC-009-1" in error or "FR-009" in error for error in checked["errors"]),
            checked["errors"],
        )

    def test_g0_g1_separate(self):
        spec_id = self.new_spec()
        self.write_spec(spec_id)
        self.run_sdd(
            "approve",
            "--spec",
            spec_id,
            "--human",
            "--evidence",
            "需求已确认",
        )
        reports = self.root / "sdd" / "reports" / spec_id
        g0 = (reports / "gate0-report.md").read_text(encoding="utf-8")
        g1 = (reports / "gate1-report.md").read_text(encoding="utf-8")
        self.assertIn("G0-", g0)
        self.assertIn("G1-", g1)
        self.assertNotIn("G1-", g0)
        self.assertIn("## 2. 检查项", g0)
        self.assertIn("## 2. 检查项", g1)


class GateRegistryTests(EvolutionTestBase):
    def test_registry_and_gate_output(self):
        """[AC-001-4] [AC-006-1] Gate 注册表、报告分组与稳定检查 ID。"""
        spec_id = self.new_spec()
        self.write_spec(spec_id)
        checked = self.run_json(
            "check", "--spec", spec_id, "--stage", "spec", "--json"
        )
        self.assertTrue(checked["ok"], checked)
        checks = checked["checks"]
        self.assertTrue(checks)
        by_id = {item["id"]: item for item in checks}
        self.assertIn("G0-04", by_id)
        self.assertIn("G1-05", by_id)
        required = {
            "id",
            "gate",
            "title",
            "trigger",
            "level",
            "waivable",
            "evidence",
            "owner",
            "result",
            "detail",
        }
        self.assertTrue(required.issubset(by_id["G0-04"]))
        self.assertEqual(checked["summary"]["block"], 0)

        self.run_sdd(
            "approve",
            "--spec",
            spec_id,
            "--human",
            "--evidence",
            "需求已确认",
        )
        g1 = (
            self.root / "sdd" / "reports" / spec_id / "gate1-report.md"
        ).read_text(encoding="utf-8")
        self.assertIn("G1-04", g1)

    def test_block_cannot_complete(self):
        """[AC-006-3] 强制项失败时阻断状态迁移。"""
        spec_id = self.new_spec()
        self.write_spec(spec_id, feat="FEAT-999")
        blocked = self.run_sdd(
            "approve",
            "--spec",
            spec_id,
            "--human",
            "--evidence",
            "错误需求",
            expect=2,
        )
        self.assertIn("FEAT", blocked.stderr + blocked.stdout)
        state = json.loads(
            (self.spec_dir(spec_id) / "state.json").read_text(encoding="utf-8")
        )
        self.assertEqual(state["state"], "DRAFT")

        legacy_dir = self.root / "docs" / "specs" / "SPEC-LEGACY-001"
        legacy_dir.mkdir(parents=True, exist_ok=True)
        self.assertEqual(
            sdd_module.check_verification_evidence(
                self.root,
                legacy_dir,
                {},
                "SPEC-LEGACY-001",
                "`src/order.py`",
                "",
                "",
                {"state": "MERGED"},
            ),
            [],
        )


class ContextBundleTests(EvolutionTestBase):
    def complete_design(self, spec_id):
        self.write(
            f"docs/specs/{spec_id}/design.md",
            DESIGN_TEXT.replace("SPEC-ORDER-001", spec_id),
        )
        self.run_sdd(
            "complete",
            "--spec",
            spec_id,
            "--evidence",
            "design complete",
        )

    def complete_tasks(self, spec_id):
        tasks = TASKS_TEXT.replace("SPEC-ORDER-001", spec_id)
        tasks = tasks.replace(
            "实现订单取消接口和状态校验",
            "实现 `src/order.py` 并补 `tests/test_order.py`",
        )
        self.write(f"docs/specs/{spec_id}/tasks.md", tasks)
        self.run_sdd(
            "complete",
            "--spec",
            spec_id,
            "--evidence",
            "tasks complete",
        )
        self.run_sdd(
            "complete",
            "--spec",
            spec_id,
            "--evidence",
            "implementation started",
        )

    def implementation_spec(self):
        spec_id = self.new_spec()
        self.write_spec(spec_id)
        self.run_sdd(
            "approve",
            "--spec",
            spec_id,
            "--human",
            "--evidence",
            "需求已确认",
        )
        self.complete_design(spec_id)
        self.complete_tasks(spec_id)
        self.write(
            f"docs/specs/{spec_id}/api/order.yaml",
            "openapi: 3.0.0\ninfo:\n  title: order\n  version: 1.0.0\n",
        )
        return spec_id

    def next_payload(self, spec_id):
        return self.run_json("next", "--spec", spec_id, "--json")

    def test_context_bundle_schema(self):
        spec_id = self.implementation_spec()
        payload = self.next_payload(spec_id)
        self.assertEqual(payload["action"], "implement_task")
        bundle = payload["context_bundle"]
        required = {
            "schema",
            "spec",
            "task",
            "requirements",
            "design_sections",
            "contracts",
            "constraints",
            "review_overlays",
            "fix_patterns",
            "knowledge",
            "allowed_paths",
            "exclude",
            "scope_policy",
            "blocked",
            "empty",
            "notes",
        }
        self.assertTrue(required.issubset(bundle))
        self.assertEqual(bundle["task"]["id"], "T-001")
        self.assertEqual(bundle["requirements"]["acs"][0]["id"], "AC-001-1")
        self.assertTrue(bundle["design_sections"])
        self.assertTrue(
            any(path.endswith("src/order.py") for path in bundle["allowed_paths"])
        )
        resumed = subprocess.run(
            [sys.executable, "-m", "sdd", "resume", "--spec", spec_id, "--json"],
            cwd=self.root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        self.assertEqual(resumed.returncode, 0, resumed.stderr)
        self.assertIn("context_bundle", json.loads(resumed.stdout)["next"])

    def test_context_empty_and_readonly(self):
        spec_id = self.new_spec()
        state_path = self.spec_dir(spec_id) / "state.json"
        event_path = self.spec_dir(spec_id) / "events.jsonl"
        before = (
            state_path.read_bytes(),
            event_path.read_bytes() if event_path.exists() else b"",
        )
        first = self.next_payload(spec_id)["context_bundle"]
        second = self.next_payload(spec_id)["context_bundle"]
        after = (
            state_path.read_bytes(),
            event_path.read_bytes() if event_path.exists() else b"",
        )
        self.assertEqual(first, second)
        self.assertTrue(first["empty"])
        self.assertIsNone(first["task"])
        self.assertEqual(first["requirements"]["acs"], [])
        self.assertEqual(before, after)

    def test_context_scope_guard(self):
        """[AC-003-5] 超出允许范围时必须停止并扩大范围。"""
        spec_id = self.implementation_spec()
        bundle = self.next_payload(spec_id)["context_bundle"]
        self.assertIn("不得静默扩大", bundle["scope_policy"])
        self.assertIn("docs/specs", " ".join(bundle["exclude"]))
        self.assertIn("tests/test_order.py", bundle["allowed_paths"])

    def test_context_patterns(self):
        """[AC-009-2] [AC-009-4] 适用 Fix Pattern 自动带入，未验证模式只作参考。"""
        spec_id = self.implementation_spec()
        self.write(
            "docs/knowledge/patterns/FP-001.md",
            """---
id: FP-001
status: verified
applies_to: src/order.py
---

# FP-001 状态更新必须有回归测试

## 症状
状态更新没有测试。
""",
        )
        self.write(
            "docs/knowledge/patterns/FP-002.md",
            """---
id: FP-002
status: draft
applies_to: src/order.py
---

# FP-002 未验证模式

## 症状
候选模式。
""",
        )
        bundle = self.next_payload(spec_id)["context_bundle"]
        by_id = {item["id"]: item for item in bundle["fix_patterns"]}
        self.assertIn("FP-001", by_id)
        self.assertIn("FP-002", by_id)
        self.assertFalse(by_id["FP-001"]["reference_only"])
        self.assertTrue(by_id["FP-002"]["reference_only"])

        self.write(
            "docs/knowledge/index.md",
            """# 知识索引

| ID | Type | Statement | Source | Version | Scope | Owner | Status | Links |
|---|---|---|---|---|---|---|---|---|
| FACT-001 | FACT | 订单状态只能由服务端更新 | ADR-001 | 1 | order | team | CONFIRMED | FEAT-001 |
| CONFLICT-001 | CONFLICT | 两个来源对取消时限冲突 | sources/a,b | v1 | order | team | OPEN | FEAT-001 |
| GAP-001 | GAP | 缺少超时规则 | N/A | N/A | order | team | OPEN | AC-001-1 |
""",
        )
        bundle = self.next_payload(spec_id)["context_bundle"]
        self.assertTrue(bundle["blocked"])
        self.assertIn(
            "CONFLICT-001",
            [item["id"] for item in bundle["knowledge"]],
        )


class EvidenceTests(ContextBundleTests):
    def test_scan_test_definitions_handles_multiline_strings(self):
        source = (
            "import unittest\n\n"
            "class SampleTest(unittest.TestCase):\n"
            "    def test_one(self):\n"
            "        value = \"\"\"line one\n"
            "no indentation inside string\n"
            "\"\"\"\n"
            "        self.assertTrue(value)\n"
        )
        definitions = sdd_module.scan_test_definitions(
            [("tests/test_sample.py", source)]
        )
        self.assertIn("test_one", definitions)

    def test_append_to_section_preserves_existing_content(self):
        text = "# 验证\n\n## 3. 结果\n\n- 第一条证据\n\n## 4. 未运行\n\n无。\n"
        updated = sdd_module.append_to_section(
            text,
            ("结果", "Results"),
            "- 第二条证据",
        )
        self.assertIn("- 第一条证据", updated)
        self.assertIn("- 第二条证据", updated)
        self.assertLess(
            updated.index("- 第一条证据"),
            updated.index("- 第二条证据"),
        )
        self.assertIn("## 4. 未运行", updated)

    def set_test_commands(self, *commands):
        path = self.root / "sdd" / "config.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["test_commands"] = list(commands)
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def write_passing_test(self, body=None, method="testCancelPendingOrder"):
        self.write(
            "tests/test_status.py",
            body
            or f"""import unittest


class OrderServiceTest(unittest.TestCase):
    def {method}(self):
        \"\"\"[AC-001-1]\"\"\"
        self.assertTrue(True)
""",
        )

    def reach_verifying(self, write_verification=True):
        spec_id = self.implementation_spec()
        self.write_passing_test()
        self.run_sdd("start", "--spec", spec_id, "--task", "T-001")
        self.run_sdd(
            "complete",
            "--spec",
            spec_id,
            "--task",
            "T-001",
            "--evidence",
            "T-001 implemented",
        )
        state = json.loads(
            (self.spec_dir(spec_id) / "state.json").read_text(encoding="utf-8")
        )
        self.assertEqual(state["state"], "VERIFYING")
        if write_verification:
            self.write(
                f"docs/specs/{spec_id}/verification.md",
                VERIFY_TEXT.replace("SPEC-ORDER-001", spec_id),
            )
        return spec_id

    def test_verify_records_and_g5_blocks(self):
        """[AC-004-5] 非零退出码或未执行命令不能作为 PASS 证据。"""
        spec_id = self.reach_verifying()
        blocked = self.run_json(
            "check", "--spec", spec_id, "--stage", "verify", "--json", expect=1
        )
        self.assertTrue(
            any("证据" in error for error in blocked["errors"]),
            blocked["errors"],
        )
        self.set_test_commands("python -m unittest tests.test_status -v")
        self.run_sdd("verify", "--spec", spec_id)
        evidence_path = self.spec_dir(spec_id) / "verification-evidence.jsonl"
        self.assertTrue(evidence_path.is_file())
        record = json.loads(evidence_path.read_text(encoding="utf-8").splitlines()[0])
        for key in (
            "schema",
            "spec",
            "command",
            "cwd",
            "started_at",
            "finished_at",
            "exit_code",
            "duration_ms",
            "output_sha256",
            "output_excerpt",
            "artifact_hashes",
        ):
            self.assertIn(key, record)
        self.assertEqual(record["exit_code"], 0)
        checked = self.run_json(
            "check", "--spec", spec_id, "--stage", "verify", "--json"
        )
        self.assertTrue(checked["ok"], checked)

    def test_fake_test_and_ac_tag(self):
        """[AC-004-4] 注释或空测试中的 AC 标签不计为覆盖。"""
        spec_id = self.reach_verifying()
        self.write_passing_test(
            body="""class OrderServiceTest:
    def testCancelPendingOrder(self):
        \"\"\"[AC-001-1]\"\"\"
        pass
"""
        )
        fake = self.run_json(
            "check", "--spec", spec_id, "--stage", "verify", "--json", expect=1
        )
        self.assertTrue(
            any("AC-001-1" in error for error in fake["errors"]),
            fake["errors"],
        )

        tasks_path = self.spec_dir(spec_id) / "tasks.md"
        tasks = tasks_path.read_text(encoding="utf-8").replace(
            "StatusTest#test_cancel_pending_order",
            "StatusTest#testDoesNotExist",
            1,
        )
        tasks_path.write_text(tasks, encoding="utf-8")
        missing = self.run_json(
            "check", "--spec", spec_id, "--stage", "tasks", "--json", expect=1
        )
        self.assertTrue(
            any("testDoesNotExist" in error for error in missing["errors"]),
            missing["errors"],
        )
        by_id = {item["id"]: item for item in missing["checks"]}
        self.assertIn("G4-03", by_id)
        self.assertEqual(by_id["G4-03"]["result"], "block")
        self.assertIn("testDoesNotExist", by_id["G4-03"]["detail"])
        self.assertNotIn(
            "testDoesNotExist",
            " ".join(
                item["detail"]
                for item in missing["checks"]
                if item["id"].endswith("-99")
            ),
        )


class ProfileTests(EvolutionTestBase):
    def run_module(self, *args, expect=0):
        env = dict(**__import__("os").environ)
        env["PYTHONPATH"] = str(self.root)
        env["PYTHONIOENCODING"] = "utf-8"
        result = subprocess.run(
            [sys.executable, "-m", "sdd", *args],
            cwd=self.root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )
        self.assertEqual(
            result.returncode,
            expect,
            msg=f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )
        return result

    def profile_copy(self):
        return json.loads(
            (KIT_ROOT / "sdd" / "workflows" / "l2-refactor.json").read_text(
                encoding="utf-8"
            )
        )

    def write_profile(self, name, data):
        self.write(
            f"sdd/workflows/{name}.json",
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        )

    def test_profile_v2_and_refactor(self):
        """[AC-010-3] 旧 JSON 字段兼容与新 Profile 预设生效。"""
        validated = json.loads(
            self.run_module(
                "workflow",
                "validate",
                "--file",
                "sdd/workflows/l2-refactor.json",
                "--json",
            ).stdout
        )
        self.assertTrue(validated["ok"], validated)
        self.assertEqual(validated["schema"], 2)
        profile = self.profile_copy()
        self.assertEqual(profile["schema"], 2)
        self.assertIn("gate_checks", profile)
        self.assertIn("human_checkpoints", profile)
        self.assertIn("context_rules", profile)

        spec_id = "SPEC-REFACTOR-001"
        self.run_sdd(
            "new",
            spec_id,
            "--title",
            "存量改造",
            "--work-item",
            "SDD-GH-901",
            "--issue-url",
            "https://example.invalid/issues/901",
            "--workflow",
            "l2-refactor",
        )
        snapshot = json.loads(
            (self.spec_dir(spec_id) / "workflow.json").read_text(encoding="utf-8")
        )
        self.assertEqual(snapshot["schema"], 2)
        self.assertEqual(snapshot["name"], "l2-refactor")
        self.assertIn("context_rules", snapshot)
        next_payload = self.run_json("next", "--spec", spec_id, "--json")
        self.assertEqual(next_payload["workflow"]["name"], "l2-refactor")

        blocked = self.run_sdd(
            "new",
            "SPEC-REFACTOR-002",
            "--title",
            "破坏性改造",
            "--work-item",
            "SDD-GH-902",
            "--workflow",
            "l2-refactor",
            "--risk-label",
            "public_api_break",
            expect=2,
        )
        self.assertIn("public_api_break", blocked.stderr + blocked.stdout)

    def test_profile_errors_and_snapshot(self):
        """[AC-005-5] [AC-010-1] 安全必需检查不可移除，旧快照继续运行。"""
        profile = self.profile_copy()
        cases = []

        unknown_field = json.loads(json.dumps(profile))
        unknown_field["unexpected_field"] = True
        cases.append((unknown_field, "unexpected_field"))

        unknown_stage = json.loads(json.dumps(profile))
        unknown_stage["stages"].append("NOT_A_STAGE")
        cases.append((unknown_stage, "NOT_A_STAGE"))

        unknown_check = json.loads(json.dumps(profile))
        unknown_check["gate_checks"]["G1"].append("G1-99")
        cases.append((unknown_check, "G1-99"))

        security_removed = json.loads(json.dumps(profile))
        security_removed["gate_checks"]["G5"] = ["G5-01"]
        cases.append((security_removed, "G5-03"))

        empty_checks = json.loads(json.dumps(profile))
        empty_checks["gate_checks"]["G4"] = []
        cases.append((empty_checks, "gate_checks.G4 不得为空检查集"))

        for index, (data, expected) in enumerate(cases, start=1):
            name = f"l2-invalid-{index}"
            data["name"] = name
            self.write_profile(name, data)
            result = self.run_module(
                "workflow",
                "validate",
                "--file",
                f"sdd/workflows/{name}.json",
                "--json",
                expect=1,
            )
            payload = json.loads(result.stdout)
            self.assertFalse(payload["ok"])
            self.assertTrue(
                any(expected in error for error in payload["errors"]),
                payload["errors"],
            )

        spec_id = "SPEC-REFACTOR-003"
        self.run_sdd(
            "new",
            spec_id,
            "--title",
            "快照兼容",
            "--work-item",
            "SDD-GH-903",
            "--workflow",
            "l2-refactor",
        )
        snapshot_path = self.spec_dir(spec_id) / "workflow.json"
        before = snapshot_path.read_text(encoding="utf-8")
        broken = self.profile_copy()
        broken["schema"] = 99
        self.write_profile("l2-refactor", broken)
        next_payload = self.run_json("next", "--spec", spec_id, "--json")
        self.assertEqual(next_payload["workflow"]["name"], "l2-refactor")
        self.assertEqual(before, snapshot_path.read_text(encoding="utf-8"))

    def test_omitted_or_empty_gate_checks_fall_back_to_full_gate(self):
        profile = self.profile_copy()
        self.assertEqual(
            sdd_module.selected_checks(profile, "G4"),
            sdd_module.check_ids_for_gate("G4"),
        )
        self.assertEqual(
            sdd_module.selected_checks(
                {"gate_checks": {"G4": []}},
                "G4",
            ),
            sdd_module.check_ids_for_gate("G4"),
        )


class WaiverTests(EvolutionTestBase):
    def reach_docs_verifying(self):
        spec_id = self.new_spec()
        self.write_spec(spec_id)
        self.run_sdd(
            "approve",
            "--spec",
            spec_id,
            "--human",
            "--evidence",
            "需求已确认",
        )
        design = DESIGN_TEXT.replace("SPEC-ORDER-001", spec_id).replace(
            "| 风险/依赖 | 影响 | 缓解措施 | 负责人 |",
            "| 风险/依赖 | 影响 | 措施 | 责任 |",
        )
        self.write(f"docs/specs/{spec_id}/design.md", design)
        checked = self.run_json(
            "check", "--spec", spec_id, "--stage", "design", "--json"
        )
        self.assertTrue(checked["ok"], checked)
        by_id = {item["id"]: item for item in checked["checks"]}
        self.assertEqual(by_id["G2-04"]["result"], "warn")
        inbox = self.run_json("inbox", "--json")
        self.assertTrue(
            any(
                item.get("action") == "warn"
                and "G2-04" in item.get("reason", "")
                for item in inbox["items"]
            ),
            inbox["items"],
        )
        self.run_sdd(
            "complete", "--spec", spec_id, "--evidence", "design complete"
        )
        tasks = TASKS_TEXT.replace("SPEC-ORDER-001", spec_id)
        self.write(f"docs/specs/{spec_id}/tasks.md", tasks)
        self.run_sdd(
            "complete", "--spec", spec_id, "--evidence", "tasks complete"
        )
        self.run_sdd(
            "complete", "--spec", spec_id, "--evidence", "implementation started"
        )
        self.write(
            "tests/test_status.py",
            """import unittest


class OrderServiceTest(unittest.TestCase):
    def testCancelPendingOrder(self):
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
            "--evidence",
            "T-001 implemented",
        )
        self.write(
            f"docs/specs/{spec_id}/verification.md",
            VERIFY_TEXT.replace("SPEC-ORDER-001", spec_id),
        )
        state = json.loads(
            (self.spec_dir(spec_id) / "state.json").read_text(encoding="utf-8")
        )
        self.assertEqual(state["state"], "VERIFYING")
        return spec_id

    def test_warn_and_waiver_lifecycle(self):
        """[AC-004-6] [AC-006-2] [AC-006-4] [AC-006-5] warn、豁免字段、到期与范围。"""
        spec_id = self.reach_docs_verifying()
        blocked = self.run_json(
            "check", "--spec", spec_id, "--stage", "verify", "--json", expect=1
        )
        self.assertTrue(
            any("G5-09" in error for error in blocked["errors"]),
            blocked["errors"],
        )
        waiver = self.run_json(
            "waive",
            "--spec",
            spec_id,
            "--check",
            "G5-09",
            "--scope",
            "verification",
            "--reason",
            "纯文档变更，不需要测试命令",
            "--expires-at",
            "2099-12-31",
            "--evidence",
            "docs-only change",
            "--approver",
            "李四 <li@example.com>",
            "--human",
            "--json",
        )
        self.assertTrue(waiver["ok"], waiver)
        record = waiver["waiver"]
        for key in (
            "id",
            "check_id",
            "spec",
            "scope",
            "reason",
            "approver",
            "created_at",
            "expires_at",
            "evidence",
        ):
            self.assertIn(key, record)
        checked = self.run_json(
            "check", "--spec", spec_id, "--stage", "verify", "--json"
        )
        self.assertTrue(checked["ok"], checked)
        by_id = {item["id"]: item for item in checked["checks"]}
        self.assertEqual(by_id["G5-09"]["result"], "waived")
        self.assertEqual(by_id["G5-09"]["waiver_id"], record["id"])
        inbox = self.run_json("inbox", "--json")
        self.assertTrue(
            any(
                item.get("action") == "waiver"
                and item.get("waiver_id") == record["id"]
                for item in inbox["items"]
            ),
            inbox["items"],
        )
        self.run_sdd(
            "complete",
            "--spec",
            spec_id,
            "--evidence",
            "验证完成（带豁免）",
        )
        state = json.loads(
            (self.spec_dir(spec_id) / "state.json").read_text(encoding="utf-8")
        )
        self.assertEqual(state["state"], "PR_READY")
        report = (
            self.root / "sdd" / "reports" / spec_id / "gate5-report.md"
        ).read_text(encoding="utf-8")
        self.assertIn("G5-09", report)
        self.assertIn("WAIVED", report)

    def test_spec_scope_does_not_cover_verification(self):
        spec_id = self.reach_docs_verifying()
        waiver = self.run_json(
            "waive",
            "--spec",
            spec_id,
            "--check",
            "G5-09",
            "--scope",
            "spec",
            "--reason",
            "验证阶段不应被 spec 范围豁免",
            "--expires-at",
            "2099-12-31",
            "--evidence",
            "negative scope regression",
            "--approver",
            "李四 <li@example.com>",
            "--human",
            "--json",
        )
        self.assertTrue(waiver["ok"], waiver)
        blocked = self.run_json(
            "check",
            "--spec",
            spec_id,
            "--stage",
            "verify",
            "--json",
            expect=1,
        )
        by_id = {item["id"]: item for item in blocked["checks"]}
        self.assertEqual(by_id["G5-09"]["result"], "block")
        self.assertNotIn("waiver_id", by_id["G5-09"])

    def test_security_redline(self):
        """[AC-006-6] 安全红线检查拒绝人工豁免。"""
        spec_id = self.new_spec()
        rejected = self.run_sdd(
            "waive",
            "--spec",
            spec_id,
            "--check",
            "G5-03",
            "--scope",
            "verification",
            "--reason",
            "试图绕过测试证据",
            "--expires-at",
            "2099-12-31",
            "--evidence",
            "none",
            "--human",
            "--json",
            expect=2,
        )
        self.assertIn("安全红线", rejected.stderr + rejected.stdout)
        events = [
            json.loads(line)
            for line in (
                self.spec_dir(spec_id) / "events.jsonl"
            ).read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertEqual(events[-1]["event"], "waiver_rejected")
        state = json.loads(
            (self.spec_dir(spec_id) / "state.json").read_text(encoding="utf-8")
        )
        self.assertFalse(state.get("waivers"))

    def test_expired_waiver_blocks_again(self):
        spec_id = self.reach_docs_verifying()
        self.run_json(
            "waive",
            "--spec",
            spec_id,
            "--check",
            "G5-09",
            "--scope",
            "verification",
            "--reason",
            "短期豁免",
            "--expires-at",
            "2000-01-01",
            "--evidence",
            "expired docs-only change",
            "--human",
            "--json",
        )
        checked = self.run_json(
            "check", "--spec", spec_id, "--stage", "verify", "--json", expect=1
        )
        self.assertTrue(
            any("已过期" in error for error in checked["errors"]),
            checked["errors"],
        )
        inbox = self.run_json("inbox", "--json")
        self.assertTrue(
            any(item.get("action") == "waiver_expired" for item in inbox["items"]),
            inbox["items"],
        )


def review_verification(
    spec_id,
    findings="未发现可执行问题",
    blocking="none",
    scope="src/order.py、src/OrderService.java、web/Order.tsx；AC-001-1",
):
    return (
        VERIFY_TEXT.replace("SPEC-ORDER-001", spec_id).replace(
            "## 6. Gate 5 结论",
            "Task：T-001\n\n## 6. Gate 5 结论",
        )
        + f"""

## 7. 独立审查

| 项 | 内容 |
|---|---|
| Reviewer | 独立评审员 |
| Session | reviewer-session-1 |
| Model | review-model |
| Scope | {scope} |
| Findings | {findings} |
| Blocking issues | {blocking} |
"""
    )


class ReviewTests(EvolutionTestBase):
    def reach_g4(self, paths=None):
        paths = paths or [
            "src/order.py",
            "src/OrderService.java",
            "web/Order.tsx",
        ]
        spec_id = self.new_spec(risk="medium")
        self.write_spec(spec_id)
        self.run_sdd(
            "approve",
            "--spec",
            spec_id,
            "--human",
            "--evidence",
            "需求已确认",
        )
        self.write(
            f"docs/specs/{spec_id}/design.md",
            DESIGN_TEXT.replace("SPEC-ORDER-001", spec_id),
        )
        self.run_sdd(
            "complete", "--spec", spec_id, "--evidence", "design complete"
        )
        task_paths = "、".join(f"`{path}`" for path in paths)
        tasks = TASKS_TEXT.replace("SPEC-ORDER-001", spec_id).replace(
            "实现订单取消接口和状态校验",
            f"实现 {task_paths} 中的订单取消接口和状态校验",
        )
        self.write(f"docs/specs/{spec_id}/tasks.md", tasks)
        self.run_sdd(
            "complete", "--spec", spec_id, "--evidence", "tasks complete"
        )
        self.run_sdd(
            "complete", "--spec", spec_id, "--evidence", "implementation started"
        )
        self.write(
            "tests/test_status.py",
            """import unittest


class OrderServiceTest(unittest.TestCase):
    def testCancelPendingOrder(self):
        # [AC-001-1]
        self.assertTrue(True)
""",
        )
        self.run_sdd("start", "--spec", spec_id, "--task", "T-001")
        return spec_id

    def test_overlays_and_review_policy(self):
        """[AC-007-1] [AC-007-4] [AC-007-6] overlay 选择、无 finding 声明与边界。"""
        self.assertTrue(
            sdd_module.review_required_for({}, {"risk": "medium"})
        )
        self.assertTrue(
            sdd_module.review_required_for({}, {"risk": "high"})
        )
        self.assertFalse(
            sdd_module.review_required_for({}, {"risk": "low"})
        )
        self.assertTrue(
            sdd_module.review_required_for(
                {"review_policy": {"required_for_risk": ["low"]}},
                {"risk": "low"},
            )
        )

        java = sdd_module._review_overlay_context(
            self.root, ["src/OrderService.java"], True
        )
        self.assertEqual([item["id"] for item in java], ["common", "java-spring"])
        python = sdd_module._review_overlay_context(
            self.root, ["src/order.py"], True
        )
        self.assertEqual([item["id"] for item in python], ["common", "python"])
        frontend = sdd_module._review_overlay_context(
            self.root, ["web/Order.tsx"], True
        )
        self.assertEqual(
            [item["id"] for item in frontend],
            ["common", "frontend"],
        )
        self.assertEqual(
            sdd_module._review_overlay_context(self.root, ["src/order.py"], False),
            [],
        )

        overlay_root = self.root / "sdd" / "prompts" / "review"
        for name in ("python.md", "java-spring.md", "frontend.md"):
            text = (overlay_root / name).read_text(encoding="utf-8")
            self.assertIn("sdd/prompts/review/contract.md", text)
            self.assertIn("权威依据", text)
            for forbidden in (
                "transition",
                "--human",
                "approve",
                "merge",
                "waive",
                "状态迁移",
                "审批",
            ):
                self.assertNotIn(forbidden, text)

        profile_path = self.root / "sdd" / "workflows" / "l2-refactor.json"
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        profile["review_policy"] = {
            "required_for_risk": ["low", "critical"],
            "unknown": True,
        }
        errors = sdd_module.validate_workflow_preset(
            profile, "l2-refactor.json"
        )
        self.assertTrue(
            any("review_policy.unknown" in error for error in errors),
            errors,
        )
        self.assertTrue(
            any("critical" in error for error in errors),
            errors,
        )

    def test_review_required(self):
        """[AC-007-3] [AC-007-4] medium/high 风险强制独立 Review。"""
        spec_id = self.reach_g4()
        next_payload = self.run_json("next", "--spec", spec_id, "--json")
        overlays = {
            item["id"] for item in next_payload["context_bundle"]["review_overlays"]
        }
        self.assertEqual(
            overlays,
            {"common", "python", "java-spring", "frontend"},
        )

        missing = self.run_sdd(
            "complete",
            "--spec",
            spec_id,
            "--task",
            "T-001",
            "--evidence",
            "T-001 implemented",
            expect=2,
        )
        self.assertIn("独立审查", missing.stderr)

        self.write(
            f"docs/specs/{spec_id}/verification.md",
            review_verification(spec_id),
        )
        self.run_sdd(
            "complete",
            "--spec",
            spec_id,
            "--evidence",
            "review complete",
        )
        state = json.loads(
            (self.spec_dir(spec_id) / "state.json").read_text(encoding="utf-8")
        )
        self.assertEqual(state["state"], "VERIFYING")

        self.write(
            f"docs/specs/{spec_id}/verification.md",
            VERIFY_TEXT.replace("SPEC-ORDER-001", spec_id).replace(
                "## 6. Gate 5 结论",
                "Task：T-001\n\n## 6. Gate 5 结论",
            ),
        )
        checked = self.run_json(
            "check", "--spec", spec_id, "--stage", "verify", "--json", expect=1
        )
        self.assertTrue(
            any("独立审查" in error for error in checked["errors"]),
            checked["errors"],
        )

    def test_review_findings_and_overlays(self):
        """[AC-007-2] [AC-007-5] finding 九字段校验与三类 overlay 结构。"""
        spec_id = self.reach_g4(["src/order.py"])
        self.write(
            f"docs/specs/{spec_id}/verification.md",
            review_verification(
                spec_id,
                findings="发现 1 个问题：RV-001",
                blocking="RV-001",
                scope="src/order.py；AC-001-1",
            ),
        )
        self.write(
            f"docs/specs/{spec_id}/review-findings.json",
            json.dumps([{"id": "RV-001"}], ensure_ascii=False),
        )
        missing = self.run_sdd(
            "complete",
            "--spec",
            spec_id,
            "--task",
            "T-001",
            "--evidence",
            "review missing fields",
            expect=2,
        )
        self.assertIn("缺少字段", missing.stderr)

        finding = {
            "id": "RV-001",
            "location": "src/order.py:42",
            "evidence": "取消已支付订单仍返回成功",
            "impact": "可能造成不可逆状态错误",
            "recommendation": "在更新前增加状态条件并补充回归测试",
            "authority": "AC-001-1；现有订单状态机测试",
            "severity": "high",
            "verification": "open",
            "blocking": True,
        }
        self.write(
            f"docs/specs/{spec_id}/review-findings.json",
            json.dumps([finding], ensure_ascii=False, indent=2),
        )
        blocked = self.run_sdd(
            "complete",
            "--spec",
            spec_id,
            "--evidence",
            "review open",
            expect=2,
        )
        self.assertIn("RV-001", blocked.stderr)
        self.assertIn("未关闭阻断", blocked.stderr)

        finding["verification"] = "verified"
        self.write(
            f"docs/specs/{spec_id}/review-findings.json",
            json.dumps([finding], ensure_ascii=False, indent=2),
        )
        self.write(
            f"docs/specs/{spec_id}/verification.md",
            review_verification(
                spec_id,
                findings="发现 1 个问题：RV-001，已修复并复核",
                blocking="none",
                scope="src/order.py；AC-001-1",
            ),
        )
        self.run_sdd(
            "complete",
            "--spec",
            spec_id,
            "--evidence",
            "review verified",
        )
        state = json.loads(
            (self.spec_dir(spec_id) / "state.json").read_text(encoding="utf-8")
        )
        self.assertEqual(state["state"], "VERIFYING")


class KnowledgeTests(ContextBundleTests):
    def knowledge_index(self):
        return """# 知识索引

| ID | Type | Statement | Source | Version | Scope | Owner | Status | Links |
|---|---|---|---|---|---|---|---|---|
| SRC-001 | SRC | 当前 SDD 规格是知识引用的权威入口 | docs/specs/SPEC-EVOL-001/spec.md | 1.0.0 | docs/specs/SPEC-EVOL-001 | repo-maintainer | CONFIRMED | FEAT-001；FR-001 |
| FACT-001 | FACT | 订单状态只能由服务端更新 | docs/specs/SPEC-EVOL-001/design.md | 1.0.0 | src/order.py | repo-maintainer | CONFIRMED | FEAT-001；AC-001-1 |
| BR-001 | BR | 取消前必须校验订单状态与归属 | docs/specs/SPEC-EVOL-001/spec.md#BR-001 | 1.0.0 | src/order.py | product-owner | CONFIRMED | FEAT-001；AC-001-1 |
| CONFLICT-001 | CONFLICT | 两版规则对取消时限存在冲突 | docs/knowledge/conflicts/CONFLICT-001.md | 1.0.0 | src/order.py | product-owner | RESOLVED | FEAT-001；FR-001 |
| GAP-001 | GAP | 缺少跨服务超时规则 | N/A | N/A | src/order.py | product-owner | OPEN | FEAT-001；AC-001-1 |
"""

    def fix_pattern(self):
        return """---
id: FP-001
symptom: 人工 G4 在缺少 Review 时仍等待审批
root_cause: G4 人工分支早于 Review 校验返回
trigger: 最后任务完成且没有独立审查
fix: 先校验 Review 和任务证据，再等待人工确认
checks: CHK-001
check_command: python -m unittest tests.test_sdd.SddFlowTest.test_manual_g4_blocks_without_review -v
scope: sdd/scripts/sdd.py
owner: repo-maintainer
status: verified
---

# FP-001 人工 G4 不得绕过 Review

## 症状

最后任务完成后直接进入等待人工审批，未校验独立审查证据。

## 根因

人工 G4 分支在 Review 校验之前返回。

## 预防检查

CHK-001：运行人工 G4 缺 Review 回归测试，必须被阻断。
"""

    def test_knowledge_index_and_pattern(self):
        """[AC-008-1] [AC-008-2] [AC-008-3] [AC-008-5] [AC-009-3] 知识记录与 Pattern 闭环。"""
        spec_id = self.implementation_spec()
        tasks_path = f"docs/specs/{spec_id}/tasks.md"
        tasks = (self.root / tasks_path).read_text(encoding="utf-8")
        self.write(
            tasks_path,
            tasks.replace(
                "实现 `src/order.py` 并补 `tests/test_order.py`",
                "实现 `sdd/scripts/sdd.py` 并补 `tests/test_status.py`",
            ),
        )
        self.write("docs/knowledge/index.md", self.knowledge_index())
        self.write("docs/knowledge/patterns/FP-001.md", self.fix_pattern())
        checked = self.run_json(
            "check", "--spec", spec_id, "--stage", "tasks", "--json"
        )
        self.assertTrue(checked["ok"], checked)
        by_id = {item["id"]: item for item in checked["checks"]}
        self.assertEqual(by_id["G3-05"]["result"], "pass")
        self.assertEqual(by_id["G3-06"]["result"], "pass")

        bundle = self.next_payload(spec_id)["context_bundle"]
        self.assertTrue(
            {"BR-001", "FACT-001", "GAP-001"}
            <= {item["id"] for item in bundle["knowledge"]}
        )
        pattern = next(
            item for item in bundle["fix_patterns"] if item["id"] == "FP-001"
        )
        self.assertEqual(pattern["checks"], ["CHK-001"])
        self.assertIn("test_manual_g4_blocks_without_review", pattern["check_command"])
        self.assertFalse(pattern["reference_only"])

        bad = self.knowledge_index().replace(
            "| GAP-001 | GAP | 缺少跨服务超时规则 | N/A | N/A | src/order.py | product-owner | OPEN | FEAT-001；AC-001-1 |",
            "| BR-002 | BR | 未确认规则 | N/A | N/A | src/order.py | product-owner | CONFIRMED | FEAT-001；AC-001-1 |",
        )
        self.write("docs/knowledge/index.md", bad)
        invalid = self.run_json(
            "check", "--spec", spec_id, "--stage", "tasks", "--json", expect=1
        )
        self.assertTrue(
            any("没有权威来源" in error for error in invalid["errors"]),
            invalid["errors"],
        )

    def test_conflict_blocks(self):
        """[AC-008-4] 未解决冲突阻断相关任务。"""
        spec_id = self.implementation_spec()
        self.write(
            "docs/knowledge/index.md",
            self.knowledge_index().replace(
                "| CONFLICT-001 | CONFLICT | 两版规则对取消时限存在冲突 | docs/knowledge/conflicts/CONFLICT-001.md | 1.0.0 | src/order.py | product-owner | RESOLVED | FEAT-001；FR-001 |",
                "| CONFLICT-001 | CONFLICT | 两版规则对取消时限存在冲突 | docs/knowledge/conflicts/CONFLICT-001.md | 1.0.0 | src/order.py | product-owner | OPEN | FEAT-001；FR-001 |",
            ),
        )
        bundle = self.next_payload(spec_id)["context_bundle"]
        self.assertTrue(bundle["blocked"])
        self.assertIn(
            "CONFLICT-001",
            [item["id"] for item in bundle["knowledge"]],
        )


class MetricsTests(EvidenceTests):
    def test_metrics_and_audit(self):
        """[AC-006-7] [AC-009-5] [AC-010-2] 指标、审计回放与迁移事件。"""
        spec_id = self.implementation_spec()
        events_payload = self.run_json(
            "events", "--spec", spec_id, "--json"
        )
        self.assertTrue(events_payload["audit"]["valid"], events_payload["audit"])
        design_transition = next(
            event
            for event in events_payload["events"]
            if event.get("event") == "state_transition"
            and event.get("to_state") == "DESIGN_READY"
        )
        self.assertEqual(design_transition["from_state"], "SPEC_READY")
        self.assertEqual(design_transition["actor"], "agent")
        self.assertEqual(design_transition["evidence"], "design complete")
        self.assertTrue(design_transition["artifacts"])
        self.assertEqual(design_transition["next"], "write_tasks")

        self.write(
            "docs/knowledge/bar/BAR-001.md",
            """---
id: BAR-001
status: verified
escaped: true
source: production
---

# BAR-001 测试证据缺失

## 根因

验证阶段未执行可复验测试。
""",
        )
        metrics = self.run_json("metrics", "--json")
        self.assertTrue(metrics["ok"], metrics)
        self.assertEqual(metrics["audit"]["valid"], True)
        quality = metrics["quality"]
        for key in (
            "waiver_rate",
            "escaped_defects",
            "escaped_defect_rate",
            "reopened_specs",
            "reopen_rate",
            "gate_first_pass_rate",
            "definitions",
            "sources",
        ):
            self.assertIn(key, quality)
        self.assertEqual(quality["escaped_defects"], 1)
        self.assertEqual(quality["escaped_defect_rate"], 1.0)
        self.assertIn("BAR front matter", quality["definitions"]["escaped_defects"])
        self.assertIn("events.jsonl", quality["sources"]["events"])

        check_stats = {item["id"]: item for item in metrics["check_stats"]}
        self.assertIn("G0-01", check_stats)
        self.assertGreater(check_stats["G0-01"]["total"], 0)
        for key in ("pass", "warn", "block", "waived", "pass_rate", "waiver_rate"):
            self.assertIn(key, check_stats["G0-01"])

        event_path = self.spec_dir(spec_id) / "events.jsonl"
        lines = [
            json.loads(line)
            for line in event_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        lines[-1]["evidence"] = "tampered"
        event_path.write_text(
            "\n".join(json.dumps(item, ensure_ascii=False) for item in lines)
            + "\n",
            encoding="utf-8",
        )
        tampered = self.run_json("events", "--spec", spec_id, "--json")
        self.assertFalse(tampered["audit"]["valid"])
        self.assertTrue(tampered["audit"]["errors"])
        broken_metrics = self.run_json("metrics", "--json")
        self.assertFalse(broken_metrics["audit"]["valid"])
        blocked = self.run_json(
            "check", "--spec", spec_id, "--stage", "verify", "--json", expect=1
        )
        self.assertTrue(
            any("审计事件链无效" in error for error in blocked["errors"]),
            blocked["errors"],
        )


class DocsReleaseTests(unittest.TestCase):
    def read(self, relative):
        return (KIT_ROOT / relative).read_text(encoding="utf-8")

    def test_standard_and_core_advantage_docs(self):
        text = self.read("docs/STANDARD-CONFORMANCE.md")
        required = (
            "## 2. P0–P5 官方阶段映射",
            "## 3. G0–G5 官方门禁映射",
            "## 4. 三项核心优势基线",
            "## 5. 可复核证据索引",
            "## 6. 已知缺口与非目标",
        )
        for heading in required:
            self.assertIn(heading, text)

        statuses = {"已自动", "已人工", "部分实现", "未实现"}
        stages = {
            "P0 Requirement 需求分析",
            "P1 Specify 规格定义",
            "P2 Plan 方案制定",
            "P3 Decompose 任务拆解",
            "P4 Implement 代码实现",
            "P5 Validate 规格验证",
            "G0 需求侧准入",
            "G1 Spec 准入",
            "G2 设计评审",
            "G3 任务拆解",
            "G4 代码审查",
            "G5 规格验证",
        }
        seen = set()
        for line in text.splitlines():
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if len(cells) >= 3 and cells[0] in stages:
                seen.add(cells[0])
                self.assertIn(cells[2], statuses, line)
        self.assertEqual(seen, stages)

        for advantage in ("轻量、使用简单", "可轻松自定义", "合规可溯源"):
            self.assertIn(advantage, text)
        for target in (
            "核心第三方依赖数",
            "核心常驻服务/数据库",
            "每仓库 bootstrap 次数",
            "新增工作流所需核心代码改动",
            "新事件哈希链",
            "质量回流指标",
        ):
            self.assertIn(target, text)
        self.assertIn("Tests.test_metrics_and_audit", text)
        self.assertIn("docs/STANDARD-CONFORMANCE.md", self.read("README.md"))

    def test_agent_loop_and_version(self):
        """[AC-010-4] [AC-010-5] [AC-010-6] 版本、manifest、全量验收与单动作协议。"""
        version = self.read("sdd/VERSION").strip()
        init_text = self.read("sdd/__init__.py")
        state_text = self.read("sdd/scripts/sdd.py")
        manifest = json.loads(self.read("sdd/manifest.json"))
        self.assertIn(f'__version__ = "{version}"', init_text)
        self.assertIn(f'VERSION = "{version}"', state_text)
        self.assertEqual(manifest["version"], version)
        self.assertIn(version, self.read("README.md"))
        self.assertIn(version, self.read("docs/GUIDE.md"))

        workflow_dir = KIT_ROOT / "sdd" / "workflows"
        workflows = {
            path.stem for path in workflow_dir.glob("*.json")
        }
        self.assertEqual(
            workflows,
            {"l2-standard", "l2-hotfix", "l2-strict", "l2-refactor"},
        )
        refactor = json.loads(
            (workflow_dir / "l2-refactor.json").read_text(encoding="utf-8")
        )
        self.assertEqual(refactor["schema"], 2)

        agent_contract = self.read("sdd/agent-contract.md")
        agent_block = self.read("sdd/agent-block.md")
        combined = agent_contract + "\n" + agent_block
        for needle in (
            "context_bundle",
            "两个",
            "l2-refactor",
            "events.jsonl",
            "verification-evidence.jsonl",
        ):
            self.assertIn(needle, combined)
        self.assertIn("每个阶段只暴露一个动作和一个提交命令", agent_contract)
        self.assertIn("每个阶段只执行一个动作、用一个提交命令", agent_block)
        self.assertIn("waive", combined)

        prompt = self.read("sdd/prompts/task.md") + self.read("sdd/prompts/verify.md")
        self.assertIn("next.context_bundle", prompt)
        self.assertIn("verification-evidence.jsonl", prompt)
        self.assertIn("python -m sdd submit-task", prompt)

