import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

try:
    from test_sdd import SPEC_TEXT
except ImportError:  # pragma: no cover
    from tests.test_sdd import SPEC_TEXT


KIT_ROOT = Path(__file__).resolve().parents[1]
SPEC_ID = "SPEC-ORDER-001"


class UpgradeTestBase(unittest.TestCase):
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
                "upgrade-session",
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

    def new_spec(self):
        self.run_sdd(
            "new",
            SPEC_ID,
            "--title",
            "订单取消",
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

    def state(self):
        return json.loads(
            (self.root / "docs" / "specs" / SPEC_ID / "state.json").read_text(
                encoding="utf-8"
            )
        )

    def snapshot(self):
        return json.loads(
            (self.root / "docs" / "specs" / SPEC_ID / "workflow.json").read_text(
                encoding="utf-8"
            )
        )

    def set_standard_version(self, version):
        path = self.root / "sdd" / "workflows" / "l2-standard.json"
        preset = json.loads(path.read_text(encoding="utf-8"))
        preset["version"] = version
        path.write_text(
            json.dumps(preset, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def upgrade(self, *target, expect=0, extra=()):
        return self.run_cli(
            "upgrade-workflow",
            "--spec",
            SPEC_ID,
            "--to",
            *target,
            "--reason",
            "统一到新门禁",
            "--human",
            *extra,
            expect=expect,
        )

    def file_hashes(self, names):
        return {
            name: hashlib.sha256(
                (self.root / "docs" / "specs" / SPEC_ID / name).read_bytes()
            ).hexdigest()
            for name in names
        }


class UpgradeWorkflowTests(UpgradeTestBase):
    def test_upgrade_same_preset_version(self):
        # [AC-001-1]
        self.new_spec()
        self.approve()
        self.set_standard_version(2)
        payload, _ = self.upgrade("l2-standard@2")
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["from"]["version"], 1)
        self.assertEqual(payload["to"]["version"], 2)
        state = self.state()
        self.assertEqual(state["workflow"]["version"], 2)
        self.assertEqual(self.snapshot()["version"], 2)
        self.assertEqual(
            state["workflow"]["digest"],
            payload["to"]["digest"],
        )

    def test_reject_same_version(self):
        # [AC-001-2]
        self.new_spec()
        self.approve()
        before = self.file_hashes(["state.json", "workflow.json"])
        _, result = self.upgrade("l2-standard@1", expect=None)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(before, self.file_hashes(["state.json", "workflow.json"]))

    def test_reject_missing_preset_and_version(self):
        # [AC-001-3]
        self.new_spec()
        self.approve()
        _, result = self.upgrade("l2-missing@1", expect=None)
        self.assertNotEqual(result.returncode, 0)
        _, result = self.upgrade("l2-standard@9", expect=None)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.state()["workflow"]["version"], 1)

    def test_cross_preset_and_downgrade_rules(self):
        # [AC-001-4]
        self.new_spec()
        self.approve()
        payload, _ = self.upgrade("l2-strict@1")
        self.assertEqual(payload["to"]["name"], "l2-strict")
        self.assertEqual(self.state()["workflow"]["name"], "l2-strict")

        self.set_standard_version(2)
        payload, _ = self.upgrade("l2-standard@2")
        self.assertEqual(payload["to"]["version"], 2)

        _, result = self.upgrade("l2-standard@1", expect=None)
        self.assertNotEqual(result.returncode, 0)
        _, result = self.upgrade(
            "l2-standard@1",
            expect=None,
            extra=("--allow-downgrade",),
        )
        self.assertNotEqual(result.returncode, 0)
        payload, _ = self.upgrade(
            "l2-standard@1",
            extra=("--allow-downgrade", "--design-change", "ADR-002"),
        )
        self.assertEqual(payload["to"]["version"], 1)
        history = self.state()["workflow_history"][-1]
        self.assertEqual(history["design_change"], "ADR-002")

    def test_reject_without_human_and_merged(self):
        # [AC-001-5]
        self.new_spec()
        self.approve()
        before = self.file_hashes(["state.json", "workflow.json"])
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "sdd",
                "--root",
                str(self.root),
                "upgrade-workflow",
                "--spec",
                SPEC_ID,
                "--to",
                "l2-standard@2",
                "--reason",
                "无人工确认",
                "--json",
            ],
            cwd=KIT_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(before, self.file_hashes(["state.json", "workflow.json"]))

        self.run_sdd("block", "--spec", SPEC_ID, "--reason", "等待外部依赖")
        self.set_standard_version(2)
        _, result = self.upgrade("l2-standard@2", expect=None)
        self.assertNotEqual(result.returncode, 0)

    def test_status_after_upgrade(self):
        # [AC-004-3]
        self.new_spec()
        self.approve()
        self.set_standard_version(2)
        self.upgrade("l2-standard@2")
        status = self.run_sdd("status", "--spec", SPEC_ID, "--json")
        payload = json.loads(status.stdout)
        self.assertEqual(payload["state"]["workflow"]["version"], 2)
        self.run_sdd("next", "--spec", SPEC_ID, "--json")


class UpgradeAuditTests(UpgradeTestBase):
    def test_upgrade_history_fields(self):
        # [AC-002-1]
        self.new_spec()
        self.approve()
        self.set_standard_version(2)
        self.upgrade(
            "l2-standard@2",
            extra=("--approver", "Tester <tester@example.com>"),
        )
        entry = self.state()["workflow_history"][-1]
        for key in ("from", "to", "approver", "reason", "at", "pending_gates"):
            self.assertIn(key, entry)
        self.assertEqual(entry["from"]["name"], "l2-standard")
        self.assertEqual(entry["to"]["version"], 2)
        self.assertEqual(entry["approver"], "Tester <tester@example.com>")
        self.assertEqual(entry["reason"], "统一到新门禁")

    def test_upgrade_keeps_artifacts(self):
        # [AC-002-2]
        self.new_spec()
        self.approve()
        names = ["spec.md", "design.md", "tasks.md", "verification.md", "gates.md"]
        before = self.file_hashes(names)
        self.set_standard_version(2)
        self.upgrade("l2-standard@2")
        self.assertEqual(before, self.file_hashes(names))

    def test_failed_upgrade_keeps_snapshot(self):
        # [AC-002-3]
        self.new_spec()
        self.approve()
        before = self.file_hashes(["state.json", "workflow.json"])
        _, result = self.upgrade("l2-missing@1", expect=None)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(before, self.file_hashes(["state.json", "workflow.json"]))


class UpgradeGateTests(UpgradeTestBase):
    def _upgrade_with_missing_gate(self):
        self.new_spec()
        self.approve()
        report = (
            self.root / "sdd" / "reports" / SPEC_ID / "gate1-report.md"
        )
        report.unlink()
        self.set_standard_version(2)
        return self.upgrade("l2-standard@2")

    def test_upgrade_records_pending_gates(self):
        # [AC-003-1]
        payload, _ = self._upgrade_with_missing_gate()
        self.assertEqual(payload["pending_gates"], ["G1"])
        entry = self.state()["workflow_history"][-1]
        self.assertEqual(entry["pending_gates"], ["G1"])

    def test_inbox_lists_pending_gate(self):
        # [AC-003-2]
        self._upgrade_with_missing_gate()
        payload, _ = self.run_cli("inbox")
        items = [
            item
            for item in payload.get("items", [])
            if item.get("gate") == "G1"
            and item.get("action") == "workflow_gate_missing"
        ]
        self.assertEqual(len(items), 1)
        self.assertIn("check", items[0]["command"])

    def test_pending_gate_disappears_after_pass(self):
        # [AC-003-3]
        self._upgrade_with_missing_gate()
        reports = self.root / "sdd" / "reports" / SPEC_ID
        source = reports / "gate0-report.md"
        (reports / "gate1-report.md").write_text(
            source.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        payload, _ = self.run_cli("inbox")
        gates = [
            item.get("gate")
            for item in payload.get("items", [])
            if item.get("action") == "workflow_gate_missing"
        ]
        self.assertNotIn("G1", gates)


class UpgradeBoundaryTests(unittest.TestCase):
    def test_mcp_does_not_expose_upgrade(self):
        # [AC-004-1]
        source = (KIT_ROOT / "sdd" / "mcp" / "server.py").read_text(encoding="utf-8")
        self.assertNotIn("upgrade_workflow", source)
        self.assertNotIn("upgrade-workflow", source)

    def test_release_metadata(self):
        # [AC-004-2]
        version = (KIT_ROOT / "sdd" / "VERSION").read_text(encoding="utf-8").strip()
        manifest = json.loads(
            (KIT_ROOT / "sdd" / "manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["version"], version)
        self.assertGreaterEqual(tuple(int(part) for part in version.split(".")), (0, 9, 9))
        for name in ("README.md", "sdd/README.md", "sdd/agent-contract.md"):
            text = (KIT_ROOT / name).read_text(encoding="utf-8")
            self.assertIn("upgrade-workflow", text, msg=name)


if __name__ == "__main__":
    unittest.main()
