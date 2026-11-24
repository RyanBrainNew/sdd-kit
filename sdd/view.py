"""Read-only single-file HTML view for one SDD Spec."""

from __future__ import annotations

import html
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from .core import Workspace


VIEW_SECTIONS = ("timeline", "gates", "tasks", "artifacts")

EMPTY_EVENT = "暂无事件"
EMPTY_GATE = "暂无 Gate 记录"
EMPTY_TASK = "暂无 Task"
EMPTY_ARTIFACT = "暂无工件"


def escape(value: Any) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def parse_gate_rows(text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    header: list[str] | None = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if cells and all(set(cell) <= set("-: ") for cell in cells):
            continue
        if header is None:
            header = [cell.lower() for cell in cells]
            continue
        row = dict(zip(header, cells))
        if row.get("gate"):
            rows.append(row)
    return rows


def list_artifacts(spec_dir: Path) -> list[Path]:
    return sorted(path for path in spec_dir.rglob("*") if path.is_file())


def relative_link(out_path: Path, target: Path) -> str:
    relative = os.path.relpath(target, start=out_path.parent)
    return Path(relative).as_posix()


def gate_hash(state: dict[str, Any], gate: str) -> str:
    hashes = state.get("artifact_hashes") or {}
    values = hashes.get(gate) or {}
    if not isinstance(values, dict) or not values:
        return ""
    return str(sorted(values.values())[0])


def short_hash(value: str) -> str:
    return value[:12] + "…" if len(value) > 12 else value


def render_event_rows(events: Iterable[dict[str, Any]]) -> str:
    rows = list(events)
    if not rows:
        return f'<p class="empty">{escape(EMPTY_EVENT)}</p>'
    items: list[str] = []
    for event in rows:
        reason = escape(event.get("reason")) if event.get("reason") else ""
        from_state = escape(event.get("from_state") or "—")
        to_state = escape(event.get("to_state") or "—")
        items.append(
            "<li>"
            f'<span class="seq">#{escape(event.get("seq"))}</span> '
            f'<time>{escape(event.get("at"))}</time> '
            f'<strong>{escape(event.get("event"))}</strong> '
            f'<span class="transition">{from_state} → {to_state}</span>'
            f'<div class="evidence">{escape(event.get("evidence"))}</div>'
            + (f'<div class="reason">reason: {reason}</div>' if reason else "")
            + "</li>"
        )
    return '<ol class="timeline">' + "".join(items) + "</ol>"


def render_gate_rows(rows: list[dict[str, str]], state: dict[str, Any]) -> str:
    if not rows:
        return f'<p class="empty">{escape(EMPTY_GATE)}</p>'
    body: list[str] = []
    for row in rows:
        digest = gate_hash(state, row.get("gate", ""))
        body.append(
            "<tr>"
            f'<td>{escape(row.get("gate"))}</td>'
            f'<td>{escape(row.get("state"))}</td>'
            f'<td>{escape(row.get("mode"))}</td>'
            f'<td>{escape(row.get("result"))}</td>'
            f'<td>{escape(row.get("evidence"))}</td>'
            f'<td title="{escape(digest)}"><code>{escape(short_hash(digest)) or "—"}</code></td>'
            "</tr>"
        )
    return (
        "<table><thead><tr>"
        "<th>Gate</th><th>State</th><th>Mode</th><th>Result</th>"
        "<th>Evidence</th><th>Artifact hash</th>"
        "</tr></thead><tbody>"
        + "".join(body)
        + "</tbody></table>"
    )


def render_task_rows(tasks: list[dict[str, Any]]) -> str:
    if not tasks:
        return f'<p class="empty">{escape(EMPTY_TASK)}</p>'
    body: list[str] = []
    for task in tasks:
        acs = ", ".join(str(item) for item in task.get("acs") or [])
        body.append(
            "<tr>"
            f'<td>{escape(task.get("id"))}</td>'
            f'<td>{escape(task.get("description"))}</td>'
            f'<td>{escape(task.get("status") or "Todo")}</td>'
            f'<td>{escape(acs)}</td>'
            f'<td><code>{escape(task.get("commit") or "—")}</code></td>'
            "</tr>"
        )
    return (
        "<table><thead><tr>"
        "<th>Task</th><th>描述</th><th>状态</th><th>AC</th><th>Commit</th>"
        "</tr></thead><tbody>"
        + "".join(body)
        + "</tbody></table>"
    )


def render_artifacts(
    artifacts: list[Path], spec_dir: Path, out_path: Path
) -> str:
    if not artifacts:
        return f'<p class="empty">{escape(EMPTY_ARTIFACT)}</p>'
    items: list[str] = []
    for path in artifacts:
        label = path.relative_to(spec_dir).as_posix()
        href = relative_link(out_path, path)
        items.append(f'<li><a href="{escape(href)}">{escape(label)}</a></li>')
    return '<ul class="artifacts">' + "".join(items) + "</ul>"


def render_html(
    *,
    spec: str,
    state: dict[str, Any],
    events: list[dict[str, Any]],
    tasks: list[dict[str, Any]],
    gate_rows: list[dict[str, str]],
    artifacts: list[Path],
    spec_dir: Path,
    out_path: Path,
) -> str:
    workflow = state.get("workflow") or {}
    workflow_label = "-"
    if workflow.get("name"):
        workflow_label = f"{workflow.get('name')}@{workflow.get('version', '')}"
    pr_url = str(state.get("pr_url") or "")
    issue = str(state.get("issue") or "")
    header_links = []
    if issue:
        header_links.append(
            f'<a href="{escape(issue)}">Issue</a>'
        )
    if pr_url:
        header_links.append(f'<a href="{escape(pr_url)}">PR</a>')
    generated = datetime.now().astimezone().isoformat(timespec="seconds")
    title = str(state.get("title") or spec)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(spec)} · SDD 运行视图</title>
<style>
:root {{ color-scheme: light dark; --fg:#1f2328; --muted:#59636e; --bg:#ffffff; --panel:#f6f8fa; --line:#d0d7de; --accent:#0969da; }}
@media (prefers-color-scheme: dark) {{ :root {{ --fg:#e6edf3; --muted:#9198a1; --bg:#0d1117; --panel:#161b22; --line:#30363d; --accent:#4493f8; }} }}
* {{ box-sizing: border-box; }}
body {{ margin:0; padding:24px; background:var(--bg); color:var(--fg); font:15px/1.6 ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif; }}
header {{ border-bottom:1px solid var(--line); padding-bottom:16px; margin-bottom:24px; }}
h1 {{ margin:0 0 8px; font-size:26px; }}
h2 {{ font-size:18px; margin:0 0 12px; }}
.meta {{ display:flex; flex-wrap:wrap; gap:8px 20px; color:var(--muted); }}
.meta strong {{ color:var(--fg); }}
.badge {{ display:inline-block; padding:1px 8px; border:1px solid var(--line); border-radius:999px; background:var(--panel); }}
main {{ display:grid; gap:28px; }}
section {{ min-width:0; }}
table {{ width:100%; border-collapse:collapse; display:block; overflow-x:auto; }}
th, td {{ border:1px solid var(--line); padding:6px 10px; text-align:left; vertical-align:top; }}
th {{ background:var(--panel); white-space:nowrap; }}
code {{ font-family:ui-monospace,SFMono-Regular,Consolas,monospace; font-size:13px; }}
.timeline {{ margin:0; padding-left:22px; }}
.timeline li {{ margin-bottom:10px; }}
.seq {{ color:var(--muted); }}
.transition {{ color:var(--muted); }}
.evidence, .reason {{ color:var(--muted); font-size:13px; word-break:break-word; }}
.empty {{ color:var(--muted); font-style:italic; }}
.artifacts {{ margin:0; padding-left:22px; }}
a {{ color:var(--accent); }}
footer {{ margin-top:32px; color:var(--muted); font-size:12px; }}
</style>
</head>
<body>
<header>
  <h1>{escape(title)}</h1>
  <div class="meta">
    <span><strong>Spec</strong> {escape(spec)}</span>
    <span><strong>State</strong> <span class="badge">{escape(state.get("state"))}</span></span>
    <span><strong>Workflow</strong> {escape(workflow_label)}</span>
    <span><strong>Risk</strong> {escape(state.get("risk") or "low")}</span>
    <span>{' '.join(header_links)}</span>
  </div>
</header>
<main>
  <section id="timeline"><h2>事件时间线</h2>{render_event_rows(events)}</section>
  <section id="gates"><h2>Gate 记录</h2>{render_gate_rows(gate_rows, state)}</section>
  <section id="tasks"><h2>Task</h2>{render_task_rows(tasks)}</section>
  <section id="artifacts"><h2>工件</h2>{render_artifacts(artifacts, spec_dir, out_path)}</section>
</main>
<footer>只读视图 · generated at {escape(generated)}</footer>
</body>
</html>
"""


def render_view(
    root: Path | str,
    spec: str,
    out: str | Path | None = None,
) -> dict[str, Any]:
    workspace = Workspace(root)
    base = workspace.root
    status = workspace.status(spec)
    state = status.get("state") or {}
    if not state:
        raise ValueError(f"Spec 不存在或缺少 state：{spec}")
    events_payload = workspace.events(spec)
    board_payload = workspace.board()
    board_item = next(
        (
            item
            for item in board_payload.get("specs", [])
            if item.get("spec") == spec
        ),
        {},
    )
    spec_dir = base / "docs" / "specs" / spec
    if not spec_dir.is_dir():
        raise ValueError(f"Spec 目录不存在：{spec}")

    if out is None:
        out_path = base / ".sdd" / "runtime" / "view" / f"{spec}.html"
    else:
        raw = Path(out)
        out_path = raw if raw.is_absolute() else base / raw
    if out_path.is_dir():
        raise ValueError(f"--out 指向目录而不是文件：{out_path}")

    gate_path = spec_dir / "gates.md"
    gate_rows = (
        parse_gate_rows(gate_path.read_text(encoding="utf-8"))
        if gate_path.is_file()
        else []
    )
    artifacts = list_artifacts(spec_dir)
    html_text = render_html(
        spec=spec,
        state=state,
        events=list(events_payload.get("events") or []),
        tasks=list(board_item.get("tasks") or []),
        gate_rows=gate_rows,
        artifacts=artifacts,
        spec_dir=spec_dir,
        out_path=out_path,
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html_text, encoding="utf-8")
    return {
        "ok": True,
        "kind": "view",
        "spec": spec,
        "out": str(out_path),
        "bytes": len(html_text.encode("utf-8")),
        "sections": list(VIEW_SECTIONS),
    }
