import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from sdd.mcp.registry import Registry, RegistryError
from sdd.mcp.service import SddService

try:
    from test_sdd import DESIGN_TEXT, SPEC_TEXT, TASKS_TEXT, VERIFY_TEXT
except ImportError:  # pragma: no cover - direct file execution fallback
    try:
        from tests.test_sdd import DESIGN_TEXT, SPEC_TEXT, TASKS_TEXT, VERIFY_TEXT
    except ImportError:
        DESIGN_TEXT = SPEC_TEXT = TASKS_TEXT = VERIFY_TEXT = ""


KIT_ROOT = Path(__file__).resolve().parents[1]


class SddMcpServiceTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        shutil.copytree(KIT_ROOT / "sdd", self.root / "sdd")
        (self.root / "docs").mkdir()
        (self.root / "tests").mkdir()
        self.registry_path = self.root / "sdd-mcp.json"
        self.registry_path.write_text(
            json.dumps(
                {
                    "workspace_root": str(self.root),
                    "projects": {
                        "demo": {
                            "path": ".",
                            "description": "test project",
                        }
                    },
                }
            ),
            encoding="utf-8",
        )
        self.service = SddService(Registry.load(self.registry_path))

    def tearDown(self):
        self.temp.cleanup()

    def run_sdd(self, *args):
        return subprocess.run(
            [
                sys.executable,
                str(self.root / "sdd" / "scripts" / "sdd.py"),
                "--root",
                str(self.root),
                *args,
            ],
            cwd=self.root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

    def approve(self, spec):
        result = self.run_sdd(
            "approve",
            "--spec",
            spec,
            "--human",
            "--evidence",
            "需求已确认",
        )
        self.assertEqual(
            result.returncode,
            0,
            msg=f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )

    def test_project_discovery_and_health(self):
        projects = self.service.list_projects()
        self.assertEqual(projects[0]["id"], "demo")
        self.assertTrue(projects[0]["valid"])
        health = self.service.health()
        self.assertTrue(health["ok"])
        self.assertEqual(health["projects"], 1)

    def test_create_status_next_and_read(self):
        created = self.service.create_spec(
            "demo",
            title="订单取消",
            spec_id="SPEC-ORDER-001",
            work_item="srdcloud-553377",
        )
        self.assertEqual(created["spec_id"], "SPEC-ORDER-001")
        status = self.service.status("demo", "SPEC-ORDER-001")
        self.assertEqual(status["state"]["state"], "DRAFT")
        action = self.service.next("demo", "SPEC-ORDER-001")
        self.assertEqual(action["action"], "write_spec")
        spec_text = self.service.read_artifact("demo", "SPEC-ORDER-001", "spec.md")
        self.assertIn("SPEC-ORDER-001", spec_text)

    def test_create_spec_with_workflow_preset(self):
        created = self.service.create_spec(
            "demo",
            title="订单取消",
            spec_id="SPEC-ORDER-001",
            work_item="srdcloud-553377",
            workflow="l2-strict",
        )
        self.assertEqual(created["spec_id"], "SPEC-ORDER-001")
        status = self.service.status("demo", "SPEC-ORDER-001")
        self.assertEqual(
            status["state"]["workflow"]["name"],
            "l2-strict",
        )
        self.assertTrue(
            (
                self.root
                / "docs/specs/SPEC-ORDER-001/workflow.json"
            ).is_file()
        )

    def test_board_returns_spec_and_task_lanes(self):
        self.service.create_spec(
            "demo",
            title="订单取消",
            spec_id="SPEC-ORDER-001",
            work_item="srdcloud-553377",
        )
        board = self.service.board("demo")
        self.assertTrue(board["ok"])
        self.assertEqual(board["kind"], "board")
        self.assertEqual(board["specs"][0]["spec"], "SPEC-ORDER-001")
        self.assertEqual(board["specs"][0]["task_counts"]["total"], 1)
        self.assertEqual(board["specs"][0]["tasks"][0]["status"], "Todo")

    def test_events_and_board_mark_current_session(self):
        self.service.create_spec(
            "demo",
            title="订单取消",
            spec_id="SPEC-ORDER-001",
            work_item="srdcloud-553377",
        )
        self.service.session("demo", "SPEC-ORDER-001")
        events = self.service.events("demo", "SPEC-ORDER-001")
        self.assertEqual(events["kind"], "events")
        self.assertEqual(events["events"][0]["event"], "spec_created")
        board = self.service.board("demo")
        self.assertEqual(board["current_spec"], "SPEC-ORDER-001")
        self.assertTrue(board["specs"][0]["current"])
        self.assertEqual(board["specs"][0]["events_count"], events["count"])

    def test_check_returns_structured_errors(self):
        self.service.create_spec(
            "demo",
            title="订单取消",
            spec_id="SPEC-ORDER-001",
            work_item="srdcloud-553377",
        )
        result = self.service.check("demo", "SPEC-ORDER-001", "spec")
        self.assertFalse(result["ok"])
        self.assertEqual(result["stage"], "spec")
        self.assertTrue(result["errors"])

    def test_context_reads_service_cards(self):
        self.service.create_spec(
            "demo",
            title="订单取消",
            spec_id="SPEC-ORDER-001",
            work_item="srdcloud-553377",
        )
        context_file = self.root / "sdd" / "context" / "services" / "order-api.md"
        context_file.parent.mkdir(parents=True, exist_ok=True)
        context_file.write_text("# order-api\n\nOwner: team-order\n", encoding="utf-8")
        context = self.service.context("demo", "SPEC-ORDER-001")
        paths = {item["path"] for item in context["files"]}
        self.assertIn("sdd/context/services/order-api.md", paths)

    def test_unknown_project_is_rejected(self):
        with self.assertRaises(RegistryError):
            self.service.resolve("missing")

    def test_single_project_registry_uses_local_mode(self):
        registry = Registry.single(self.root)
        self.assertEqual(registry.mode, "local")
        self.assertEqual(list(registry.projects), ["demo"])
        health = SddService(registry).health()
        self.assertEqual(health["mode"], "local")
        self.assertEqual(health["projects"], 1)

    def test_single_project_registry_rejects_non_sdd_repo(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(RegistryError):
                Registry.single(temp)

    def test_reserve_spec_id_is_monotonic(self):
        first = self.service.reserve_spec_id("demo", "ORDER")
        second = self.service.reserve_spec_id("demo", "order")
        self.assertEqual(first["spec_id"], "SPEC-ORDER-001")
        self.assertEqual(second["spec_id"], "SPEC-ORDER-002")

    def test_reserve_spec_id_sees_existing_directories(self):
        existing = self.root / "docs" / "specs" / "SPEC-ORDER-005"
        existing.mkdir(parents=True)
        reserved = self.service.reserve_spec_id("demo", "ORDER")
        self.assertEqual(reserved["spec_id"], "SPEC-ORDER-006")

    def test_session_guides_create_then_returns_state(self):
        empty = self.service.session("demo")
        self.assertEqual(empty["action"], "create_spec")
        self.assertEqual(empty["start_with"], "sdd_start_work")
        self.service.create_spec(
            "demo",
            title="订单取消",
            spec_id="SPEC-ORDER-010",
            work_item="srdcloud-553380",
        )
        session = self.service.session("demo")
        self.assertEqual(session["spec"], "SPEC-ORDER-010")
        self.assertEqual(session["state"], "DRAFT")
        self.assertEqual(session["next"]["action"], "write_spec")
        self.assertEqual(len(session["specs"]), 1)

    def test_session_requires_selection_with_multiple_specs(self):
        for number in (11, 12):
            self.service.create_spec(
                "demo",
                title=f"需求 {number}",
                spec_id=f"SPEC-ORDER-{number:03d}",
                work_item=f"srdcloud-5533{number}",
            )
        session = self.service.session("demo")
        self.assertEqual(session["action"], "select_spec")
        self.assertEqual(len(session["specs"]), 2)
        selected = self.service.session("demo", "SPEC-ORDER-011")
        self.assertEqual(selected["spec"], "SPEC-ORDER-011")
        self.assertEqual(selected["next"]["action"], "write_spec")

    def test_start_work_returns_autopilot_order_and_can_resume(self):
        result = self.service.start_work(
            "demo",
            "srdcloud-553377",
            issue_url="https://example.invalid/item/553377",
            title="订单取消",
            description="支持用户取消未支付订单。",
            domain="ORDER",
        )
        spec = result["spec_id"]
        self.assertFalse(result["resumed"])
        self.assertEqual(result["work_order"]["next"]["action"], "write_spec")
        self.assertEqual(
            result["work_order"]["next"]["submit_with"], "sdd_submit_artifact"
        )
        self.assertTrue(result["human_checkpoint"]["required"])
        self.assertEqual(result["human_checkpoint"]["type"], "spec_approval")
        spec_dir = self.root / "docs" / "specs" / spec
        self.assertTrue((spec_dir / "context.md").is_file())
        self.assertIn("取消", (spec_dir / "context.md").read_text(encoding="utf-8"))

        resumed = self.service.start_work("demo", "srdcloud-553377")
        self.assertTrue(resumed["resumed"])
        self.assertEqual(resumed["spec_id"], spec)

    def test_submit_artifact_enforces_current_stage_and_human_approval(self):
        result = self.service.start_work(
            "demo",
            "srdcloud-553377",
            title="订单取消",
            domain="ORDER",
        )
        spec = result["spec_id"]
        wrong = self.service.submit_artifact(
            "demo", spec, "design.md", DESIGN_TEXT.replace("SPEC-ORDER-001", spec)
        )
        self.assertFalse(wrong["ok"])
        self.assertEqual(wrong["next"]["action"], "write_spec")

        submitted = self.service.submit_artifact(
            "demo", spec, "spec.md", SPEC_TEXT.replace("SPEC-ORDER-001", spec)
        )
        self.assertTrue(submitted["ok"])
        self.assertTrue(submitted["awaiting_human_approval"])
        self.assertEqual(submitted["next"]["action"], "write_spec")

        self.approve(spec)
        design = self.service.submit_artifact(
            "demo", spec, "design.md", DESIGN_TEXT.replace("SPEC-ORDER-001", spec)
        )
        self.assertTrue(design["ok"])
        self.assertEqual(design["next"]["action"], "write_tasks")
        self.assertEqual(design["next"]["state"], "DESIGN_READY")

    def test_inbox_lists_human_actions_without_writing(self):
        result = self.service.start_work(
            "demo",
            "srdcloud-553377",
            title="订单取消",
            domain="ORDER",
        )
        spec = result["spec_id"]
        state_path = self.root / "docs" / "specs" / spec / "state.json"
        before = state_path.read_text(encoding="utf-8")
        inbox = self.service.inbox("demo")
        self.assertTrue(inbox["ok"])
        self.assertEqual(inbox["kind"], "inbox")
        self.assertEqual(inbox["items"][0]["action"], "approve_spec")
        self.assertEqual(before, state_path.read_text(encoding="utf-8"))

    def test_tasks_and_task_submissions_auto_advance(self):
        result = self.service.start_work(
            "demo",
            "srdcloud-553377",
            title="订单取消",
            domain="ORDER",
        )
        spec = result["spec_id"]
        self.service.submit_artifact(
            "demo", spec, "spec.md", SPEC_TEXT.replace("SPEC-ORDER-001", spec)
        )
        self.approve(spec)
        self.service.submit_artifact(
            "demo", spec, "design.md", DESIGN_TEXT.replace("SPEC-ORDER-001", spec)
        )
        tasks = self.service.submit_artifact(
            "demo", spec, "tasks.md", TASKS_TEXT.replace("SPEC-ORDER-001", spec)
        )
        self.assertTrue(tasks["ok"])
        self.assertEqual(tasks["next"]["action"], "implement_task")
        self.assertEqual(tasks["next"]["state"], "IMPLEMENTING")

        test_file = self.root / "tests" / "test_status.py"
        test_file.write_text(
            "import unittest\n\n"
            "class StatusTest(unittest.TestCase):\n"
            "    def test_cancel_pending_order(self):\n"
            "        # [AC-001-1]\n"
            "        self.assertTrue(True)\n",
            encoding="utf-8",
        )
        task = self.service.submit_task(
            "demo",
            spec,
            "T-001",
            "python -m unittest tests.test_status: 1 passed",
            "abc1234",
        )
        self.assertTrue(task["ok"])
        self.assertEqual(task["next"]["action"], "run_verification")
        self.assertEqual(task["next"]["state"], "VERIFYING")

    def test_manual_gate_submission_returns_awaiting_human(self):
        config_path = self.root / "sdd" / "config.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        config["gates"] = {"G3": "human"}
        config_path.write_text(
            json.dumps(config, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        result = self.service.start_work(
            "demo",
            "srdcloud-553377",
            title="订单取消",
            domain="ORDER",
        )
        spec = result["spec_id"]
        self.service.submit_artifact(
            "demo", spec, "spec.md", SPEC_TEXT.replace("SPEC-ORDER-001", spec)
        )
        self.approve(spec)
        self.service.submit_artifact(
            "demo", spec, "design.md", DESIGN_TEXT.replace("SPEC-ORDER-001", spec)
        )
        tasks = self.service.submit_artifact(
            "demo", spec, "tasks.md", TASKS_TEXT.replace("SPEC-ORDER-001", spec)
        )
        self.assertTrue(tasks["ok"])
        self.assertTrue(tasks["awaiting_human_approval"])
        self.assertEqual(tasks["human_checkpoint"]["type"], "manual_gate")
        self.assertEqual(tasks["human_checkpoint"]["gate"], "G3")
        self.assertEqual(tasks["next"]["state"], "DESIGN_READY")

    def test_manual_g4_submit_task_returns_awaiting_human(self):
        config_path = self.root / "sdd" / "config.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        config["gates"] = {"G4": "human"}
        config_path.write_text(
            json.dumps(config, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        result = self.service.start_work(
            "demo",
            "srdcloud-553377",
            title="订单取消",
            domain="ORDER",
        )
        spec = result["spec_id"]
        self.service.submit_artifact(
            "demo", spec, "spec.md", SPEC_TEXT.replace("SPEC-ORDER-001", spec)
        )
        self.approve(spec)
        self.service.submit_artifact(
            "demo", spec, "design.md", DESIGN_TEXT.replace("SPEC-ORDER-001", spec)
        )
        self.service.submit_artifact(
            "demo", spec, "tasks.md", TASKS_TEXT.replace("SPEC-ORDER-001", spec)
        )
        (self.root / "tests" / "test_status.py").write_text(
            "import unittest\n\n"
            "class StatusTest(unittest.TestCase):\n"
            "    def test_cancel_pending_order(self):\n"
            "        # [AC-001-1]\n"
            "        self.assertTrue(True)\n",
            encoding="utf-8",
        )
        task = self.service.submit_task(
            "demo",
            spec,
            "T-001",
            "python -m unittest tests.test_status: 1 passed",
            "abc1234",
        )
        self.assertTrue(task["ok"])
        self.assertTrue(task["awaiting_human_approval"])
        self.assertEqual(task["human_checkpoint"]["type"], "manual_gate")
        self.assertEqual(task["human_checkpoint"]["gate"], "G4")
        self.assertEqual(task["next"]["action"], "finish_implementation")

    def test_verification_auto_runs_and_reaches_pr_ready(self):
        result = self.service.start_work(
            "demo",
            "srdcloud-553377",
            title="订单取消",
            domain="ORDER",
        )
        spec = result["spec_id"]
        self.service.submit_artifact(
            "demo", spec, "spec.md", SPEC_TEXT.replace("SPEC-ORDER-001", spec)
        )
        self.approve(spec)
        self.service.submit_artifact(
            "demo", spec, "design.md", DESIGN_TEXT.replace("SPEC-ORDER-001", spec)
        )
        self.service.submit_artifact(
            "demo", spec, "tasks.md", TASKS_TEXT.replace("SPEC-ORDER-001", spec)
        )
        (self.root / "tests" / "test_status.py").write_text(
            "import unittest\n\n"
            "class StatusTest(unittest.TestCase):\n"
            "    def test_cancel_pending_order(self):\n"
            "        # [AC-001-1]\n"
            "        self.assertTrue(True)\n",
            encoding="utf-8",
        )
        self.service.submit_task(
            "demo",
            spec,
            "T-001",
            "python -m unittest tests.test_status: 1 passed",
            "abc1234",
        )
        config_path = self.root / "sdd" / "config.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        config["test_commands"] = [
            f'"{sys.executable}" -m unittest tests.test_status'
        ]
        config_path.write_text(
            json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        verification = self.service.submit_artifact(
            "demo",
            spec,
            "verification.md",
            VERIFY_TEXT.replace("SPEC-ORDER-001", spec),
        )
        self.assertTrue(
            verification["ok"],
            msg=str(verification.get("errors")),
        )
        self.assertEqual(verification["next"]["action"], "confirm_merge")
        self.assertEqual(verification["next"]["state"], "PR_READY")
        self.assertEqual(verification["verification"]["stdout"].count("run:"), 1)
        self.assertTrue(
            (self.root / "docs" / "specs" / spec / "PR_BODY.md").is_file()
        )


if __name__ == "__main__":
    unittest.main()
