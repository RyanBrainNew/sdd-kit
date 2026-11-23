import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

try:
    from tests.test_sdd import SPEC_ID, SddFlowBase
except ImportError:  # pragma: no cover - unittest discover
    from test_sdd import SPEC_ID, SddFlowBase

from sdd.core import Workspace
from sdd.scripts import sdd as engine


class GitFlowBase(SddFlowBase):
    def git(self, *args, check=True):
        return subprocess.run(
            ["git", *args],
            cwd=self.root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=check,
        )

    def init_git(self):
        self.git("init", "-q")
        self.git("config", "user.email", "agent@example.invalid")
        self.git("config", "user.name", "SDD Agent")

    def commit(self, message, trailers, allow_empty=True):
        args = ["commit", "-m", message]
        for trailer in trailers:
            args.extend(["-m", trailer])
        if allow_empty:
            args.append("--allow-empty")
        self.git(*args)
        return self.git("rev-parse", "HEAD").stdout.strip()

    def json_command(self, *args, expect=0):
        result = self.run_sdd(*args, expect=expect)
        return json.loads(result.stdout)

    def prepared_implementation(self):
        self.new_spec()
        self.approve_valid_spec()
        self.complete_design()
        self.complete_tasks()
        self.run_sdd(
            "complete", "--spec", SPEC_ID, "--evidence", "开始实现"
        )


class CommitAuditTests(GitFlowBase):
    def setUp(self):
        super().setUp()
        self.prepared_implementation()
        self.init_git()
        self.git("add", "-A")
        self.commit(
            "%srdcloud-553377 chore(spec): baseline",
            ["Spec-Id: SPEC-ORDER-001"],
        )
        self.git("branch", "main")
        self.git("checkout", "-b", "feature")

    def test_early_bad_commit_is_found(self):
        """[AC-001-1] [AC-001-2] [AC-002-1] 中间坏 commit 仍被发现。"""
        bad_sha = ""
        for index in range(25):
            trailers = ["Spec-Id: SPEC-ORDER-001"]
            if index != 10:
                trailers.append("Task-Id: T-001")
            sha = self.commit(
                f"%srdcloud-553377 feat(core): change {index}", trailers
            )
            if index == 10:
                bad_sha = sha
        errors = engine.check_git(self.root, SPEC_ID, "IMPLEMENTING")
        joined = "\n".join(errors)
        self.assertIn("Task-Id", joined)
        self.assertIn(bad_sha[:7], joined)

    def test_docs_commit_with_task_id_blocks(self):
        """[AC-002-2] 文档 commit 带 Task-Id 时阻断。"""
        self.commit(
            "%srdcloud-553377 docs(spec): bad docs commit",
            ["Spec-Id: SPEC-ORDER-001", "Task-Id: T-001"],
        )
        errors = engine.check_git(self.root, SPEC_ID, "IMPLEMENTING")
        self.assertTrue(any("文档 Commit" in item or "docs" in item for item in errors))

    def test_missing_merge_base_reports_error(self):
        """[AC-001-3] 没有主干分支时明确报错。"""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self.git("init", "-q", str(root))
            subprocess.run(
                ["git", "-C", str(root), "config", "user.email", "a@b.c"],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(root), "config", "user.name", "a"],
                check=True,
            )
            (root / "README.md").write_text("x\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "README.md"], check=True)
            subprocess.run(
                ["git", "-C", str(root), "commit", "-m", "init"], check=True
            )
            subprocess.run(
                ["git", "-C", str(root), "branch", "-m", "trunk"], check=True
            )
            errors = engine.check_git(root, SPEC_ID, "IMPLEMENTING")
            self.assertTrue(any("merge-base" in item for item in errors))

    def test_merge_commit_is_skipped(self):
        """[AC-001-3] merge commit 不要求 trailer。"""
        self.git("checkout", "-b", "side")
        self.commit(
            "%srdcloud-553377 feat(core): side change",
            ["Spec-Id: SPEC-ORDER-001", "Task-Id: T-001"],
        )
        self.git("checkout", "feature")
        self.git("merge", "--no-ff", "side", "-m", "merge side")
        errors = engine.check_git(self.root, SPEC_ID, "IMPLEMENTING")
        self.assertEqual(errors, [])


class TraceTests(GitFlowBase):
    def setUp(self):
        super().setUp()
        self.prepared_implementation()
        self.write(
            "tests/test_status.py",
            """import unittest


class StatusTest(unittest.TestCase):
    def test_cancel_pending_order(self):
        # [AC-001-1]
        self.assertTrue(True)
""",
        )
        self.run_sdd(
            "change", "--spec", SPEC_ID, "--reason", "trace verification"
        )
        self.write(
            "docs/specs/SPEC-ORDER-001/verification-evidence.jsonl",
            json.dumps(
                {
                    "schema": 2,
                    "run_id": "trace-run",
                    "spec": SPEC_ID,
                    "task": "T-001",
                    "command": "python -m unittest tests.test_status",
                    "cwd": self.root.as_posix(),
                    "started_at": "2026-11-23T10:00:00+08:00",
                    "finished_at": "2026-11-23T10:00:01+08:00",
                    "exit_code": 0,
                    "timed_out": False,
                    "duration_ms": 1000,
                    "output_sha256": "a" * 64,
                    "artifact_hashes": {},
                },
                ensure_ascii=False,
            )
            + "\n",
        )
        self.init_git()
        self.git("add", "-A")
        self.commit(
            "%srdcloud-553377 chore(spec): baseline",
            ["Spec-Id: SPEC-ORDER-001"],
        )
        self.git("branch", "main")
        self.git("checkout", "-b", "feature")
        self.head = self.commit(
            "%srdcloud-553377 feat(core): implement cancel",
            ["Spec-Id: SPEC-ORDER-001", "Task-Id: T-001"],
        )

    def assert_complete(self, payload):
        self.assertTrue(payload["ok"], payload.get("missing"))
        self.assertEqual(payload["schema"], 1)
        self.assertEqual(payload["spec"], SPEC_ID)
        self.assertEqual(payload["task"], "T-001")
        self.assertIn("AC-001-1", payload["acs"])
        self.assertEqual(payload["feat"], "FEAT-001")
        self.assertEqual(payload["work_item"], "srdcloud-553377")
        self.assertTrue(payload["prd"]["registered"])
        self.assertTrue(payload["approval"]["digest_bound"])
        self.assertTrue(payload["commits"])
        self.assertTrue(payload["evidence"]["records"])
        self.assertEqual(payload["missing"], [])

    def test_trace_by_test_ac_and_commit(self):
        """[AC-003-1] [AC-003-2] [AC-003-3] trace 三入口输出完整链路。"""
        by_test = self.json_command(
            "trace",
            "--test",
            "tests.test_status.StatusTest#test_cancel_pending_order",
            "--json",
        )
        self.assert_complete(by_test)
        by_ac = self.json_command(
            "trace", "--ac", "AC-001-1", "--json"
        )
        self.assert_complete(by_ac)
        by_commit = self.json_command(
            "trace", "--commit", self.head, "--json"
        )
        self.assert_complete(by_commit)

    def test_trace_reports_missing_link(self):
        """[AC-003-4] 断链输出 missing。"""
        payload = self.json_command(
            "trace", "--ac", "AC-999-1", "--json", expect=1
        )
        self.assertFalse(payload["ok"])
        self.assertTrue(payload["missing"])
        self.assertIn("AC-999-1", json.dumps(payload["missing"]))

    def test_trace_is_read_only(self):
        """[AC-003-5] trace 不修改任何工件。"""
        paths = [
            self.root / "docs/specs/SPEC-ORDER-001/state.json",
            self.root / "docs/specs/SPEC-ORDER-001/events.jsonl",
            self.root / "docs/specs/SPEC-ORDER-001/change-set.md",
        ]
        before = {
            path: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in paths
            if path.is_file()
        }
        self.json_command("trace", "--ac", "AC-001-1", "--json")
        after = {
            path: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in paths
            if path.is_file()
        }
        self.assertEqual(before, after)


class PrdIndexPlacementTests(GitFlowBase):
    def test_new_spec_row_goes_into_main_table(self):
        """[AC-004-2] 新 Spec 行必须落在主表而不是 FEAT 映射后。"""
        text = (
            "# PRD 追溯索引\n\n"
            "- source: workitem\n"
            "- updated: 2026-11-23\n\n"
            "| 工作项 ID | PRD 链接/路径 | PRD 版本 | FEAT | Spec ID | 摘要 | 澄清标记 |\n"
            "| --- | --- | --- | --- | --- | --- | --- |\n"
            "| WORK-1 | N/A | current | FEAT-001 | SPEC-REQ-001 | one | 0 |\n\n"
            "## FEAT 映射\n\n"
            "| FEAT | 工作项 ID | Spec ID | FR | AC |\n"
            "| --- | --- | --- | --- | --- |\n"
        )
        self.write("docs/prd-index.md", text)
        config = {
            "prd_index": "docs/prd-index.md",
            "prd_mode": "workitem",
            "spec_root": "docs/specs",
        }
        engine.ensure_prd_index(
            self.root,
            config,
            "SPEC-REQ-002",
            "WORK-2",
            "two",
            "https://example.invalid/2",
            feat_id="FEAT-002",
        )
        updated = (self.root / "docs/prd-index.md").read_text(encoding="utf-8")
        self.assertLess(
            updated.index("SPEC-REQ-002"),
            updated.index("## FEAT 映射"),
        )

