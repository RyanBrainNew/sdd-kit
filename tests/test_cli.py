import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

try:
    from test_sdd import DESIGN_TEXT, SPEC_TEXT, TASKS_TEXT
except ImportError:  # pragma: no cover
    try:
        from tests.test_sdd import DESIGN_TEXT, SPEC_TEXT, TASKS_TEXT
    except ImportError:
        SPEC_TEXT = DESIGN_TEXT = TASKS_TEXT = ""


KIT_ROOT = Path(__file__).resolve().parents[1]


class CliTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        shutil.copytree(KIT_ROOT / "sdd", self.root / "sdd")
        shutil.copyfile(KIT_ROOT / "AGENTS.md", self.root / "AGENTS.md")
        (self.root / "docs").mkdir()
        (self.root / "tests").mkdir()
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=False)

    def tearDown(self):
        self.temp.cleanup()

    def run_cli(self, *args, session="session-a", expect=0):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "sdd",
                "--root",
                str(self.root),
                "--session-key",
                session,
                *args,
                "--json",
            ],
            cwd=KIT_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        self.assertEqual(
            result.returncode,
            expect,
            msg=f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError:
            payload = {"raw": result.stdout, "stderr": result.stderr}
        return payload

    def start(self, work_item, title, session="session-a", domain="ORDER"):
        return self.run_cli(
            "start-work",
            "--work-item",
            work_item,
            "--title",
            title,
            "--domain",
            domain,
            session=session,
        )

    def write_artifact(self, spec, name, text):
        path = self.root / "docs" / "specs" / spec / name
        path.write_text(text.replace("SPEC-ORDER-001", spec), encoding="utf-8")

    def test_start_work_binds_session_and_resume_restores_it(self):
        started = self.start("srdcloud-553377", "订单取消")
        spec = started["spec_id"]
        self.assertEqual(started["work_order"]["next"]["action"], "write_spec")
        self.assertEqual(started["work_order"]["next"]["kind"], "artifact")
        self.assertEqual(started["work_order"]["next"]["step_id"], f"{spec}:spec")
        self.assertEqual(
            started["work_order"]["next"]["prompt_file"],
            "sdd/prompts/spec.md",
        )
        pointer = self.root / ".sdd" / "runtime" / "sessions"
        self.assertTrue(any(pointer.iterdir()))

        resumed = self.run_cli("resume")
        self.assertEqual(resumed["spec"], spec)
        self.assertEqual(resumed["next"]["action"], "write_spec")

    def test_start_work_accepts_workflow(self):
        started = self.run_cli(
            "start-work",
            "--work-item",
            "srdcloud-553379",
            "--title",
            "紧急修复",
            "--domain",
            "ORDER",
            "--workflow",
            "l2-hotfix",
            "--risk",
            "medium",
        )
        spec = started["spec_id"]
        status = self.run_cli("status", "--spec", spec)
        self.assertEqual(
            status["state"]["workflow"]["name"],
            "l2-hotfix",
        )
        self.assertEqual(
            status["next"]["workflow"]["version"],
            1,
        )

    def test_two_sessions_keep_independent_current_specs(self):
        first = self.start("srdcloud-553377", "订单取消", session="session-a")
        second = self.start("srdcloud-553378", "订单改址", session="session-b")
        self.assertNotEqual(first["spec_id"], second["spec_id"])

        self.assertEqual(self.run_cli("resume", session="session-a")["spec"], first["spec_id"])
        self.assertEqual(self.run_cli("resume", session="session-b")["spec"], second["spec_id"])

    def test_branch_name_is_used_when_session_pointer_is_missing(self):
        first = self.start("srdcloud-553377", "订单取消", session="session-a")
        second = self.start("srdcloud-553378", "订单改址", session="session-b")
        self.assertNotEqual(first["spec_id"], second["spec_id"])
        subprocess.run(
            ["git", "checkout", "-q", "-b", f"feature/{second['spec_id']}-address"],
            cwd=self.root,
            check=True,
        )
        session_file = next((self.root / ".sdd" / "runtime" / "sessions").iterdir())
        session_file.unlink()
        resumed = self.run_cli("resume", session="session-c")
        self.assertEqual(resumed["spec"], second["spec_id"])

    def test_approve_is_rejected_without_human_flag(self):
        started = self.start("srdcloud-553377", "订单取消")
        spec = started["spec_id"]
        self.write_artifact(spec, "spec.md", SPEC_TEXT)
        rejected = self.run_cli(
            "approve",
            "--spec",
            spec,
            "--evidence",
            "需求已确认",
            expect=2,
        )
        self.assertFalse(rejected["ok"])
        state = self.run_cli("status", "--spec", spec)["state"]["state"]
        self.assertEqual(state, "DRAFT")

        approved = self.run_cli(
            "approve",
            "--spec",
            spec,
            "--human",
            "--evidence",
            "需求已确认",
        )
        self.assertTrue(approved["ok"])
        self.assertEqual(approved["next"]["state"], "SPEC_READY")

    def test_submit_wrong_stage_is_rejected(self):
        started = self.start("srdcloud-553377", "订单取消")
        spec = started["spec_id"]
        result = self.run_cli(
            "submit",
            "--spec",
            spec,
            "--artifact",
            "design.md",
            "--content",
            "# design",
            expect=1,
        )
        self.assertFalse(result["ok"])
        self.assertIn("write_spec", result["errors"][0])

    def test_check_all_with_no_specs_is_ok(self):
        result = self.run_cli("check", "--all", "--stage", "ci", "--check-git")
        self.assertTrue(result["ok"])
        self.assertEqual(result["specs"], [])

    def test_full_cli_loop_reaches_pr_ready(self):
        started = self.start("srdcloud-553377", "订单取消")
        spec = started["spec_id"]
        self.write_artifact(spec, "spec.md", SPEC_TEXT)
        submitted = self.run_cli(
            "submit", "--spec", spec, "--artifact", "spec.md",
            "--file", str(self.root / "docs" / "specs" / spec / "spec.md"),
        )
        self.assertTrue(submitted["awaiting_human_approval"])

        self.run_cli(
            "approve", "--spec", spec, "--human", "--evidence", "需求已确认"
        )
        self.write_artifact(spec, "design.md", DESIGN_TEXT)
        design = self.run_cli(
            "submit", "--spec", spec, "--artifact", "design.md",
            "--file", str(self.root / "docs" / "specs" / spec / "design.md"),
        )
        self.assertEqual(design["next"]["action"], "write_tasks")

        self.write_artifact(spec, "tasks.md", TASKS_TEXT)
        tasks = self.run_cli(
            "submit", "--spec", spec, "--artifact", "tasks.md",
            "--file", str(self.root / "docs" / "specs" / spec / "tasks.md"),
        )
        self.assertEqual(tasks["next"]["action"], "implement_task")
        board = self.run_cli("board")
        self.assertEqual(board["kind"], "board")
        self.assertEqual(board["specs"][0]["tasks"][0]["status"], "Todo")

        (self.root / "tests" / "test_status.py").write_text(
            "import unittest\n\n"
            "class StatusTest(unittest.TestCase):\n"
            "    def test_cancel_pending_order(self):\n"
            "        # [AC-001-1]\n"
            "        self.assertTrue(True)\n",
            encoding="utf-8",
        )
        task = self.run_cli(
            "submit-task",
            "--spec",
            spec,
            "--task",
            "T-001",
            "--evidence",
            "python -m unittest tests.test_status: 1 passed",
            "--commit",
            "abc1234",
        )
        self.assertEqual(task["next"]["action"], "run_verification")
        verified = self.run_cli(
            "verify",
            "--spec",
            spec,
            "--command",
            "python -m unittest tests.test_status -v",
        )
        self.assertIn("verify passed", verified["stdout"])
        evidence = (
            self.root
            / "docs"
            / "specs"
            / spec
            / "verification-evidence.jsonl"
        )
        self.assertTrue(evidence.is_file())

    def test_events_are_append_only_and_board_marks_current_session(self):
        started = self.start("srdcloud-553377", "订单取消")
        spec = started["spec_id"]
        first = self.run_cli("events", "--spec", spec)
        self.assertEqual(first["kind"], "events")
        self.assertEqual(first["source"], "events.jsonl")
        self.assertEqual(first["count"], 1)
        first_event = first["events"][0]
        self.assertEqual(first_event["event"], "spec_created")
        self.assertEqual(first_event["to_state"], "DRAFT")

        self.write_artifact(spec, "spec.md", SPEC_TEXT)
        self.run_cli(
            "submit",
            "--spec",
            spec,
            "--artifact",
            "spec.md",
            "--file",
            str(self.root / "docs" / "specs" / spec / "spec.md"),
        )
        self.run_cli(
            "approve", "--spec", spec, "--human", "--evidence", "需求已确认"
        )

        second = self.run_cli("events", "--spec", spec)
        self.assertGreaterEqual(second["count"], 2)
        self.assertEqual(second["events"][0], first_event)
        self.assertEqual(second["events"][-1]["to_state"], "SPEC_READY")

        board = self.run_cli("board")
        self.assertEqual(board["current_spec"], spec)
        item = next(item for item in board["specs"] if item["spec"] == spec)
        self.assertTrue(item["current"])
        self.assertEqual(item["events_count"], second["count"])

    def test_verify_core_and_agent_detect_tampering(self):
        self.run_cli("manifest", "--write")
        self.assertEqual(self.run_cli("verify-core")["ok"], True)
        core = self.root / "sdd" / "core.py"
        core.write_text(core.read_text(encoding="utf-8") + "\n# tamper\n", encoding="utf-8")
        tampered = self.run_cli("verify-core", expect=1)
        self.assertTrue(tampered["errors"])

        self.run_cli("sync-agent")
        self.assertTrue(self.run_cli("verify-agent")["ok"])
        agents = self.root / "AGENTS.md"
        agents.write_text(
            agents.read_text(encoding="utf-8").replace(
                "python -m sdd resume --json", "python -m sdd status"
            ),
            encoding="utf-8",
        )
        self.assertFalse(self.run_cli("verify-agent", expect=1)["ok"])


if __name__ == "__main__":
    unittest.main()
