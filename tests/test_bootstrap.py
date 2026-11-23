import json
import os
import tempfile
import unittest
from pathlib import Path

import bootstrap


class BootstrapTest(unittest.TestCase):
    def test_defaults_target_to_cwd_and_project_to_folder_name(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "order-api"
            target.mkdir()
            previous = Path.cwd()
            try:
                os.chdir(target)
                code = bootstrap.main(["--no-hooks"])
            finally:
                os.chdir(previous)
            self.assertEqual(code, 0)
            self.assertTrue((target / "sdd" / "scripts" / "sdd.py").is_file())
            config = json.loads(
                (target / "sdd" / "config.json").read_text(encoding="utf-8")
            )
            self.assertEqual(config["project"], "order-api")

    def test_refuses_to_bootstrap_the_kit_source_repository(self):
        with self.assertRaises(SystemExit) as caught:
            bootstrap.main(["--target", str(bootstrap.KIT_ROOT), "--no-hooks"])
        self.assertIn("sdd-kit source repository", str(caught.exception))
        with self.assertRaises(SystemExit):
            bootstrap.main(
                ["--target", str(bootstrap.KIT_ROOT / "docs"), "--no-hooks"]
            )

    def test_bootstrap_installs_core_and_local_mcp(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)
            code = bootstrap.main(
                [
                    "--target",
                    str(target),
                    "--project",
                    "demo-service",
                    "--test-command",
                    "python -m unittest",
                    "--no-hooks",
                ]
            )
            self.assertEqual(code, 0)
            self.assertTrue((target / "sdd" / "scripts" / "sdd.py").is_file())
            self.assertTrue((target / "sdd" / "mcp" / "server.py").is_file())
            self.assertTrue((target / "AGENTS.md").is_file())
            agents_text = (target / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("<!-- SDD:MANAGED:START -->", agents_text)
            self.assertIn("<!-- SDD:MANAGED:END -->", agents_text)
            self.assertIn("不要问", agents_text)
            self.assertIn("python -m sdd resume --json", agents_text)
            self.assertTrue((target / "sdd" / "manifest.json").is_file())
            self.assertTrue(
                (target / "sdd" / "workflows" / "l2-standard.json").is_file()
            )
            self.assertTrue((target / "sdd" / "context" / "services").is_dir())
            self.assertIn(
                ".sdd-allocations.json",
                (target / ".gitignore").read_text(encoding="utf-8"),
            )
            self.assertIn(
                ".sdd/runtime/",
                (target / ".gitignore").read_text(encoding="utf-8"),
            )
            config = json.loads(
                (target / "sdd" / "config.json").read_text(encoding="utf-8")
            )
            self.assertEqual(config["project"], "demo-service")
            self.assertEqual(config["test_commands"], ["python -m unittest"])
            self.assertEqual(config["sdd_level"], "L2")
            self.assertTrue(config["require_approver"])
            self.assertTrue(config["require_artifact_hash"])
            self.assertEqual(config["workflow"], "l2-standard")

    def test_existing_agents_keeps_project_rules_and_merges_managed_block(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)
            original = "# Existing project rules\n\nUse pnpm.\n"
            (target / "AGENTS.md").write_text(original, encoding="utf-8")
            code = bootstrap.main(
                [
                    "--target",
                    str(target),
                    "--project",
                    "demo-service",
                    "--no-hooks",
                ]
            )
            self.assertEqual(code, 0)
            merged = (target / "AGENTS.md").read_text(encoding="utf-8")
            self.assertTrue(merged.startswith(original))
            self.assertIn("<!-- SDD:MANAGED:START -->", merged)
            self.assertIn("python -m sdd resume --json", merged)
            self.assertFalse((target / "AGENTS.sdd.md").exists())

    def test_bootstrap_is_idempotent_for_agents_block_and_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)
            args = [
                "--target",
                str(target),
                "--project",
                "demo-service",
                "--no-hooks",
            ]
            self.assertEqual(bootstrap.main(args), 0)
            first = (target / "AGENTS.md").read_text(encoding="utf-8")
            first_manifest = (target / "sdd" / "manifest.json").read_text(
                encoding="utf-8"
            )
            self.assertEqual(bootstrap.main(args + ["--force"]), 0)
            self.assertEqual(
                (target / "AGENTS.md").read_text(encoding="utf-8"),
                first,
            )
            self.assertEqual(
                (target / "sdd" / "manifest.json").read_text(encoding="utf-8"),
                first_manifest,
            )

    def test_force_preserves_existing_test_commands(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)
            base_args = [
                "--target",
                str(target),
                "--project",
                "demo-service",
                "--no-hooks",
            ]
            self.assertEqual(
                bootstrap.main(base_args + ["--test-command", "make test"]),
                0,
            )
            self.assertEqual(
                bootstrap.main(base_args + ["--force"]),
                0,
            )
            config = json.loads(
                (target / "sdd" / "config.json").read_text(encoding="utf-8")
            )
            self.assertEqual(config["test_commands"], ["make test"])
            self.assertTrue(config["require_approver"])
            self.assertTrue(config["require_artifact_hash"])

    def test_force_keeps_project_id_when_not_passed(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)
            self.assertEqual(
                bootstrap.main(
                    [
                        "--target",
                        str(target),
                        "--project",
                        "custom-id",
                        "--no-hooks",
                    ]
                ),
                0,
            )
            self.assertEqual(
                bootstrap.main(["--target", str(target), "--force", "--no-hooks"]),
                0,
            )
            config = json.loads(
                (target / "sdd" / "config.json").read_text(encoding="utf-8")
            )
            self.assertEqual(config["project"], "custom-id")


if __name__ == "__main__":
    unittest.main()
