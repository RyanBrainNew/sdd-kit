import json
import subprocess
import sys
import unittest

try:
    from tests.test_sdd import SPEC_ID, SPEC_TEXT, SddFlowBase
except ImportError:  # pragma: no cover - unittest discover imports top-level modules
    from test_sdd import SPEC_ID, SPEC_TEXT, SddFlowBase

from sdd.core import Workspace
from sdd.scripts import sdd as engine


class GovernanceFlowBase(SddFlowBase):
    def init_git(self):
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        subprocess.run(
            ["git", "config", "user.email", "agent@example.invalid"],
            cwd=self.root,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "SDD Agent"],
            cwd=self.root,
            check=True,
        )

    def git_add(self, *paths):
        subprocess.run(
            ["git", "add", *paths], cwd=self.root, check=True
        )

    def json_command(self, *args, expect=0):
        result = self.run_sdd(*args, expect=expect)
        return json.loads(result.stdout)

    def prepared_tasks_state(self):
        self.new_spec()
        self.approve_valid_spec()
        self.complete_design()
        self.complete_tasks()

    def change_set_text(self):
        return (self.root / "docs/specs" / SPEC_ID / "change-set.md").read_text(
            encoding="utf-8"
        )


class ApprovalBindingTests(GovernanceFlowBase):
    def setUp(self):
        super().setUp()
        self.new_spec()
        self.approve_valid_spec()
        self.complete_design()

    def test_approve_records_digest_and_gate_report(self):
        """[AC-001-1] approve 写入审批摘要，并同步到 G0/G1 报告。"""
        state = self.state()
        digest = state.get("approved_spec_digest")
        self.assertTrue(digest)
        self.assertEqual(digest, state["approvals"][-1]["sha256"])
        self.assertEqual(state.get("approved_by"), state.get("last_approver"))
        self.assertEqual(state.get("approval_evidence"), "需求已确认")
        self.assertTrue(state.get("approved_at"))
        report = (
            self.root / "sdd/reports/SPEC-ORDER-001/gate1-report.md"
        ).read_text(encoding="utf-8")
        self.assertIn("审批 Spec 摘要", report)
        self.assertIn(digest, report)

    def test_spec_change_blocks_until_reapprove(self):
        """[AC-001-2] [AC-001-3] 审批后修改 Spec 触发 G1-08，reapprove 后恢复。"""
        path = self.root / "docs/specs/SPEC-ORDER-001/spec.md"
        original = path.read_text(encoding="utf-8")
        path.write_text(
            original.replace("返回成功", "返回成功并记录审计"),
            encoding="utf-8",
        )
        blocked = self.json_command(
            "check", "--spec", SPEC_ID, "--stage", "design", "--json", expect=1
        )
        joined = "\n".join(blocked.get("errors", []))
        self.assertIn("G1-08", joined)
        self.assertIn("reapprove", joined)
        self.assertEqual(self.state()["state"], "DESIGN_READY")

        self.run_sdd(
            "reapprove",
            "--spec",
            SPEC_ID,
            "--human",
            "--reason",
            "AC 文案调整",
            "--evidence",
            "需求重新确认",
            "--json",
        )
        passed = self.json_command(
            "check", "--spec", SPEC_ID, "--stage", "design", "--json"
        )
        self.assertFalse(
            any("G1-08" in error for error in passed.get("errors", []))
        )
        self.assertEqual(
            self.state()["approval_evidence"], "需求重新确认"
        )

    def test_reapprove_requires_human_and_reason(self):
        """[AC-001-4] reapprove 缺 human 或理由为空时拒绝。"""
        before = self.state()["approved_spec_digest"]
        self.run_sdd(
            "reapprove",
            "--spec",
            SPEC_ID,
            "--reason",
            "调整",
            "--evidence",
            "证据",
            expect=2,
        )
        self.run_sdd(
            "reapprove",
            "--spec",
            SPEC_ID,
            "--human",
            "--reason",
            "",
            "--evidence",
            "证据",
            expect=2,
        )
        self.assertEqual(self.state()["approved_spec_digest"], before)

    def test_legacy_active_spec_without_digest_blocks(self):
        """[AC-001-4] 活跃 Spec 缺审批摘要时给出迁移命令。"""
        state_path = self.root / "docs/specs/SPEC-ORDER-001/state.json"
        state = self.state()
        state.pop("approved_spec_digest", None)
        state.pop("approved_at", None)
        state.pop("approved_by", None)
        state.pop("approval_evidence", None)
        state_path.write_text(
            json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        blocked = self.json_command(
            "check", "--spec", SPEC_ID, "--stage", "design", "--json", expect=1
        )
        joined = "\n".join(blocked.get("errors", []))
        self.assertIn("G1-08", joined)
        self.assertIn("legacy-migration", joined)
        self.assertIn(SPEC_ID, joined)


class ImpactTests(GovernanceFlowBase):
    def setUp(self):
        super().setUp()
        self.prepared_tasks_state()

    def test_impact_lists_links_and_paths(self):
        """[AC-002-1] impact 输出 FEAT/FR/AC/Task/测试/路径。"""
        payload = self.json_command(
            "impact", "--spec", SPEC_ID, "--json"
        )
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["kind"], "impact")
        self.assertEqual(payload["feat_ids"], ["FEAT-001"])
        self.assertEqual(payload["fr_ids"], ["FR-001"])
        self.assertEqual(payload["ac_ids"], ["AC-001-1"])
        self.assertEqual(payload["task_ids"], ["T-001"])
        self.assertTrue(
            any(
                "StatusTest#test_cancel_pending_order" in item
                for item in payload["test_selectors"]
            )
        )
        self.assertIsInstance(payload["code_paths"], list)
        self.assertFalse(payload["approval_required"])

    def test_impact_reports_missing_links(self):
        """[AC-002-2] change-set 引用不存在 AC 时 impact 输出 missing。"""
        self.write(
            "docs/specs/SPEC-ORDER-001/change-set.md",
            "# 变更集（Change Set）\n\n"
            "## CHG-001\n"
            "- Status: pending\n"
            "- Impact-AC: AC-999-1\n",
        )
        payload = self.json_command(
            "impact", "--spec", SPEC_ID, "--json"
        )
        self.assertIn("AC-999-1", payload["missing"])
        self.assertTrue(payload["approval_required"])

    def test_approval_required_combinations(self):
        """[AC-002-3] pending change-set 或摘要变化时要求审批。"""
        self.run_sdd(
            "change",
            "--spec",
            SPEC_ID,
            "--reason",
            "调整审批判定",
        )
        pending = self.json_command(
            "impact", "--spec", SPEC_ID, "--json"
        )
        self.assertTrue(pending["approval_required"])
        self.assertEqual(pending["pending_change_ids"], ["CHG-001"])

        self.run_sdd(
            "reapprove",
            "--spec",
            SPEC_ID,
            "--human",
            "--reason",
            "调整审批判定",
            "--evidence",
            "需求重新确认",
        )
        clean = self.json_command(
            "impact", "--spec", SPEC_ID, "--json"
        )
        self.assertFalse(clean["approval_required"])


class ChangeSetTests(GovernanceFlowBase):
    def setUp(self):
        super().setUp()
        self.prepared_tasks_state()

    def test_change_writes_required_fields(self):
        """[AC-003-1] change 生成完整 change-set 记录。"""
        payload = self.json_command(
            "change",
            "--spec",
            SPEC_ID,
            "--reason",
            "AC 语义调整",
            "--json",
        )
        self.assertEqual(payload["change_id"], "CHG-001")
        self.assertEqual(payload["status"], "pending")
        text = self.change_set_text()
        for expected in (
            "## CHG-001",
            "- Status: pending",
            "- Reason: AC 语义调整",
            "- Impact-FEAT: FEAT-001",
            "- Impact-FR: FR-001",
            "- Impact-AC: AC-001-1",
            "- Impact-Task: T-001",
            "- Impact-Tests:",
            "- Risk: low",
            "- Rollback:",
            "- Approval: pending",
        ):
            self.assertIn(expected, text)

    def test_reapprove_marks_change_approved(self):
        """[AC-003-2] reapprove 将 pending change-set 标记为 approved。"""
        self.run_sdd(
            "change", "--spec", SPEC_ID, "--reason", "AC 语义调整"
        )
        payload = self.json_command(
            "reapprove",
            "--spec",
            SPEC_ID,
            "--human",
            "--reason",
            "AC 语义调整",
            "--evidence",
            "需求重新确认",
            "--json",
        )
        self.assertEqual(payload["approved_change_ids"], ["CHG-001"])
        text = self.change_set_text()
        self.assertIn("- Status: approved", text)
        self.assertIn("- Approval: approved", text)
        self.assertIn(
            "- Approved-Spec-Digest: " + self.state()["approved_spec_digest"],
            text,
        )
        actions = [item.get("action") for item in self.state()["approvals"]]
        self.assertIn("reapprove_spec", actions)

    def test_docs_only_change_is_explicit_exemption(self):
        """[AC-003-4] docs-only 显式豁免且不要求 reapprove。"""
        payload = self.json_command(
            "change",
            "--spec",
            SPEC_ID,
            "--reason",
            "只更新文档",
            "--docs-only",
            "--json",
        )
        self.assertEqual(payload["status"], "docs-only")
        text = self.change_set_text()
        self.assertIn("- Status: docs-only", text)
        self.assertIn("- Approval: exempt", text)
        impact = self.json_command(
            "impact", "--spec", SPEC_ID, "--json"
        )
        self.assertFalse(impact["approval_required"])

    def test_invalid_change_reference_fails(self):
        """[AC-003-5] change-set 引用不存在 AC 时失败且不落盘。"""
        tasks_path = self.root / "docs/specs/SPEC-ORDER-001/tasks.md"
        tasks_path.write_text(
            tasks_path.read_text(encoding="utf-8").replace(
                "AC-001-1", "AC-999-1"
            ),
            encoding="utf-8",
        )
        failed = self.run_sdd(
            "change",
            "--spec",
            SPEC_ID,
            "--reason",
            "非法引用",
            "--json",
            expect=2,
        )
        self.assertIn("AC-999-1", failed.stdout + failed.stderr)
        self.assertFalse(
            (self.root / "docs/specs/SPEC-ORDER-001/change-set.md").exists()
        )


class ChangeEnforcementTests(GovernanceFlowBase):
    def setUp(self):
        super().setUp()
        self.prepared_tasks_state()
        self.run_sdd("complete", "--spec", SPEC_ID, "--evidence", "开始实现")
        self.init_git()

    def test_pending_change_blocks_code_commit(self):
        """[AC-003-3] pending change-set 阻断暂存代码的 pre-commit。"""
        self.run_sdd(
            "change", "--spec", SPEC_ID, "--reason", "范围调整"
        )
        self.write("src/app.py", "print('change')\n")
        self.git_add("src/app.py")
        blocked = self.run_sdd("hook", "pre-commit", expect=1)
        output = blocked.stdout + blocked.stderr
        self.assertIn("G1-09", output)
        self.assertIn("reapprove", output)

        self.run_sdd(
            "reapprove",
            "--spec",
            SPEC_ID,
            "--human",
            "--reason",
            "范围调整",
            "--evidence",
            "需求重新确认",
        )
        self.run_sdd("hook", "pre-commit", expect=0)

    def test_docs_only_allows_docs_but_blocks_code(self):
        """[AC-003-4] docs-only 放行文档提交但阻断代码提交。"""
        self.run_sdd(
            "change",
            "--spec",
            SPEC_ID,
            "--reason",
            "只更新文档",
            "--docs-only",
        )
        self.write("README.md", "# changed\n")
        self.git_add("README.md")
        self.run_sdd("hook", "pre-commit", expect=0)

        self.write("src/app.py", "print('change')\n")
        self.git_add("src/app.py")
        blocked = self.run_sdd("hook", "pre-commit", expect=1)
        self.assertIn("docs-only", blocked.stdout + blocked.stderr)

    def test_ci_blocks_pending_change(self):
        """[AC-003-3] 普通 stage 检查同样报告 G1-09。"""
        self.run_sdd(
            "change", "--spec", SPEC_ID, "--reason", "范围调整"
        )
        blocked = self.json_command(
            "check", "--spec", SPEC_ID, "--stage", "tasks", "--json", expect=1
        )
        self.assertIn(
            "G1-09",
            "\n".join(blocked.get("errors", [])),
        )


class GovernanceBoundaryTests(GovernanceFlowBase):
    def setUp(self):
        super().setUp()
        self.new_spec()
        self.approve_valid_spec()

    def test_reapprove_is_cli_only_human_action(self):
        """[AC-004-1] reapprove 只允许 CLI 人工动作。"""
        rejected = self.run_sdd(
            "reapprove",
            "--spec",
            SPEC_ID,
            "--reason",
            "调整",
            "--evidence",
            "证据",
            expect=2,
        )
        self.assertIn("--human", rejected.stderr)
        workspace = Workspace(self.root, session_key="boundary-test")
        with self.assertRaises(ValueError):
            workspace.reapprove(
                SPEC_ID,
                "调整",
                "证据",
                human=False,
            )

    def test_merged_legacy_spec_is_compatible(self):
        """[AC-004-2] MERGED 历史 Spec 缺摘要时不阻断。"""
        state = self.state()
        state["state"] = "MERGED"
        state.pop("approved_spec_digest", None)
        errors = engine.approval_digest_errors(
            self.root,
            self.root / "docs/specs" / SPEC_ID,
            state,
        )
        self.assertEqual(errors, [])

    def test_release_metadata_matches_package_version(self):
        """[AC-004-3] 发布版本文件与核心版本常量一致。"""
        version = (self.root / "sdd" / "VERSION").read_text(
            encoding="utf-8"
        ).strip()
        init_text = (self.root / "sdd" / "__init__.py").read_text(
            encoding="utf-8"
        )
        engine_text = (self.root / "sdd" / "scripts" / "sdd.py").read_text(
            encoding="utf-8"
        )
        self.assertIn(f'__version__ = "{version}"', init_text)
        self.assertIn(f'VERSION = "{version}"', engine_text)
        self.assertRegex(version, r"^\d+\.\d+\.\d+$")


class FeatMapSyncTests(unittest.TestCase):
    def test_separator_rows_are_not_treated_as_data(self):
        """[AC-004-2] FEAT 映射重复同步不能累积分隔行。"""
        text = (
            "## FEAT 映射\n\n"
            "| FEAT | 工作项 ID | Spec ID | FR | AC |\n"
            "| --- | --- | --- | --- | --- |\n"
            "| --- | --- | --- | --- | --- |\n"
            "| FEAT-001 | WORK-1 | SPEC-REQ-001 | FR-001 | AC-001-1 |\n"
        )
        rows = engine.parse_feat_map(text)
        self.assertEqual(len(rows), 1)
        rendered = engine.render_feat_map(rows)
        self.assertEqual(rendered.count("| --- | --- | --- | --- | --- |"), 1)

