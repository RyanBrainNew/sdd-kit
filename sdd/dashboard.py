"""Read-only portfolio dashboard built from existing SDD read models."""

from __future__ import annotations

import os
import shutil
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Any

from .core import SddCommandError, Workspace
from .view import escape, relative_link, render_view


SCHEMA_VERSION = 1
RECENT_EVENT_LIMIT = 15
STATE_ORDER = {
    "DRAFT": 0,
    "SPEC_READY": 1,
    "DESIGN_READY": 2,
    "TASKS_READY": 3,
    "IMPLEMENTING": 4,
    "VERIFYING": 5,
    "PR_READY": 6,
    "BLOCKED": 7,
    "MERGED": 8,
}
GROUP_ORDER = {"active": 0, "blocked": 1, "completed": 2}
GATE_NAMES = ("G0", "G1", "G2", "G3", "G4", "G5")
RESULT_KEYS = ("pass", "warn", "block", "waived")


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _number(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _percent(done: int, total: int) -> int | None:
    return round(done * 100 / total) if total else None


def _source_warnings(payload: dict[str, Any], source: str) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    for item in payload.get("warnings") or []:
        if isinstance(item, dict):
            warning = dict(item)
        else:
            warning = {"message": str(item)}
        warning["source"] = source
        warnings.append(warning)
    return warnings


def _read_model(
    label: str,
    reader: Any,
    warnings: list[dict[str, Any]],
) -> dict[str, Any] | None:
    try:
        return reader()
    except (OSError, SddCommandError, ValueError) as exc:
        warnings.append(
            {
                "source": label,
                "message": f"{label} 不可用：{exc}",
            }
        )
        return None


def _spec_group(state: str) -> str:
    if state == "MERGED":
        return "completed"
    if state == "BLOCKED":
        return "blocked"
    return "active"


def _normalize_spec(item: dict[str, Any]) -> dict[str, Any]:
    state = str(item.get("state") or "UNKNOWN")
    raw_counts = item.get("task_counts") or {}
    total = _number(raw_counts.get("total"))
    done = _number(raw_counts.get("done"))
    return {
        "spec": str(item.get("spec") or "-"),
        "title": str(item.get("title") or ""),
        "state": state,
        "group": _spec_group(state),
        "workflow": item.get("workflow") or {},
        "risk": item.get("risk"),
        "updated_at": item.get("updated_at"),
        "blocked_reason": item.get("blocked_reason"),
        "next": item.get("next") or {},
        "task_counts": {
            "total": total,
            "todo": _number(raw_counts.get("todo")),
            "in_progress": _number(raw_counts.get("in_progress")),
            "done": done,
        },
        "progress": _percent(done, total),
        "last_event": item.get("last_event"),
        "current": bool(item.get("current")),
    }


def _spec_sort_key(item: dict[str, Any]) -> tuple[int, int, str]:
    state = str(item.get("state") or "")
    return (
        GROUP_ORDER.get(str(item.get("group")), 99),
        STATE_ORDER.get(state, 99),
        str(item.get("spec") or ""),
    )


def _gate_health(metrics: dict[str, Any] | None) -> dict[str, Any]:
    if metrics is None:
        return {
            "available": False,
            "pass": None,
            "warn": None,
            "block": None,
            "waived": None,
            "total": None,
            "by_gate": [],
            "blocked_checks": [],
        }

    totals = {key: 0 for key in RESULT_KEYS}
    by_gate: dict[str, dict[str, Any]] = {}
    for bucket in metrics.get("check_stats") or []:
        check_id = str(bucket.get("id") or "")
        gate = check_id.split("-", 1)[0] if "-" in check_id else "other"
        row = by_gate.setdefault(
            gate,
            {
                "gate": gate,
                "pass": 0,
                "warn": 0,
                "block": 0,
                "waived": 0,
                "total": 0,
            },
        )
        for key in RESULT_KEYS:
            count = _number(bucket.get(key))
            totals[key] += count
            row[key] += count
        row["total"] += _number(bucket.get("total"))

    blocked_checks: list[dict[str, Any]] = []
    for spec in metrics.get("specs") or []:
        spec_id = str(spec.get("spec") or "-")
        for check in spec.get("checks") or []:
            if _number(check.get("block")) <= 0:
                continue
            blocked_checks.append(
                {
                    "spec": spec_id,
                    "gate": str(check.get("gate") or ""),
                    "check_id": str(check.get("check_id") or ""),
                    "name": str(check.get("name") or ""),
                    "level": str(check.get("level") or "required"),
                }
            )
    blocked_checks.sort(key=lambda item: (item["spec"], item["check_id"]))
    ordered_gates = sorted(
        by_gate.values(),
        key=lambda item: (
            GATE_NAMES.index(item["gate"])
            if item["gate"] in GATE_NAMES
            else len(GATE_NAMES),
            item["gate"],
        ),
    )
    return {
        "available": True,
        **totals,
        "total": sum(totals.values()),
        "by_gate": ordered_gates,
        "blocked_checks": blocked_checks,
    }


def _event_time(event: dict[str, Any]) -> float:
    value = str(event.get("at") or "")
    if not value:
        return 0.0
    try:
        return datetime.fromisoformat(value).timestamp()
    except ValueError:
        return 0.0


def _recent_events(specs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for spec in specs:
        event = spec.get("last_event")
        if not isinstance(event, dict):
            continue
        item = dict(event)
        item["spec"] = spec["spec"]
        events.append(item)
    events.sort(
        key=lambda item: (
            _event_time(item),
            _number(item.get("seq")),
            str(item.get("spec") or ""),
        ),
        reverse=True,
    )
    return events[:RECENT_EVENT_LIMIT]


def build_dashboard(
    root: Path | str,
    since: str | None = None,
) -> dict[str, Any]:
    """Aggregate board, metrics and inbox without changing repository state."""
    if since:
        try:
            datetime.fromisoformat(since)
        except ValueError as exc:
            raise ValueError(
                "--since 需要 ISO 日期或日期时间，例如 2026-11-01"
            ) from exc
    workspace = Workspace(root)
    warnings: list[dict[str, Any]] = []

    board = _read_model("board", workspace.board, warnings)
    metrics = _read_model(
        "metrics",
        lambda: workspace.metrics(since),
        warnings,
    )
    inbox = _read_model("inbox", workspace.inbox, warnings)

    if board is not None:
        warnings.extend(_source_warnings(board, "board"))
    if metrics is not None:
        warnings.extend(_source_warnings(metrics, "metrics"))
    if inbox is not None:
        warnings.extend(_source_warnings(inbox, "inbox"))

    raw_specs = list((board or {}).get("specs") or [])
    specs = sorted(
        (_normalize_spec(item) for item in raw_specs),
        key=_spec_sort_key,
    )
    active_specs = [item for item in specs if item["group"] == "active"]
    blocked_specs = [item for item in specs if item["group"] == "blocked"]
    completed_specs = [item for item in specs if item["group"] == "completed"]

    tasks_done = sum(item["task_counts"]["done"] for item in specs)
    tasks_total = sum(item["task_counts"]["total"] for item in specs)
    inbox_items = list((inbox or {}).get("items") or [])
    audit = (metrics or {}).get("audit") or {}
    gate_health = _gate_health(metrics)

    return {
        "ok": True,
        "kind": "dashboard",
        "schema_version": SCHEMA_VERSION,
        "generated_at": _now(),
        "project": workspace.root.name,
        "since": since,
        "summary": {
            "specs": {
                "total": len(specs) if board is not None else None,
                "active": len(active_specs) if board is not None else None,
                "blocked": len(blocked_specs) if board is not None else None,
                "merged": len(completed_specs) if board is not None else None,
            },
            "tasks": {
                "done": tasks_done,
                "total": tasks_total,
                "percent": _percent(tasks_done, tasks_total),
            },
            "gate_health": {
                key: gate_health[key]
                for key in (*RESULT_KEYS, "total", "available")
            },
            "audit": {
                "valid": audit.get("valid"),
                "errors": list(audit.get("errors") or []),
            },
            "inbox": {
                "waiting": len(inbox_items) if inbox is not None else None,
            },
        },
        "groups": {
            "active": [item["spec"] for item in active_specs],
            "blocked": [item["spec"] for item in blocked_specs],
            "completed": [item["spec"] for item in completed_specs],
        },
        "specs": specs,
        "gate_health": gate_health,
        "quality": (metrics or {}).get("quality"),
        "aggregate": (metrics or {}).get("aggregate"),
        "inbox": inbox_items,
        "recent_events": _recent_events(specs),
        "warnings": warnings,
    }


def _format_value(value: Any, suffix: str = "", missing: str = "—") -> str:
    if value is None:
        return missing
    return f"{value}{suffix}"


def _format_rate(value: Any) -> str:
    if value is None:
        return "—"
    try:
        return f"{float(value) * 100:.1f}%"
    except (TypeError, ValueError):
        return "—"


def _progress_text(progress: int | None, width: int = 10) -> str:
    if progress is None:
        return "—"
    filled = min(width, max(0, round(progress * width / 100)))
    bar = "█" * filled + "░" * (width - filled)
    return f"{bar} {progress:>3}%"


def _status_text(item: dict[str, Any], color: bool) -> str:
    state = str(item.get("state") or "UNKNOWN")
    if not color:
        return f"[{state}]"
    codes = {
        "MERGED": "\033[32m",
        "BLOCKED": "\033[31m",
        "PR_READY": "\033[33m",
    }
    return f"{codes.get(state, '')}[{state}]\033[0m"


def _quality_line(payload: dict[str, Any]) -> str:
    quality = payload.get("quality")
    aggregate = payload.get("aggregate") or {}
    if not isinstance(quality, dict):
        return "—"
    parts = [
        "median lead time "
        + _format_value(aggregate.get("median_lead_time_hours"), "h"),
        "reworks " + _format_value(aggregate.get("median_reworks")),
        "waiver rate " + _format_rate(quality.get("waiver_rate")),
        "reopen rate " + _format_rate(quality.get("reopen_rate")),
        "gate first-pass " + _format_rate(quality.get("gate_first_pass_rate")),
    ]
    return " · ".join(parts)


def render_terminal(
    payload: dict[str, Any],
    *,
    color: bool = False,
    width: int | None = None,
) -> str:
    columns = width or shutil.get_terminal_size(fallback=(120, 24)).columns
    summary = payload["summary"]
    specs_summary = summary["specs"]
    tasks = summary["tasks"]
    gate = summary["gate_health"]
    lines = [
        f"SDD Dashboard · {payload['project']} · {payload['generated_at']}",
        "",
        "Summary",
        (
            "  Specs            "
            f"{_format_value(specs_summary['total'])} total · "
            f"{_format_value(specs_summary['active'])} active · "
            f"{_format_value(specs_summary['blocked'])} blocked · "
            f"{_format_value(specs_summary['merged'])} merged"
        ),
        (
            "  Tasks            "
            f"{tasks['done']}/{tasks['total']}"
            + (
                f" done ({tasks['percent']}%)"
                if tasks["percent"] is not None
                else " done"
            )
        ),
        (
            "  Gate health      "
            f"pass {_format_value(gate['pass'])} · "
            f"warn {_format_value(gate['warn'])} · "
            f"block {_format_value(gate['block'])} · "
            f"waived {_format_value(gate['waived'])}"
        ),
        (
            "  Audit            "
            + (
                "INVALID"
                if summary["audit"]["valid"] is False
                else "valid"
                if summary["audit"]["valid"] is True
                else "—"
            )
        ),
        (
            "  Human inbox      "
            f"{_format_value(summary['inbox']['waiting'])} waiting"
        ),
        "",
        "Active Specs",
    ]

    active = [item for item in payload["specs"] if item["group"] == "active"]
    if not active:
        lines.append("  (none)")
    for item in active:
        counts = item["task_counts"]
        state = _status_text(item, color)
        next_action = (item.get("next") or {}).get("action") or "—"
        risk = item.get("risk") or "—"
        if columns < 90:
            lines.append(
                f"  {item['spec']}  {state}  tasks={counts['done']}/"
                f"{counts['total']}  next={next_action}  risk={risk}"
            )
        else:
            lines.append(
                f"  {item['spec']:<16} {state:<22} "
                f"{_progress_text(item.get('progress')):<18} "
                f"next={next_action:<20} risk={risk}"
            )
        if columns >= 90 and item.get("title"):
            lines.append(f"    {item['title']}")

    blocked = [item for item in payload["specs"] if item["group"] == "blocked"]
    if blocked:
        lines.extend(["", "Blocked Specs"])
        for item in blocked:
            lines.append(
                f"  {item['spec']}  {item['blocked_reason'] or '等待人工处理'}"
            )

    lines.extend(["", "Human Inbox"])
    if not payload["inbox"]:
        lines.append("  (none)")
    for item in payload["inbox"]:
        lines.append(
            f"  {item.get('spec')}  {item.get('action')}  "
            f"{item.get('reason') or ''}".rstrip()
        )

    lines.extend(["", "Quality", f"  {_quality_line(payload)}"])

    blocked_checks = payload["gate_health"].get("blocked_checks") or []
    if blocked_checks:
        lines.extend(["", "Blocking Checks"])
        for item in blocked_checks:
            lines.append(
                f"  {item['spec']}  {item['check_id']}  {item['name']}"
            )

    lines.extend(["", "Recent Events"])
    if not payload["recent_events"]:
        lines.append("  (none)")
    for event in payload["recent_events"]:
        label = event.get("gate") or event.get("task") or ""
        status = event.get("status") or event.get("to_state") or ""
        evidence = event.get("evidence") or ""
        lines.append(
            f"  {event.get('spec')}  {event.get('event')}  "
            f"{label} {status}  {evidence}".rstrip()
        )

    if not payload["specs"]:
        lines.extend(
            [
                "",
                "No Specs",
                "  还没有 Spec；先运行 python -m sdd start-work --work-item <id>。",
            ]
        )

    if payload["warnings"]:
        lines.extend(["", "Warnings"])
        for warning in payload["warnings"]:
            spec_dir = warning.get("spec_dir")
            prefix = f"{spec_dir}: " if spec_dir else ""
            lines.append(
                f"  [{warning.get('source', 'sdd')}] {prefix}"
                f"{warning.get('message', '')}"
            )

    return "\n".join(lines)


def _workflow_label(item: dict[str, Any]) -> str:
    workflow = item.get("workflow") or {}
    if not workflow.get("name"):
        return "—"
    return f"{workflow.get('name')}@{workflow.get('version', '')}"


def _render_spec_rows(
    specs: list[dict[str, Any]],
    detail_links: dict[str, str],
    *,
    completed: bool = False,
) -> str:
    if not specs:
        return '<p class="empty">暂无 Spec</p>'
    rows: list[str] = []
    for item in specs:
        spec_id = item["spec"]
        detail = detail_links.get(spec_id)
        label = (
            f'<a href="{escape(detail)}">{escape(spec_id)}</a>'
            if detail
            else escape(spec_id)
        )
        next_action = (item.get("next") or {}).get("action") or "—"
        last_event = item.get("last_event") or {}
        event_text = "—"
        if isinstance(last_event, dict) and last_event.get("event"):
            event_text = (
                f"{last_event.get('event')} · {last_event.get('at') or '—'}"
            )
        if completed:
            rows.append(
                "<tr>"
                f"<td>{label}</td>"
                f"<td>{escape(item.get('title'))}</td>"
                f"<td><span class=\"badge state-merged\">{escape(item.get('state'))}</span></td>"
                f"<td>{escape(_workflow_label(item))}</td>"
                f"<td>{escape(item.get('updated_at') or '—')}</td>"
                "</tr>"
            )
            continue
        rows.append(
            "<tr>"
            f"<td>{label}</td>"
            f"<td>{escape(item.get('title'))}</td>"
            f"<td>{escape(item.get('state'))}</td>"
            f"<td>"
            f'<div class="progress" aria-label="{escape(item.get("progress"))}%">'
            f'<span style="width:{_number(item.get("progress"))}%"></span></div>'
            f'<small>{_format_value(item.get("progress"), "%")}</small>'
            "</td>"
            f"<td><code>{escape(next_action)}</code></td>"
            f"<td>{escape(item.get('risk') or '—')}</td>"
            f"<td>{escape(_workflow_label(item))}</td>"
            f"<td>{escape(event_text)}</td>"
            "</tr>"
        )
    if completed:
        return (
            "<table><thead><tr><th>Spec</th><th>标题</th><th>状态</th>"
            "<th>Workflow</th><th>更新时间</th></tr></thead><tbody>"
            + "".join(rows)
            + "</tbody></table>"
        )
    return (
        "<table><thead><tr><th>Spec</th><th>标题</th><th>状态</th>"
        "<th>Task 进度</th><th>Next action</th><th>Risk</th>"
        "<th>Workflow</th><th>Last event</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )


def _render_inbox(
    items: list[dict[str, Any]],
    detail_links: dict[str, str],
) -> str:
    if not items:
        return '<p class="empty">没有等待人类处理的事项</p>'
    rows: list[str] = []
    for item in items:
        spec_id = str(item.get("spec") or "-")
        detail = detail_links.get(spec_id)
        spec = (
            f'<a href="{escape(detail)}">{escape(spec_id)}</a>'
            if detail
            else escape(spec_id)
        )
        rows.append(
            "<tr>"
            f"<td>{spec}</td>"
            f"<td>{escape(item.get('state'))}</td>"
            f"<td>{escape(item.get('action'))}</td>"
            f"<td>{escape(item.get('reason'))}</td>"
            f"<td><code>{escape(item.get('command') or '—')}</code></td>"
            "</tr>"
        )
    return (
        "<table><thead><tr><th>Spec</th><th>状态</th><th>动作</th>"
        "<th>原因</th><th>人工命令</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )


def _render_gate_health(payload: dict[str, Any]) -> str:
    health = payload["gate_health"]
    if not health["available"]:
        return '<p class="empty">metrics 不可用，Gate health 暂缺。</p>'
    rows = "".join(
        "<tr>"
        f"<td>{escape(item['gate'])}</td>"
        f"<td>{item['pass']}</td><td>{item['warn']}</td>"
        f"<td>{item['block']}</td><td>{item['waived']}</td>"
        f"<td>{item['total']}</td>"
        "</tr>"
        for item in health["by_gate"]
    )
    if not rows:
        rows = '<tr><td colspan="6" class="empty">暂无 Gate 检查记录</td></tr>'
    blocked = health["blocked_checks"]
    blocked_text = (
        '<p class="empty">当前没有阻断检查</p>'
        if not blocked
        else "<ul>"
        + "".join(
            "<li>"
            f"<strong>{escape(item['check_id'])}</strong> "
            f"{escape(item['spec'])} · {escape(item['gate'])} · "
            f"{escape(item['name'])}"
            "</li>"
            for item in blocked
        )
        + "</ul>"
    )
    return (
        "<table><thead><tr><th>Gate</th><th>Pass</th><th>Warn</th>"
        "<th>Block</th><th>Waived</th><th>Total</th></tr></thead><tbody>"
        + rows
        + "</tbody></table>"
        + "<h3>当前阻断检查</h3>"
        + blocked_text
    )


def _render_quality(payload: dict[str, Any]) -> str:
    quality = payload.get("quality")
    aggregate = payload.get("aggregate") or {}
    if not isinstance(quality, dict):
        return '<p class="empty">metrics 不可用，质量指标暂缺。</p>'
    values = (
        ("Median lead time", _format_value(aggregate.get("median_lead_time_hours"), "h")),
        ("Median reworks", _format_value(aggregate.get("median_reworks"))),
        ("Waiver rate", _format_rate(quality.get("waiver_rate"))),
        ("Reopen rate", _format_rate(quality.get("reopen_rate"))),
        ("Gate first-pass", _format_rate(quality.get("gate_first_pass_rate"))),
        ("Escaped defects", _format_value(quality.get("escaped_defects"))),
    )
    return '<div class="metrics">' + "".join(
        f'<div><span>{escape(label)}</span><strong>{escape(value)}</strong></div>'
        for label, value in values
    ) + "</div>"


def _render_recent_events(events: list[dict[str, Any]]) -> str:
    if not events:
        return '<p class="empty">暂无事件</p>'
    rows = "".join(
        "<tr>"
        f"<td>{escape(event.get('at') or '—')}</td>"
        f"<td>{escape(event.get('spec') or '—')}</td>"
        f"<td>{escape(event.get('event') or '—')}</td>"
        f"<td>{escape(event.get('gate') or event.get('task') or '—')}</td>"
        f"<td>{escape(event.get('status') or event.get('to_state') or '—')}</td>"
        f"<td>{escape(event.get('evidence') or '')}</td>"
        "</tr>"
        for event in events
    )
    return (
        "<table><thead><tr><th>时间</th><th>Spec</th><th>事件</th>"
        "<th>Gate / Task</th><th>结果</th><th>证据</th></tr></thead><tbody>"
        + rows
        + "</tbody></table>"
    )


def render_dashboard_html(
    payload: dict[str, Any],
    *,
    detail_links: dict[str, str],
) -> str:
    summary = payload["summary"]
    specs_summary = summary["specs"]
    tasks = summary["tasks"]
    gate = summary["gate_health"]
    audit_valid = summary["audit"]["valid"]
    audit_text = (
        "INVALID" if audit_valid is False else "valid" if audit_valid is True else "—"
    )
    warnings = "".join(
        "<li>"
        + (
            f"<strong>{escape(item.get('spec_dir'))}</strong>: "
            if item.get("spec_dir")
            else ""
        )
        + f"[{escape(item.get('source', 'sdd'))}] "
        + escape(item.get("message") or "")
        + "</li>"
        for item in payload["warnings"]
    )
    warning_html = (
        f'<section class="warnings"><h2>Warnings</h2><ul>{warnings}</ul></section>'
        if warnings
        else ""
    )
    active_specs = [item for item in payload["specs"] if item["group"] == "active"]
    blocked_specs = [item for item in payload["specs"] if item["group"] == "blocked"]
    completed_specs = [
        item for item in payload["specs"] if item["group"] == "completed"
    ]
    detail_count = len(detail_links)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(payload["project"])} · SDD Dashboard</title>
<style>
:root {{ color-scheme: light dark; --fg:#1f2328; --muted:#59636e; --bg:#f6f8fa; --panel:#ffffff; --line:#d0d7de; --accent:#0969da; --pass:#1a7f37; --warn:#9a6700; --block:#cf222e; --bar:#2da44e; }}
@media (prefers-color-scheme: dark) {{ :root {{ --fg:#e6edf3; --muted:#9198a1; --bg:#0d1117; --panel:#161b22; --line:#30363d; --accent:#4493f8; --pass:#3fb950; --warn:#d29922; --block:#f85149; --bar:#3fb950; }} }}
* {{ box-sizing:border-box; }}
body {{ margin:0; padding:28px 20px 48px; background:var(--bg); color:var(--fg); font:15px/1.55 ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif; }}
main {{ max-width:1440px; margin:0 auto; }}
header {{ margin-bottom:24px; }}
h1 {{ margin:0 0 6px; font-size:30px; letter-spacing:-.02em; }}
h2 {{ font-size:18px; margin:0 0 14px; }}
h3 {{ font-size:14px; margin:18px 0 8px; }}
.meta {{ color:var(--muted); display:flex; flex-wrap:wrap; gap:8px 18px; }}
.cards {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:12px; margin-bottom:28px; }}
.card {{ background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:14px 16px; }}
.card span {{ color:var(--muted); display:block; font-size:12px; text-transform:uppercase; letter-spacing:.04em; }}
.card strong {{ display:block; font-size:24px; margin-top:4px; }}
.card small {{ color:var(--muted); }}
.alert {{ color:var(--block); font-weight:700; }}
section {{ background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:18px; margin-bottom:18px; min-width:0; }}
table {{ width:100%; border-collapse:collapse; display:block; overflow-x:auto; }}
th,td {{ border-bottom:1px solid var(--line); padding:8px 10px; text-align:left; vertical-align:top; white-space:nowrap; }}
th {{ color:var(--muted); font-size:12px; text-transform:uppercase; letter-spacing:.04em; }}
tr:last-child td {{ border-bottom:0; }}
code {{ font-family:ui-monospace,SFMono-Regular,Consolas,monospace; font-size:12px; white-space:normal; word-break:break-word; }}
a {{ color:var(--accent); text-decoration:none; }}
a:hover {{ text-decoration:underline; }}
.progress {{ width:120px; height:8px; border-radius:999px; background:var(--line); overflow:hidden; display:inline-block; vertical-align:middle; }}
.progress span {{ display:block; height:100%; background:var(--bar); }}
small {{ color:var(--muted); margin-left:8px; }}
.badge {{ border:1px solid var(--line); border-radius:999px; padding:1px 8px; background:var(--bg); }}
.state-merged {{ color:var(--pass); }}
.metrics {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:10px; }}
.metrics div {{ border-left:3px solid var(--accent); padding:4px 10px; }}
.metrics span {{ color:var(--muted); display:block; font-size:12px; }}
.metrics strong {{ font-size:18px; }}
.empty {{ color:var(--muted); font-style:italic; }}
.warnings {{ border-color:var(--warn); }}
.warnings li {{ margin-bottom:4px; }}
footer {{ color:var(--muted); font-size:12px; text-align:center; }}
@media (max-width:720px) {{ body {{ padding:18px 10px 36px; }} h1 {{ font-size:24px; }} section {{ padding:14px; }} }}
</style>
</head>
<body>
<main>
<header>
  <h1>SDD Dashboard</h1>
  <div class="meta">
    <span><strong>Project</strong> {escape(payload["project"])}</span>
    <span><strong>Generated</strong> {escape(payload["generated_at"])}</span>
    <span><strong>Since</strong> {escape(payload.get("since") or "all history")}</span>
    <span><strong>Detail pages</strong> {detail_count}</span>
  </div>
</header>
<div class="cards">
  <div class="card"><span>Specs</span><strong>{_format_value(specs_summary["total"])}</strong><small>{_format_value(specs_summary["active"])} active · {_format_value(specs_summary["merged"])} merged</small></div>
  <div class="card"><span>Blocked</span><strong>{_format_value(specs_summary["blocked"])}</strong><small>需要人工解除</small></div>
  <div class="card"><span>Task progress</span><strong>{tasks["done"]}/{tasks["total"]}</strong><small>{_format_value(tasks["percent"], "%")}</small></div>
  <div class="card"><span>Gate health</span><strong>{_format_value(gate["pass"])} pass</strong><small>{_format_value(gate["warn"])} warn · {_format_value(gate["block"])} block</small></div>
  <div class="card"><span>Audit</span><strong class="{'alert' if audit_valid is False else ''}">{escape(audit_text)}</strong><small>{len(summary["audit"]["errors"])} error(s)</small></div>
  <div class="card"><span>Human inbox</span><strong>{_format_value(summary["inbox"]["waiting"])}</strong><small>等待处理</small></div>
</div>
{warning_html}
<section id="active"><h2>Active Specs</h2>{_render_spec_rows(active_specs, detail_links)}</section>
<section id="blocked"><h2>Blocked Specs</h2>{_render_spec_rows(blocked_specs, detail_links)}</section>
<section id="inbox"><h2>Human Inbox</h2>{_render_inbox(payload["inbox"], detail_links)}</section>
<section id="completed"><h2>Completed Specs</h2>{_render_spec_rows(completed_specs, detail_links, completed=True)}</section>
<section id="gates"><h2>Gate Health</h2>{_render_gate_health(payload)}</section>
<section id="quality"><h2>Quality</h2>{_render_quality(payload)}</section>
<section id="events"><h2>Recent Events</h2>{_render_recent_events(payload["recent_events"])}</section>
<section id="library"><h2>Specs Library</h2>{_render_spec_rows(payload["specs"], detail_links)}</section>
<footer>只读看板 · 派生文件位于 .sdd/runtime/ · 不提供服务端或写操作</footer>
</main>
</body>
</html>
"""


def _resolve_out(root: Path, out: str | Path) -> Path:
    runtime = (root / ".sdd" / "runtime").resolve()
    raw = Path(out)
    target = (raw if raw.is_absolute() else root / raw).resolve()
    try:
        target.relative_to(runtime)
    except ValueError as exc:
        raise ValueError("--out 必须位于 .sdd/runtime/ 下") from exc
    if target.exists() and target.is_dir():
        raise ValueError(f"--out 指向目录而不是文件：{target}")
    return target


def _write_html(
    workspace: Workspace,
    payload: dict[str, Any],
    *,
    out_path: Path,
    detail_dir: Path,
    no_detail: bool,
) -> dict[str, Any]:
    detail_links: dict[str, str] = {}
    failed_details: list[str] = []
    if not no_detail:
        for item in payload["specs"]:
            spec_id = item["spec"]
            detail_path = detail_dir / f"{spec_id}.html"
            try:
                render_view(workspace.root, spec_id, detail_path)
            except (OSError, ValueError) as exc:
                failed_details.append(f"{spec_id}: {exc}")
                continue
            detail_links[spec_id] = relative_link(out_path, detail_path)

    for failure in failed_details:
        payload["warnings"].append(
            {
                "source": "view",
                "message": f"详情页生成失败：{failure}",
            }
        )
    html_text = render_dashboard_html(payload, detail_links=detail_links)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html_text, encoding="utf-8", newline="\n")
    return {
        "out": str(out_path),
        "bytes": len(html_text.encode("utf-8")),
        "details": len(detail_links),
        "detail_dir": str(detail_dir) if not no_detail else None,
        "no_detail": no_detail,
    }


def run_dashboard(
    root: Path | str,
    *,
    since: str | None = None,
    json_output: bool = False,
    html_output: bool = False,
    out: str | Path | None = None,
    open_browser: bool = False,
    no_color: bool = False,
    no_detail: bool = False,
    color: bool | None = None,
    width: int | None = None,
) -> dict[str, Any]:
    """Build the selected dashboard representation."""
    if json_output and (html_output or open_browser or out is not None):
        raise ValueError("--json 不能与 --html、--open 或 --out 同时使用")
    if out is not None and not (html_output or open_browser):
        raise ValueError("--out 需要与 --html 或 --open 一起使用")

    workspace = Workspace(root)
    payload = build_dashboard(workspace.root, since)
    generate_html = html_output or open_browser
    if generate_html:
        if out is not None:
            out_path = _resolve_out(workspace.root, out)
            detail_dir = out_path.parent / "view"
        else:
            out_path = (
                workspace.root
                / ".sdd"
                / "runtime"
                / "dashboard"
                / "index.html"
            )
            detail_dir = workspace.root / ".sdd" / "runtime" / "view"
        payload["html"] = _write_html(
            workspace,
            payload,
            out_path=out_path,
            detail_dir=detail_dir,
            no_detail=no_detail,
        )
        if open_browser:
            payload["html"]["opened"] = bool(
                webbrowser.open(out_path.resolve().as_uri())
            )
        payload["terminal"] = (
            f"SDD Dashboard · {payload['project']}\n"
            f"  HTML   {payload['html']['out']}\n"
            f"  Detail {payload['html']['details']} page(s)"
            + (" (disabled)" if no_detail else "")
            + f"\n  Bytes  {payload['html']['bytes']}"
        )
        return payload

    use_color = (
        bool(color)
        if color is not None
        else (not no_color and os.isatty(1))
    )
    payload["terminal"] = render_terminal(
        payload,
        color=use_color,
        width=width,
    )
    return payload
