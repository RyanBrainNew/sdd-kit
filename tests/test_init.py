import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from sdd import bootstrap as bootstrap_module
from sdd import cli as cli_module


KIT_ROOT = Path(__file__).resolve().parents[1]


class InitCliTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def run_init(self, target, *args, expect=0):
        env = os.environ.copy()
        env.setdefault("PYTHONIOENCODING", "utf-8")
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "sdd",
                "init",
                "--target",
                str(target),
                "--json",
                *args,
            ],
            cwd=KIT_ROOT,
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
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError:
            payload = {"raw": result.stdout, "stderr": result.stderr}
        return payload, result

    def test_install_creates_workspace_and_passes_verification(self):
        target = self.base / "order api"
        target.mkdir()
        payload, _ = self.run_init(
            target,
            "--project",
            "order-api",
            "--no-hooks",
        )

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["kind"], "init")
        self.assertEqual(payload["mode"], "install")
        self.assertEqual(payload["project"], "order-api")
        self.assertEqual(
            [check["name"] for check in payload["checks"]],
            ["verify-core", "verify-agent"],
        )
        self.assertTrue(all(check["ok"] for check in payload["checks"]))
        self.assertFalse((target / ".sdd").exists())
        self.assertFalse(
            list(target.rglob("state.json")),
            "init must not create SDD state",
        )
        self.assertFalse(
            list(target.rglob("events.jsonl")),
            "init must not create audit events",
        )

        for relative in (
            "sdd/scripts/sdd.py",
            "sdd/config.json",
            "sdd/manifest.json",
            "AGENTS.md",
            ".gitignore",
            "docs/prd-index.md",
            "sdd/context/services",
        ):
            self.assertTrue((target / relative).exists(), relative)

        config = json.loads(
            (target / "sdd" / "config.json").read_text(encoding="utf-8")
        )
        self.assertEqual(config["project"], "order-api")
        self.assertEqual(config["sdd_level"], "L2")
        self.assertTrue(config["require_approver"])
        self.assertTrue(config["require_artifact_hash"])
        self.assertEqual(config["workflow"], "l2-standard")
        self.assertEqual(config["test_commands"], [])

        agents = (target / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("<!-- SDD:MANAGED:START -->", agents)
        self.assertIn("<!-- SDD:MANAGED:END -->", agents)
        gitignore = (target / ".gitignore").read_text(encoding="utf-8")
        self.assertIn(".sdd/runtime/", gitignore)
        self.assertIn(".sdd-allocations.json", gitignore)
        manifest = json.loads(
            (target / "sdd" / "manifest.json").read_text(encoding="utf-8")
        )
        self.assertIn("sdd/bootstrap.py", manifest["files"])

    def test_second_run_is_repair_and_keeps_files_unchanged(self):
        target = self.base / "demo"
        target.mkdir()
        self.run_init(target, "--no-hooks")
        tracked = (
            "AGENTS.md",
            "sdd/config.json",
            "sdd/manifest.json",
            ".gitignore",
            "docs/prd-index.md",
        )
        before = {
            item: (target / item).read_bytes()
            for item in tracked
        }

        payload, _ = self.run_init(target, "--no-hooks")

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["mode"], "repair")
        self.assertEqual(payload["actions"], [])
        for item in tracked:
            self.assertEqual((target / item).read_bytes(), before[item], item)

    def test_second_run_in_a_git_repo_has_no_actions(self):
        target = self.base / "git-demo"
        target.mkdir()
        subprocess.run(
            ["git", "init", "-q"],
            cwd=target,
            check=True,
        )
        self.run_init(target)
        payload, _ = self.run_init(target)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["mode"], "repair")
        self.assertEqual(payload["actions"], [])

    def test_force_refreshes_core_and_preserves_user_files(self):
        target = self.base / "legacy"
        target.mkdir()
        self.run_init(
            target,
            "--project",
            "legacy-api",
            "--test-command",
            "make test",
        )

        spec = target / "docs" / "specs" / "SPEC-ORDER-001" / "spec.md"
        spec.parent.mkdir(parents=True)
        spec.write_text("# keep me\n", encoding="utf-8")
        service = target / "sdd" / "context" / "services" / "order.yaml"
        service.write_text("name: order\n", encoding="utf-8")
        context_readme = target / "sdd" / "context" / "README.md"
        context_readme.write_text("# team context\n", encoding="utf-8")
        config_path = target / "sdd" / "config.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        config["gate_overrides"] = {"G2": "human"}
        config_path.write_text(
            json.dumps(config, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        core = target / "sdd" / "agents.py"
        core.write_text(
            core.read_text(encoding="utf-8") + "\n# local drift\n",
            encoding="utf-8",
        )
        hook = target / ".githooks" / "pre-commit"
        hook.write_text("#!/bin/sh\n# local hook\n", encoding="utf-8")

        payload, _ = self.run_init(target, "--force")

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["mode"], "repair")
        self.assertIn("sdd/config.json", payload["preserved"])
        self.assertIn("sdd/context", payload["preserved"])
        self.assertEqual(spec.read_text(encoding="utf-8"), "# keep me\n")
        self.assertEqual(service.read_text(encoding="utf-8"), "name: order\n")
        self.assertEqual(
            context_readme.read_text(encoding="utf-8"), "# team context\n"
        )
        config = json.loads(config_path.read_text(encoding="utf-8"))
        self.assertEqual(config["project"], "legacy-api")
        self.assertEqual(config["test_commands"], ["make test"])
        self.assertEqual(config["gate_overrides"], {"G2": "human"})
        self.assertNotIn(
            "local drift", core.read_text(encoding="utf-8")
        )
        self.assertEqual(
            hook.read_text(encoding="utf-8"), "#!/bin/sh\n# local hook\n"
        )

    def test_dry_run_writes_nothing(self):
        target = self.base / "dry"
        target.mkdir()
        payload, _ = self.run_init(target, "--dry-run")

        self.assertTrue(payload["ok"])
        self.assertTrue(payload["dry_run"])
        self.assertTrue(payload["actions"])
        self.assertEqual(list(target.iterdir()), [])

    def test_rejects_target_inside_the_kit_source(self):
        for target in (KIT_ROOT, KIT_ROOT / "docs"):
            payload, _ = self.run_init(target, expect=1)
            self.assertFalse(payload["ok"])
            self.assertIn(
                "sdd-kit source repository",
                "\n".join(payload["errors"]),
            )
            self.assertIn("--target", payload["next"]["command"])

    def test_half_initialized_workspace_requires_force(self):
        target = self.base / "half"
        (target / "sdd" / "context").mkdir(parents=True)
        payload, _ = self.run_init(target, "--no-hooks", expect=1)
        self.assertFalse(payload["ok"])
        self.assertIn("--force", payload["next"]["command"])

        payload, _ = self.run_init(target, "--force", "--no-hooks")
        self.assertTrue(payload["ok"])
        self.assertTrue((target / "sdd" / "config.json").is_file())
        self.assertTrue((target / "sdd" / "manifest.json").is_file())

    def test_ci_and_hooks_install_and_existing_files_are_kept(self):
        target = self.base / "pipeline"
        target.mkdir()
        payload, _ = self.run_init(target, "--ci", "github")
        self.assertTrue(payload["ok"])
        github = target / ".github" / "workflows" / "sdd.yml"
        self.assertTrue(github.is_file())
        self.assertTrue((target / ".githooks" / "pre-commit").is_file())
        self.assertTrue((target / ".githooks" / "commit-msg").is_file())

        github.write_text("# custom workflow\n", encoding="utf-8")
        payload, _ = self.run_init(target, "--ci", "github")
        self.assertTrue(payload["ok"])
        self.assertEqual(
            github.read_text(encoding="utf-8"), "# custom workflow\n"
        )
        self.assertIn(
            ".github/workflows/sdd.yml", payload["preserved"]
        )

        payload, _ = self.run_init(target, "--ci", "gitlab")
        self.assertTrue(payload["ok"])
        self.assertTrue((target / ".gitlab-ci.yml").is_file())

    def test_no_agent_skips_agents_and_verify_agent(self):
        target = self.base / "agentless"
        target.mkdir()
        payload, _ = self.run_init(
            target, "--no-agent", "--no-hooks"
        )
        self.assertTrue(payload["ok"])
        self.assertFalse((target / "AGENTS.md").exists())
        checks = {check["name"]: check for check in payload["checks"]}
        self.assertTrue(checks["verify-core"]["ok"])
        self.assertTrue(checks["verify-agent"]["skipped"])

    def test_invalid_target_returns_stable_json_error(self):
        target = self.base / "missing"
        payload, _ = self.run_init(target, expect=1)
        for key in (
            "ok",
            "kind",
            "mode",
            "target",
            "project",
            "actions",
            "warnings",
            "next",
            "errors",
        ):
            self.assertIn(key, payload)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["kind"], "init")
        self.assertTrue(payload["errors"])

    def test_bootstrap_shim_prints_deprecation_and_delegates(self):
        target = self.base / "shim"
        target.mkdir()
        env = os.environ.copy()
        env.setdefault("PYTHONIOENCODING", "utf-8")
        result = subprocess.run(
            [
                sys.executable,
                str(KIT_ROOT / "bootstrap.py"),
                "--target",
                str(target),
                "--no-hooks",
                "--json",
            ],
            cwd=KIT_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("deprecated", result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["ok"])
        self.assertTrue((target / "sdd" / "config.json").is_file())


class VersionConsistencyTest(unittest.TestCase):
    def test_pyproject_version_matches_kit_version(self):
        version = (KIT_ROOT / "sdd" / "VERSION").read_text(
            encoding="utf-8"
        ).strip()
        pyproject = tomllib.loads(
            (KIT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        )
        self.assertEqual(pyproject["project"]["version"], version)
        self.assertIn(
            f'__version__ = "{version}"',
            (KIT_ROOT / "sdd" / "__init__.py").read_text(encoding="utf-8"),
        )
        self.assertIn(
            f'VERSION = "{version}"',
            (KIT_ROOT / "sdd" / "scripts" / "sdd.py").read_text(
                encoding="utf-8"
            ),
        )


class InitVerificationFailureTest(unittest.TestCase):
    def test_verify_failure_is_reported_and_fails_the_payload(self):
        with tempfile.TemporaryDirectory() as temp:
            args = SimpleNamespace(
                target=temp,
                project="demo",
                test_command=[],
                ci="none",
                no_hooks=True,
                no_agent=False,
                force=False,
                dry_run=False,
                source=str(KIT_ROOT),
                json=True,
            )
            with mock.patch(
                "sdd.bootstrap.verify_core",
                return_value=["broken core"],
            ):
                payload = bootstrap_module.init_repository(args)
        self.assertFalse(payload["ok"])
        self.assertIn("verify-core: broken core", payload["errors"])
        checks = {check["name"]: check for check in payload["checks"]}
        self.assertFalse(checks["verify-core"]["ok"])

    def test_init_failure_returns_a_nonzero_cli_exit_code(self):
        payload = {
            "ok": False,
            "kind": "init",
            "mode": "install",
            "target": ".",
            "project": None,
            "actions": [],
            "warnings": [],
            "preserved": [],
            "checks": [],
            "errors": ["verify-core: broken"],
            "dry_run": False,
            "next": None,
        }
        with mock.patch("sdd.cli.run_init", return_value=payload):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = cli_module.main(
                    ["init", "--target", ".", "--json"]
                )
        self.assertEqual(code, 1)
        self.assertFalse(json.loads(output.getvalue())["ok"])


if __name__ == "__main__":
    unittest.main()
