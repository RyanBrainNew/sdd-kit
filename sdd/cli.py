from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from . import __version__
from .agents import sync_agents, verify_agents
from .core import (
    SddCommandError,
    Workspace,
    verify_core,
    write_manifest,
)


def _print_json(payload: Any) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _print_human(payload: dict[str, Any]) -> None:
    if payload.get("ok") is False:
        for error in payload.get("errors", []):
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
    if payload.get("kind") == "manifest":
        print(
            f"[sdd] wrote sdd/manifest.json "
            f"(version {payload.get('version')}, {len(payload.get('files', {}))} files)"
        )
        return
    if payload.get("kind") == "sync_agent":
        if payload.get("changed"):
            print("[sdd] updated the SDD managed block in AGENTS.md")
        else:
            print("[sdd] AGENTS.md managed block already up to date")
        return
    if payload.get("kind") in {"verify_core", "verify_agent"}:
        if payload.get("ok"):
            print(f"[sdd] {payload['kind']} passed")
        else:
            for error in payload.get("errors", []):
                print(f"[sdd] {error}", file=sys.stderr)
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
        _print_json(payload)
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

    p = sub.add_parser("events", help="show the append-only audit events")
    p.add_argument("--spec")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=lambda a, w: w.events(a.spec))

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

    p = sub.add_parser("approve", help="human approval: DRAFT -> SPEC_READY")
    p.add_argument("--spec")
    p.add_argument("--evidence", required=True)
    p.add_argument("--human", action="store_true")
    p.add_argument("--json", action="store_true")
    p.set_defaults(
        func=lambda a, w: (_require_human(a), w.approve(a.spec, a.evidence))[1]
    )

    p = sub.add_parser("merge", help="human merge: PR_READY -> MERGED")
    p.add_argument("--spec")
    p.add_argument("--evidence", required=True)
    p.add_argument("--human", action="store_true")
    p.add_argument("--json", action="store_true")
    p.set_defaults(
        func=lambda a, w: (_require_human(a), w.merge(a.spec, a.evidence))[1]
    )

    p = sub.add_parser("unblock", help="resume after a human answer")
    p.add_argument("--spec")
    p.add_argument("--evidence", default="")
    p.add_argument("--human", action="store_true")
    p.add_argument("--json", action="store_true")
    p.set_defaults(
        func=lambda a, w: (_require_human(a), w.unblock(a.spec, a.evidence))[1]
    )

    p = sub.add_parser("complete", help="low-level completion compatibility")
    p.add_argument("--spec")
    p.add_argument("--task")
    p.add_argument("--evidence", required=True)
    p.add_argument("--commit")
    p.add_argument("--human", action="store_true")
    p.add_argument("--json", action="store_true")
    p.set_defaults(
        func=lambda a, w: w.complete(
            a.spec or w._resolve_current_spec(),
            a.evidence,
            task=a.task,
            commit=a.commit,
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

    return parser


def _verify_agent_payload(root: Path) -> dict[str, Any]:
    errors = verify_agents(root)
    return {"ok": not errors, "kind": "verify_agent", "errors": errors}


def _verify_core_payload(root: Path) -> dict[str, Any]:
    errors = verify_core(root)
    return {"ok": not errors, "kind": "verify_core", "errors": errors}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
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
