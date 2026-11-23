import shutil
import subprocess
import sys
import unittest
from pathlib import Path

from tests.test_sdd import SPEC_ID, SPEC_TEXT, SddFlowBase


KIT_ROOT = Path(__file__).resolve().parents[1]


class CiWorkflowTests(SddFlowBase):
    def run_module(self, *args):
        result = subprocess.run(
            [sys.executable, "-m", "sdd", *args],
            cwd=self.root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        self.assertEqual(
            result.returncode,
            0,
            msg=f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )
        return result

    def test_ci_workflow_runs_sdd_checks(self):
        # [AC-003-1] [AC-003-2] [AC-003-3] [AC-005-3]
        workflow = (KIT_ROOT / ".github" / "workflows" / "tests.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("python -m sdd verify-core", workflow)
        self.assertIn("python -m sdd verify-agent", workflow)
        self.assertIn(
            "python -m sdd check --all --stage ci --check-git",
            workflow,
        )
        self.assertNotIn("continue-on-error", workflow)
        self.assertIn("python -m unittest discover -s tests -v", workflow)

        self.new_spec()
        self.write(f"docs/specs/{SPEC_ID}/spec.md", SPEC_TEXT)
        self.run_sdd("index", "--spec", SPEC_ID)
        self.approve_valid_spec()
        self.complete_design()
        self.complete_tasks()
        self.run_sdd(
            "complete", "--spec", SPEC_ID, "--evidence", "开始实现"
        )
        self.finish_implementation()
        self.finish_verification()

        for path in (self.root / "docs").rglob("*.md"):
            path.write_bytes(path.read_bytes().replace(b"\r\n", b"\n"))

        shutil.copy2(KIT_ROOT / "AGENTS.md", self.root / "AGENTS.md")
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        subprocess.run(
            ["git", "config", "user.email", "ci@example.invalid"],
            cwd=self.root,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "CI"],
            cwd=self.root,
            check=True,
        )
        subprocess.run(["git", "add", "-A"], cwd=self.root, check=True)
        subprocess.run(
            [
                "git",
                "commit",
                "-q",
                "-m",
                "chore(sdd): verify ci gates",
                "-m",
                f"Spec-Id: {SPEC_ID}",
            ],
            cwd=self.root,
            check=True,
        )

        self.run_module("verify-core")
        self.run_module("verify-agent")
        self.run_module("check", "--all", "--stage", "ci", "--check-git")


if __name__ == "__main__":
    unittest.main()
