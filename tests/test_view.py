import ast
import hashlib
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
    from tests.test_sdd import DESIGN_TEXT, SPEC_TEXT, TASKS_TEXT


KIT_ROOT = Path(__file__).resolve().parents[1]
SPEC_ID = "SPEC-ORDER-001"


class ViewTestBase(unittest.TestCase):
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

    def run_cli(self, *args, expect=0):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "sdd",
                "--root",
                str(self.root),
                "--session-key",
                "view-session",
                *args,
                "--json",
            ],
            cwd=KIT_ROOT,
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
        try:
            return json.loads(result.stdout), result
        except json.JSONDecodeError:
            return {"raw": result.stdout, "stderr": result.stderr}, result

    def write(self, relative, text):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def new_spec(self, title="订单取消"):
        self.run_sdd(
            "new",
            SPEC_ID,
            "--title",
            title,
            "--work-item",
            "srdcloud-553377",
            "--issue-url",
            "https://example.invalid/item/553377",
            "--risk",
            "low",
        )

    def approve(self):
        self.write(f"docs/specs/{SPEC_ID}/spec.md", SPEC_TEXT)
        self.run_sdd(
            "approve",
            "--spec",
            SPEC_ID,
            "--human",
            "--evidence",
            "需求已确认",
        )

    def implement_and_verify(self):
        self.write(f"docs/specs/{SPEC_ID}/design.md", DESIGN_TEXT)
        self.run_sdd("complete", "--spec", SPEC_ID, "--evidence", "design 完成")
        self.write(f"docs/specs/{SPEC_ID}/tasks.md", TASKS_TEXT)
        self.run_sdd("complete", "--spec", SPEC_ID, "--evidence", "tasks 完成")
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


class ViewRenderTests(ViewTestBase):
    def test_view_contains_all_sections(self):
        # [AC-001-1]
        self.new_spec()
        self.approve()
        payload, _ = self.run_cli("view", "--spec", SPEC_ID)
        out = self.root / payload["out"]
        html = out.read_text(encoding="utf-8")
        self.assertIn("<!DOCTYPE html>", html)
        for marker in ('id="timeline"', 'id="gates"', 'id="tasks"', 'id="artifacts"'):
            self.assertIn(marker, html)
        self.assertIn(SPEC_ID, html)
        self.assertIn("SPEC_READY", html)
        self.assertIn("l2-standard", html)

    def test_view_default_output_path(self):
        # [AC-001-2]
        self.new_spec()
        payload, _ = self.run_cli("view", "--spec", SPEC_ID)
        expected = self.root / ".sdd" / "runtime" / "view" / f"{SPEC_ID}.html"
        self.assertEqual(Path(payload["out"]).resolve(), expected.resolve())
        self.assertTrue(expected.is_file())
        self.assertGreater(payload["bytes"], 0)

    def test_view_empty_spec_renders_empty_states(self):
        # [AC-001-3]
        self.new_spec()
        (self.root / "docs" / "specs" / SPEC_ID / "tasks.md").unlink()
        payload, _ = self.run_cli("view", "--spec", SPEC_ID)
        html = (self.root / payload["out"]).read_text(encoding="utf-8")
        self.assertIn("暂无 Gate 记录", html)
        self.assertIn("暂无 Task", html)
        self.assertIn("id=\"timeline\"", html)


class ViewReadOnlyTests(ViewTestBase):
    def test_view_does_not_change_audit_files(self):
        # [AC-002-1]
        self.new_spec()
        self.approve()
        targets = [
            self.root / "docs" / "specs" / SPEC_ID / "state.json",
            self.root / "docs" / "specs" / SPEC_ID / "events.jsonl",
        ]
        before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in targets}
        self.run_cli("view", "--spec", SPEC_ID)
        after = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in targets}
        self.assertEqual(before, after)


class ViewTimelineTests(ViewTestBase):
    def test_view_shows_rewind_event(self):
        # [AC-002-2]
        self.new_spec()
        self.approve()
        self.implement_and_verify()
        self.run_sdd(
            "rewind",
            "--spec",
            SPEC_ID,
            "--to",
            "DESIGN_READY",
            "--reason",
            "返工",
            "--human",
            "--force",
        )
        payload, _ = self.run_cli("view", "--spec", SPEC_ID)
        html = (self.root / payload["out"]).read_text(encoding="utf-8")
        self.assertIn("rewind", html)
        self.assertIn("返工", html)
        self.assertIn("VERIFYING", html)
        self.assertIn("DESIGN_READY", html)


class ViewBoundaryTests(ViewTestBase):
    def test_view_rejects_missing_spec_and_bad_out(self):
        # [AC-003-1]
        payload, result = self.run_cli("view", "--spec", "SPEC-MISSING-001", expect=None)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(payload.get("ok", True))

        self.new_spec()
        payload, result = self.run_cli(
            "view", "--spec", SPEC_ID, "--out", str(self.root), expect=None
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(payload.get("ok", True))

    def test_view_escapes_html_and_has_no_script(self):
        # [AC-003-2]
        self.new_spec(title="<script>alert(1)</script>")
        payload, _ = self.run_cli("view", "--spec", SPEC_ID)
        html = (self.root / payload["out"]).read_text(encoding="utf-8")
        self.assertIn("&lt;script&gt;", html)
        self.assertNotIn("<script>", html.lower())
        self.assertNotIn("<link", html.lower())
        self.assertNotIn("src=", html.lower())

    def test_view_does_not_import_state_machine_rules(self):
        # [AC-002-3]
        source = (KIT_ROOT / "sdd" / "view.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
            elif isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
        self.assertFalse(any("scripts" in name for name in imports))
        self.assertNotIn("parse_tasks", source)
        mcp = (KIT_ROOT / "sdd" / "mcp" / "server.py").read_text(encoding="utf-8")
        self.assertNotIn("sdd_view", mcp)


class ReleaseMetadataTests(unittest.TestCase):
    def test_view_release_metadata(self):
        # [AC-003-3]
        version = (KIT_ROOT / "sdd" / "VERSION").read_text(encoding="utf-8").strip()
        manifest = json.loads(
            (KIT_ROOT / "sdd" / "manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["version"], version)
        self.assertIn("sdd/view.py", manifest["files"])
        self.assertGreaterEqual(tuple(int(part) for part in version.split(".")), (0, 9, 8))
        for name in ("README.md", "sdd/README.md", "sdd/agent-contract.md"):
            text = (KIT_ROOT / name).read_text(encoding="utf-8")
            self.assertIn("sdd view", text, msg=name)


if __name__ == "__main__":
    unittest.main()
