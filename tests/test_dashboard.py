import ast
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


KIT_ROOT = Path(__file__).resolve().parents[1]


class DashboardTestBase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        shutil.copytree(KIT_ROOT / "sdd", self.root / "sdd")
        shutil.copyfile(KIT_ROOT / "AGENTS.md", self.root / "AGENTS.md")
        (self.root / "docs" / "specs").mkdir(parents=True)
        (self.root / "tests").mkdir()
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=False)

    def tearDown(self):
        self.temp.cleanup()

    def run_cli(self, *args, expect=0):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "sdd",
                "--root",
                str(self.root),
                "--session-key",
                "dashboard-session",
                *args,
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
        return result

    def run_json(self, *args, expect=0):
        result = self.run_cli(*args, expect=expect)
        return json.loads(result.stdout)

    def write_spec(
        self,
        spec_id,
        state,
        title,
        *,
        risk="low",
        tasks=None,
        blocked_reason=None,
        updated_at="2026-11-28T12:00:00+08:00",
    ):
        tasks = tasks or []
        directory = self.root / "docs" / "specs" / spec_id
        directory.mkdir(parents=True, exist_ok=True)
        history = [
            {
                "state": "DRAFT",
                "at": "2026-11-28T10:00:00+08:00",
                "evidence": "created",
                "role": "planner",
            }
        ]
        if state != "DRAFT":
            history.append(
                {
                    "state": state,
                    "at": updated_at,
                    "evidence": "fixture transition",
                    "role": "planner",
                }
            )
        payload = {
            "spec_id": spec_id,
            "title": title,
            "work_item": f"WORK-{spec_id[-3:]}",
            "risk": risk,
            "risk_labels": [],
            "workflow": {"name": "l2-standard", "version": 1},
            "state": state,
            "created_at": "2026-11-28T10:00:00+08:00",
            "updated_at": updated_at,
            "history": history,
        }
        if blocked_reason is not None:
            payload["blocked_reason"] = blocked_reason
        (directory / "state.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (directory / "spec.md").write_text(
            f"# {title}\n\n## 1. 元数据\n\n| Spec ID | {spec_id} |\n",
            encoding="utf-8",
        )
        if tasks:
            rows = []
            for index, status in enumerate(tasks, 1):
                rows.append(
                    f"| T-{index:03d} | 任务 {index} | FR-001；AC-001-1 | "
                    f"None | P | 验收 {index} | `StatusTest#test_{index}` | "
                    f"`python -m unittest tests.test_status` | {status} | "
                    f"{'abc1234' if status == 'Done' else '—'} |"
                )
            (directory / "tasks.md").write_text(
                "# 任务清单\n\n"
                "| Task ID | 任务描述 | 关联FR/AC | 依赖Task | 并行标识 | "
                "验收标准 | 单元测试类/方法 | 单Task测试命令 | 状态 | Commit SHA |\n"
                "|---|---|---|---|---|---|---|---|---|---|\n"
                + "\n".join(rows)
                + "\n",
                encoding="utf-8",
            )
        return directory

    def mixed_fixture(self):
        self.write_spec("SPEC-ORDER-001", "DRAFT", "草稿订单")
        self.write_spec(
            "SPEC-ORDER-002",
            "IMPLEMENTING",
            "实现订单",
            tasks=["Todo"],
        )
        self.write_spec(
            "SPEC-ORDER-003",
            "VERIFYING",
            "验证订单",
            tasks=["Done", "Done"],
        )
        self.write_spec(
            "SPEC-ORDER-004",
            "PR_READY",
            "<script>alert('title')</script>",
            tasks=["Done"],
            risk="medium",
        )
        self.write_spec(
            "SPEC-ORDER-005",
            "BLOCKED",
            "阻塞订单",
            tasks=["Todo"],
            risk="high",
            blocked_reason="<script>alert('blocked')</script>",
        )
        self.write_spec(
            "SPEC-ORDER-006",
            "MERGED",
            "已合并订单",
            tasks=["Done"],
        )


class DashboardDataTests(DashboardTestBase):
    def test_json_groups_and_summary_match_existing_sources(self):
        # [AC-001-1]
        self.mixed_fixture()
        dashboard = self.run_json("dashboard", "--json")
        board = self.run_json("board", "--json")
        metrics = self.run_json("metrics", "--json")
        inbox = self.run_json("inbox", "--json")

        self.assertTrue(dashboard["ok"])
        self.assertEqual(dashboard["schema_version"], 1)
        self.assertEqual(dashboard["summary"]["specs"]["total"], 6)
        self.assertEqual(dashboard["summary"]["specs"]["active"], 4)
        self.assertEqual(dashboard["summary"]["specs"]["blocked"], 1)
        self.assertEqual(dashboard["summary"]["specs"]["merged"], 1)
        self.assertEqual(dashboard["groups"]["active"], [
            "SPEC-ORDER-001",
            "SPEC-ORDER-002",
            "SPEC-ORDER-003",
            "SPEC-ORDER-004",
        ])
        self.assertEqual(dashboard["groups"]["blocked"], ["SPEC-ORDER-005"])
        self.assertEqual(dashboard["groups"]["completed"], ["SPEC-ORDER-006"])

        board_done = sum(
            item["task_counts"]["done"] for item in board["specs"]
        )
        board_total = sum(
            item["task_counts"]["total"] for item in board["specs"]
        )
        self.assertEqual(dashboard["summary"]["tasks"]["done"], board_done)
        self.assertEqual(dashboard["summary"]["tasks"]["total"], board_total)
        self.assertEqual(
            dashboard["summary"]["inbox"]["waiting"],
            len(inbox["items"]),
        )
        self.assertEqual(
            dashboard["summary"]["audit"]["valid"],
            metrics["audit"]["valid"],
        )
        for key in ("pass", "warn", "block", "waived"):
            expected = sum(int(item.get(key, 0)) for item in metrics["check_stats"])
            self.assertEqual(dashboard["summary"]["gate_health"][key], expected)

        board_item = next(
            item for item in board["specs"] if item["spec"] == "SPEC-ORDER-004"
        )
        self.assertEqual(board_item["risk"], "medium")
        self.assertEqual(
            board_item["updated_at"],
            "2026-11-28T12:00:00+08:00",
        )

        second = self.run_json("dashboard", "--json")
        dashboard.pop("generated_at")
        second.pop("generated_at")
        self.assertEqual(dashboard, second)

    def test_empty_terminal_is_clear_and_has_no_ansi(self):
        # [AC-001-2]
        result = self.run_cli("dashboard", "--no-color")
        self.assertIn("Specs            0 total", result.stdout)
        self.assertIn("No Specs", result.stdout)
        self.assertIn("还没有 Spec", result.stdout)
        self.assertNotIn("\x1b[", result.stdout)

        piped = self.run_cli("dashboard")
        self.assertNotIn("\x1b[", piped.stdout)

    def test_since_is_forwarded_to_metrics(self):
        # [AC-001-3]
        metrics = {
            "ok": True,
            "kind": "metrics",
            "specs": [],
            "check_stats": [],
            "quality": {},
            "audit": {"valid": True, "errors": []},
            "aggregate": {},
        }
        with patch(
            "sdd.dashboard.Workspace.board",
            return_value={"ok": True, "kind": "board", "specs": []},
        ), patch(
            "sdd.dashboard.Workspace.metrics",
            return_value=metrics,
        ) as metrics_call, patch(
            "sdd.dashboard.Workspace.inbox",
            return_value={"ok": True, "kind": "inbox", "items": []},
        ):
            from sdd.dashboard import build_dashboard

            payload = build_dashboard(self.root, since="2026-11-01")
        metrics_call.assert_called_once_with("2026-11-01")
        self.assertEqual(payload["since"], "2026-11-01")

        invalid = self.run_cli(
            "dashboard",
            "--since",
            "not-a-date",
            "--json",
            expect=2,
        )
        self.assertIn("--since", invalid.stdout)

    def test_corrupt_spec_is_skipped_with_warning(self):
        # [AC-002-1]
        self.write_spec("SPEC-ORDER-001", "DRAFT", "正常草稿")
        self.write_spec("SPEC-ORDER-002", "MERGED", "已合并")
        broken = self.root / "docs" / "specs" / "SPEC-BROKEN-001"
        broken.mkdir()
        (broken / "state.json").write_text("{broken", encoding="utf-8")

        dashboard = self.run_json("dashboard", "--json")
        self.assertTrue(dashboard["ok"])
        self.assertEqual(dashboard["summary"]["specs"]["total"], 2)
        self.assertEqual(
            [item["spec"] for item in dashboard["specs"]],
            ["SPEC-ORDER-001", "SPEC-ORDER-002"],
        )
        self.assertTrue(
            any(
                warning.get("spec_dir") == "docs/specs/SPEC-BROKEN-001"
                for warning in dashboard["warnings"]
            )
        )
        self.assertTrue(dashboard["gate_health"]["available"])

    def test_dashboard_does_not_import_state_machine_rules(self):
        # [AC-002-2]
        source = (KIT_ROOT / "sdd" / "dashboard.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
            elif isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
        self.assertFalse(any("scripts" in name for name in imports))
        self.assertNotIn("parse_tasks", source)


class DashboardHtmlTests(DashboardTestBase):
    def test_html_is_offline_escaped_and_detail_links_exist(self):
        # [AC-003-1]
        self.mixed_fixture()
        self.run_cli("dashboard", "--html")
        out = self.root / ".sdd" / "runtime" / "dashboard" / "index.html"
        self.assertTrue(out.is_file())
        html = out.read_text(encoding="utf-8")

        for marker in (
            'id="active"',
            'id="blocked"',
            'id="inbox"',
            'id="completed"',
            'id="gates"',
            'id="quality"',
            'id="events"',
            'id="library"',
        ):
            self.assertIn(marker, html)
        self.assertIn("&lt;script&gt;", html)
        self.assertNotIn("<script>", html.lower())
        self.assertNotIn("<link", html.lower())
        self.assertNotIn("src=", html.lower())
        self.assertNotIn("http://", html.lower())
        self.assertNotIn("https://", html.lower())

        hrefs = re.findall(r'href="([^"]+)"', html)
        self.assertGreaterEqual(len(hrefs), 6)
        for href in hrefs:
            target = (out.parent / href).resolve()
            self.assertTrue(
                target.is_file(),
                msg=f"detail link points to missing file: {href}",
            )
            target.relative_to(self.root.resolve())

    def test_out_no_detail_and_open(self):
        # [AC-003-2]
        self.write_spec("SPEC-ORDER-001", "DRAFT", "订单")
        result = self.run_cli(
            "dashboard",
            "--html",
            "--out",
            ".sdd/runtime/share/board.html",
            "--no-detail",
        )
        out = self.root / ".sdd" / "runtime" / "share" / "board.html"
        html = out.read_text(encoding="utf-8")
        self.assertTrue(out.is_file())
        self.assertIn("Detail 0 page(s)", result.stdout)
        self.assertNotIn("href=", html)
        self.assertFalse((out.parent / "view").exists())

        from sdd.dashboard import run_dashboard

        with patch("sdd.dashboard.webbrowser.open") as opener:
            payload = run_dashboard(
                self.root,
                open_browser=True,
                no_detail=True,
            )
        opener.assert_called_once()
        self.assertTrue(opener.call_args.args[0].startswith("file:"))
        self.assertTrue(payload["html"]["opened"])

    def test_bad_output_paths_and_json_conflict(self):
        # [AC-003-3]
        self.write_spec("SPEC-ORDER-001", "DRAFT", "订单")
        outside = self.run_cli(
            "dashboard",
            "--html",
            "--out",
            "dashboard.html",
            expect=2,
        )
        self.assertIn(".sdd/runtime", outside.stderr)
        orphan = self.run_cli(
            "dashboard",
            "--out",
            ".sdd/runtime/share/board.html",
            expect=2,
        )
        self.assertIn("--out", orphan.stderr)
        conflict = self.run_cli(
            "dashboard",
            "--json",
            "--html",
            expect=2,
        )
        self.assertIn("--json", conflict.stdout)

    def test_custom_out_places_details_in_sibling_view(self):
        # [AC-003-4]
        self.write_spec("SPEC-ORDER-001", "DRAFT", "订单")
        self.run_cli(
            "dashboard",
            "--html",
            "--out",
            ".sdd/runtime/share/board.html",
        )
        fragment = self.root / ".sdd" / "runtime" / "share" / "view" / "SPEC-ORDER-001.html"
        self.assertTrue(fragment.is_file())
        html = (self.root / ".sdd" / "runtime" / "share" / "board.html").read_text(
            encoding="utf-8"
        )
        self.assertIn('href="view/SPEC-ORDER-001.html"', html)


class DashboardReadOnlyTests(DashboardTestBase):
    def test_dashboard_does_not_change_audit_artifacts(self):
        # [AC-004-1]
        self.mixed_fixture()
        targets = sorted(
            path
            for path in (self.root / "docs" / "specs").rglob("*")
            if path.is_file()
        )
        before = {
            path: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in targets
        }

        self.run_cli("dashboard", "--no-color")
        self.run_cli("dashboard", "--json")
        self.run_cli("dashboard", "--html", "--no-detail")

        after = {
            path: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in targets
        }
        self.assertEqual(before, after)


class DashboardReleaseMetadataTests(unittest.TestCase):
    def test_dashboard_release_metadata_and_docs(self):
        # [AC-004-2]
        version = (KIT_ROOT / "sdd" / "VERSION").read_text(encoding="utf-8").strip()
        manifest = json.loads(
            (KIT_ROOT / "sdd" / "manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["version"], version)
        self.assertIn("sdd/dashboard.py", manifest["files"])
        self.assertGreaterEqual(
            tuple(int(part) for part in version.split(".")),
            (0, 10, 0),
        )
        for name in ("README.md", "sdd/README.md", "docs/GUIDE.md"):
            text = (KIT_ROOT / name).read_text(encoding="utf-8")
            self.assertIn("sdd dashboard", text, msg=name)


if __name__ == "__main__":
    unittest.main()
