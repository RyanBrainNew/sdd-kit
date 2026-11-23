import unittest
from pathlib import Path


KIT_ROOT = Path(__file__).resolve().parents[1]


class CiWorkflowTests(unittest.TestCase):
    def test_ci_workflow_runs_sdd_checks(self):
        # [AC-003-1] [AC-003-2] [AC-003-3]
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


if __name__ == "__main__":
    unittest.main()
