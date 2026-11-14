#!/usr/bin/env python3
"""Repo-local SDD workflow.

The script owns the state machine. The coding agent owns the content.
No third-party dependencies; Python 3.9+.
"""

from __future__ import annotations

import argparse
import glob
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Optional


VERSION = "0.6.0"

SPEC_SECTIONS = (
    ("元数据", "Metadata"),
    ("范围声明", "Scope"),
    ("业务上下文", "Business Context"),
    ("功能需求与验收条件", "Functional Requirements", "Acceptance Criteria"),
    ("边界与异常", "Boundaries and Exceptions"),
    ("非功能需求", "Non-functional Requirements"),
    ("外部接口", "External Interfaces"),
    ("数据模型", "Data Model"),
    ("约束与假设", "Constraints and Assumptions"),
    ("变更历史", "Change History"),
)

DESIGN_SECTIONS = (
    ("元数据", "Metadata"),
    ("设计目标", "Design Goals"),
    ("方案概述", "Design"),
    ("Spec 覆盖关系", "Spec Coverage"),
    ("系统架构", "System Architecture"),
    ("数据模型", "Data Model"),
    ("接口契约", "Interfaces"),
    ("认证、授权、幂等与安全", "Security"),
    ("关键决策 ADR", "Design Decisions"),
    ("非功能需求设计", "Non-functional Design"),
    ("依赖与风险", "Dependencies and Risks", "Risks"),
    ("回滚方案", "Rollback"),
    ("验收标准", "Acceptance Criteria"),
    ("变更历史", "Change History"),
)

TASK_SECTIONS = (("任务清单", "Tasks", "Task List"),)

VERIFY_SECTIONS = (
    ("元数据", "Metadata"),
    ("命令", "Commands"),
    ("结果", "Results"),
    ("未运行", "Not Run"),
    ("AC 覆盖", "AC Coverage"),
    ("Gate 5 结论", "Gate 5 Result"),
)

PR_SECTIONS = (
    ("Spec", "Spec 文件"),
    ("Spec Items", "Spec Item", "Spec Item 列表"),
    ("Change Summary", "变更说明"),
    ("AC Verification", "AC 验证", "AC 验证清单"),
)

TODO_RE = re.compile(r"<!--\s*TODO\b.*?-->", re.IGNORECASE | re.DOTALL)
PLACEHOLDER_RE = re.compile(r"\{\{[A-Z0-9_]+\}\}")
CLARIFY_RE = re.compile(r"\[NEEDS\s+CLARIFICATION\]", re.IGNORECASE)
FR_RE = re.compile(r"\bFR-\d{3}\b")
AC_RE = re.compile(r"\bAC-\d{3}-[1-9]\d*\b")
TASK_RE = re.compile(
    r"^\s*-\s*\[(?P<done>[ xX])\]\s*(?P<id>T-[A-Za-z0-9_-]+)\s*"
    r"\[(?P<acs>[^\]]+)\]\s*(?P<description>.*)$"
)
TASK_ID_RE = re.compile(r"^T-[A-Za-z0-9_-]+$")
SPEC_ID_RE = re.compile(r"^SPEC-[A-Z][A-Z0-9]*-[0-9]{3}$")
DOMAIN_RE = re.compile(r"^[A-Z][A-Z0-9]*$")
WORK_ITEM_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]*-[0-9]+$")
FEAT_RE = re.compile(r"\bFEAT-\d{3}\b")

GATE_STAGES = {
    "G0": ("REQUIREMENT", "需求侧准入"),
    "G1": ("SPECIFY", "Spec 准入"),
    "G2": ("PLAN", "设计评审"),
    "G3": ("DECOMPOSE", "任务拆解"),
    "G4": ("IMPLEMENT", "代码审查"),
    "G5": ("VALIDATE", "规格验证"),
}

GATE_AC_STATUS = {
    "G0": "DEFINED",
    "G1": "DEFINED",
    "G2": "DESIGN_COVERED",
    "G3": "TASK_MAPPED",
    "G4": "IMPLEMENTED",
    "G5": "VERIFIED",
}


class SddError(Exception):
    """Expected user-facing error."""


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def eprint(message: str) -> None:
    print(message, file=sys.stderr)


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SddError(f"找不到文件：{path}") from exc
    except json.JSONDecodeError as exc:
        raise SddError(f"JSON 格式错误：{path} ({exc})") from exc


def write_json(path: Path, data: dict[str, Any]) -> None:
    write_text(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def find_root(requested: Optional[str]) -> Path:
    if requested:
        root = Path(requested).expanduser().resolve()
        if not (root / "sdd" / "config.json").is_file():
            raise SddError(f"{root} 下没有 sdd/config.json")
        return root

    starts = [Path.cwd().resolve(), Path(__file__).resolve().parents[2]]
    for start in starts:
        for candidate in (start, *start.parents):
            if (candidate / "sdd" / "config.json").is_file():
                return candidate
    raise SddError("找不到 sdd/config.json；请在仓库根目录运行，或传 --root")


def load_config(root: Path) -> dict[str, Any]:
    config = load_json(root / "sdd" / "config.json")
    config.setdefault("project", "demo")
    config.setdefault("sdd_level", "L2")
    config.setdefault("spec_root", "docs/specs")
    config.setdefault("report_root", "sdd/reports")
    config.setdefault("prd_index", "docs/prd-index.md")
    config.setdefault("prd_mode", "workitem")
    config.setdefault("require_prd_index", True)
    config.setdefault("test_globs", [])
    config.setdefault("exclude_dirs", [])
    config.setdefault("test_commands", [])
    config.setdefault("risk_stop", [])
    config.setdefault("gates", {})
    config.setdefault("require_commit_sha", False)
    return config


def spec_root(root: Path, config: dict[str, Any]) -> Path:
    raw = Path(str(config["spec_root"]))
    return raw if raw.is_absolute() else root / raw


def report_root(root: Path, config: dict[str, Any]) -> Path:
    raw = Path(str(config["report_root"]))
    return raw if raw.is_absolute() else root / raw


def spec_dir_for(root: Path, config: dict[str, Any], spec_id: str) -> Path:
    if Path(spec_id).name != spec_id:
        raise SddError(f"非法 Spec ID：{spec_id}")
    return spec_root(root, config) / spec_id


def resolve_spec(
    root: Path, config: dict[str, Any], requested: Optional[str]
) -> tuple[str, Path, dict[str, Any]]:
    base = spec_root(root, config)
    if requested:
        directory = spec_dir_for(root, config, requested)
        if not (directory / "state.json").is_file():
            raise SddError(f"Spec 不存在：{requested}")
        return requested, directory, load_json(directory / "state.json")

    candidates: list[Path] = []
    if base.exists():
        candidates = [
            item
            for item in sorted(base.iterdir())
            if item.is_dir() and (item / "state.json").is_file()
        ]
    if not candidates:
        raise SddError("还没有 Spec；先运行 sdd new <SPEC-ID> --title \"...\"")

    active: list[tuple[Path, dict[str, Any]]] = []
    for directory in candidates:
        state = load_json(directory / "state.json")
        if state.get("state") != "MERGED":
            active.append((directory, state))
    if len(active) == 1:
        directory, state = active[0]
        return str(state.get("spec_id", directory.name)), directory, state
    if len(candidates) == 1:
        directory = candidates[0]
        state = load_json(directory / "state.json")
        return str(state.get("spec_id", directory.name)), directory, state

    names = ", ".join(item.name for item, _ in active) or ", ".join(
        item.name for item in candidates
    )
    raise SddError(f"存在多个活跃 Spec，请用 --spec 指定：{names}")


def save_state(directory: Path, state: dict[str, Any]) -> None:
    state_path = directory / "state.json"
    state["updated_at"] = now()
    write_json(state_path, state)
    append_event_log(directory, state)


def _event_from_history(
    seq: int, entry: dict[str, Any], from_state: Optional[str]
) -> dict[str, Any]:
    evidence = str(entry.get("evidence") or "")
    event_name = entry.get("action") or (
        "spec_created" if evidence == "created" else "state_transition"
    )
    event: dict[str, Any] = {
        "schema": 1,
        "seq": seq,
        "at": entry.get("at"),
        "event": event_name,
        "from_state": from_state,
        "to_state": entry.get("state"),
        "evidence": evidence,
    }
    for key in ("task", "commit", "pr_url", "gate", "reason", "actor", "source"):
        if entry.get(key) is not None:
            event[key] = entry[key]
    return event


def read_event_log(directory: Path) -> list[dict[str, Any]]:
    path = directory / "events.jsonl"
    if not path.is_file():
        return []
    events: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            events.append(item)
    return events


def derive_events(state: dict[str, Any]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    previous_state: Optional[str] = None
    for seq, entry in enumerate(state.get("history", []), start=1):
        if not isinstance(entry, dict):
            continue
        event = _event_from_history(seq, entry, previous_state)
        events.append(event)
        previous_state = entry.get("state")
    return events


def append_event_log(directory: Path, state: dict[str, Any]) -> None:
    """Append new history entries to events.jsonl without rewriting old events."""
    history = [entry for entry in state.get("history", []) if isinstance(entry, dict)]
    existing = read_event_log(directory)
    if len(existing) >= len(history):
        return
    previous_state = existing[-1].get("to_state") if existing else None
    path = directory / "events.jsonl"
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        for seq, entry in enumerate(history[len(existing) :], start=len(existing) + 1):
            event = _event_from_history(seq, entry, previous_state)
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")
            previous_state = entry.get("state")


def add_history(
    state: dict[str, Any], state_name: str, evidence: str, **extra: Any
) -> None:
    entry: dict[str, Any] = {
        "state": state_name,
        "at": now(),
        "evidence": evidence,
    }
    entry.update(extra)
    state.setdefault("history", []).append(entry)


def transition(
    state: dict[str, Any], new_state: str, evidence: str, **extra: Any
) -> None:
    state["previous_state"] = state.get("state")
    state["state"] = new_state
    add_history(state, new_state, evidence, **extra)


def render_template(root: Path, name: str, context: dict[str, str]) -> str:
    path = root / "sdd" / "templates" / name
    text = read_text(path)
    if not text:
        raise SddError(f"模板不存在或为空：{path}")
    for key, value in context.items():
        text = text.replace("{{" + key + "}}", str(value))
    return text


def normalize_heading(value: str) -> str:
    value = value.strip()
    value = re.sub(r"^[0-9]+(?:\.[0-9]+)*[.、．\s]*", "", value)
    value = re.sub(r"^[一二三四五六七八九十]+[、.．]\s*", "", value)
    value = re.sub(r"[（(][^）)]*[）)]", "", value)
    return re.sub(r"[\s\-_/、，,。.：:（）()【】\[\]]+", "", value).lower()


def iter_sections(text: str) -> Iterable[tuple[str, list[str]]]:
    heading: Optional[str] = None
    body: list[str] = []
    for line in text.splitlines():
        if re.match(r"^\s*#{1,6}\s+", line):
            if heading is not None:
                yield heading, body
            heading = re.sub(r"^\s*#{1,6}\s+", "", line).strip().rstrip("#").strip()
            body = []
        elif heading is not None:
            body.append(line)
    if heading is not None:
        yield heading, body


def has_section(text: str, aliases: tuple[str, ...]) -> bool:
    wanted = {normalize_heading(alias) for alias in aliases}
    return any(normalize_heading(name) in wanted for name, _ in iter_sections(text))


def section_body(text: str, aliases: tuple[str, ...]) -> str:
    wanted = {normalize_heading(alias) for alias in aliases}
    for name, body in iter_sections(text):
        if normalize_heading(name) in wanted:
            return "\n".join(body).strip()
    return ""


def strip_comments(text: str) -> str:
    return re.sub(r"<!--.*?-->", "", text, flags=re.IGNORECASE | re.DOTALL).strip()


def split_table_row(line: str) -> list[str]:
    value = line.strip()
    if value.startswith("|"):
        value = value[1:]
    if value.endswith("|"):
        value = value[:-1]
    return [part.strip().replace("\\|", "|") for part in re.split(r"(?<!\\)\|", value)]


def table_rows(text: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            continue
        cells = split_table_row(stripped)
        if not cells or all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in cells):
            continue
        rows.append(cells)
    return rows


def metadata_map(text: str) -> dict[str, str]:
    body = section_body(text, ("元数据", "Metadata"))
    result: dict[str, str] = {}
    for cells in table_rows(body):
        if len(cells) >= 2 and cells[0]:
            result[normalize_heading(cells[0])] = cells[1]
    return result


def metadata_value(text: str, *names: str) -> str:
    data = metadata_map(text)
    for name in names:
        value = data.get(normalize_heading(name), "")
        if value:
            return value.strip()
    return ""


def is_placeholder_value(value: str) -> bool:
    cleaned = strip_comments(value).strip().strip("`").strip()
    if not cleaned:
        return True
    if cleaned in {"-", "—", "N/A", "n/a", "待填写", "待补充", "TODO", "TBD"}:
        return True
    if cleaned.startswith("{{") and cleaned.endswith("}}"):
        return True
    if re.fullmatch(r"<[^<>]+>", cleaned):
        return True
    return False


def section_has_content(text: str, aliases: tuple[str, ...]) -> bool:
    body = section_body(text, aliases)
    if not strip_comments(body):
        return False
    meaningful = [
        line
        for line in strip_comments(body).splitlines()
        if line.strip() and not re.fullmatch(r"[-|:\s]+", line.strip())
    ]
    return bool(meaningful)


def placeholder_errors(label: str, text: str) -> list[str]:
    errors: list[str] = []
    if TODO_RE.search(text):
        errors.append(f"{label} 还有未完成的 TODO")
    if PLACEHOLDER_RE.search(text):
        errors.append(f"{label} 还有未替换的 {{{{占位符}}}}")
    if CLARIFY_RE.search(text):
        errors.append(f"{label} 还有 [NEEDS CLARIFICATION] 标记，禁止进入下一阶段")
    return errors


def extract_acs(text: str) -> list[str]:
    return sorted(set(AC_RE.findall(text)))


def extract_frs(text: str) -> list[str]:
    return sorted(set(FR_RE.findall(text)))


TASK_COLUMNS = {
    "id": ("taskid",),
    "description": ("任务描述", "description"),
    "items": ("关联frac", "关联fr/ac", "关联frc", "fr/ac"),
    "depends": ("依赖task", "依赖", "depends"),
    "parallel": ("并行标识", "parallel"),
    "acceptance": ("验收标准", "acceptance"),
    "test": ("单元测试类/方法", "单元测试类方法", "test"),
    "command": ("单task测试命令", "测试命令", "command"),
    "status": ("状态", "status"),
    "commit": ("commitsha", "commit"),
}


def normalize_column(value: str) -> str:
    return re.sub(r"[\s\-_/（）()]+", "", value).lower()


def column_index(header: list[str], key: str) -> Optional[int]:
    wanted = {normalize_column(item) for item in TASK_COLUMNS[key]}
    for index, value in enumerate(header):
        if normalize_column(value) in wanted:
            return index
    return None


def parse_tasks(text: str) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []

    for line in text.splitlines():
        match = TASK_RE.match(line)
        if match:
            tasks.append(
                {
                    "id": match.group("id"),
                    "done": match.group("done").lower() == "x",
                    "acs": sorted(set(AC_RE.findall(match.group("acs")))),
                    "frs": [],
                    "description": match.group("description").strip(),
                    "depends": [],
                    "parallel": "",
                    "acceptance": "",
                    "test": "",
                    "command": "",
                    "status": "Done" if match.group("done").lower() == "x" else "Todo",
                    "commit": "",
                }
            )
            continue

        stripped = line.strip()
        if not stripped.startswith("| T-"):
            continue
        cells = split_table_row(stripped)
        if not cells or not TASK_ID_RE.match(cells[0]):
            continue
        tasks.append(
            {
                "id": cells[0],
                "done": len(cells) > 8 and cells[8].strip().lower() == "done",
                "acs": sorted(set(AC_RE.findall(" ".join(cells)))),
                "frs": sorted(set(FR_RE.findall(" ".join(cells[2:3])))),
                "description": cells[1] if len(cells) > 1 else "",
                "depends": [
                    item.strip()
                    for item in (cells[3] if len(cells) > 3 else "").split(",")
                    if item.strip() and item.strip().lower() != "none"
                ],
                "parallel": cells[4] if len(cells) > 4 else "",
                "acceptance": cells[5] if len(cells) > 5 else "",
                "test": cells[6] if len(cells) > 6 else "",
                "command": cells[7] if len(cells) > 7 else "",
                "status": cells[8] if len(cells) > 8 else "",
                "commit": cells[9] if len(cells) > 9 else "",
            }
        )

    if tasks:
        return tasks

    header: Optional[list[str]] = None
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            continue
        cells = split_table_row(stripped)
        if "taskid" in {normalize_column(cell) for cell in cells}:
            header = cells
            continue
        if header is None:
            continue
        if not cells or not TASK_ID_RE.match(cells[0]):
            continue

        def cell(key: str) -> str:
            index = column_index(header or [], key)
            return cells[index].strip() if index is not None and index < len(cells) else ""

        items = cell("items")
        depends_raw = cell("depends")
        status = cell("status")
        tasks.append(
            {
                "id": cells[0],
                "done": status.lower() == "done",
                "acs": sorted(set(AC_RE.findall(items))),
                "frs": sorted(set(FR_RE.findall(items))),
                "description": cell("description"),
                "depends": [
                    item.strip()
                    for item in depends_raw.split(",")
                    if item.strip() and item.strip().lower() != "none"
                ],
                "parallel": cell("parallel"),
                "acceptance": cell("acceptance"),
                "test": cell("test"),
                "command": cell("command"),
                "status": status,
                "commit": cell("commit"),
            }
        )
    return tasks


def task_table_error(tasks: list[dict[str, Any]], spec_acs: list[str], config: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    by_id: dict[str, dict[str, Any]] = {}
    task_acs: set[str] = set()
    spec_ac_set = set(spec_acs)

    for task in tasks:
        task_id = str(task["id"])
        if task_id in seen:
            errors.append(f"Task ID 重复：{task_id}")
        seen.add(task_id)
        by_id[task_id] = task
        if not task["description"]:
            errors.append(f"{task_id} 没有任务描述")
        if not task["acs"]:
            errors.append(f"{task_id} 没有关联 AC")
        if not task["frs"]:
            errors.append(f"{task_id} 没有关联 FR")
        if not task["acceptance"] or is_placeholder_value(str(task["acceptance"])):
            errors.append(f"{task_id} 没有明确验收标准")
        if not task["test"] or is_placeholder_value(str(task["test"])):
            errors.append(f"{task_id} 没有具体单元测试类/方法")
        if not task["command"] or is_placeholder_value(str(task["command"])):
            errors.append(f"{task_id} 没有单 Task 测试命令")
        if task["parallel"] not in {"P", "S"}:
            errors.append(f"{task_id} 并行标识必须是 P 或 S")
        if task["status"] not in {"Todo", "In Progress", "Done"}:
            errors.append(f"{task_id} 状态必须是 Todo / In Progress / Done")
        if config.get("require_commit_sha") and task["status"] == "Done":
            if not task["commit"] or is_placeholder_value(str(task["commit"])):
                errors.append(f"{task_id} 已完成但没有回填 Commit SHA")
        for fr in task["frs"]:
            suffix = fr[3:]
            if not any(ac.startswith(f"AC-{suffix}-") for ac in task["acs"]):
                errors.append(f"{task_id} 的 {fr} 没有对应 AC 关联")
        unknown = sorted(set(task["acs"]) - spec_ac_set)
        if unknown:
            errors.append(f"{task_id} 关联了 Spec 中不存在的 AC：" + ", ".join(unknown))
        task_acs.update(task["acs"])

    missing = sorted(spec_ac_set - task_acs)
    if missing:
        errors.append("以下 AC 没有对应任务：" + ", ".join(missing))

    for task in tasks:
        for dependency in task["depends"]:
            if dependency == task["id"]:
                errors.append(f"{task['id']} 不能依赖自身")
            elif dependency not in by_id:
                errors.append(f"{task['id']} 依赖的 {dependency} 不存在")

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(task_id: str, path: list[str]) -> None:
        if task_id in visited:
            return
        if task_id in visiting:
            errors.append("任务依赖存在环：" + " -> ".join(path + [task_id]))
            return
        visiting.add(task_id)
        task = by_id.get(task_id)
        if task:
            for dependency in task["depends"]:
                if dependency in by_id:
                    visit(dependency, path + [task_id])
        visiting.discard(task_id)
        visited.add(task_id)

    for task_id in by_id:
        visit(task_id, [])
    return errors


def check_spec(text: str, spec_id: Optional[str] = None) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    for aliases in SPEC_SECTIONS:
        if not has_section(text, aliases):
            errors.append(f"spec.md 缺少章节：{aliases[0]}")
    errors.extend(placeholder_errors("spec.md", text))

    if spec_id:
        declared = metadata_value(text, "Spec ID", "SpecID")
        if declared != spec_id:
            errors.append(f"spec.md 元数据 Spec ID 必须是 {spec_id}，当前是 {declared or '空'}")
    work_item = metadata_value(text, "工作项 ID", "工作项ID", "Work Item ID")
    if is_placeholder_value(work_item):
        errors.append("spec.md 缺少有效的工作项 ID")
    elif work_item.startswith("%"):
        errors.append("spec.md 的工作项 ID 不能带前导 %")

    scope = section_body(text, ("范围声明", "Scope"))
    in_scope = re.search(r"(?im)^\s*[-*]?\s*In-Scope\s*[：:]\s*(.+)$", scope)
    out_scope = re.search(r"(?im)^\s*[-*]?\s*Out-of-Scope\s*[：:]\s*(.+)$", scope)
    if not in_scope or is_placeholder_value(in_scope.group(1)):
        errors.append("spec.md 的 In-Scope 未填写")
    if not out_scope or is_placeholder_value(out_scope.group(1)):
        errors.append("spec.md 的 Out-of-Scope 未填写")

    acs = extract_acs(text)
    frs = extract_frs(text)
    if not frs:
        errors.append("spec.md 没有 FR-xxx 形式的功能需求")
    if not acs:
        errors.append("spec.md 没有 AC-xxx-y 形式的验收标准")

    for fr in frs:
        suffix = fr[3:]
        if not any(ac.startswith(f"AC-{suffix}-") for ac in acs):
            errors.append(f"{fr} 没有对应 AC")

    for ac in acs:
        line = ""
        for raw in text.splitlines():
            if ac in raw:
                line = raw
                break
        if not all(word in line for word in ("Given", "When", "Then")):
            errors.append(f"{ac} 必须在同一条验收定义中包含 Given/When/Then")
        if "执行路径" not in line:
            errors.append(f"{ac} 缺少【执行路径：...】标注")

    fr_defs = re.findall(r"(?m)^#{1,6}\s+(FR-\d{3})\b", text)
    ac_defs = re.findall(
        r"(?m)^\s*[-*]?\s*(AC-\d{3}-[1-9]\d*)\s*[:：]", text
    )
    if len(fr_defs) != len(set(fr_defs)):
        errors.append("spec.md 存在重复 FR 定义")
    if len(ac_defs) != len(set(ac_defs)):
        errors.append("spec.md 存在重复 AC 定义")
    return errors, acs


def check_design(text: str, spec_acs: list[str]) -> list[str]:
    errors: list[str] = []
    for aliases in DESIGN_SECTIONS:
        if not has_section(text, aliases):
            errors.append(f"design.md 缺少章节：{aliases[0]}")
    errors.extend(placeholder_errors("design.md", text))
    covered = set(extract_acs(text))
    missing = sorted(set(spec_acs) - covered)
    if missing:
        errors.append("design.md 没有覆盖以下 AC：" + ", ".join(missing))
    if not section_has_content(text, ("方案概述", "方案", "Design")):
        errors.append("design.md 的“方案概述”没有实际内容")
    if not section_has_content(text, ("依赖与风险", "风险", "Risks")):
        errors.append("design.md 的“依赖与风险”没有实际内容")
    if not section_has_content(text, ("回滚方案", "Rollback")):
        errors.append("design.md 的“回滚方案”没有实际内容")
    return errors


def check_tasks(
    text: str, spec_acs: list[str], config: Optional[dict[str, Any]] = None
) -> list[str]:
    errors: list[str] = []
    required = (
        ("元数据", "Metadata"),
        ("任务清单", "Tasks", "Task List"),
        ("AC—Task—单元测试映射", "AC-Task-单元测试映射", "AC Coverage"),
        ("依赖图", "Dependency Graph"),
        ("实施与提交顺序", "Implementation Order"),
        ("全量单元测试记录", "Unit Test Record"),
        ("自检清单", "Self Check"),
        ("变更历史", "Change History"),
    )
    for aliases in required:
        if not has_section(text, aliases):
            errors.append(f"tasks.md 缺少章节：{aliases[0]}")
    errors.extend(placeholder_errors("tasks.md", text))
    tasks = parse_tasks(text)
    if not tasks:
        errors.append("tasks.md 没有任务；请填写公司任务表格")
        return errors
    errors.extend(task_table_error(tasks, spec_acs, config or {}))

    mapping = section_body(
        text, ("AC—Task—单元测试映射", "AC-Task-单元测试映射", "AC Coverage")
    )
    for ac in spec_acs:
        if ac not in mapping:
            errors.append(f"tasks.md 的 AC—Task—单元测试映射缺少 {ac}")
    if not re.search(r"(?im)^\s*```mermaid", section_body(text, ("依赖图", "Dependency Graph"))):
        errors.append("tasks.md 的依赖图像缺少 Mermaid 图")
    return errors


def check_verification(text: str, spec_acs: list[str]) -> list[str]:
    errors: list[str] = []
    for aliases in VERIFY_SECTIONS:
        if not has_section(text, aliases):
            errors.append(f"verification.md 缺少章节：{aliases[0]}")
    errors.extend(placeholder_errors("verification.md", text))
    if not section_has_content(text, ("命令", "Commands")):
        errors.append("verification.md 的“命令”章节没有实际内容")
    if not section_has_content(text, ("结果", "Results")):
        errors.append("verification.md 的“结果”章节没有实际内容")
    missing = sorted(set(spec_acs) - set(extract_acs(text)))
    if missing:
        errors.append("verification.md 没有覆盖以下 AC：" + ", ".join(missing))
    gate5 = section_body(text, ("Gate 5 结论", "Gate 5 Result"))
    if not re.search(r"(?i)\b(PASS|通过)\b", gate5):
        errors.append("verification.md 的 Gate 5 结论必须是 PASS/通过")
    return errors


def collect_test_files(root: Path, config: dict[str, Any]) -> list[Path]:
    exclude = set(str(item) for item in config.get("exclude_dirs", []))
    found: dict[Path, None] = {}
    for pattern in config.get("test_globs", []):
        for raw in glob.glob(str(root / pattern), recursive=True):
            path = Path(raw)
            if not path.is_file():
                continue
            try:
                relative = path.relative_to(root)
            except ValueError:
                continue
            if any(part in exclude for part in relative.parts):
                continue
            found[path] = None
    return sorted(found)


def check_test_coverage(root: Path, config: dict[str, Any], spec_acs: list[str]) -> list[str]:
    files = collect_test_files(root, config)
    if not files:
        return ["没有找到测试文件；请按 config.json 的 test_globs 添加测试"]
    covered: set[str] = set()
    for path in files:
        covered.update(extract_acs(read_text(path)))
    missing = sorted(set(spec_acs) - covered)
    if missing:
        return ["测试文件没有关联以下 AC：" + ", ".join(missing)]
    return []


def check_pr_body(text: str, spec_id: str) -> list[str]:
    errors: list[str] = []
    for aliases in PR_SECTIONS:
        if not has_section(text, aliases):
            errors.append(f"PR_BODY.md 缺少章节：{aliases[0]}")
    errors.extend(placeholder_errors("PR_BODY.md", text))
    if spec_id not in text:
        errors.append(f"PR_BODY.md 没有引用 Spec：{spec_id}")
    return errors


def prd_index_path(root: Path, config: dict[str, Any]) -> Path:
    raw = Path(str(config["prd_index"]))
    return raw if raw.is_absolute() else root / raw


def prd_index_rows(text: str) -> list[dict[str, str]]:
    header: Optional[list[str]] = None
    rows: list[dict[str, str]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            continue
        cells = split_table_row(stripped)
        if "工作项id" in {normalize_column(cell) for cell in cells}:
            header = cells
            continue
        if header is None or not cells:
            continue
        row = {
            normalize_column(header[index]): cells[index].strip()
            for index in range(min(len(header), len(cells)))
        }
        if any(row.values()):
            rows.append(row)
    return rows


def prd_index_source(text: str) -> str:
    match = re.search(r"(?im)^\s*(?:[-*]\s*)?source\s*[:：]\s*(workitem|repo)\s*$", text)
    return match.group(1).lower() if match else ""


def ensure_prd_index(
    root: Path,
    config: dict[str, Any],
    spec_id: str,
    work_item: str,
    title: str,
    issue: Optional[str],
) -> Path:
    path = prd_index_path(root, config)
    text = read_text(path)
    if not text:
        text = (
            "# PRD 追溯索引\n\n"
            "<!-- source: workitem 表示 PRD 全文留在工作项系统；"
            "source: repo 表示 docs/prd.md 为权威源。 -->\n\n"
            f"- source: {config.get('prd_mode', 'workitem')}\n"
            f"- updated: {now()}\n\n"
            "| 工作项 ID | PRD 链接/路径 | PRD 版本 | FEAT | Spec ID | 摘要 | 澄清标记 |\n"
            "| --- | --- | --- | --- | --- | --- | --- |\n"
        )
    if spec_id not in text:
        numbers = [
            int(match.group(1))
            for match in re.finditer(r"\bFEAT-([0-9]{3})\b", text)
        ]
        feat = f"FEAT-{max(numbers, default=0) + 1:03d}"
        safe_title = " ".join(title.split()).replace("|", "\\|")
        link = (issue or "N/A").replace("|", "\\|")
        text += (
            f"| {work_item} | {link} | current | {feat} | {spec_id} | "
            f"{safe_title} | 0 |\n"
        )
        write_text(path, text)
    return path


def check_prd_index(
    root: Path,
    config: dict[str, Any],
    state: dict[str, Any],
    spec_text: str,
) -> list[str]:
    if not config.get("require_prd_index"):
        return []
    path = prd_index_path(root, config)
    text = read_text(path)
    if not text:
        return [f"缺少 PRD 追溯索引：{path.relative_to(root).as_posix()}"]
    errors: list[str] = []
    source = prd_index_source(text)
    expected = str(config.get("prd_mode", "workitem")).lower()
    if not source:
        errors.append("docs/prd-index.md 头部缺少 source: workitem 或 source: repo")
    elif source != expected:
        errors.append(
            f"docs/prd-index.md 的 source={source} 与 config.prd_mode={expected} 不一致"
        )
    if CLARIFY_RE.search(text):
        errors.append("docs/prd-index.md 还有 [NEEDS CLARIFICATION] 标记")
    spec_id = str(state.get("spec_id", ""))
    work_item = metadata_value(spec_text, "工作项 ID", "工作项ID") or str(
        state.get("work_item") or state.get("issue") or ""
    )
    rows = prd_index_rows(text)
    if spec_id and not any(row.get("specid") == spec_id for row in rows):
        errors.append(f"docs/prd-index.md 没有登记 Spec {spec_id}")
    if work_item and not any(row.get("工作项id") == work_item for row in rows):
        errors.append(f"docs/prd-index.md 没有登记工作项 {work_item}")
    if source == "repo":
        prd_path = root / "docs" / "prd.md"
        if not prd_path.is_file():
            errors.append("source: repo 时必须存在 docs/prd.md")
    return errors


def check_duplicate_spec_files(root: Path, config: dict[str, Any]) -> list[str]:
    base = spec_root(root, config)
    if not base.exists():
        return []
    errors: list[str] = []
    duplicate = re.compile(
        r"^(?:spec|design|tasks)[_-](?:v[0-9]+|final|new|latest)\.md$",
        re.IGNORECASE,
    )
    for path in base.rglob("*.md"):
        if duplicate.match(path.name):
            errors.append(
                "禁止创建重复版本文件："
                + path.relative_to(root).as_posix()
            )
    return errors


def read_gates(directory: Path) -> list[str]:
    text = read_text(directory / "gates.md")
    gates: list[str] = []
    for line in text.splitlines():
        match = re.match(r"^\|\s*(G\d+)\s*\|", line)
        if match:
            gates.append(match.group(1))
    return gates


def required_gates(state_name: str) -> list[str]:
    return {
        "DRAFT": [],
        "SPEC_READY": ["G0", "G1"],
        "DESIGN_READY": ["G0", "G1", "G2"],
        "TASKS_READY": ["G0", "G1", "G2", "G3"],
        "IMPLEMENTING": ["G0", "G1", "G2", "G3"],
        "VERIFYING": ["G0", "G1", "G2", "G3", "G4"],
        "PR_READY": ["G0", "G1", "G2", "G3", "G4", "G5"],
        "MERGED": ["G0", "G1", "G2", "G3", "G4", "G5"],
    }.get(state_name, [])


def gate_report_path(
    root: Path, config: dict[str, Any], spec_id: str, gate: str
) -> Path:
    number = gate.lstrip("G")
    return report_root(root, config) / spec_id / f"gate{number}-report.md"


def gate_report_status(path: Path) -> str:
    text = read_text(path)
    if not text:
        return ""
    for line in text.splitlines():
        match = re.match(r"^\|\s*总体结果\s*\|\s*([^|]+)\|", line)
        if match:
            return match.group(1).strip().upper()
    return ""


def check_gates(
    root: Path, config: dict[str, Any], directory: Path, state_name: str
) -> list[str]:
    errors: list[str] = []
    state = load_json(directory / "state.json")
    spec_id = str(state.get("spec_id", directory.name))
    for gate in required_gates(state_name):
        path = gate_report_path(root, config, spec_id, gate)
        if not path.is_file():
            errors.append(
                f"缺少 Gate 报告：{path.relative_to(root).as_posix()}"
            )
            continue
        status = gate_report_status(path)
        if status != "PASS":
            errors.append(
                f"{path.relative_to(root).as_posix()} 的总体结果不是 PASS（当前 {status or '空'}）"
            )
        report = read_text(path)
        if spec_id not in report:
            errors.append(f"{path.relative_to(root).as_posix()} 没有引用 Spec ID {spec_id}")
    return errors


def append_gate(
    directory: Path,
    gate: str,
    state_name: str,
    mode: str,
    evidence: str,
    status: str = "PASS",
) -> None:
    path = directory / "gates.md"
    text = read_text(path)
    if not text:
        text = (
            "# Gate 记录\n\n"
            "| Gate | State | Mode | Result | Evidence | At |\n"
            "| --- | --- | --- | --- | --- | --- |\n"
        )
    safe_evidence = " ".join(str(evidence).split()).replace("|", "\\|")
    row = (
        f"| {gate} | {state_name} | {mode} | {status} | "
        f"{safe_evidence} | {now()} |\n"
    )
    if not text.endswith("\n"):
        text += "\n"
    write_text(path, text + row)


def write_gate_report(
    root: Path,
    config: dict[str, Any],
    directory: Path,
    state: dict[str, Any],
    gate: str,
    state_name: str,
    mode: str,
    evidence: str,
    checks: list[tuple[str, str, str]],
    errors: Optional[list[str]] = None,
) -> Path:
    spec_id = str(state.get("spec_id", directory.name))
    stage, label = GATE_STAGES.get(gate, ("UNKNOWN", "未知 Gate"))
    status = "FAILED" if errors else "PASS"
    spec_text = read_text(directory / "spec.md")
    design_text = read_text(directory / "design.md")
    tasks_text = read_text(directory / "tasks.md")
    acs = extract_acs(spec_text)
    tasks = parse_tasks(tasks_text)
    task_for_ac: dict[str, str] = {}
    for task in tasks:
        for ac in task["acs"]:
            task_for_ac.setdefault(ac, str(task["id"]))
    work_item = metadata_value(spec_text, "工作项 ID", "工作项ID") or str(
        state.get("work_item") or state.get("issue") or "N/A"
    )
    product_type = metadata_value(spec_text, "产品类型") or str(
        state.get("product_type") or "传统产品"
    )
    relative_dir = directory.relative_to(root).as_posix()
    report_path = gate_report_path(root, config, spec_id, gate)

    lines = [
        f"# {gate} {label}报告",
        "",
        "## 1. 元数据",
        "",
        "| 项 | 内容 |",
        "| --- | --- |",
        f"| Spec ID | {spec_id} |",
        f"| 工作项 ID | {work_item} |",
        f"| 产品类型 | {product_type} |",
        f"| 阶段 | {stage} |",
        f"| Gate | GATE_{gate.lstrip('G')} |",
        f"| 检查时间 | {now()} |",
        f"| 执行模式 | {mode} |",
        f"| 总体结果 | {status} |",
        "",
        "## 2. 检查项",
        "",
        "| 检查项 | 结果 | 证据 |",
        "| --- | --- | --- |",
    ]
    for name, result, detail in checks:
        safe_detail = " ".join(str(detail).split()).replace("|", "\\|")
        lines.append(f"| {name} | {result} | {safe_detail} |")
    if not checks:
        lines.append("| 无自动检查项 | PASS | 由人工评审 |")

    lines.extend(
        [
            "",
            "## 3. AC 清单",
            "",
            "| AC ID | 关联 Task | 状态 | 证据 |",
            "| --- | --- | --- | --- |",
        ]
    )
    ac_status = GATE_AC_STATUS.get(gate, "UNKNOWN")
    for ac in acs:
        lines.append(
            f"| {ac} | {task_for_ac.get(ac, '-')} | {ac_status} | "
            f"`{relative_dir}/spec.md` / `{relative_dir}/verification.md` |"
        )
    if not acs:
        lines.append("| - | - | - | 当前阶段尚无 AC |")

    lines.extend(
        [
            "",
            "## 4. 产物",
            "",
            f"- `{relative_dir}/spec.md`",
            f"- `{relative_dir}/design.md`",
            f"- `{relative_dir}/tasks.md`",
            f"- `{relative_dir}/verification.md`",
            f"- `{relative_dir}/PR_BODY.md`（G5 生成）",
            "",
            "## 5. 证据与人工确认",
            "",
            f"- 执行证据：{evidence.strip() or 'N/A'}",
            f"- 执行模式：{mode}",
            f"- 人工确认：{'已确认' if mode == 'manual' else '无需额外人工确认'}",
            "",
            "## 6. 问题与建议",
            "",
        ]
    )
    if errors:
        lines.extend(f"- BLOCK：{error}" for error in errors)
    else:
        lines.append("- 无阻断问题。")
    lines.append("")
    write_text(report_path, "\n".join(lines))
    return report_path


def record_gate(
    root: Path,
    config: dict[str, Any],
    directory: Path,
    state: dict[str, Any],
    gate: str,
    state_name: str,
    mode: str,
    evidence: str,
    checks: list[tuple[str, str, str]],
    errors: Optional[list[str]] = None,
) -> None:
    status = "FAILED" if errors else "PASS"
    append_gate(directory, gate, state_name, mode, evidence, status)
    write_gate_report(
        root,
        config,
        directory,
        state,
        gate,
        state_name,
        mode,
        evidence,
        checks,
        errors,
    )


def gate_mode(
    config: dict[str, Any], gate: str, state: dict[str, Any], human: bool
) -> str:
    if human:
        return "manual"
    policy = str(config.get("gates", {}).get(gate, "auto"))
    if policy == "human":
        raise SddError(f"{gate} 需要人工审批；重跑时加 --human")
    risk_labels = set(str(item) for item in state.get("risk_labels", []))
    stop_labels = set(str(item) for item in config.get("risk_stop", []))
    is_risky = state.get("risk") == "high" or bool(risk_labels & stop_labels)
    if policy == "auto_if_no_risk" and is_risky:
        raise SddError(
            f"{gate} 因 risk={state.get('risk')} labels={sorted(risk_labels)} "
            "需要人工审批；重跑时加 --human"
        )
    return "auto"


def check_git(root: Path, spec_id: str) -> list[str]:
    if not (root / ".git").exists():
        return ["--check-git 需要 Git 仓库"]
    result = subprocess.run(
        ["git", "log", "-20", "--pretty=%B"],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        return ["git log 执行失败：" + result.stderr.strip()]
    if f"Spec-Id: {spec_id}" not in result.stdout:
        return [f"最近 20 个 commit 中没有 `Spec-Id: {spec_id}` trailer"]
    return []


def run_checks(
    root: Path,
    config: dict[str, Any],
    directory: Path,
    state: dict[str, Any],
    stage: str,
    check_git_trailer: bool = False,
) -> tuple[list[str], str]:
    if stage == "auto":
        current = str(state.get("state", "DRAFT"))
        stage = {
            "DRAFT": "spec",
            "SPEC_READY": "spec",
            "DESIGN_READY": "design",
            "TASKS_READY": "tasks",
            "IMPLEMENTING": "tasks",
            "VERIFYING": "verify",
            "PR_READY": "ci",
            "MERGED": "ci",
        }.get(current, "spec")

    spec_id = str(state.get("spec_id", directory.name))
    spec_text = read_text(directory / "spec.md")
    design_text = read_text(directory / "design.md")
    tasks_text = read_text(directory / "tasks.md")
    verification_text = read_text(directory / "verification.md")
    spec_errors, spec_acs = check_spec(spec_text, spec_id)
    errors: list[str] = []

    if stage in {"spec", "design", "tasks", "verify", "ci"}:
        errors.extend(spec_errors)
    if stage in {"design", "tasks", "verify", "ci"}:
        errors.extend(check_design(design_text, spec_acs))
    if stage in {"tasks", "verify", "ci"}:
        errors.extend(check_tasks(tasks_text, spec_acs, config))
    if stage in {"verify", "ci"}:
        errors.extend(check_verification(verification_text, spec_acs))
        errors.extend(check_test_coverage(root, config, spec_acs))
    if stage == "ci":
        if state.get("state") not in {"PR_READY", "MERGED"}:
            errors.append("CI 检查要求状态为 PR_READY 或 MERGED")
        errors.extend(check_pr_body(read_text(directory / "PR_BODY.md"), spec_id))
        errors.extend(
            check_gates(root, config, directory, str(state.get("state", "DRAFT")))
        )
        errors.extend(check_prd_index(root, config, state, spec_text))
        errors.extend(check_duplicate_spec_files(root, config))
        if check_git_trailer:
            errors.extend(check_git(root, spec_id))

    return errors, stage


def build_next_action(
    root: Path, directory: Path, state: dict[str, Any]
) -> dict[str, Any]:
    state_name = str(state.get("state", "DRAFT"))
    spec_id = str(state.get("spec_id", directory.name))
    relative_dir = directory.relative_to(root).as_posix()
    base: dict[str, Any] = {
        "spec": spec_id,
        "state": state_name,
        "spec_dir": relative_dir,
        "step_id": f"{spec_id}:{state_name}",
        "kind": "state",
        "decision_required": False,
        "question": None,
        "options": [],
        "expected_result": "success",
    }

    if state_name == "DRAFT":
        base.update(
            {
                "action": "write_spec",
                "kind": "artifact",
                "step_id": f"{spec_id}:spec",
                "expected_result": "artifact_submitted",
                "prompt": "sdd/prompts/spec.md",
                "artifact": f"{relative_dir}/spec.md",
                "done_when": (
                    "sdd check --stage spec 通过，然后由人类运行 "
                    "python -m sdd approve --human"
                ),
            }
        )
    elif state_name == "SPEC_READY":
        base.update(
            {
                "action": "write_design",
                "kind": "artifact",
                "step_id": f"{spec_id}:design",
                "expected_result": "artifact_submitted",
                "prompt": "sdd/prompts/design.md",
                "artifact": f"{relative_dir}/design.md",
                "done_when": "sdd check --stage design 通过，然后 sdd complete --evidence ...",
            }
        )
    elif state_name == "DESIGN_READY":
        base.update(
            {
                "action": "write_tasks",
                "kind": "artifact",
                "step_id": f"{spec_id}:tasks",
                "expected_result": "artifact_submitted",
                "prompt": "sdd/prompts/tasks.md",
                "artifact": f"{relative_dir}/tasks.md",
                "done_when": "sdd check --stage tasks 通过，然后 sdd complete --evidence ...",
            }
        )
    elif state_name == "TASKS_READY":
        base.update(
            {
                "action": "start_implementation",
                "kind": "transition",
                "step_id": f"{spec_id}:start_implementation",
                "expected_result": "transition_completed",
                "prompt": "sdd/prompts/driver.md",
                "done_when": "sdd complete --evidence '开始实现'",
            }
        )
    elif state_name == "IMPLEMENTING":
        tasks = parse_tasks(read_text(directory / "tasks.md"))
        pending = [task for task in tasks if not task["done"]]
        if pending:
            task = pending[0]
            base.update(
                {
                    "action": "implement_task",
                    "kind": "task",
                    "step_id": f"{spec_id}:{task['id']}",
                    "expected_result": "task_completed",
                    "prompt": "sdd/prompts/task.md",
                    "artifact": f"{relative_dir}/tasks.md",
                    "task": task["id"],
                    "acceptance_criteria": task["acs"],
                    "task_description": task["description"],
                    "done_when": (
                        f"失败测试先行、实现完成、目标/模块测试通过，然后 "
                        f"sdd complete --task {task['id']} --evidence ..."
                    ),
                }
            )
        else:
            base.update(
                {
                    "action": "finish_implementation",
                    "kind": "transition",
                    "step_id": f"{spec_id}:finish_implementation",
                    "expected_result": "transition_completed",
                    "prompt": "sdd/prompts/driver.md",
                    "done_when": "sdd complete --evidence '所有任务完成'",
                }
            )
    elif state_name == "VERIFYING":
        base.update(
            {
                "action": "run_verification",
                "kind": "artifact",
                "step_id": f"{spec_id}:verification",
                "expected_result": "artifact_submitted",
                "prompt": "sdd/prompts/verify.md",
                "artifact": f"{relative_dir}/verification.md",
                "done_when": "sdd verify 通过、verification.md 填完、sdd complete --evidence ...",
            }
        )
    elif state_name == "PR_READY":
        base.update(
            {
                "action": "open_pr",
                "kind": "human_checkpoint",
                "step_id": f"{spec_id}:pr_merge",
                "expected_result": "human_merge",
                "prompt": "sdd/prompts/pr.md",
                "artifact": f"{relative_dir}/PR_BODY.md",
                "done_when": "用 PR_BODY.md 开 PR，记录 URL；不要合并",
            }
        )
    elif state_name == "MERGED":
        base.update(
            {
                "action": "done",
                "kind": "done",
                "step_id": f"{spec_id}:done",
                "expected_result": "done",
                "done_when": "Spec 已合并",
            }
        )
    elif state_name == "BLOCKED":
        base.update(
            {
                "action": "resolve_blocker",
                "kind": "decision",
                "step_id": f"{spec_id}:blocked",
                "decision_required": True,
                "question": state.get("blocked_reason") or "请回答阻塞问题后解除阻塞",
                "options": ["答案已提供", "取消本次工作"],
                "expected_result": "human_answer",
                "prompt": "sdd/prompts/blocked.md",
                "done_when": "人类回答后运行 sdd unblock --evidence ...",
            }
        )
    else:
        raise SddError(f"未知状态：{state_name}")
    if base.get("prompt"):
        base["prompt_file"] = base["prompt"]
    return base


def ensure_layout(root: Path, config: dict[str, Any]) -> None:
    spec_root(root, config).mkdir(parents=True, exist_ok=True)
    report_root(root, config).mkdir(parents=True, exist_ok=True)
    prd_index_path(root, config).parent.mkdir(parents=True, exist_ok=True)


def allocate_spec_id(root: Path, config: dict[str, Any], domain: str) -> str:
    if not DOMAIN_RE.match(domain):
        raise SddError("域编码必须是大写字母开头的字母/数字，例如 ORDER、PAY")
    base = spec_root(root, config)
    numbers = [0]
    if base.exists():
        for path in base.iterdir():
            match = re.fullmatch(rf"SPEC-{re.escape(domain)}-([0-9]{{3}})", path.name)
            if match:
                numbers.append(int(match.group(1)))
    return f"SPEC-{domain}-{max(numbers) + 1:03d}"


def command_new(args: argparse.Namespace, root: Path, config: dict[str, Any]) -> int:
    work_item = (args.work_item or "").strip()
    if not work_item:
        raise SddError(
            "new 需要 --work-item（公司工作项 ID，例如 srdcloud-553377）；"
            "它是需求追溯链的起点"
        )
    if work_item.startswith("%"):
        raise SddError("工作项 ID 不要带前导 %，commit 前缀才使用 %")
    if not WORK_ITEM_RE.match(work_item):
        raise SddError(
            "工作项 ID 格式应类似 srdcloud-553377（字母/数字/点/下划线/短横线，末尾为数字）"
        )

    if args.spec_id:
        spec_id = args.spec_id
        if not SPEC_ID_RE.match(spec_id):
            raise SddError("Spec ID 格式应为 SPEC-<域>-<三位序号>，例如 SPEC-ORDER-001")
        if args.domain:
            expected_prefix = f"SPEC-{args.domain.upper()}-"
            if not spec_id.startswith(expected_prefix):
                raise SddError(f"Spec ID 必须以 {expected_prefix} 开头")
    else:
        if not args.domain:
            raise SddError("未提供 Spec ID 时必须提供 --domain，例如 --domain ORDER")
        spec_id = allocate_spec_id(root, config, args.domain.upper())

    ensure_layout(root, config)
    directory = spec_dir_for(root, config, spec_id)
    if directory.exists():
        raise SddError(f"Spec 已存在：{directory}")

    product_type = args.product_type or "传统产品"
    adapt = {
        "传统产品": "核心骨架",
        "AI辅助·L2": "核心骨架＋AI扩展",
        "AI增强·L3": "核心骨架＋AI扩展",
        "AI原生·L4": "核心骨架＋AI扩展＋AI原生扩展",
    }.get(product_type, "核心骨架")
    context = {
        "SPEC_ID": spec_id,
        "TITLE": args.title,
        "WORK_ITEM": work_item,
        "ISSUE": args.issue or "N/A",
        "DATE": now(),
        "PRODUCT_TYPE": product_type,
        "TEMPLATE_ADAPT": adapt,
        "AUTHOR": args.author or "SDD Agent",
    }
    directory.mkdir(parents=True, exist_ok=False)
    for name in ("spec.md", "design.md", "tasks.md", "verification.md"):
        write_text(directory / name, render_template(root, name, context))
    write_text(directory / "gates.md", render_template(root, "gates.md", context))
    write_text(directory / "decisions.md", render_template(root, "decisions.md", context))
    (directory / "adrs").mkdir(exist_ok=True)
    (directory / "api").mkdir(exist_ok=True)
    state = {
        "spec_id": spec_id,
        "title": args.title,
        "work_item": work_item,
        "issue": args.issue,
        "product_type": product_type,
        "risk": args.risk,
        "risk_labels": args.risk_label or [],
        "state": "DRAFT",
        "created_at": now(),
        "updated_at": now(),
        "pr_url": None,
        "history": [
            {
                "state": "DRAFT",
                "at": now(),
                "evidence": "created",
            }
        ],
    }
    save_state(directory, state)
    ensure_prd_index(root, config, spec_id, work_item, args.title, args.issue)
    print(f"[sdd] created {directory.relative_to(root)}")
    print(f"[sdd] work item: {work_item}")
    print("[sdd] next: python -m sdd next --spec " + spec_id)
    return 0


def command_status(
    args: argparse.Namespace, root: Path, config: dict[str, Any]
) -> int:
    spec_id, directory, state = resolve_spec(root, config, args.spec)
    action = build_next_action(root, directory, state)
    if args.json:
        print(json.dumps({"state": state, "next": action}, ensure_ascii=False, indent=2))
        return 0
    print(f"Spec:   {spec_id}")
    print(f"Title:  {state.get('title', '')}")
    print(f"State:  {state.get('state')}")
    print(f"Risk:   {state.get('risk', 'low')}")
    print(f"Dir:    {directory.relative_to(root)}")
    print(f"Next:   {action['action']}")
    if action.get("task"):
        print(f"Task:   {action['task']} ({', '.join(action.get('acceptance_criteria', []))})")
    print(f"Done:   {action.get('done_when', '')}")
    return 0


def command_next(args: argparse.Namespace, root: Path, config: dict[str, Any]) -> int:
    _, directory, state = resolve_spec(root, config, args.spec)
    action = build_next_action(root, directory, state)
    if args.json:
        print(json.dumps(action, ensure_ascii=False, indent=2))
    else:
        print(f"{action['action']}")
        for key in (
            "step_id",
            "kind",
            "task",
            "artifact",
            "prompt",
            "decision_required",
            "question",
            "options",
            "done_when",
        ):
            if action.get(key):
                print(f"{key}: {action[key]}")
    return 0


def command_events(
    args: argparse.Namespace, root: Path, config: dict[str, Any]
) -> int:
    spec_id, directory, state = resolve_spec(root, config, args.spec)
    events = read_event_log(directory)
    source = "events.jsonl"
    if len(events) < len(
        [entry for entry in state.get("history", []) if isinstance(entry, dict)]
    ):
        events = derive_events(state)
        source = "state.json.history"
    payload = {
        "ok": True,
        "kind": "events",
        "spec": spec_id,
        "source": source,
        "count": len(events),
        "events": events,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    for event in events:
        print(
            f"{event.get('seq')}  {event.get('at')}  "
            f"{event.get('event')}  "
            f"{event.get('from_state')} -> {event.get('to_state')}  "
            f"{event.get('evidence', '')}"
        )
    return 0


def command_board(args: argparse.Namespace, root: Path, config: dict[str, Any]) -> int:
    """Show a deterministic, read-only view of specs and task lanes."""
    base = spec_root(root, config)
    directories = (
        sorted(
            item
            for item in base.iterdir()
            if item.is_dir() and (item / "state.json").is_file()
        )
        if base.exists()
        else []
    )
    specs: list[dict[str, Any]] = []
    for directory in directories:
        state = load_json(directory / "state.json")
        spec_id = str(state.get("spec_id", directory.name))
        try:
            action = build_next_action(root, directory, state)
        except SddError as exc:
            action = {
                "action": "unknown",
                "step_id": f"{spec_id}:unknown",
                "error": str(exc),
            }
        tasks = parse_tasks(read_text(directory / "tasks.md"))
        statuses = [str(task.get("status", "Todo")) for task in tasks]
        events = read_event_log(directory)
        history_count = len(
            [entry for entry in state.get("history", []) if isinstance(entry, dict)]
        )
        if len(events) < history_count:
            events = derive_events(state)
        specs.append(
            {
                "spec": spec_id,
                "title": state.get("title", ""),
                "state": state.get("state", "UNKNOWN"),
                "next": action,
                "events_count": len(events),
                "last_event": events[-1] if events else None,
                "tasks": [
                    {
                        "id": task["id"],
                        "description": task["description"],
                        "status": task.get("status", "Todo"),
                        "acs": task.get("acs", []),
                        "depends": task.get("depends", []),
                    }
                    for task in tasks
                ],
                "task_counts": {
                    "total": len(tasks),
                    "todo": statuses.count("Todo"),
                    "in_progress": statuses.count("In Progress"),
                    "done": statuses.count("Done"),
                },
            }
        )

    payload = {"ok": True, "kind": "board", "specs": specs}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    if not specs:
        print("[sdd] no specs found")
        return 0
    for item in specs:
        counts = item["task_counts"]
        print(
            f"{item['spec']}  [{item['state']}]  "
            f"next={item['next'].get('action')}  "
            f"tasks={counts['done']}/{counts['total']} done  "
            f"events={item['events_count']}"
        )
        for task in item["tasks"]:
            print(
                f"  {task['id']}  [{task['status']}]  {task['description']}"
            )
        if not item["tasks"]:
            print("  (no tasks yet)")
    return 0


def command_check(
    args: argparse.Namespace, root: Path, config: dict[str, Any]
) -> int:
    if getattr(args, "all", False):
        if args.spec:
            raise SddError("--all 与 --spec 不能同时使用")
        base = spec_root(root, config)
        directories = (
            sorted(
                item
                for item in base.iterdir()
                if item.is_dir() and (item / "state.json").is_file()
            )
            if base.exists()
            else []
        )
        if not directories:
            if args.json:
                print(
                    json.dumps(
                        {"ok": True, "specs": [], "skipped": True},
                        ensure_ascii=False,
                        indent=2,
                    )
                )
            else:
                print("[sdd] no specs found; skip artifact check")
            return 0

        results: list[dict[str, Any]] = []
        for directory in directories:
            state = load_json(directory / "state.json")
            spec_id = str(state.get("spec_id", directory.name))
            errors, resolved_stage = run_checks(
                root,
                config,
                directory,
                state,
                args.stage,
                args.check_git,
            )
            results.append(
                {
                    "spec": spec_id,
                    "stage": resolved_stage,
                    "ok": not errors,
                    "errors": errors,
                }
            )
            if not args.json:
                if errors:
                    print(f"[sdd] {spec_id} check failed (stage={resolved_stage})")
                    for error in errors:
                        print(f"- {error}")
                else:
                    print(f"[sdd] {spec_id} check passed (stage={resolved_stage})")

        ok = all(item["ok"] for item in results)
        if args.json:
            print(
                json.dumps(
                    {"ok": ok, "specs": results},
                    ensure_ascii=False,
                    indent=2,
                )
            )
        elif ok:
            print(f"[sdd] all {len(results)} spec(s) passed")
        else:
            print(f"[sdd] {sum(not item['ok'] for item in results)} spec(s) failed")
        return 0 if ok else 1

    _, directory, state = resolve_spec(root, config, args.spec)
    errors, resolved_stage = run_checks(
        root, config, directory, state, args.stage, args.check_git
    )
    if args.json:
        print(
            json.dumps(
                {
                    "ok": not errors,
                    "stage": resolved_stage,
                    "errors": errors,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    elif errors:
        print(f"[sdd] check failed (stage={resolved_stage})")
        for error in errors:
            print(f"- {error}")
    else:
        print(f"[sdd] check passed (stage={resolved_stage})")
    return 1 if errors else 0


def command_approve(
    args: argparse.Namespace, root: Path, config: dict[str, Any]
) -> int:
    spec_id, directory, state = resolve_spec(root, config, args.spec)
    if state.get("state") != "DRAFT":
        raise SddError(f"只有 DRAFT 状态可以 approve，当前是 {state.get('state')}")
    if not args.human:
        raise SddError("approve 需要 --human；agent 不允许代替人类确认需求")
    errors, _ = run_checks(root, config, directory, state, "spec")
    spec_text = read_text(directory / "spec.md")
    errors.extend(check_prd_index(root, config, state, spec_text))
    if errors:
        for error in errors:
            eprint(f"- {error}")
        record_gate(
            root,
            config,
            directory,
            state,
            "G0",
            "SPEC_READY",
            "manual",
            args.evidence or "requirement confirmed by human",
            [("需求侧准入", "FAILED", "spec 或 prd-index 校验未通过")],
            errors,
        )
        raise SddError("spec 校验失败，不能 approve")
    evidence = args.evidence or "requirement confirmed by human"
    record_gate(
        root,
        config,
        directory,
        state,
        "G0",
        "SPEC_READY",
        "manual",
        evidence,
        [
            ("工作项 ID 已登记", "PASS", f"work_item={state.get('work_item')}"),
            ("PRD 追溯映射", "PASS", "docs/prd-index.md 已登记当前 Spec"),
            ("澄清标记清零", "PASS", "[NEEDS CLARIFICATION] = 0"),
            ("范围声明", "PASS", "In-Scope / Out-of-Scope 已填写"),
        ],
    )
    record_gate(
        root,
        config,
        directory,
        state,
        "G1",
        "SPEC_READY",
        "auto",
        "spec check passed",
        [
            ("Spec 章节齐备", "PASS", "核心 1–10 章存在"),
            ("FR/AC 映射", "PASS", "每个 FR 至少一条 AC"),
            ("AC 可测试性", "PASS", "Given/When/Then + 执行路径"),
            ("占位符/澄清标记", "PASS", "TODO、占位符、NEEDS CLARIFICATION 均为 0"),
        ],
    )
    transition(state, "SPEC_READY", evidence, gate="G0/G1")
    save_state(directory, state)
    print(f"[sdd] {spec_id} approved -> SPEC_READY")
    return 0


def mark_task_status(
    text: str, task_id: str, status: str, commit: Optional[str] = None
) -> tuple[str, bool]:
    lines: list[str] = []
    found = False
    header: Optional[list[str]] = None
    status_index: Optional[int] = None
    commit_index: Optional[int] = None
    for line in text.splitlines():
        match = TASK_RE.match(line)
        if match and match.group("id") == task_id:
            found = True
            if status == "Done":
                line = re.sub(r"\[\s\]", "[x]", line, count=1)
            else:
                line = re.sub(r"\[[xX]\]", "[ ]", line, count=1)
        elif line.strip().startswith(f"| {task_id} |"):
            cells = split_table_row(line)
            if status_index is None:
                status_index = 8
                commit_index = 9
            if len(cells) > status_index:
                cells[status_index] = status
            if commit and len(cells) > (commit_index or 9):
                cells[commit_index or 9] = commit
            if len(cells) > 8:
                line = "| " + " | ".join(cells) + " |"
                found = True
        elif line.strip().startswith("|") and line.strip().endswith("|"):
            cells = split_table_row(line)
            if "taskid" in {normalize_column(cell) for cell in cells}:
                header = cells
                status_index = column_index(header, "status")
                commit_index = column_index(header, "commit")
        lines.append(line)
    return "\n".join(lines) + "\n", found


def append_to_section(
    text: str, aliases: tuple[str, ...], content: str
) -> str:
    lines = text.splitlines()
    wanted = {normalize_heading(alias) for alias in aliases}
    start: Optional[int] = None
    end = len(lines)
    for index, line in enumerate(lines):
        match = re.match(r"^\s*#{1,6}\s+(.*)$", line)
        if not match:
            continue
        if start is None and normalize_heading(match.group(1)) in wanted:
            start = index + 1
            continue
        if start is not None:
            end = index
            break
    if start is None:
        if text and not text.endswith("\n"):
            text += "\n"
        return text + "\n" + content.strip() + "\n"
    before = lines[:start]
    after = lines[end:]
    return "\n".join(before + [""] + content.strip().splitlines() + [""] + after) + "\n"


def append_verification_evidence(
    directory: Path,
    title: str,
    body: str,
    section: tuple[str, ...] = ("结果", "Results"),
) -> None:
    path = directory / "verification.md"
    text = read_text(path)
    if not text:
        text = "# 验证\n"
    block = (
        f"- Evidence recorded: {title}\n\n"
        f"### {title}\n\n- At: {now()}\n\n{body.strip()}\n"
    )
    text = append_to_section(text, section, block)
    write_text(path, text)


def command_complete(
    args: argparse.Namespace, root: Path, config: dict[str, Any]
) -> int:
    spec_id, directory, state = resolve_spec(root, config, args.spec)
    evidence = args.evidence.strip()
    if not evidence:
        raise SddError("complete 需要 --evidence，记录实际做了什么/检查了什么")

    if args.task:
        if state.get("state") != "IMPLEMENTING":
            raise SddError(f"只有 IMPLEMENTING 状态可以完成 task，当前是 {state.get('state')}")
        tasks_text = read_text(directory / "tasks.md")
        tasks_before = parse_tasks(tasks_text)
        target = next((task for task in tasks_before if task["id"] == args.task), None)
        if target is None:
            raise SddError(f"找不到任务：{args.task}")
        if target.get("done"):
            raise SddError(f"任务 {args.task} 已经是 Done")
        started = any(
            item.get("action") == "task_start" and item.get("task") == args.task
            for item in state.get("history", [])
        )
        if (
            str(target.get("status", "")).strip().lower() != "in progress"
            and not started
        ):
            raise SddError(
                f"任务 {args.task} 还没有开始；先运行 "
                f"`sdd start --spec {spec_id} --task {args.task}`"
            )
        updated, found = mark_task_status(tasks_text, args.task, "Done", args.commit)
        if not found:
            raise SddError(f"找不到任务：{args.task}")
        write_text(directory / "tasks.md", updated)
        append_verification_evidence(directory, f"Task {args.task}", evidence)
        add_history(state, "IMPLEMENTING", evidence, action="task_done", task=args.task)
        tasks = parse_tasks(updated)
        if tasks and all(task["done"] for task in tasks):
            mode = gate_mode(config, "G4", state, args.human)
            verification_text = read_text(directory / "verification.md")
            missing_evidence = [
                task["id"] for task in tasks if task["id"] not in verification_text
            ]
            errors = []
            if missing_evidence:
                errors.append(
                    "以下 Task 没有验证证据：" + ", ".join(missing_evidence)
                )
            errors.extend(task_table_error(tasks, check_spec(
                read_text(directory / "spec.md"), spec_id
            )[1], config))
            if errors:
                record_gate(
                    root,
                    config,
                    directory,
                    state,
                    "G4",
                    "VERIFYING",
                    mode,
                    evidence,
                    [("Task 完成与证据", "FAILED", "见问题清单")],
                    errors,
                )
                for error in errors:
                    eprint(f"- {error}")
                save_state(directory, state)
                raise SddError("Gate 4 校验失败")
            record_gate(
                root,
                config,
                directory,
                state,
                "G4",
                "VERIFYING",
                mode,
                "all tasks completed",
                [
                    ("Task 全部完成", "PASS", f"{len(tasks)} 个 Task 状态均为 Done"),
                    ("Task 验证证据", "PASS", "verification.md 已记录每个 Task"),
                    ("Task 测试映射", "PASS", "每个 Task 有测试类/方法和命令"),
                ],
            )
            transition(state, "VERIFYING", "all tasks completed", gate="G4")
        save_state(directory, state)
        print(f"[sdd] {spec_id} task {args.task} completed -> {state['state']}")
        return 0

    current = str(state.get("state", "DRAFT"))
    if current == "DRAFT":
        raise SddError(
            "DRAFT 状态需要人类运行 `python -m sdd approve --human --evidence ...`"
        )
    if current == "SPEC_READY":
        spec_text = read_text(directory / "spec.md")
        _, spec_acs = check_spec(spec_text, spec_id)
        errors = check_design(read_text(directory / "design.md"), spec_acs)
        if errors:
            for error in errors:
                eprint(f"- {error}")
            record_gate(
                root,
                config,
                directory,
                state,
                "G2",
                "DESIGN_READY",
                "auto",
                evidence,
                [("Design 完整性", "FAILED", "见问题清单")],
                errors,
            )
            raise SddError("design 校验失败")
        mode = gate_mode(config, "G2", state, args.human)
        record_gate(
            root,
            config,
            directory,
            state,
            "G2",
            "DESIGN_READY",
            mode,
            evidence,
            [
                ("Design 章节齐备", "PASS", "公司 14 章骨架"),
                ("AC 设计覆盖", "PASS", "全部 AC 在 design.md 中有落点"),
                ("方案与回滚", "PASS", "方案、风险、回滚章节已填写"),
            ],
        )
        transition(state, "DESIGN_READY", evidence, gate="G2")
    elif current == "DESIGN_READY":
        _, spec_acs = check_spec(read_text(directory / "spec.md"), spec_id)
        errors = check_tasks(read_text(directory / "tasks.md"), spec_acs, config)
        if errors:
            for error in errors:
                eprint(f"- {error}")
            record_gate(
                root,
                config,
                directory,
                state,
                "G3",
                "TASKS_READY",
                "auto",
                evidence,
                [("Tasks 完整性", "FAILED", "见问题清单")],
                errors,
            )
            raise SddError("tasks 校验失败")
        mode = gate_mode(config, "G3", state, args.human)
        record_gate(
            root,
            config,
            directory,
            state,
            "G3",
            "TASKS_READY",
            mode,
            evidence,
            [
                ("Task 字段完整", "PASS", "公司任务表字段完整"),
                ("AC 全覆盖", "PASS", "无孤立 AC"),
                ("依赖无环", "PASS", "依赖 DAG 校验通过"),
                ("测试映射", "PASS", "每个 Task 有测试类和命令"),
            ],
        )
        transition(state, "TASKS_READY", evidence, gate="G3")
    elif current == "TASKS_READY":
        _, spec_acs = check_spec(read_text(directory / "spec.md"), spec_id)
        errors = check_tasks(read_text(directory / "tasks.md"), spec_acs, config)
        if errors:
            for error in errors:
                eprint(f"- {error}")
            raise SddError("tasks 校验失败")
        transition(state, "IMPLEMENTING", evidence)
    elif current == "IMPLEMENTING":
        tasks = parse_tasks(read_text(directory / "tasks.md"))
        if not tasks or not all(task["done"] for task in tasks):
            raise SddError("还有未完成的 task；用 `sdd complete --task T-xxx` 逐个完成")
        mode = gate_mode(config, "G4", state, args.human)
        verification_text = read_text(directory / "verification.md")
        missing_evidence = [
            task["id"] for task in tasks if task["id"] not in verification_text
        ]
        _, spec_acs = check_spec(read_text(directory / "spec.md"), spec_id)
        errors = task_table_error(tasks, spec_acs, config)
        if missing_evidence:
            errors.append("以下 Task 没有验证证据：" + ", ".join(missing_evidence))
        if errors:
            record_gate(
                root,
                config,
                directory,
                state,
                "G4",
                "VERIFYING",
                mode,
                evidence,
                [("Task 完成与证据", "FAILED", "见问题清单")],
                errors,
            )
            for error in errors:
                eprint(f"- {error}")
            raise SddError("Gate 4 校验失败")
        record_gate(
            root,
            config,
            directory,
            state,
            "G4",
            "VERIFYING",
            mode,
            evidence,
            [
                ("Task 全部完成", "PASS", f"{len(tasks)} 个 Task 状态均为 Done"),
                ("Task 验证证据", "PASS", "verification.md 已记录每个 Task"),
                ("Task 测试映射", "PASS", "每个 Task 有测试类/方法和命令"),
            ],
        )
        transition(state, "VERIFYING", evidence, gate="G4")
    elif current == "VERIFYING":
        _, spec_acs = check_spec(read_text(directory / "spec.md"), spec_id)
        errors = check_verification(read_text(directory / "verification.md"), spec_acs)
        errors.extend(check_test_coverage(root, config, spec_acs))
        errors.extend(
            check_gates(root, config, directory, "VERIFYING")
        )
        if errors:
            for error in errors:
                eprint(f"- {error}")
            record_gate(
                root,
                config,
                directory,
                state,
                "G5",
                "PR_READY",
                "auto",
                evidence,
                [("规格验证", "FAILED", "见问题清单")],
                errors,
            )
            raise SddError("verification 校验失败")
        mode = gate_mode(config, "G5", state, args.human)
        record_gate(
            root,
            config,
            directory,
            state,
            "G5",
            "PR_READY",
            mode,
            evidence,
            [
                ("全部 AC 有测试关联", "PASS", "test_globs 命中全部 AC"),
                ("验证命令与结果", "PASS", "verification.md 已填写"),
                ("Gate 5 结论", "PASS", "verification.md 明确 PASS"),
                ("G0–G4 报告", "PASS", "Gate 报告齐备且为 PASS"),
            ],
        )
        write_report(root, directory, state)
        transition(state, "PR_READY", evidence, gate="G5")
    elif current == "PR_READY":
        raise SddError("PR_READY 之后必须由人类运行 `sdd merge --human --evidence ...`")
    elif current == "MERGED":
        print("[sdd] already merged")
        return 0
    elif current == "BLOCKED":
        raise SddError("当前是 BLOCKED；先运行 `sdd unblock --evidence ...`")
    else:
        raise SddError(f"未知状态：{current}")

    save_state(directory, state)
    print(f"[sdd] {spec_id} -> {state['state']}")
    return 0


def command_verify(
    args: argparse.Namespace, root: Path, config: dict[str, Any]
) -> int:
    spec_id, directory, state = resolve_spec(root, config, args.spec)
    if state.get("state") != "VERIFYING":
        raise SddError("只有 VERIFYING 状态可以运行 sdd verify")
    commands = list(args.command or [])
    if not commands:
        commands = [str(item) for item in config.get("test_commands", []) if str(item).strip()]
    if not commands:
        print("[sdd] config.json 没有 test_commands；请手动跑测试并把结果写进 verification.md")
        return 0

    failed = False
    for command in commands:
        print(f"[sdd] run: {command}")
        result = subprocess.run(
            command,
            cwd=root,
            shell=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
        )
        output = (result.stdout or "") + (result.stderr or "")
        output = output.strip()
        if len(output) > 20000:
            output = output[:20000] + "\n... (truncated)"
        body = (
            f"- Command: `{command}`\n"
            f"- CWD: `{root}`\n"
            f"- Exit: `{result.returncode}`\n\n"
            "```text\n"
            f"{output}\n"
            "```"
        )
        append_verification_evidence(
            directory,
            f"Command: {command}",
            body,
            section=("命令", "Commands"),
        )
        if result.returncode != 0:
            failed = True
            eprint(f"[sdd] command failed ({result.returncode}): {command}")
    print(f"[sdd] {spec_id} verify {'failed' if failed else 'passed'}")
    return 1 if failed else 0


def write_report(root: Path, directory: Path, state: dict[str, Any]) -> Path:
    spec_text = read_text(directory / "spec.md")
    design_text = read_text(directory / "design.md")
    tasks_text = read_text(directory / "tasks.md")
    verification_text = read_text(directory / "verification.md")
    gates_text = read_text(directory / "gates.md")
    acs = extract_acs(spec_text)
    tasks = parse_tasks(tasks_text)
    task_for_ac: dict[str, str] = {}
    for task in tasks:
        for ac in task["acs"]:
            task_for_ac.setdefault(ac, task["id"])

    spec_id = str(state.get("spec_id", directory.name))
    title = str(state.get("title", ""))
    relative_dir = directory.relative_to(root).as_posix()
    change_summary = (
        section_body(design_text, ("方案概述", "方案", "Design")) or "见 design.md"
    )
    risk = (
        section_body(design_text, ("依赖与风险", "风险", "Risks"))
        or "见 design.md"
    )
    not_run = section_body(verification_text, ("未运行", "Not Run")) or "None"
    commands = section_body(verification_text, ("命令", "Commands")) or "见 verification.md"

    lines = [
        f"# {spec_id} {title}",
        "",
        "## Spec 文件",
        "",
        f"- `{relative_dir}/spec.md`",
        f"- Issue: `{state.get('issue') or 'N/A'}`",
        "",
        "## Spec Item 列表",
        "",
    ]
    lines.extend(f"- {ac}" for ac in acs)
    lines.extend(f"- {task['id']} {task['description']}" for task in tasks)
    lines.extend(
        [
            "",
            "## 变更说明",
            "",
            change_summary,
            "",
            "## AC 验证清单",
            "",
            "| AC | Task | Evidence |",
            "| --- | --- | --- |",
        ]
    )
    for ac in acs:
        lines.append(f"| {ac} | {task_for_ac.get(ac, '-')} | 见 `{relative_dir}/verification.md` |")
    lines.extend(
        [
            "",
            "## 命令与结果",
            "",
            commands,
            "",
            "## 未运行 / Not run",
            "",
            not_run,
            "",
            "## 风险与回滚",
            "",
            risk,
            "",
            "## Gate 记录",
            "",
            gates_text.strip(),
            "",
            "## 证据",
            "",
            f"- `{relative_dir}/verification.md`",
            f"- `{relative_dir}/gates.md`",
            f"- `sdd/reports/{spec_id}/gate1-report.md`",
            f"- `sdd/reports/{spec_id}/gate2-report.md`",
            f"- `sdd/reports/{spec_id}/gate3-report.md`",
            f"- `sdd/reports/{spec_id}/gate4-report.md`",
            f"- `sdd/reports/{spec_id}/gate5-report.md`",
            "",
        ]
    )
    path = directory / "PR_BODY.md"
    write_text(path, "\n".join(lines))
    return path


def command_report(
    args: argparse.Namespace, root: Path, config: dict[str, Any]
) -> int:
    spec_id, directory, state = resolve_spec(root, config, args.spec)
    path = write_report(root, directory, state)
    print(f"[sdd] wrote {path.relative_to(root)}")
    return 0


def command_pr(
    args: argparse.Namespace, root: Path, config: dict[str, Any]
) -> int:
    spec_id, directory, state = resolve_spec(root, config, args.spec)
    if state.get("state") not in {"PR_READY", "MERGED"}:
        raise SddError("只有 PR_READY/MERGED 状态可以记录 PR")
    if args.url:
        state["pr_url"] = args.url
        add_history(state, str(state.get("state")), "PR recorded", pr_url=args.url)
        save_state(directory, state)
        print(f"[sdd] {spec_id} PR: {args.url}")
    else:
        print(f"[sdd] PR body: {directory.relative_to(root)}/PR_BODY.md")
        print(
            "[sdd] example: gh pr create --title \""
            + spec_id
            + " "
            + str(state.get("title", ""))
            + "\" --body-file "
            + str((directory / "PR_BODY.md").relative_to(root))
        )
    return 0


def command_block(
    args: argparse.Namespace, root: Path, config: dict[str, Any]
) -> int:
    spec_id, directory, state = resolve_spec(root, config, args.spec)
    if state.get("state") == "MERGED":
        raise SddError("已合并的 Spec 不能 block")
    if state.get("state") == "BLOCKED":
        raise SddError("已经是 BLOCKED")
    state["blocked_from"] = state.get("state")
    state["blocked_reason"] = args.reason
    add_history(state, "BLOCKED", args.reason)
    state["state"] = "BLOCKED"
    decisions = read_text(directory / "decisions.md")
    if not decisions:
        decisions = "# 决策记录\n\n## Decisions\n\n## Blocked\n"
    decisions += f"\n### {now()}\n\n- From: {state['blocked_from']}\n- Reason: {args.reason}\n"
    write_text(directory / "decisions.md", decisions)
    save_state(directory, state)
    print(f"[sdd] {spec_id} -> BLOCKED")
    return 0


def command_unblock(
    args: argparse.Namespace, root: Path, config: dict[str, Any]
) -> int:
    spec_id, directory, state = resolve_spec(root, config, args.spec)
    if state.get("state") != "BLOCKED":
        raise SddError("只有 BLOCKED 状态可以 unblock")
    if not args.human:
        raise SddError("unblock 需要 --human；agent 不允许代替人类解除阻塞")
    previous = state.get("blocked_from") or "TASKS_READY"
    state["state"] = previous
    state.pop("blocked_from", None)
    state.pop("blocked_reason", None)
    add_history(state, previous, args.evidence or "unblocked")
    save_state(directory, state)
    print(f"[sdd] {spec_id} unblocked -> {previous}")
    return 0


def command_merge(
    args: argparse.Namespace, root: Path, config: dict[str, Any]
) -> int:
    spec_id, directory, state = resolve_spec(root, config, args.spec)
    if state.get("state") != "PR_READY":
        raise SddError("只有 PR_READY 状态可以 merge")
    if not args.human:
        raise SddError("merge 需要 --human；agent 不允许自己合并")
    errors, _ = run_checks(root, config, directory, state, "ci")
    if errors:
        for error in errors:
            eprint(f"- {error}")
        raise SddError("CI 检查未通过，不能登记合并")
    state["merged_at"] = now()
    transition(state, "MERGED", args.evidence)
    save_state(directory, state)
    print(f"[sdd] {spec_id} -> MERGED")
    return 0


def command_start(
    args: argparse.Namespace, root: Path, config: dict[str, Any]
) -> int:
    spec_id, directory, state = resolve_spec(root, config, args.spec)
    if state.get("state") != "IMPLEMENTING":
        raise SddError("只有 IMPLEMENTING 状态可以 start task")
    text = read_text(directory / "tasks.md")
    updated, found = mark_task_status(text, args.task, "In Progress")
    if not found:
        raise SddError(f"找不到任务：{args.task}")
    write_text(directory / "tasks.md", updated)
    add_history(state, "IMPLEMENTING", "task started", action="task_start", task=args.task)
    save_state(directory, state)
    print(f"[sdd] {spec_id} {args.task} -> In Progress")
    return 0


def command_init(
    args: argparse.Namespace, root: Path, config: dict[str, Any]
) -> int:
    ensure_layout(root, config)
    index = prd_index_path(root, config)
    if not index.exists():
        write_text(
            index,
            "# PRD 追溯索引\n\n"
            "<!-- source: workitem 表示 PRD 全文留在工作项系统；"
            "source: repo 表示 docs/prd.md 为权威源。 -->\n\n"
            f"- source: {config.get('prd_mode', 'workitem')}\n"
            f"- updated: {now()}\n\n"
            "| 工作项 ID | PRD 链接/路径 | PRD 版本 | FEAT | Spec ID | 摘要 | 澄清标记 |\n"
            "| --- | --- | --- | --- | --- | --- | --- |\n",
        )
        print(f"[sdd] created {index.relative_to(root)}")
    if args.prd_mode:
        config["prd_mode"] = args.prd_mode
        write_json(root / "sdd" / "config.json", config)
        print(f"[sdd] prd_mode -> {args.prd_mode}")

    if args.hooks:
        hooks_dir = root / ".githooks"
        hooks_dir.mkdir(exist_ok=True)
        for name in ("pre-commit", "commit-msg"):
            source = root / "sdd" / "hooks" / name
            target = hooks_dir / name
            if not source.is_file():
                raise SddError(f"缺少 hook 模板：{source.relative_to(root)}")
            if target.exists() and not args.force:
                print(f"[sdd] keep existing {target.relative_to(root)}")
            else:
                write_text(target, read_text(source))
                try:
                    target.chmod(0o755)
                except OSError:
                    pass
                print(f"[sdd] wrote {target.relative_to(root)}")
        if (root / ".git").exists():
            result = subprocess.run(
                ["git", "config", "core.hooksPath", ".githooks"],
                cwd=root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            if result.returncode == 0:
                print("[sdd] git core.hooksPath = .githooks")
            else:
                print("[sdd] 未能自动设置 core.hooksPath，请手动执行：")
                print("       git config core.hooksPath .githooks")
        else:
            print("[sdd] 当前不是 Git 仓库；提交前请配置 .githooks")

    if args.ci in {"github", "both"}:
        target = root / ".github" / "workflows" / "sdd.yml"
        source = root / "sdd" / "ci" / "github-actions.yml"
        if not source.is_file():
            raise SddError(f"缺少 CI 模板：{source.relative_to(root)}")
        if target.exists() and not args.force:
            print(f"[sdd] keep existing {target.relative_to(root)}")
        else:
            write_text(target, read_text(source))
            print(f"[sdd] wrote {target.relative_to(root)}")
    if args.ci in {"gitlab", "both"}:
        target = root / ".gitlab-ci.yml"
        source = root / "sdd" / "ci" / "gitlab-ci.yml"
        if not source.is_file():
            raise SddError(f"缺少 CI 模板：{source.relative_to(root)}")
        if target.exists() and not args.force:
            print(f"[sdd] keep existing {target.relative_to(root)}")
            print("[sdd] 请把 sdd/ci/gitlab-ci.yml 的 job 合并进现有 .gitlab-ci.yml")
        else:
            write_text(target, read_text(source))
            print(f"[sdd] wrote {target.relative_to(root)}")

    print("[sdd] init done")
    print(
        "[sdd] next: python -m sdd start-work "
        "--work-item srdcloud-123 --title \"...\" --json"
    )
    return 0


def staged_paths(root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMRD"],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise SddError("git diff 执行失败：" + result.stderr.strip())
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def git_show(root: Path, path: str) -> str:
    result = subprocess.run(
        ["git", "show", f":{path}"],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        return ""
    return result.stdout


def hook_pre_commit(root: Path, config: dict[str, Any]) -> int:
    if not (root / ".git").exists():
        raise SddError("pre-commit hook 需要 Git 仓库")
    paths = staged_paths(root)
    spec_paths = [
        path
        for path in paths
        if re.match(r"^docs/specs/SPEC-[A-Z][A-Z0-9]*-[0-9]{3}/spec\.md$", path)
    ]
    errors: list[str] = []
    duplicate = re.compile(
        r"^(?:spec|design|tasks)[_-](?:v[0-9]+|final|new|latest)\.md$",
        re.IGNORECASE,
    )
    for path in paths:
        if path.startswith("docs/specs/") and duplicate.match(Path(path).name):
            errors.append("禁止创建重复版本文件：" + path)
    for path in spec_paths:
        spec_id = Path(path).parent.name
        text = git_show(root, path)
        check_errors, _ = check_spec(text, spec_id)
        errors.extend(f"{path}: {error}" for error in check_errors)
        for required in ("design.md", "tasks.md"):
            target = str(Path(path).parent / required).replace("\\", "/")
            result = subprocess.run(
                ["git", "cat-file", "-e", f":{target}"],
                cwd=root,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                errors.append(f"暂存区缺少基础文件：{target}")
    for path in paths:
        if path.startswith("docs/specs/") and path.endswith(".md"):
            text = git_show(root, path)
            if CLARIFY_RE.search(text):
                errors.append(f"{path}: 还有 [NEEDS CLARIFICATION] 标记")
    if errors:
        for error in errors:
            print(f"[SDD][BLOCK] {error}", file=sys.stderr)
        return 1
    print("[SDD][PASS] pre-commit 检查通过")
    return 0


COMMIT_HEADER_RE = re.compile(
    r"^%(?P<work>[A-Za-z0-9_.-]+-[0-9]+)\s+"
    r"(?P<type>feat|fix|perf|docs|chore|style|build|ci|test|refactor|revert|hotfix)"
    r"\((?P<scope>[^)]+)\):\s+(?P<description>.+)$"
)


def hook_commit_msg(root: Path, config: dict[str, Any], message_file: str) -> int:
    path = Path(message_file)
    if not path.is_absolute():
        path = root / path
    if not path.is_file():
        raise SddError(f"找不到 commit message 文件：{path}")
    text = read_text(path)
    lines = text.splitlines()
    header = lines[0] if lines else ""
    errors: list[str] = []
    match = COMMIT_HEADER_RE.match(header)
    if not match:
        errors.append("首行必须匹配 %<工作项ID> <type>(<scope>): <描述>")
    spec_ids = re.findall(r"(?im)^Spec-Id:\s*(SPEC-[A-Z][A-Z0-9]*-[0-9]{3})\s*$", text)
    task_ids = re.findall(r"(?im)^Task-Id:\s*(T-[A-Za-z0-9_-]+)\s*$", text)
    if len(spec_ids) != 1:
        errors.append("必须包含且只包含一个合法 Spec-Id Trailer")
    commit_type = match.group("type") if match else ""
    if commit_type == "docs" and task_ids:
        errors.append("文档 Commit 不得包含 Task-Id")
    if commit_type in {"feat", "fix", "perf", "hotfix"} and len(task_ids) != 1:
        errors.append("代码 Commit 必须包含且只包含一个 Task-Id")
    if len(task_ids) > 1:
        errors.append("只能包含一个 Task-Id")

    if spec_ids:
        spec_id = spec_ids[0]
        directory = spec_dir_for(root, config, spec_id)
        spec_text = read_text(directory / "spec.md")
        if not spec_text:
            errors.append(f"Spec-Id 对应的 spec.md 不存在：{spec_id}")
        else:
            declared = metadata_value(spec_text, "Spec ID", "SpecID")
            if declared != spec_id:
                errors.append("Spec 目录与元数据中的 Spec ID 不一致")
            work_item = metadata_value(spec_text, "工作项 ID", "工作项ID")
            if match and work_item != match.group("work"):
                errors.append(
                    f"Commit 工作项 {match.group('work')} 与 Spec 元数据 {work_item} 不一致"
                )
        if task_ids:
            tasks_text = read_text(directory / "tasks.md")
            if task_ids[0] not in tasks_text:
                errors.append(f"Task-Id 在 tasks.md 中不存在：{task_ids[0]}")
    if errors:
        for error in errors:
            print(f"[SDD-COMMIT][BLOCK] {error}", file=sys.stderr)
        return 1
    print("[SDD-COMMIT][PASS] commit message 检查通过")
    return 0


def command_hook(
    args: argparse.Namespace, root: Path, config: dict[str, Any]
) -> int:
    if args.hook_name == "pre-commit":
        return hook_pre_commit(root, config)
    if args.hook_name == "commit-msg":
        if not args.message_file:
            raise SddError("commit-msg hook 需要 --message-file")
        return hook_commit_msg(root, config, args.message_file)
    raise SddError(f"未知 hook：{args.hook_name}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sdd",
        description="Repo-local SDD state machine (stdlib only)",
    )
    parser.add_argument("--root", help="repository root; default: auto-detect")
    parser.add_argument("--version", action="version", version=VERSION)
    sub = parser.add_subparsers(dest="command", required=True)

    def add_spec_option(p: argparse.ArgumentParser) -> None:
        p.add_argument("--spec", help="Spec ID; required when multiple specs exist")

    p = sub.add_parser("init", help="initialize docs/specs, hooks and CI")
    p.add_argument("--hooks", action="store_true", help="install .githooks wrappers")
    p.add_argument(
        "--ci",
        default="none",
        choices=["none", "github", "gitlab", "both"],
        help="install CI template",
    )
    p.add_argument(
        "--prd-mode",
        default=None,
        choices=["workitem", "repo"],
        help="PRD authority mode",
    )
    p.add_argument("--force", action="store_true", help="overwrite generated hook/CI files")
    p.set_defaults(func=command_init)

    p = sub.add_parser("new", help="create a new spec")
    p.add_argument("spec_id", nargs="?")
    p.add_argument("--domain", help="domain code, e.g. ORDER; auto-allocates SPEC-ORDER-001")
    p.add_argument("--title", required=True)
    p.add_argument("--work-item", "--issue", dest="work_item", default=None)
    p.add_argument("--issue-url", dest="issue", default=None)
    p.add_argument(
        "--product-type",
        default="传统产品",
        choices=["传统产品", "AI辅助·L2", "AI增强·L3", "AI原生·L4"],
    )
    p.add_argument("--author", default="SDD Agent")
    p.add_argument("--risk", default="low", choices=["low", "medium", "high"])
    p.add_argument(
        "--risk-label",
        action="append",
        default=[],
        help="risk label, e.g. security or data_migration; repeatable",
    )
    p.set_defaults(func=command_new)

    p = sub.add_parser("status", help="show current state")
    add_spec_option(p)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=command_status)

    p = sub.add_parser("next", help="print the next action for the agent")
    add_spec_option(p)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=command_next)

    p = sub.add_parser("board", help="show specs and task statuses")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=command_board)

    p = sub.add_parser("events", help="show the append-only audit events for a Spec")
    add_spec_option(p)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=command_events)

    p = sub.add_parser("check", help="validate artifacts")
    add_spec_option(p)
    p.add_argument(
        "--stage",
        default="auto",
        choices=["auto", "spec", "design", "tasks", "verify", "ci"],
    )
    p.add_argument("--check-git", action="store_true")
    p.add_argument(
        "--all",
        action="store_true",
        help="validate every Spec under spec_root; used by CI",
    )
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=command_check)

    p = sub.add_parser("approve", help="human approval: DRAFT -> SPEC_READY")
    add_spec_option(p)
    p.add_argument("--evidence", default="requirement confirmed by human")
    p.add_argument("--human", action="store_true")
    p.set_defaults(func=command_approve)

    p = sub.add_parser("complete", help="complete current stage or task")
    add_spec_option(p)
    p.add_argument("--task", help="mark T-xxx done")
    p.add_argument("--evidence", required=True)
    p.add_argument("--commit", help="fill Commit SHA for the task")
    p.add_argument("--human", action="store_true", help="manual approval for a human gate")
    p.set_defaults(func=command_complete)

    p = sub.add_parser("start", help="mark a task In Progress")
    add_spec_option(p)
    p.add_argument("--task", required=True)
    p.set_defaults(func=command_start)

    p = sub.add_parser("verify", help="run configured test commands and record evidence")
    add_spec_option(p)
    p.add_argument("--command", action="append", help="override test_commands; repeatable")
    p.set_defaults(func=command_verify)

    p = sub.add_parser("report", help="write PR_BODY.md")
    add_spec_option(p)
    p.set_defaults(func=command_report)

    p = sub.add_parser("pr", help="print or record PR URL")
    add_spec_option(p)
    p.add_argument("--url", default=None)
    p.set_defaults(func=command_pr)

    p = sub.add_parser("block", help="stop and record a blocker")
    add_spec_option(p)
    p.add_argument("--reason", required=True)
    p.set_defaults(func=command_block)

    p = sub.add_parser("unblock", help="resume after a human answer")
    add_spec_option(p)
    p.add_argument("--evidence", default="")
    p.add_argument("--human", action="store_true")
    p.set_defaults(func=command_unblock)

    p = sub.add_parser("merge", help="human merge: PR_READY -> MERGED")
    add_spec_option(p)
    p.add_argument("--evidence", required=True)
    p.add_argument("--human", action="store_true")
    p.set_defaults(func=command_merge)

    p = sub.add_parser("hook", help="run repository git hooks")
    p.add_argument("hook_name", choices=["pre-commit", "commit-msg"])
    p.add_argument("--message-file", default=None)
    p.set_defaults(func=command_hook)
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        root = find_root(args.root)
        config = load_config(root)
        return int(args.func(args, root, config))
    except SddError as exc:
        eprint(f"[sdd] {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
