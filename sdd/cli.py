from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from . import __version__
from .agents import sync_agents, verify_agents
from .bootstrap import add_init_arguments, run_init
from .core import (
    SddCommandError,
    Workspace,
    verify_core,
    write_manifest,
)
from .dashboard import run_dashboard
from .scripts import sdd as engine
from .view import render_view


def _print_json(payload: Any) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _print_human(payload: dict[str, Any]) -> None:
    if payload.get("kind") == "init":
        if payload.get("ok"):
            print(
                f"[sdd] init {payload.get('mode')}: {payload.get('target')} "
                f"(project {payload.get('project')})"
            )
            for action in payload.get("actions", []):
                suffix = ""
                if action.get("files"):
                    suffix = f" ({action['files']} files)"
                print(
                    f"[sdd] {action.get('action')}: "
                    f"{action.get('path')}{suffix}"
                )
            for item in payload.get("preserved", []):
                print(f"[sdd] kept existing {item}")
            for item in payload.get("warnings", []):
                print(f"[sdd] warning: {item}")
            for check in payload.get("checks", []):
                if check.get("skipped"):
                    print(f"[sdd] {check.get('name')}: skipped")
                elif check.get("ok"):
                    print(f"[sdd] {check.get('name')}: passed")
                else:
                    print(f"[sdd] {check.get('name')}: failed")
            next_action = payload.get("next") or {}
            if next_action.get("command"):
                print(f"[sdd] next: {next_action['command']}")
        for error in payload.get("errors", []):
            print(f"[sdd] {error}", file=sys.stderr)
        return
    if payload.get("ok") is False:
        for error in payload.get("errors", []):
            if isinstance(error, dict):
                print(
                    f"[sdd] {error.get('path', '$')}: {error.get('message', '')}",
                    file=sys.stderr,
                )
            else:
                print(f"[sdd] {error}", file=sys.stderr)
        return
    if payload.get("skipped"):
        print("[sdd] no specs found; skip artifact check")
        return
    if payload.get("kind") == "board":
        specs = payload.get("specs", [])
        if not specs:
            print("[sdd] no specs found")
            return
        if payload.get("current_spec"):
            print(f"[sdd] current session: {payload['current_spec']}")
        for item in specs:
            counts = item.get("task_counts", {})
            next_action = item.get("next", {})
            marker = "*" if item.get("current") else " "
            print(
                f"{marker} {item.get('spec')}  [{item.get('state')}]  "
                f"flow={(item.get('workflow') or {}).get('name', '-')}  "
                f"next={next_action.get('action')}  "
                f"tasks={counts.get('done', 0)}/{counts.get('total', 0)} done"
            )
            for task in item.get("tasks", []):
                print(
                    f"  {task.get('id')}  [{task.get('status')}]  "
                    f"{task.get('description', '')}"
                )
            if not item.get("tasks"):
                print("  (no tasks yet)")
        return
    if payload.get("kind") == "events":
        for event in payload.get("events", []):
            print(
                f"{event.get('seq')}  {event.get('at')}  "
                f"{event.get('event')}  "
                f"{event.get('from_state')} -> {event.get('to_state')}  "
                f"{event.get('evidence', '')}"
            )
        return
    if payload.get("kind") == "view":
        print(f"[sdd] view written: {payload.get('out')}")
        print(f"[sdd] bytes: {payload.get('bytes')}")
        return
    if payload.get("kind") == "dashboard":
        print(payload.get("terminal", ""))
        return
    if payload.get("kind") == "inbox":
        items = payload.get("items", [])
        if not items:
            print("[sdd] no human actions waiting")
            return
        for item in items:
            print(
                f"{item.get('spec')}  [{item.get('state')}]  "
                f"{item.get('action')}  priority={item.get('priority')}  "
                f"{item.get('reason')}"
            )
            if item.get("command"):
                print(f"  {item['command']}")
        return
    if payload.get("kind") == "metrics":
        for item in payload.get("specs", []):
            lead = item.get("lead_time_hours")
            print(
                f"{item.get('spec')}  [{item.get('state')}]  "
                f"lead_time={lead if lead is not None else 'running'}h  "
                f"reworks={item.get('reworks', 0)}  "
                f"human={item.get('human_interventions', 0)}  "
                f"gate_failures={item.get('gate_failures', 0)}"
            )
        aggregate = payload.get("aggregate", {})
        print(
            f"[sdd] specs={aggregate.get('specs', 0)}  "
            f"median_lead_time={aggregate.get('median_lead_time_hours')}h  "
            f"median_reworks={aggregate.get('median_reworks', 0)}"
        )
        quality = payload.get("quality", {})
        print(
            f"[sdd] waiver_rate={quality.get('waiver_rate', 0)}  "
            f"gate_first_pass_rate={quality.get('gate_first_pass_rate')}  "
            f"escaped_defects={quality.get('escaped_defects', 0)}  "
            f"reopen_rate={quality.get('reopen_rate', 0)}  "
            f"audit_valid={payload.get('audit', {}).get('valid')}"
        )
        return
    if payload.get("kind") == "rewind":
        print(
            f"[sdd] {payload.get('spec')} rewind "
            f"{payload.get('from')} -> {payload.get('to')}"
        )
        print(
            f"[sdd] archived={len(payload.get('archived', []))}  "
            f"invalidated={','.join(payload.get('invalidated_gates', []))}"
        )
        if payload.get("reopened_tasks"):
            print(f"[sdd] reopened={','.join(payload['reopened_tasks'])}")
        return
    if payload.get("kind") == "waiver":
        print(
            f"[sdd] {payload.get('spec')} waiver "
            f"{payload.get('check')} on {payload.get('gate')} "
            f"until {payload.get('expires_at')}"
        )
        return
    if payload.get("kind") == "manifest":
        print(
            f"[sdd] wrote sdd/manifest.json "
            f"(version {payload.get('version')}, {len(payload.get('files', {}))} files)"
        )
        return
    if payload.get("kind") == "index":
        print(f"[sdd] {payload.get('spec')} index synced: {payload.get('message')}")
        return
    if payload.get("kind") == "change":
        print(
            f"[sdd] {payload.get('spec')} change "
            f"{payload.get('change_id')} status={payload.get('status')}"
        )
        return
    if payload.get("kind") == "impact":
        print(f"[sdd] {payload.get('spec')} impact")
        print(
            "  FEAT=" + (", ".join(payload.get("feat_ids") or []) or "-")
            + "  FR=" + (", ".join(payload.get("fr_ids") or []) or "-")
            + "  AC=" + str(len(payload.get("ac_ids") or []))
        )
        print(
            "  approval_required="
            + str(payload.get("approval_required")).lower()
        )
        if payload.get("missing"):
            print("  missing=" + "; ".join(payload["missing"]))
        return
    if payload.get("kind") == "reapprove":
        print(
            f"[sdd] {payload.get('spec')} reapproved; "
            f"changes={', '.join(payload.get('approved_change_ids') or []) or '-'}"
        )
        return
    if payload.get("kind") == "trace":
        entry = payload.get("entry") or {}
        print(
            f"[sdd] trace {entry.get('type')}={entry.get('value')} "
            f"ok={str(payload.get('ok')).lower()}"
        )
        for item in payload.get("chain", []):
            print(f"  {item.get('link')}: {item.get('value')}")
        for item in payload.get("missing", []):
            print(f"  missing {item.get('link')}: {item.get('detail')}")
        return
    if payload.get("kind") == "verify":
        output = str(payload.get("stdout") or "").strip()
        if output:
            print(output)
        return
    if payload.get("kind") == "sync_agent":
        if payload.get("changed"):
            print("[sdd] updated the SDD managed block in AGENTS.md")
        else:
            print("[sdd] AGENTS.md managed block already up to date")
        return
    if payload.get("kind") == "workflow_validate":
        if payload.get("ok"):
            print(
                f"[sdd] {payload.get('name')}@{payload.get('version')} "
                f"digest={payload.get('digest')}"
            )
        return
    if payload.get("kind") in {"verify_core", "verify_agent"}:
        if payload.get("ok"):
            print(f"[sdd] {payload['kind']} passed")
        else:
            for error in payload.get("errors", []):
                print(f"[sdd] {error}", file=sys.stderr)
        return
    if payload.get("kind") == "workflow_validate":
        if payload.get("ok"):
            print(
                f"[sdd] workflow {payload.get('name')}@"
                f"{payload.get('version')} is valid"
            )
        else:
            for error in payload.get("errors", []):
                print(f"[sdd] {error}", file=sys.stderr)
        return
    if payload.get("kind") == "waiver":
        waiver = payload.get("waiver", {})
        print(
            f"[sdd] {payload.get('spec')} waiver {waiver.get('id')} "
            f"created for {waiver.get('check_id')} until "
            f"{waiver.get('expires_at')}"
        )
        return
    spec = payload.get("spec") or payload.get("spec_id") or "-"
    state = payload.get("state") or payload.get("next", {}).get("state") or "-"
    action = payload.get("next", {}).get("action") or payload.get("action") or "-"
    print(f"Spec:   {spec}")
    print(f"State:  {state}")
    print(f"Next:   {action}")
    if payload.get("step_id"):
        print(f"Step:   {payload['step_id']}")
    if payload.get("kind"):
        print(f"Kind:   {payload['kind']}")
    if payload.get("decision_required"):
        print(f"Question: {payload.get('question', '')}")
    if payload.get("next", {}).get("task"):
        print(f"Task:   {payload['next']['task']}")
    checkpoint = payload.get("human_checkpoint", {})
    if checkpoint.get("required"):
        print(f"Human:  {checkpoint.get('type')} -> {checkpoint.get('command')}")


def _workspace(args: argparse.Namespace) -> Workspace:
    root = args.root or Path.cwd()
    return Workspace(root, session_key=args.session_key)


def _emit(args: argparse.Namespace, payload: dict[str, Any]) -> None:
    if getattr(args, "json", False):
        _print_json(
            {
                key: value
                for key, value in payload.items()
                if key != "terminal"
            }
        )
    else:
        _print_human(payload)


def _read_content(args: argparse.Namespace) -> str:
    if args.file and args.content:
        raise ValueError("use either --file or --content, not both")
    if args.file:
        return Path(args.file).read_text(encoding="utf-8")
    if args.content is not None:
        return args.content
    raise ValueError("submit requires --file or --content")


def _require_human(args: argparse.Namespace) -> None:
    if not getattr(args, "human", False):
        raise ValueError("this command is human-only; add --human to confirm")


def _workflow_error_path(message: str) -> str:
    match = re.search(
        r"的 (\$[^\s]+|[A-Za-z0-9_]+(?:\[[0-9]+\])?(?:\.[A-Za-z0-9_]+)*) ",
        message,
    )
    return match.group(1) if match else "$"


def _workflow_validate(file_name: str) -> dict[str, Any]:
    path = Path(file_name)
    if not path.is_file():
        return {
            "ok": False,
            "kind": "workflow_validate",
            "errors": [
                {"path": str(path), "message": f"文件不存在：{file_name}"}
            ],
        }
    try:
        preset = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "ok": False,
            "kind": "workflow_validate",
            "errors": [
                {"path": str(path), "message": f"JSON 解析失败：{exc}"}
            ],
        }
    source = path.name
    errors = engine.validate_workflow_preset(preset, source)
    if isinstance(preset, dict) and str(preset.get("name") or "") != path.stem:
        errors.append(
            f"{source} 的 name 必须与文件名一致（期望 {path.stem}）"
        )
    payload: dict[str, Any] = {
        "ok": not errors,
        "kind": "workflow_validate",
        "name": preset.get("name") if isinstance(preset, dict) else None,
        "version": preset.get("version") if isinstance(preset, dict) else None,
        "schema": preset.get("schema") if isinstance(preset, dict) else None,
    }
    if isinstance(preset, dict):
        payload["digest"] = engine.workflow_digest(preset)
    if errors:
        payload["errors"] = [
            {
                "path": _workflow_error_path(message),
                "message": message,
            }
            for message in errors
        ]
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sdd",
        description="CLI-first SDD workflow. MCP is optional.",
    )
    parser.add_argument("--root", help="repository root; default: current directory")
    parser.add_argument(
        "--session-key",
        help="stable session identifier; otherwise detect from host environment",
    )
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init", help="install or repair the SDD workspace")
    add_init_arguments(p)
    p.set_defaults(func=run_init)

    p = sub.add_parser("resume", help="resume the current session-bound work")
    p.add_argument("--spec", help="explicitly select a Spec")
    p.add_argument("--max-chars", type=int, default=12000)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=lambda a, w: w.session(a.spec, a.max_chars))

    p = sub.add_parser("start-work", help="start or resume one work item")
    p.add_argument("--work-item", required=True)
    p.add_argument("--issue-url")
    p.add_argument("--title")
    p.add_argument("--description")
    p.add_argument("--domain", default="REQ")
    p.add_argument(
        "--workflow",
        default=None,
        help="workflow preset name; default: sdd/config.json workflow",
    )
    p.add_argument("--risk", default="low", choices=["low", "medium", "high"])
    p.add_argument("--risk-label", action="append", default=[])
    p.add_argument(
        "--product-type",
        default="传统产品",
        choices=["传统产品", "AI辅助·L2", "AI增强·L3", "AI原生·L4"],
    )
    p.add_argument("--json", action="store_true")
    p.set_defaults(
        func=lambda a, w: w.start_work(
            a.work_item,
            issue_url=a.issue_url,
            title=a.title,
            description=a.description,
            domain=a.domain,
            risk=a.risk,
            risk_labels=a.risk_label,
            product_type=a.product_type,
            workflow=a.workflow,
        )
    )

    p = sub.add_parser("submit", help="submit the current stage artifact")
    p.add_argument(
        "--artifact",
        required=True,
        choices=[
            "spec.md",
            "design.md",
            "tasks.md",
            "verification.md",
            "context.md",
            "unknowns.md",
        ],
    )
    p.add_argument("--file")
    p.add_argument("--content")
    p.add_argument("--spec")
    p.add_argument("--no-run-commands", action="store_true")
    p.add_argument("--json", action="store_true")
    p.set_defaults(
        func=lambda a, w: w.submit_artifact(
            a.spec or w._resolve_current_spec(),
            a.artifact,
            _read_content(a),
            run_commands=not a.no_run_commands,
        )
    )

    p = sub.add_parser("submit-task", help="start and complete one implementation task")
    p.add_argument("--task", required=True)
    p.add_argument("--evidence", required=True)
    p.add_argument("--commit")
    p.add_argument("--spec")
    p.add_argument("--json", action="store_true")
    p.set_defaults(
        func=lambda a, w: w.submit_task(
            a.spec or w._resolve_current_spec(),
            a.task,
            a.evidence,
            a.commit,
        )
    )

    p = sub.add_parser("current", help="show the session pointer")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=lambda a, w: w.current())

    p = sub.add_parser("status", help="show current state")
    p.add_argument("--spec")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=lambda a, w: w.status(a.spec or w._resolve_current_spec()))

    p = sub.add_parser("next", help="show the exact next action")
    p.add_argument("--spec")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=lambda a, w: w._agent_next(a.spec or w._resolve_current_spec()))

    p = sub.add_parser("board", help="show specs and task statuses")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=lambda a, w: w.board())

    p = sub.add_parser("inbox", help="show work waiting for a human")
    p.add_argument("--stale-days", type=int)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=lambda a, w: w.inbox(a.stale_days))

    p = sub.add_parser("metrics", help="show lead time, rework and gate metrics")
    p.add_argument("--since", help="ISO date/datetime; default: all history")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=lambda a, w: w.metrics(a.since))

    p = sub.add_parser("events", help="show the append-only audit events")
    p.add_argument("--spec")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=lambda a, w: w.events(a.spec))

    p = sub.add_parser("view", help="render a read-only single-file HTML view")
    p.add_argument("--spec", required=True)
    p.add_argument("--out", help="output HTML path; default .sdd/runtime/view/<spec>.html")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=lambda a, w: render_view(w.root, a.spec, a.out))

    p = sub.add_parser("dashboard", help="show the read-only cross-Spec dashboard")
    p.add_argument("--json", action="store_true")
    p.add_argument("--html", action="store_true")
    p.add_argument("--out", help="HTML path under .sdd/runtime/")
    p.add_argument("--open", dest="open_browser", action="store_true")
    p.add_argument("--since", help="ISO date/datetime passed to metrics")
    p.add_argument("--no-color", action="store_true")
    p.add_argument("--no-detail", action="store_true")
    p.set_defaults(
        func=lambda a, w: run_dashboard(
            w.root,
            since=a.since,
            json_output=a.json,
            html_output=a.html,
            out=a.out,
            open_browser=a.open_browser,
            no_color=a.no_color,
            no_detail=a.no_detail,
        )
    )

    p = sub.add_parser("check", help="validate artifacts")
    p.add_argument("--spec")
    p.add_argument("--all", action="store_true")
    p.add_argument(
        "--stage",
        default="auto",
        choices=["auto", "spec", "design", "tasks", "verify", "ci"],
    )
    p.add_argument("--check-git", action="store_true")
    p.add_argument("--json", action="store_true")
    p.set_defaults(
        func=lambda a, w: w.check(
            a.spec,
            stage=a.stage,
            check_git=a.check_git,
            all_specs=a.all,
        )
    )

    p = sub.add_parser("index", help="sync FEAT mapping rows into docs/prd-index.md")
    p.add_argument("--spec")
    p.add_argument("--json", action="store_true")
    p.set_defaults(
        func=lambda a, w: w.index(a.spec or w._resolve_current_spec())
    )

    p = sub.add_parser("verify", help="run test commands and record evidence")
    p.add_argument("--spec")
    p.add_argument("--command", action="append", default=[])
    p.add_argument("--json", action="store_true")
    p.set_defaults(
        func=lambda a, w: _verify_payload(
            w,
            a.spec or w._resolve_current_spec(),
            a.command or [],
        )
    )

    p = sub.add_parser("approve", help="human approval: DRAFT -> SPEC_READY")
    p.add_argument("--spec")
    p.add_argument("--evidence", required=True)
    p.add_argument("--approver", help="approver identity, default: git config user")
    p.add_argument("--human", action="store_true")
    p.add_argument("--json", action="store_true")
    p.set_defaults(
        func=lambda a, w: (
            _require_human(a),
            w.approve(a.spec, a.evidence, a.approver),
        )[1]
    )

    p = sub.add_parser(
        "reapprove",
        help="human-only re-approval after the approved Spec changes",
    )
    p.add_argument("--spec")
    p.add_argument("--reason", required=True)
    p.add_argument("--evidence", required=True)
    p.add_argument("--approver")
    p.add_argument("--human", action="store_true")
    p.add_argument("--json", action="store_true")
    p.set_defaults(
        func=lambda a, w: w.reapprove(
            a.spec,
            a.reason,
            a.evidence,
            approver=a.approver,
            human=a.human,
        )
    )

    p = sub.add_parser(
        "impact",
        help="read-only FEAT/FR/AC/Task/test/code impact view",
    )
    p.add_argument("--spec")
    p.add_argument("--json", action="store_true")
    p.set_defaults(
        func=lambda a, w: w.impact(a.spec or w._resolve_current_spec())
    )

    p = sub.add_parser(
        "change",
        help="record a change-set before code changes",
    )
    p.add_argument("--spec")
    p.add_argument("--reason", required=True)
    p.add_argument("--docs-only", action="store_true")
    p.add_argument("--risk", choices=["low", "medium", "high"])
    p.add_argument("--rollback")
    p.add_argument("--json", action="store_true")
    p.set_defaults(
        func=lambda a, w: w.change(
            a.spec or w._resolve_current_spec(),
            a.reason,
            docs_only=a.docs_only,
            risk=a.risk,
            rollback=a.rollback,
        )
    )

    p = sub.add_parser(
        "trace",
        help="read-only trace by test, AC or commit",
    )
    trace_group = p.add_mutually_exclusive_group(required=True)
    trace_group.add_argument("--test")
    trace_group.add_argument("--ac")
    trace_group.add_argument("--commit")
    p.add_argument("--json", action="store_true")
    p.set_defaults(
        func=lambda a, w: w.trace(
            "test" if a.test else "ac" if a.ac else "commit",
            a.test or a.ac or a.commit,
        )
    )

    p = sub.add_parser("waive", help="human-only Gate check waiver")
    p.add_argument("--spec")
    p.add_argument("--check", required=True)
    p.add_argument("--scope", required=True)
    p.add_argument("--reason", required=True)
    p.add_argument("--expires-at", "--expires", dest="expires_at", required=True)
    p.add_argument("--evidence", required=True)
    p.add_argument("--approver")
    p.add_argument("--human", action="store_true")
    p.add_argument("--json", action="store_true")
    p.set_defaults(
        func=lambda a, w: w.waive(
            a.spec or w._resolve_current_spec(),
            a.check,
            a.scope,
            a.reason,
            a.expires_at,
            a.evidence,
            approver=a.approver,
            human=a.human,
        )
    )

    p = sub.add_parser("merge", help="human merge: PR_READY -> MERGED")
    p.add_argument("--spec")
    p.add_argument("--evidence", required=True)
    p.add_argument("--approver", help="approver identity, default: git config user")
    p.add_argument("--human", action="store_true")
    p.add_argument("--json", action="store_true")
    p.set_defaults(
        func=lambda a, w: (
            _require_human(a),
            w.merge(a.spec, a.evidence, a.approver),
        )[1]
    )

    p = sub.add_parser("unblock", help="resume after a human answer")
    p.add_argument("--spec")
    p.add_argument("--evidence", default="")
    p.add_argument("--approver", help="approver identity, default: git config user")
    p.add_argument("--human", action="store_true")
    p.add_argument("--json", action="store_true")
    p.set_defaults(
        func=lambda a, w: (
            _require_human(a),
            w.unblock(a.spec, a.evidence, a.approver),
        )[1]
    )

    p = sub.add_parser("rewind", help="human rewind to an earlier SDD stage")
    p.add_argument("--spec")
    p.add_argument("--to", required=True, help="target stage, e.g. VERIFYING")
    p.add_argument("--reason", required=True)
    p.add_argument("--approver", help="approver identity, default: git config user")
    p.add_argument("--force", action="store_true")
    p.add_argument("--reopen-task")
    p.add_argument("--reset-tasks", action="store_true")
    p.add_argument("--human", action="store_true")
    p.add_argument("--json", action="store_true")
    p.set_defaults(
        func=lambda a, w: (
            _require_human(a),
            w.rewind(
                a.spec or w._resolve_current_spec(),
                a.to,
                a.reason,
                approver=a.approver,
                force=a.force,
                reopen_task=a.reopen_task,
                reset_tasks=a.reset_tasks,
            ),
        )[1]
    )

    p = sub.add_parser(
        "upgrade-workflow",
        help="human upgrade to a fixed workflow preset version",
    )
    p.add_argument("--spec")
    p.add_argument("--to", required=True, help="target preset, e.g. l2-standard@2")
    p.add_argument("--reason", required=True)
    p.add_argument("--approver", help="approver identity, default: git config user")
    p.add_argument("--allow-downgrade", action="store_true")
    p.add_argument("--design-change")
    p.add_argument("--human", action="store_true")
    p.add_argument("--json", action="store_true")
    p.set_defaults(
        func=lambda a, w: (
            _require_human(a),
            w.upgrade_workflow(
                a.spec or w._resolve_current_spec(),
                a.to,
                a.reason,
                approver=a.approver,
                allow_downgrade=a.allow_downgrade,
                design_change=a.design_change,
            ),
        )[1]
    )

    p = sub.add_parser("complete", help="low-level completion compatibility")
    p.add_argument("--spec")
    p.add_argument("--task")
    p.add_argument("--evidence", required=True)
    p.add_argument("--commit")
    p.add_argument("--approver", help="approver identity for a manual gate")
    p.add_argument("--human", action="store_true")
    p.add_argument("--json", action="store_true")
    p.set_defaults(
        func=lambda a, w: w.complete(
            a.spec or w._resolve_current_spec(),
            a.evidence,
            task=a.task,
            commit=a.commit,
            human=a.human,
            approver=a.approver,
        )
    )

    p = sub.add_parser("report", help="write PR_BODY.md")
    p.add_argument("--spec")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=lambda a, w: w.report(a.spec or w._resolve_current_spec()))

    p = sub.add_parser("pr", help="record a PR URL")
    p.add_argument("--spec")
    p.add_argument("--url")
    p.add_argument("--json", action="store_true")
    p.set_defaults(
        func=lambda a, w: w.record_pr(
            a.spec or w._resolve_current_spec(), a.url
        )
    )

    p = sub.add_parser("context", help="read service cards, contracts and ADRs")
    p.add_argument("--spec")
    p.add_argument("--max-chars", type=int, default=40000)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=lambda a, w: w.context(a.spec, a.max_chars))

    p = sub.add_parser("list-specs", help="list active specs")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=lambda a, w: {"specs": w.list_specs()})

    p = sub.add_parser("sync-agent", help="merge the managed SDD block into AGENTS.md")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=lambda a, w: sync_agents(w.root))

    p = sub.add_parser("verify-agent", help="verify the AGENTS.md managed block")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=lambda a, w: _verify_agent_payload(w.root))

    p = sub.add_parser("manifest", help="write sdd/manifest.json")
    p.add_argument("--write", action="store_true", required=True)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=lambda a, w: write_manifest(w.root))

    p = sub.add_parser("verify-core", help="verify protected core hashes")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=lambda a, w: _verify_core_payload(w.root))

    p = sub.add_parser("workflow", help="validate declarative workflow profiles")
    workflow_sub = p.add_subparsers(dest="workflow_command", required=True)
    w = workflow_sub.add_parser("validate", help="validate a profile file")
    w.add_argument("--file", required=True)
    w.add_argument("--json", action="store_true")
    w.set_defaults(
        func=lambda a, w: w.validate_workflow(a.file)
    )

    return parser


def _verify_agent_payload(root: Path) -> dict[str, Any]:
    errors = verify_agents(root)
    return {"ok": not errors, "kind": "verify_agent", "errors": errors}


def _verify_core_payload(root: Path) -> dict[str, Any]:
    errors = verify_core(root)
    return {"ok": not errors, "kind": "verify_core", "errors": errors}


def _verify_payload(
    workspace: Workspace, spec: str, commands: list[str]
) -> dict[str, Any]:
    payload = workspace.verify(spec, commands)
    payload["ok"] = True
    payload["kind"] = "verify"
    return payload


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "init":
        try:
            payload = run_init(args)
        except (ValueError, OSError) as exc:
            payload = {
                "ok": False,
                "kind": "init",
                "mode": None,
                "target": str(Path(args.target).expanduser().resolve()),
                "project": None,
                "actions": [],
                "warnings": [],
                "preserved": [],
                "checks": [],
                "errors": [str(exc)],
                "dry_run": bool(args.dry_run),
                "next": None,
            }
        _emit(args, payload)
        return 0 if payload.get("ok") else 1
    try:
        workspace = _workspace(args)
        payload = args.func(args, workspace)
        if payload is None:
            payload = {"ok": True}
        if not isinstance(payload, dict):
            payload = {"ok": True, "result": payload}
        _emit(args, payload)
        if payload.get("ok") is False:
            return 1
        return 0
    except (SddCommandError, ValueError, FileNotFoundError, OSError) as exc:
        payload = {"ok": False, "errors": [str(exc)]}
        if getattr(args, "json", False):
            _print_json(payload)
        else:
            print(f"[sdd] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
