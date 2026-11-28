import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


KIT_ROOT = Path(__file__).resolve().parents[1]


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ExplorerTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def run_explorer(
        self,
        *args,
        cwd: Path | None = None,
        expect: int = 0,
    ) -> dict:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONPATH"] = str(KIT_ROOT)
        result = subprocess.run(
            [sys.executable, "-m", "sdd", "explorer", *args, "--json"],
            cwd=str(cwd or KIT_ROOT),
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
        payload = json.loads(result.stdout)
        payload["_stdout"] = result.stdout
        return payload

    def make_python_repo(self, name: str = "python-repo") -> Path:
        root = self.base / name
        write(root / "README.md", "# Python fixture\n")
        write(
            root / "pyproject.toml",
            "[project]\n"
            "name = 'fixture-service'\n"
            "dependencies = ['pytest>=8']\n"
            "[tool.pytest.ini_options]\n"
            "testpaths = ['tests']\n",
        )
        write(
            root / "src" / "main.py",
            "if __name__ == '__main__':\n    print('hello')\n",
        )
        write(root / "tests" / "test_main.py", "def test_ok():\n    assert True\n")
        return root

    def test_non_sdd_repo_reports_evidence_without_writing(self):
        root = self.make_python_repo()
        write(root / ".env", "SECRET_SENTINEL_30=do-not-leak\n")
        write(root / "node_modules" / "ignored.js", "throw new Error('no');\n")
        before = sorted(
            path.relative_to(root).as_posix()
            for path in root.rglob("*")
            if path.is_file()
        )

        payload = self.run_explorer("--repo", str(root))

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["kind"], "explorer")
        self.assertEqual(payload["schema_version"], 1)
        repo = payload["repos"][0]
        self.assertIsNone(repo["git"])
        self.assertEqual(repo["languages"].get("python"), 2)
        self.assertIn("python", [item["name"] for item in repo["stack"]])
        self.assertTrue(repo["tests"]["commands"])
        self.assertTrue(repo["tests"]["commands"][0]["evidence"])
        self.assertEqual(
            repo["entrypoints"][0]["path"],
            "src/main.py",
        )
        self.assertTrue(payload["sdd"]["readme"])
        codes = [risk["code"] for risk in payload["risks"]]
        self.assertIn("not_a_git_repo", codes)
        self.assertIn("secret_file_present", codes)
        self.assertIn("large_dir_skipped", codes)
        self.assertNotIn("SECRET_SENTINEL_30", json.dumps(payload))
        after = sorted(
            path.relative_to(root).as_posix()
            for path in root.rglob("*")
            if path.is_file()
        )
        self.assertEqual(before, after)

    def test_defaults_to_current_directory(self):
        root = self.make_python_repo()
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONPATH"] = str(KIT_ROOT)
        result = subprocess.run(
            [sys.executable, "-m", "sdd", "explorer", "--json"],
            cwd=str(root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["roots"][0]["path"], ".")
        self.assertIn("python", payload["summary"]["languages"])

    def test_sdd_repo_reports_specs_context_and_ci(self):
        root = self.base / "sdd-repo"
        write(
            root / "sdd" / "config.json",
            json.dumps(
                {
                    "project": "order",
                    "test_commands": ["python -m pytest -q"],
                }
            ),
        )
        write(
            root / "docs" / "specs" / "SPEC-ORDER-001" / "state.json",
            json.dumps(
                {
                    "spec_id": "SPEC-ORDER-001",
                    "title": "订单取消",
                    "state": "MERGED",
                    "updated_at": "2026-11-28T12:00:00+08:00",
                }
            ),
        )
        write(root / "docs" / "prd-index.md", "# PRD\n")
        write(root / "sdd" / "context" / "services.yaml", "services: []\n")
        write(root / "AGENTS.md", "# Agent\n")
        write(root / "README.md", "# Readme\n")
        write(
            root / ".github" / "workflows" / "tests.yml",
            "jobs:\n"
            "  test:\n"
            "    steps:\n"
            "      - run: python -m pytest -q\n",
        )

        payload = self.run_explorer("--repo", str(root))

        repo = payload["repos"][0]
        self.assertTrue(payload["sdd"]["initialized"])
        self.assertIn("SPEC-ORDER-001", payload["sdd"]["specs"])
        self.assertTrue(payload["sdd"]["prd_index"])
        self.assertIn(
            "sdd/context/services.yaml", payload["sdd"]["context_files"]
        )
        self.assertIn("AGENTS.md", payload["sdd"]["agents_md"])
        self.assertEqual(repo["docs"]["specs"][0]["state"], "MERGED")
        self.assertEqual(repo["docs"]["specs"][0]["title"], "订单取消")
        commands = [item["command"] for item in repo["tests"]["commands"]]
        self.assertIn("python -m pytest -q", commands)
        config_command = next(
            item
            for item in repo["tests"]["commands"]
            if item["command"] == "python -m pytest -q"
        )
        self.assertEqual(config_command["confidence"], "high")
        self.assertIn("sdd/config.json", config_command["evidence"])
        jobs = repo["ci"][0]["jobs"]
        self.assertTrue(any(job["runs_tests"] for job in jobs))

    def test_gitlab_and_jenkins_test_jobs(self):
        root = self.base / "ci-repo"
        write(root / "README.md", "# CI\n")
        write(
            root / ".gitlab-ci.yml",
            "stages:\n"
            "  - test\n"
            "test:\n"
            "  script:\n"
            "    - python -m pytest -q\n",
        )
        write(
            root / "Jenkinsfile",
            "pipeline { stages { stage('Test') { steps { sh 'pytest -q' } } } }\n",
        )

        payload = self.run_explorer("--repo", str(root))

        providers = {
            item["provider"]: item for item in payload["repos"][0]["ci"]
        }
        self.assertTrue(
            any(job["runs_tests"] for job in providers["gitlab-ci"]["jobs"])
        )
        self.assertTrue(
            any(job["runs_tests"] for job in providers["jenkins"]["jobs"])
        )

    def test_workspace_declares_and_shares_contracts(self):
        api = self.base / "order-api"
        web = self.base / "order-web"
        write(
            api / "package.json",
            json.dumps({"name": "order-api", "scripts": {"test": "jest"}}),
        )
        write(
            web / "package.json",
            json.dumps(
                {
                    "name": "order-web",
                    "scripts": {"test": "vitest run"},
                    "dependencies": {"order-api": "^1.0.0"},
                }
            ),
        )
        contract = "contracts/order.openapi.yaml"
        write(
            api / contract,
            "openapi: 3.0.3\ninfo:\n  title: Order\n",
        )
        write(
            web / contract,
            "openapi: 3.0.3\ninfo:\n  title: Order\n",
        )
        workspace = self.base / "workspace.json"
        write(
            workspace,
            json.dumps(
                {
                    "version": 1,
                    "repos": [
                        {
                            "id": "order-api",
                            "path": "order-api",
                            "role": "service",
                        },
                        {
                            "id": "order-web",
                            "path": "order-web",
                            "role": "frontend",
                            "depends_on": ["order-api"],
                        },
                    ],
                }
            ),
        )

        payload = self.run_explorer("--workspace", str(workspace))

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["summary"]["repos"], 2)
        relationships = {
            (item["from"], item["to"], item["source"])
            for item in payload["relationships"]
        }
        self.assertIn(
            ("order-web", "order-api", "declared"), relationships
        )
        self.assertIn(
            ("order-api", "order-web", "shared-contract"), relationships
        )
        self.assertIn(
            ("order-web", "order-api", "package-name"), relationships
        )
        contract_fact = payload["contracts"][0]
        self.assertEqual(contract_fact["path"], contract)
        self.assertEqual(contract_fact["repos"], ["order-api", "order-web"])
        self.assertEqual(
            contract_fact["evidence"],
            [
                "order-api/contracts/order.openapi.yaml",
                "order-web/contracts/order.openapi.yaml",
            ],
        )
        for item in payload["relationships"]:
            self.assertTrue(item["evidence"], item)

        repeated = self.run_explorer(
            "--repo", str(api), "--repo", str(web)
        )
        self.assertEqual(repeated["summary"]["repos"], 2)
        self.assertEqual(
            repeated["roots"][0]["role"], None
        )

        bad = self.base / "bad-workspace.json"
        write(
            bad,
            json.dumps(
                {
                    "version": 1,
                    "repos": [
                        {"id": "same", "path": "order-api"},
                        {"id": "same", "path": "order-web"},
                    ],
                }
            ),
        )
        rejected = self.run_explorer("--workspace", str(bad), expect=2)
        self.assertFalse(rejected["ok"])
        self.assertIn("重复的仓库 id", rejected["errors"][0])

        duplicate_path = self.base / "duplicate-path.json"
        write(
            duplicate_path,
            json.dumps(
                {
                    "version": 1,
                    "repos": [
                        {"id": "a", "path": "order-api"},
                        {"id": "b", "path": "order-api"},
                    ],
                }
            ),
        )
        rejected = self.run_explorer(
            "--workspace", str(duplicate_path), expect=2
        )
        self.assertIn("重复的仓库路径", rejected["errors"][0])

    def test_python_node_java_go_stack_fixtures(self):
        fixtures = {
            "python": (
                "pyproject.toml",
                "[project]\nname = 'p'\ndependencies = ['pytest']\n",
            ),
            "node": (
                "package.json",
                json.dumps(
                    {
                        "name": "n",
                        "scripts": {"test": "vitest run"},
                        "devDependencies": {"vitest": "^1.0.0"},
                    }
                ),
            ),
            "java": (
                "pom.xml",
                "<project><dependencies><dependency>"
                "<artifactId>junit-jupiter</artifactId>"
                "</dependency></dependencies></project>",
            ),
            "go": ("go.mod", "module example.com/order-api\n\ngo 1.22\n"),
        }
        for name, (manifest, text) in fixtures.items():
            root = self.base / f"{name}-repo"
            write(root / manifest, text)
            if name == "python":
                write(root / "tests" / "test_x.py", "def test_x(): pass\n")
            if name == "node":
                write(root / "src" / "index.ts", "console.log('x');\n")
                write(root / "tests" / "index.test.ts", "test('x', () => {});\n")
            if name == "java":
                write(
                    root
                    / "src"
                    / "main"
                    / "java"
                    / "demo"
                    / "Application.java",
                    "public class Application { public static void main(String[] a) {} }\n",
                )
                write(
                    root
                    / "src"
                    / "test"
                    / "java"
                    / "demo"
                    / "AppTest.java",
                    "class AppTest {}\n",
                )
            if name == "go":
                write(root / "cmd" / "app" / "main.go", "package main\nfunc main() {}\n")
                write(
                    root / "cmd" / "app" / "main_test.go",
                    "package main\n",
                )

            payload = self.run_explorer("--repo", str(root))
            repo = payload["repos"][0]
            self.assertIn(name, [item["name"] for item in repo["stack"]])
            self.assertTrue(repo["tests"]["commands"], name)
            for command in repo["tests"]["commands"]:
                self.assertTrue(command["evidence"], command)
                self.assertIn(command["confidence"], {"high", "medium", "low"})
            self.assertTrue(repo["tests"]["files"], name)

    def test_ignored_directories_gitignore_and_truncation(self):
        root = self.base / "git-repo"
        root.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        write(root / ".gitignore", "ignored/\n")
        write(root / "ignored" / "openapi.yaml", "openapi: 3.0.0\n")
        write(root / "node_modules" / "x.js", "x\n")
        write(root / "pyproject.toml", "[project]\nname = 'x'\n")
        write(root / "tests" / "test_x.py", "def test_x(): pass\n")

        payload = self.run_explorer(
            "--repo", str(root), "--max-files", "1"
        )

        self.assertTrue(payload["scan"]["truncated"])
        self.assertGreater(payload["scan"]["files_skipped"], 0)
        codes = [risk["code"] for risk in payload["risks"]]
        self.assertIn("scan_truncated", codes)
        self.assertIn("large_dir_skipped", codes)
        self.assertNotIn(
            "ignored/openapi.yaml",
            [item["path"] for item in payload["repos"][0]["contracts"]],
        )
        self.assertFalse(
            any(
                "ignored/" in path
                for path in payload["repos"][0]["tests"]["files"]
            )
        )

    def test_bad_manifest_and_encoding_only_warn(self):
        root = self.base / "bad-repo"
        write(root / "package.json", "{not valid json")
        (root / "pyproject.toml").write_bytes(b"\xff\xfe\x00bad")
        write(root / "README.md", "# Bad\n")

        payload = self.run_explorer("--repo", str(root))

        self.assertTrue(payload["ok"])
        self.assertTrue(payload["scan"]["warnings"])
        messages = " ".join(
            item["message"] for item in payload["scan"]["warnings"]
        )
        self.assertIn("JSON", messages)
        self.assertIn("UTF-8", messages)

    def test_deterministic_except_generated_at_and_alias(self):
        root = self.make_python_repo()
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONPATH"] = str(KIT_ROOT)
        outputs = []
        for command in ("explorer", "explore"):
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "sdd",
                    command,
                    "--repo",
                    str(root),
                    "--json",
                ],
                cwd=str(KIT_ROOT),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            payload.pop("generated_at")
            outputs.append(payload)
        self.assertEqual(outputs[0], outputs[1])

    def test_out_writes_only_requested_report(self):
        root = self.base / "sdd-repo"
        write(root / "sdd" / "config.json", json.dumps({"project": "x"}))
        write(
            root / "docs" / "specs" / "SPEC-X-001" / "state.json",
            json.dumps(
                {
                    "spec_id": "SPEC-X-001",
                    "state": "DRAFT",
                    "updated_at": "2026-11-28T12:00:00+08:00",
                }
            ),
        )
        write(root / "docs" / "specs" / "SPEC-X-001" / "events.jsonl", "{}\n")
        tracked = [
            root / "sdd" / "config.json",
            root / "docs" / "specs" / "SPEC-X-001" / "state.json",
            root / "docs" / "specs" / "SPEC-X-001" / "events.jsonl",
        ]
        before = {path: sha256(path) for path in tracked}
        before_files = sorted(
            path.relative_to(root).as_posix()
            for path in root.rglob("*")
            if path.is_file()
        )

        json_out = self.base / "report.json"
        payload = self.run_explorer(
            "--repo", str(root), "--out", str(json_out)
        )
        self.assertTrue(json_out.is_file())
        self.assertEqual(json.loads(json_out.read_text(encoding="utf-8"))["kind"], "explorer")
        self.assertEqual(before, {path: sha256(path) for path in tracked})
        self.assertEqual(
            before_files,
            sorted(
                path.relative_to(root).as_posix()
                for path in root.rglob("*")
                if path.is_file()
            ),
        )
        self.assertIn("summary", payload)

        md_out = self.base / "report.md"
        self.run_explorer("--repo", str(root), "--out", str(md_out))
        self.assertTrue(md_out.read_text(encoding="utf-8").startswith(
            "# SDD Explorer 事实地图"
        ))

    def test_rejects_home_filesystem_root_and_git_dir(self):
        home = Path.home()
        rejected = self.run_explorer("--repo", str(home), expect=2)
        self.assertFalse(rejected["ok"])
        self.assertIn("用户主目录", rejected["errors"][0])

        anchor = Path(Path.cwd().anchor)
        if anchor.exists():
            rejected = self.run_explorer("--repo", str(anchor), expect=2)
            self.assertFalse(rejected["ok"])

        root = self.base / "git-repo"
        root.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        rejected = self.run_explorer("--repo", str(root / ".git"), expect=2)
        self.assertIn("拒绝扫描 .git", rejected["errors"][0])

    def test_symlinks_are_not_followed(self):
        root = self.base / "symlink-repo"
        outside = self.base / "outside"
        write(outside / "contracts" / "openapi.yaml", "openapi: 3.0.0\n")
        write(root / "README.md", "# Symlink\n")
        try:
            (root / "contracts").mkdir(parents=True, exist_ok=True)
            os.symlink(
                outside / "contracts" / "openapi.yaml",
                root / "contracts" / "openapi.yaml",
            )
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation is not available")

        payload = self.run_explorer("--repo", str(root))

        self.assertNotIn(
            "contracts/openapi.yaml",
            [item["path"] for item in payload["repos"][0]["contracts"]],
        )

    def test_deep_reads_entry_and_contract_metadata(self):
        root = self.base / "deep-repo"
        write(
            root / "pyproject.toml",
            "[project]\nname = 'deep'\ndependencies = ['pytest']\n",
        )
        write(root / "src" / "main.py", "if __name__ == '__main__':\n    pass\n")
        write(
            root / "contracts" / "openapi.yaml",
            "openapi: 3.0.3\ninfo:\n  title: Deep\n",
        )

        shallow = self.run_explorer("--repo", str(root))
        deep = self.run_explorer("--repo", str(root), "--deep")

        shallow_contract = shallow["repos"][0]["contracts"][0]
        deep_contract = deep["repos"][0]["contracts"][0]
        self.assertNotIn("version", shallow_contract)
        self.assertEqual(deep_contract["version"], "3.0.3")
        deep_entry = deep["repos"][0]["entrypoints"][0]
        self.assertIn("python_main_guard", deep_entry["signals"])
        self.assertGreaterEqual(
            deep["scan"]["bytes_read"], shallow["scan"]["bytes_read"]
        )

    def test_include_exclude_and_depth(self):
        root = self.base / "filter-repo"
        write(root / "pyproject.toml", "[project]\nname = 'x'\n")
        write(root / "src" / "main.py", "print('x')\n")
        write(root / "tests" / "test_x.py", "def test_x(): pass\n")

        payload = self.run_explorer(
            "--repo",
            str(root),
            "--include",
            "src/**",
            "--include",
            "tests/**",
            "--exclude",
            "src/main.py",
            "--depth",
            "2",
        )

        repo = payload["repos"][0]
        self.assertEqual(repo["files"], 1)
        self.assertIn("tests/test_x.py", repo["tests"]["files"])
        self.assertNotIn(
            "src/main.py",
            [item["path"] for item in repo["entrypoints"]],
        )


if __name__ == "__main__":
    unittest.main()
