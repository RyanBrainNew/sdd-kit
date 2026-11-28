#!/usr/bin/env python3
"""Repo-local SDD workflow.

The script owns the state machine. The coding agent owns the content.
No third-party dependencies; Python 3.9+.
"""

from __future__ import annotations

import argparse
import ast
import fnmatch
import glob
import hashlib
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Optional

try:
    from sdd_ext import (
        CHECK_REGISTRY as EXT_CHECK_REGISTRY,
        SECURITY_CHECK_IDS,
        blocking_errors,
        build_check_results,
        check_id_for_error,
        check_ids_for_gate,
        declared_code_paths,
        extract_backtick_paths,
        fix_pattern_errors,
        is_code_path,
        knowledge_record_errors,
        next_feat_number,
        parse_front_matter,
        pattern_applies,
        review_required_for,
        scan_test_definitions,
        test_reference_errors,
        traceability_errors,
        validate_review_findings,
    )
except ImportError:  # pragma: no cover - package import fallback
    from .sdd_ext import (
        CHECK_REGISTRY as EXT_CHECK_REGISTRY,
        SECURITY_CHECK_IDS,
        blocking_errors,
        build_check_results,
        check_id_for_error,
        check_ids_for_gate,
        declared_code_paths,
        extract_backtick_paths,
        fix_pattern_errors,
        is_code_path,
        knowledge_record_errors,
        next_feat_number,
        parse_front_matter,
        pattern_applies,
        review_required_for,
        scan_test_definitions,
        test_reference_errors,
        traceability_errors,
        validate_review_findings,
    )

VERSION = "0.10.0"
EVENT_SCHEMA = 2

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

GATE_ARTIFACTS = {
    "G0": ("spec.md",),
    "G1": ("spec.md",),
    "G2": ("design.md",),
    "G3": ("tasks.md#plan",),
    "G4": ("tasks.md#plan",),
    "G5": ("verification.md",),
}

TEXT_ARTIFACT_SUFFIXES = {".md", ".json", ".yaml", ".yml", ".txt"}

TASK_PLAN_FIELDS = (
    "id",
    "description",
    "acs",
    "frs",
    "depends",
    "parallel",
    "acceptance",
    "test",
    "command",
)

CHECK_REQUIRED_FIELDS = (
    "id",
    "gate",
    "name",
    "level",
    "trigger",
    "waivable",
    "evidence",
    "owner",
)

CHECK_REGISTRY = (
    {
        "id": "G0-01",
        "gate": "G0",
        "name": "工作项与 Spec 元数据一致",
        "level": "required",
        "trigger": "approve",
        "waivable": False,
        "evidence": "spec.md 工作项 ID 与 state/prd-index 一致",
        "owner": "planner",
    },
    {
        "id": "G0-02",
        "gate": "G0",
        "name": "PRD 索引结构可解析",
        "level": "required",
        "trigger": "approve",
        "waivable": False,
        "evidence": "docs/prd-index.md 有 source/updated 且表格可解析",
        "owner": "planner",
    },
    {
        "id": "G0-03",
        "gate": "G0",
        "name": "PRD 澄清标记为 0",
        "level": "required",
        "trigger": "approve",
        "waivable": False,
        "evidence": "docs/prd-index.md 不含 [NEEDS CLARIFICATION]",
        "owner": "planner",
    },
    {
        "id": "G0-04",
        "gate": "G0",
        "name": "FEAT 已登记且唯一",
        "level": "required",
        "trigger": "approve",
        "waivable": False,
        "evidence": "spec.md FEAT ID 与 docs/prd-index.md 一致且不重复",
        "owner": "planner",
    },
    {
        "id": "G0-05",
        "gate": "G0",
        "name": "FEAT 映射覆盖全部 FR/AC",
        "level": "required",
        "trigger": "approve",
        "waivable": False,
        "evidence": "## FEAT 映射 表覆盖 Spec 的全部 FR/AC，无孤儿项",
        "owner": "planner",
    },
    {
        "id": "G0-06",
        "gate": "G0",
        "name": "范围声明可判定",
        "level": "required",
        "trigger": "approve",
        "waivable": False,
        "evidence": "spec.md 的 In-Scope / Out-of-Scope 已填写",
        "owner": "planner",
    },
    {
        "id": "G0-07",
        "gate": "G0",
        "name": "历史 Spec 兼容标注",
        "level": "advisory",
        "trigger": "approve",
        "waivable": True,
        "evidence": "MERGED 历史 Spec 使用 legacy 校验并在报告标注",
        "owner": "planner",
    },
    {
        "id": "G1-01",
        "gate": "G1",
        "name": "Spec 章节齐备",
        "level": "required",
        "trigger": "approve",
        "waivable": False,
        "evidence": "spec.md 核心章节存在",
        "owner": "planner",
    },
    {
        "id": "G1-02",
        "gate": "G1",
        "name": "FR/AC 映射完整",
        "level": "required",
        "trigger": "approve",
        "waivable": False,
        "evidence": "每个 FR 至少有一条 AC",
        "owner": "planner",
    },
    {
        "id": "G1-03",
        "gate": "G1",
        "name": "AC 可测试性",
        "level": "required",
        "trigger": "approve",
        "waivable": False,
        "evidence": "每条 AC 含 Given/When/Then 与执行路径",
        "owner": "planner",
    },
    {
        "id": "G1-04",
        "gate": "G1",
        "name": "无占位符与澄清标记",
        "level": "required",
        "trigger": "approve",
        "waivable": False,
        "evidence": "spec.md 无 TODO、占位符或 [NEEDS CLARIFICATION]",
        "owner": "planner",
    },
)

CHECK_LEVELS = {"required", "advisory"}
CHECK_TRIGGERS = {"doc_pr", "code_pr", "local", "ci", "pipeline"}
CHECK_TRIGGER_ALIASES = {
    "approve": "doc_pr",
    "document": "doc_pr",
    "code": "code_pr",
}


def normalize_check_registry_item(
    check_id: str,
    item: dict[str, Any],
) -> dict[str, Any]:
    trigger = str(item.get("trigger") or "local")
    return {
        "id": check_id,
        "gate": str(item.get("gate") or ""),
        "name": str(item.get("name") or item.get("title") or check_id),
        "level": str(item.get("level") or "required"),
        "trigger": CHECK_TRIGGER_ALIASES.get(trigger, trigger),
        "waivable": bool(item.get("waivable")),
        "redline": bool(
            item.get("redline") or check_id in SECURITY_CHECK_IDS
        ),
        "evidence": str(item.get("evidence") or ""),
        "owner": str(item.get("owner") or ""),
    }


def combined_check_registry() -> tuple[dict[str, Any], ...]:
    items: dict[str, dict[str, Any]] = {}
    for check_id, item in EXT_CHECK_REGISTRY.items():
        items[check_id] = normalize_check_registry_item(check_id, item)
    for item in CHECK_REGISTRY:
        check_id = str(item["id"])
        items[check_id] = normalize_check_registry_item(check_id, item)
    return tuple(items[key] for key in sorted(items))


CHECK_REGISTRY_ALL = combined_check_registry()

CHECK_REGISTRY_BY_ID = dict(EXT_CHECK_REGISTRY)
CHECK_REGISTRY_BY_ID.update(
    {str(item["id"]): item for item in CHECK_REGISTRY}
)

STAGE_ORDER = (
    "DRAFT",
    "SPEC_READY",
    "DESIGN_READY",
    "TASKS_READY",
    "IMPLEMENTING",
    "VERIFYING",
    "PR_READY",
    "MERGED",
)
NEXT_ACTION_BY_STATE = {
    "DRAFT": "write_spec",
    "SPEC_READY": "write_design",
    "DESIGN_READY": "write_tasks",
    "TASKS_READY": "start_implementation",
    "IMPLEMENTING": "complete_task",
    "VERIFYING": "verify",
    "PR_READY": "human_merge",
    "MERGED": "done",
}

WORKFLOW_SCHEMA = 1
WORKFLOW_SCHEMA_V2 = 2
WORKFLOW_SCHEMAS = {WORKFLOW_SCHEMA, WORKFLOW_SCHEMA_V2}
DEFAULT_WORKFLOW = "l2-standard"
WORKFLOW_POLICIES = {"human", "auto", "auto_if_no_risk"}
WORKFLOW_DESIGN_MODES = {"full", "lite"}
HUMAN_CHECKPOINTS = {
    "spec",
    "design",
    "tasks",
    "implement",
    "implementation",
    "verify",
    "merge",
    *GATE_STAGES,
}
WORKFLOW_V2_FIELDS = {
    "schema",
    "name",
    "version",
    "description",
    "stages",
    "artifacts",
    "gates",
    "required_gates",
    "gate_checks",
    "human_checkpoints",
    "allow_rewind_to",
    "design_mode",
    "review_required",
    "review_policy",
    "risk_policy",
    "risk_stop",
    "context_rules",
}
HUMAN_CHECKPOINT_TYPES = {"approve_spec", "confirm_delivery", "complete_gate"}
HUMAN_CHECKPOINT_FIELDS = {"type", "gate"}
CONTEXT_RULE_FIELDS = {"include", "exclude"}
RISK_POLICY_FIELDS = {"max_risk", "deny_risk_stop"}
CANONICAL_STAGE_ARTIFACTS = {
    "DRAFT": "spec.md",
    "SPEC_READY": "design.md",
    "DESIGN_READY": "tasks.md",
    "TASKS_READY": "tasks.md",
    "IMPLEMENTING": "tasks.md",
    "VERIFYING": "verification.md",
    "PR_READY": "PR_BODY.md",
}
GATE_OWNER_STAGE = {
    "G0": "SPEC_READY",
    "G1": "SPEC_READY",
    "G2": "DESIGN_READY",
    "G3": "TASKS_READY",
    "G4": "VERIFYING",
    "G5": "PR_READY",
}
WORKFLOW_REQUIRED_STAGES = {"IMPLEMENTING", "VERIFYING"}
RISK_RANK = {"low": 0, "medium": 1, "high": 2}
LEGACY_STANDARD_GATES = {
    "G0": "human",
    "G1": "auto",
    "G2": "auto_if_no_risk",
    "G3": "auto",
    "G4": "auto",
    "G5": "auto",
}

DESIGN_LITE_SECTIONS = (
    ("元数据", "Metadata"),
    ("根因", "Root Cause"),
    ("修复策略", "Fix Strategy"),
    ("影响范围", "Impact"),
    ("回滚方案", "Rollback"),
    ("验收标准", "Acceptance Criteria"),
)

REWIND_PLANS = {
    "DRAFT": (
        ("spec.md", "design.md", "tasks.md", "verification.md", "PR_BODY.md"),
        ("G0", "G1", "G2", "G3", "G4", "G5"),
        "reset_all",
    ),
    "SPEC_READY": (
        ("design.md", "tasks.md", "verification.md", "PR_BODY.md"),
        ("G2", "G3", "G4", "G5"),
        "reset_all",
    ),
    "DESIGN_READY": (
        ("tasks.md", "verification.md", "PR_BODY.md"),
        ("G3", "G4", "G5"),
        "reset_all",
    ),
    "TASKS_READY": (
        ("verification.md", "PR_BODY.md"),
        ("G4", "G5"),
        "reset_all",
    ),
    "IMPLEMENTING": (
        ("verification.md", "PR_BODY.md"),
        ("G4", "G5"),
        "implementation",
    ),
    "VERIFYING": (
        ("verification.md", "PR_BODY.md"),
        ("G5",),
        "keep",
    ),
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


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.tmp")
    temp.write_text(text, encoding="utf-8", newline="\n")
    os.replace(temp, path)


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    atomic_write_text(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SddError(f"找不到文件：{path}") from exc
    except json.JSONDecodeError as exc:
        raise SddError(f"JSON 格式错误：{path} ({exc})") from exc


def write_json(path: Path, data: dict[str, Any]) -> None:
    atomic_write_text(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_text_bytes(data: bytes) -> Optional[bytes]:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return None
    return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def artifact_sha256(path: Path) -> str:
    data = path.read_bytes()
    if path.suffix.lower() in TEXT_ARTIFACT_SUFFIXES:
        canonical = canonical_text_bytes(data)
        if canonical is not None:
            return sha256_bytes(canonical)
    return sha256_bytes(data)


def artifact_hash_candidates(path: Path) -> set[str]:
    data = path.read_bytes()
    candidates = {sha256_bytes(data)}
    if path.suffix.lower() in TEXT_ARTIFACT_SUFFIXES:
        canonical = canonical_text_bytes(data)
        if canonical is not None:
            candidates.add(sha256_bytes(canonical))
            candidates.add(sha256_bytes(canonical.replace(b"\n", b"\r\n")))
    return candidates


def artifact_hash_matches(path: Path, expected: str) -> bool:
    return expected in artifact_hash_candidates(path)


def task_plan_hash(text: str) -> str:
    plan = [
        {field: task.get(field) for field in TASK_PLAN_FIELDS}
        for task in parse_tasks(text)
    ]
    normalized = json.dumps(
        plan, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def artifact_digest(
    root: Path, directory: Path, name: str
) -> tuple[str, str, int]:
    if name.endswith("#plan"):
        path = directory / name[: -len("#plan")]
        relative = path.relative_to(root).as_posix() + "#plan"
        if not path.is_file():
            return relative, "MISSING", 0
        digest = task_plan_hash(read_text(path))
        return relative, digest, path.stat().st_size
    path = directory / name
    relative = path.relative_to(root).as_posix()
    if not path.is_file():
        return relative, "MISSING", 0
    return relative, artifact_sha256(path), path.stat().st_size


def history_meta() -> dict[str, Any]:
    key = os.environ.get("SDD_SESSION_KEY") or "local"
    source = os.environ.get("SDD_SESSION_SOURCE") or (
        "SDD_SESSION_KEY" if os.environ.get("SDD_SESSION_KEY") else "repo-fallback"
    )
    meta: dict[str, Any] = {
        "actor": os.environ.get("SDD_ACTOR") or "agent",
        "session": hashlib.sha256(key.encode("utf-8")).hexdigest()[:12],
        "session_source": source,
        "source": os.environ.get("SDD_SOURCE") or "cli",
    }
    for key_name, env_name in (
        ("role", "SDD_ROLE"),
        ("executor", "SDD_EXECUTOR"),
        ("model", "SDD_MODEL"),
    ):
        value = os.environ.get(env_name)
        if value:
            meta[key_name] = value
    return meta


def role_for_stage(stage: str) -> str:
    return {
        "spec": "planner",
        "design": "designer",
        "tasks": "planner",
        "verify": "verifier",
        "ci": "reviewer",
    }.get(stage, "orchestrator")


def git_config_value(root: Path, key: str) -> str:
    result = subprocess.run(
        ["git", "config", key],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def resolve_approver(root: Path, explicit: Optional[str]) -> str:
    if explicit and explicit.strip():
        return explicit.strip()
    name = git_config_value(root, "user.name")
    email = git_config_value(root, "user.email")
    if name and email:
        return f"{name} <{email}>"
    return name or email or "unknown"


def git_head_sha(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def append_audit_event(directory: Path, event: dict[str, Any]) -> None:
    existing = read_event_log(directory)
    next_seq = max((int(item.get("seq", 0)) for item in existing), default=0) + 1
    payload = {
        "schema": EVENT_SCHEMA,
        "seq": next_seq,
        "at": now(),
        "history_index": None,
    }
    payload.update(event)
    previous_hash = last_event_hash(existing)
    payload["prev_sha256"] = previous_hash
    payload["event_sha256"] = event_hash(payload)
    path = directory / "events.jsonl"
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def record_check_failure(
    directory: Path,
    stage: str,
    errors: list[str],
    gate: Optional[str] = None,
) -> None:
    event: dict[str, Any] = {
        "event": "check_failed",
        "stage": stage,
        "errors": [str(error) for error in errors],
        "role": role_for_stage(stage),
    }
    if gate:
        event["gate"] = gate
        event["check_ids"] = sorted(
            {
                check_id_for_error(gate, error)
                for error in errors
            }
        )
    event.update(history_meta())
    append_audit_event(directory, event)


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
    config.setdefault("require_approver", False)
    config.setdefault("require_artifact_hash", False)
    config.setdefault("workflow", DEFAULT_WORKFLOW)
    return config


def workflow_root(root: Path) -> Path:
    return root / "sdd" / "workflows"


def workflow_digest(preset: dict[str, Any]) -> str:
    canonical = json.dumps(
        preset,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def workflow_defaults() -> dict[str, list[str]]:
    return {
        stage: list(required_gates(stage))
        for stage in STAGE_ORDER
    }


def validate_workflow_preset(
    preset: dict[str, Any], source: str
) -> list[str]:
    if not isinstance(preset, dict):
        return [f"{source} 必须是 JSON 对象"]
    schema = preset.get("schema")
    if schema == WORKFLOW_SCHEMA:
        return validate_workflow_v1(preset, source)
    if schema == WORKFLOW_SCHEMA_V2:
        return validate_workflow_v2(preset, source)
    return [
        f"{source} 的 schema 必须是 "
        + " 或 ".join(str(item) for item in sorted(WORKFLOW_SCHEMAS))
    ]


def validate_workflow_v1(
    preset: dict[str, Any], source: str
) -> list[str]:
    errors: list[str] = []
    if not isinstance(preset, dict):
        return [f"{source} 必须是 JSON 对象"]
    schema = preset.get("schema")
    if not isinstance(schema, int) or schema not in WORKFLOW_SCHEMAS:
        errors.append(
            f"{source}.schema 必须是 "
            + " 或 ".join(str(item) for item in sorted(WORKFLOW_SCHEMAS))
        )
    if schema == 2:
        for key in sorted(set(preset) - WORKFLOW_V2_FIELDS):
            errors.append(f"{source}.{key} 是未知字段")
        for key in ("stages", "artifacts", "gates", "required_gates"):
            if key not in preset:
                errors.append(f"{source}.{key} 是必填字段")
    name = str(preset.get("name") or "")
    if not re.fullmatch(r"[a-z][a-z0-9-]*", name):
        errors.append(f"{source}.name 必须是小写字母、数字和短横线")
    version = preset.get("version")
    if not isinstance(version, int) or version < 1:
        errors.append(f"{source}.version 必须是正整数")
    stages = preset.get("stages")
    if stages != list(STAGE_ORDER):
        errors.append(
            f"{source} 在当前版本只支持完整阶段序列："
            + " -> ".join(STAGE_ORDER)
            + f"（当前 {stages}）"
        )
    gates = preset.get("gates")
    if not isinstance(gates, dict):
        errors.append(f"{source}.gates 必须是对象")
    else:
        missing = [gate for gate in GATE_STAGES if gate not in gates]
        if missing:
            errors.append(f"{source}.gates 缺少：" + ", ".join(missing))
        for gate, policy in gates.items():
            if gate not in GATE_STAGES:
                errors.append(f"{source}.gates.{gate} 是未知 Gate")
            elif str(policy) not in WORKFLOW_POLICIES:
                errors.append(
                    f"{source}.gates.{gate} 必须是 "
                    + ", ".join(sorted(WORKFLOW_POLICIES))
                )
    required = preset.get("required_gates")
    if not isinstance(required, dict):
        errors.append(f"{source}.required_gates 必须是对象")
    else:
        expected = workflow_defaults()
        for stage in STAGE_ORDER:
            actual = required.get(stage)
            if not isinstance(actual, list):
                errors.append(
                    f"{source}.required_gates.{stage} 必须是数组"
                )
                continue
            unknown = [gate for gate in actual if gate not in GATE_STAGES]
            if unknown:
                errors.append(
                    f"{source}.required_gates.{stage} 包含未知 Gate："
                    + ", ".join(str(gate) for gate in unknown)
                )
            if schema == 1 and actual != expected[stage]:
                errors.append(
                    f"{source}.required_gates.{stage} 必须是 "
                    f"{expected[stage]}"
                )
            elif schema == 2:
                missing = [
                    gate for gate in expected[stage] if gate not in actual
                ]
                if missing:
                    errors.append(
                        f"{source}.required_gates.{stage} 不得移除必需 Gate："
                        + ", ".join(missing)
                    )
    allow_rewind = preset.get("allow_rewind_to")
    if not isinstance(allow_rewind, list):
        errors.append(f"{source}.allow_rewind_to 必须是数组")
    else:
        for stage in allow_rewind:
            if stage not in REWIND_PLANS:
                errors.append(
                    f"{source}.allow_rewind_to 包含不支持的目标：{stage}"
                )
    artifacts = preset.get("artifacts")
    if not isinstance(artifacts, dict):
        errors.append(f"{source}.artifacts 必须是对象")
    else:
        for stage, artifact in artifacts.items():
            if stage not in STAGE_ORDER:
                errors.append(f"{source}.artifacts.{stage} 是未知阶段")
            if not isinstance(artifact, str) or not artifact.strip():
                errors.append(f"{source}.artifacts.{stage} 必须是非空文件名")
    design_mode = str(preset.get("design_mode") or "full")
    if design_mode not in WORKFLOW_DESIGN_MODES:
        errors.append(
            f"{source}.design_mode 必须是 full 或 lite"
        )
    review_required = preset.get("review_required", False)
    if not isinstance(review_required, bool):
        errors.append(f"{source}.review_required 必须是布尔值")
    review_policy = preset.get("review_policy")
    if review_policy is not None:
        if not isinstance(review_policy, dict):
            errors.append(f"{source}.review_policy 必须是对象")
        else:
            for key in sorted(set(review_policy) - {"required_for_risk"}):
                errors.append(
                    f"{source}.review_policy.{key} 是未知字段"
                )
            required_for_risk = review_policy.get("required_for_risk", [])
            if not isinstance(required_for_risk, list):
                errors.append(
                    f"{source}.review_policy.required_for_risk 必须是数组"
                )
            else:
                for value in required_for_risk:
                    if value not in RISK_RANK:
                        errors.append(
                            f"{source}.review_policy.required_for_risk "
                            f"包含未知风险等级：{value}"
                        )
    risk_policy = preset.get("risk_policy")
    if risk_policy is not None:
        if not isinstance(risk_policy, dict):
            errors.append(f"{source}.risk_policy 必须是对象")
        else:
            max_risk = risk_policy.get("max_risk")
            if max_risk is not None and max_risk not in RISK_RANK:
                errors.append(
                    f"{source}.risk_policy.max_risk 必须是 low/medium/high"
                )
            if "deny_risk_stop" in risk_policy and not isinstance(
                risk_policy["deny_risk_stop"], bool
            ):
                errors.append(
                    f"{source}.risk_policy.deny_risk_stop 必须是布尔值"
                )
    if schema == 2:
        gate_checks = preset.get("gate_checks", {})
        if not isinstance(gate_checks, dict):
            errors.append(f"{source}.gate_checks 必须是对象")
        else:
            for gate, selected in gate_checks.items():
                if gate not in GATE_STAGES:
                    errors.append(
                        f"{source}.gate_checks.{gate} 是未知 Gate"
                    )
                    continue
                if not isinstance(selected, list):
                    errors.append(
                        f"{source}.gate_checks.{gate} 必须是检查 ID 数组"
                    )
                    continue
                if not selected:
                    errors.append(
                        f"{source}.gate_checks.{gate} 不得为空检查集；"
                        "省略该 Gate 才表示使用完整检查集"
                    )
                known = set(check_ids_for_gate(gate))
                for check_id in selected:
                    if check_id not in EXT_CHECK_REGISTRY:
                        errors.append(
                            f"{source}.gate_checks.{gate} 包含未知检查 ID："
                            f"{check_id}"
                        )
                    elif check_id not in known:
                        errors.append(
                            f"{source}.gate_checks.{gate} 的检查 {check_id} "
                            f"不属于 {gate}"
                        )
                missing_security = sorted(
                    check_id
                    for check_id in SECURITY_CHECK_IDS
                    if check_id in known and check_id not in selected
                )
                if missing_security:
                    errors.append(
                        f"{source}.gate_checks.{gate} 不得移除安全必需检查："
                        + ", ".join(missing_security)
                    )
        checkpoints = preset.get("human_checkpoints", [])
        if not isinstance(checkpoints, list):
            errors.append(f"{source}.human_checkpoints 必须是数组")
        else:
            for value in checkpoints:
                if str(value) not in HUMAN_CHECKPOINTS:
                    errors.append(
                        f"{source}.human_checkpoints 包含不支持的人工检查点："
                        f"{value}"
                    )
        risk_stop = preset.get("risk_stop", [])
        if not isinstance(risk_stop, list):
            errors.append(f"{source}.risk_stop 必须是字符串数组")
        else:
            for value in risk_stop:
                if not isinstance(value, str) or not value.strip():
                    errors.append(
                        f"{source}.risk_stop 必须是非空字符串数组"
                    )
                    break
        context_rules = preset.get("context_rules", {})
        if not isinstance(context_rules, dict):
            errors.append(f"{source}.context_rules 必须是对象")
        else:
            for key in sorted(set(context_rules) - {"allowed_paths", "exclude"}):
                errors.append(f"{source}.context_rules.{key} 是未知字段")
            for key in ("allowed_paths", "exclude"):
                if key in context_rules and not isinstance(
                    context_rules[key], list
                ):
                    errors.append(
                        f"{source}.context_rules.{key} 必须是字符串数组"
                    )
    return errors


def validate_workflow_stages(
    stages: Any, source: str
) -> list[str]:
    errors: list[str] = []
    if not isinstance(stages, list) or not stages:
        return [f"{source} 的 stages 必须是非空数组"]
    seen: dict[str, int] = {}
    for index, stage in enumerate(stages):
        path = f"stages[{index}]"
        if not isinstance(stage, str):
            errors.append(f"{source} 的 {path} 必须是字符串")
            continue
        if stage not in STAGE_ORDER:
            errors.append(f"{source} 的 {path} 不是规范阶段：{stage}")
            continue
        if stage in seen:
            errors.append(
                f"{source} 的 {path} 重复出现：{stage}（已在 stages[{seen[stage]}]）"
            )
            continue
        seen[stage] = index
    if errors:
        return errors
    if stages[0] != "DRAFT":
        errors.append(f"{source} 的 stages[0] 必须是 DRAFT")
    if stages[-1] != "MERGED":
        errors.append(f"{source} 的 stages[-1] 必须是 MERGED")
    for index in range(1, len(stages)):
        previous = STAGE_ORDER.index(stages[index - 1])
        current = STAGE_ORDER.index(stages[index])
        if current <= previous:
            errors.append(
                f"{source} 的 stages[{index}] 必须严格晚于 stages[{index - 1}]"
            )
    for stage in STAGE_ORDER:
        if stage in seen:
            continue
        if stage in WORKFLOW_REQUIRED_STAGES:
            errors.append(
                f"{source} 的 stages 不能省略 {stage}；该阶段承载不可跳过的执行工作"
            )
    return errors


def context_rule_pattern_errors(
    source: str, path: str, value: Any
) -> list[str]:
    if not isinstance(value, str) or not value.strip():
        return [f"{source} 的 {path} 必须是非空字符串"]
    pattern = value.strip().replace("\\", "/")
    errors: list[str] = []
    if pattern.startswith("/") or re.match(r"^[A-Za-z]:", pattern):
        errors.append(f"{source} 的 {path} 不能是绝对路径：{value}")
    if ".." in pattern.split("/"):
        errors.append(f"{source} 的 {path} 不能包含 ..：{value}")
    if pattern == "docs/specs" or pattern.startswith("docs/specs/"):
        errors.append(f"{source} 的 {path} 不能引用 docs/specs 目录：{value}")
    if pattern == ".sdd" or pattern.startswith(".sdd/"):
        errors.append(f"{source} 的 {path} 不能引用 .sdd 运行目录：{value}")
    return errors


def validate_workflow_v2(
    preset: dict[str, Any], source: str
) -> list[str]:
    errors: list[str] = []
    for key in sorted(set(preset) - WORKFLOW_V2_FIELDS):
        errors.append(
            f"{source} 的 $.{key} 不是 schema 2 支持的字段"
        )
    if preset.get("schema") != WORKFLOW_SCHEMA_V2:
        errors.append(f"{source} 的 schema 必须是 {WORKFLOW_SCHEMA_V2}")
    name = str(preset.get("name") or "")
    if not re.fullmatch(r"[a-z][a-z0-9-]*", name):
        errors.append(f"{source} 的 name 必须是小写字母、数字和短横线")
    version = preset.get("version")
    if not isinstance(version, int) or version < 1:
        errors.append(f"{source} 的 version 必须是正整数")
    description = preset.get("description")
    if not isinstance(description, str) or not description.strip():
        errors.append(f"{source} 的 description 必须是非空说明")

    stages = preset.get("stages")
    stage_errors = validate_workflow_stages(stages, source)
    errors.extend(stage_errors)
    declared = (
        [stage for stage in stages if isinstance(stage, str)]
        if isinstance(stages, list) and not stage_errors
        else []
    )
    declared_set = set(declared)

    artifacts = preset.get("artifacts")
    if not isinstance(artifacts, dict):
        errors.append(f"{source} 的 artifacts 必须是对象")
    else:
        for stage, artifact in artifacts.items():
            path = f"artifacts.{stage}"
            if stage not in STAGE_ORDER:
                errors.append(f"{source} 的 {path} 包含未知阶段：{stage}")
                continue
            if declared_set and stage not in declared_set:
                errors.append(f"{source} 的 {path} 指向未声明的阶段：{stage}")
                continue
            canonical = CANONICAL_STAGE_ARTIFACTS.get(str(stage))
            if canonical is None:
                errors.append(f"{source} 的 {path} 没有可声明的规范产物")
            elif artifact != canonical:
                errors.append(
                    f"{source} 的 {path} 必须是 {canonical}（不允许重命名产物）"
                )
        if declared_set:
            for stage in declared:
                if stage == "MERGED":
                    continue
                if stage not in artifacts:
                    errors.append(
                        f"{source} 的 artifacts.{stage} 缺失；每个已声明阶段必须映射产物"
                    )

    gates = preset.get("gates")
    if not isinstance(gates, dict):
        errors.append(f"{source} 的 gates 必须是对象")
    else:
        missing = [gate for gate in GATE_STAGES if gate not in gates]
        if missing:
            errors.append(f"{source} 的 gates 缺少：" + ", ".join(missing))
        for gate, policy in gates.items():
            path = f"gates.{gate}"
            if gate not in GATE_STAGES:
                errors.append(f"{source} 的 {path} 是未知 Gate：{gate}")
            elif str(policy) not in WORKFLOW_POLICIES:
                errors.append(
                    f"{source} 的 {path} 必须是 "
                    + ", ".join(sorted(WORKFLOW_POLICIES))
                )

    required = preset.get("required_gates")
    if not isinstance(required, dict):
        errors.append(f"{source} 的 required_gates 必须是对象")
    else:
        for stage in required:
            if stage not in STAGE_ORDER:
                errors.append(
                    f"{source} 的 required_gates.{stage} 是未知阶段"
                )
            elif declared_set and stage not in declared_set:
                errors.append(
                    f"{source} 的 required_gates.{stage} 指向未声明的阶段"
                )
        if declared_set:
            for stage in declared:
                expected = required_gates(stage)
                actual = required.get(stage)
                if actual != expected:
                    errors.append(
                        f"{source} 的 required_gates.{stage} 必须是 {expected}"
                    )

    gate_checks = preset.get("gate_checks")
    if gate_checks is not None:
        if not isinstance(gate_checks, dict):
            errors.append(f"{source} 的 gate_checks 必须是对象")
        else:
            known_by_gate: dict[str, set[str]] = {}
            required_by_gate: dict[str, set[str]] = {}
            for check_id, item in CHECK_REGISTRY_BY_ID.items():
                gate = str(item["gate"])
                known_by_gate.setdefault(gate, set()).add(str(check_id))
            for item in CHECK_REGISTRY:
                gate = str(item["gate"])
                if item["level"] == "required":
                    required_by_gate.setdefault(gate, set()).add(str(item["id"]))
            for gate, checks in gate_checks.items():
                path = f"gate_checks.{gate}"
                if gate not in GATE_STAGES:
                    errors.append(f"{source} 的 {path} 是未知 Gate：{gate}")
                    continue
                if not isinstance(checks, list) or not all(
                    isinstance(check, str) for check in checks
                ):
                    errors.append(f"{source} 的 {path} 必须是检查 ID 数组")
                    continue
                if not checks:
                    errors.append(
                        f"{source} 的 {path} 不得为空检查集；"
                        "省略该 Gate 才表示使用完整检查集"
                    )
                    continue
                duplicates = sorted(
                    {check for check in checks if checks.count(check) > 1}
                )
                if duplicates:
                    errors.append(
                        f"{source} 的 {path} 包含重复检查：" + ", ".join(duplicates)
                    )
                unknown = sorted(set(checks) - known_by_gate.get(gate, set()))
                if unknown:
                    errors.append(
                        f"{source} 的 {path} 包含未知检查 ID：" + ", ".join(unknown)
                    )
                missing = sorted(required_by_gate.get(gate, set()) - set(checks))
                if missing:
                    errors.append(
                        f"{source} 的 {path} 缺少 required 检查："
                        + ", ".join(missing)
                    )
                missing_security = sorted(
                    check_id
                    for check_id in SECURITY_CHECK_IDS
                    if check_id in known_by_gate.get(gate, set())
                    and check_id not in checks
                )
                if missing_security:
                    errors.append(
                        f"{source} 的 {path} 不得移除安全必需检查："
                        + ", ".join(missing_security)
                    )

    checkpoints = preset.get("human_checkpoints")
    if not isinstance(checkpoints, list) or not checkpoints:
        errors.append(f"{source} 的 human_checkpoints 必须是非空数组")
    else:
        seen_types: set[str] = set()
        for index, item in enumerate(checkpoints):
            path = f"human_checkpoints[{index}]"
            if not isinstance(item, dict):
                errors.append(f"{source} 的 {path} 必须是对象")
                continue
            for key in sorted(set(item) - HUMAN_CHECKPOINT_FIELDS):
                errors.append(
                    f"{source} 的 {path}.{key} 不是支持的字段"
                )
            checkpoint_type = item.get("type")
            if checkpoint_type not in HUMAN_CHECKPOINT_TYPES:
                errors.append(
                    f"{source} 的 {path}.type 必须是 "
                    + ", ".join(sorted(HUMAN_CHECKPOINT_TYPES))
                )
                continue
            seen_types.add(str(checkpoint_type))
            if checkpoint_type == "complete_gate":
                gate = item.get("gate")
                if gate not in GATE_STAGES:
                    errors.append(
                        f"{source} 的 {path}.gate 必须是 G0–G5"
                    )
                    continue
                if isinstance(gates, dict) and str(gates.get(gate)) != "human":
                    errors.append(
                        f"{source} 的 {path}.gate 只能绑定 gates 中策略为 human 的 Gate"
                    )
                owner = GATE_OWNER_STAGE.get(str(gate))
                if declared_set and owner and owner not in declared_set:
                    errors.append(
                        f"{source} 的 {path}.gate 无法绑定到被省略阶段 {owner}"
                    )
            elif "gate" in item:
                errors.append(
                    f"{source} 的 {path}.gate 只允许出现在 complete_gate"
                )
        missing_types = {"approve_spec", "confirm_delivery"} - seen_types
        for missing in sorted(missing_types):
            errors.append(
                f"{source} 的 human_checkpoints 缺少 {missing}"
            )
        if declared_set and "SPEC_READY" not in declared_set:
            errors.append(
                f"{source} 的 human_checkpoints.approve_spec 无法绑定到被省略阶段 SPEC_READY"
            )
        if declared_set and "PR_READY" not in declared_set:
            errors.append(
                f"{source} 的 human_checkpoints.confirm_delivery 无法绑定到被省略阶段 PR_READY"
            )

    design_mode = str(preset.get("design_mode") or "")
    if design_mode not in WORKFLOW_DESIGN_MODES:
        errors.append(f"{source} 的 design_mode 必须是 full 或 lite")
    review_required = preset.get("review_required")
    if not isinstance(review_required, bool):
        errors.append(f"{source} 的 review_required 必须是布尔值")

    risk_stop = preset.get("risk_stop")
    if risk_stop is not None:
        if not isinstance(risk_stop, list) or not all(
            isinstance(item, str) and item.strip() for item in risk_stop
        ):
            errors.append(f"{source} 的 risk_stop 必须是非空字符串数组")

    context_rules = preset.get("context_rules")
    if context_rules is not None:
        if not isinstance(context_rules, dict):
            errors.append(f"{source} 的 context_rules 必须是对象")
        else:
            for key in sorted(set(context_rules) - CONTEXT_RULE_FIELDS):
                errors.append(
                    f"{source} 的 context_rules.{key} 不是支持的字段"
                )
            for key in ("include", "exclude"):
                values = context_rules.get(key)
                if values is None:
                    continue
                if not isinstance(values, list):
                    errors.append(
                        f"{source} 的 context_rules.{key} 必须是数组"
                    )
                    continue
                for index, value in enumerate(values):
                    errors.extend(
                        context_rule_pattern_errors(
                            source,
                            f"context_rules.{key}[{index}]",
                            value,
                        )
                    )

    allow_rewind = preset.get("allow_rewind_to")
    if not isinstance(allow_rewind, list):
        errors.append(f"{source} 的 allow_rewind_to 必须是数组")
    else:
        for stage in allow_rewind:
            if stage not in REWIND_PLANS:
                errors.append(
                    f"{source} 的 allow_rewind_to 包含不支持的目标：{stage}"
                )
            elif declared_set and stage not in declared_set:
                errors.append(
                    f"{source} 的 allow_rewind_to 包含未声明的阶段：{stage}"
                )

    review_policy = preset.get("review_policy")
    if review_policy is not None:
        if not isinstance(review_policy, dict):
            errors.append(f"{source} 的 review_policy 必须是对象")
        else:
            for key in sorted(set(review_policy) - {"required_for_risk"}):
                errors.append(
                    f"{source} 的 review_policy.{key} 是未知字段"
                )
            required_for_risk = review_policy.get("required_for_risk", [])
            if not isinstance(required_for_risk, list):
                errors.append(
                    f"{source} 的 review_policy.required_for_risk 必须是数组"
                )
            else:
                for value in required_for_risk:
                    if value not in RISK_RANK:
                        errors.append(
                            f"{source} 的 review_policy.required_for_risk "
                            f"包含未知风险等级：{value}"
                        )

    risk_policy = preset.get("risk_policy")
    if risk_policy is not None:
        if not isinstance(risk_policy, dict):
            errors.append(f"{source} 的 risk_policy 必须是对象")
        else:
            for key in sorted(set(risk_policy) - RISK_POLICY_FIELDS):
                errors.append(
                    f"{source} 的 risk_policy.{key} 不是支持的字段"
                )
            max_risk = risk_policy.get("max_risk")
            if max_risk is not None and max_risk not in RISK_RANK:
                errors.append(
                    f"{source} 的 risk_policy.max_risk 必须是 low/medium/high"
                )
            if "deny_risk_stop" in risk_policy and not isinstance(
                risk_policy["deny_risk_stop"], bool
            ):
                errors.append(
                    f"{source} 的 risk_policy.deny_risk_stop 必须是布尔值"
                )
    return errors


def load_workflow_preset(root: Path, name: str) -> dict[str, Any]:
    if not re.fullmatch(r"[a-z][a-z0-9-]*", name):
        raise SddError(f"非法工作流名称：{name}")
    path = workflow_root(root) / f"{name}.json"
    if not path.is_file():
        available = sorted(
            item.stem for item in workflow_root(root).glob("*.json")
        )
        raise SddError(
            f"找不到工作流预设 {name}；可选："
            + (", ".join(available) if available else "无")
        )
    preset = load_json(path)
    errors = validate_workflow_preset(preset, path.relative_to(root).as_posix())
    if preset.get("name") != name:
        errors.append(
            f"{path.relative_to(root).as_posix()} 的 name 必须与文件名一致"
        )
    if errors:
        raise SddError("工作流预设无效：\n- " + "\n- ".join(errors))
    return preset


def workflow_reference(preset: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": str(preset["name"]),
        "version": int(preset["version"]),
        "digest": workflow_digest(preset),
        "snapshot": "workflow.json",
    }


def create_workflow_snapshot(
    root: Path,
    config: dict[str, Any],
    directory: Path,
    requested: Optional[str],
) -> dict[str, Any]:
    name = (requested or str(config.get("workflow") or DEFAULT_WORKFLOW)).strip()
    preset = load_workflow_preset(root, name)
    write_json(directory / "workflow.json", preset)
    return workflow_reference(preset)


def resolve_workflow(
    root: Path, directory: Path, state: dict[str, Any]
) -> dict[str, Any]:
    reference = state.get("workflow")
    snapshot = directory / "workflow.json"
    if isinstance(reference, dict) and reference.get("name"):
        if snapshot.is_file():
            preset = load_json(snapshot)
            errors = validate_workflow_preset(
                preset,
                snapshot.relative_to(root).as_posix(),
            )
            if errors:
                raise SddError("工作流快照无效：\n- " + "\n- ".join(errors))
            digest = workflow_digest(preset)
            if reference.get("digest") and reference["digest"] != digest:
                raise SddError(
                    "工作流快照的 digest 与 state.json 不一致；"
                    "Spec 目录可能被手工修改"
                )
            if int(reference.get("version") or 0) != int(preset["version"]):
                raise SddError(
                    "工作流快照的版本与 state.json 不一致；"
                    "Spec 目录可能被手工修改"
                )
            return preset
        preset = load_workflow_preset(root, str(reference["name"]))
        expected_version = int(reference.get("version") or 0)
        if expected_version and int(preset["version"]) != expected_version:
            raise SddError(
                f"Spec 固定的是 {reference['name']}@{expected_version}，"
                f"但仓库预设已是 @{preset['version']}；"
                "旧 Spec 需要保留快照或执行后续版本的 upgrade-workflow"
            )
        if (
            reference.get("digest")
            and reference["digest"] != workflow_digest(preset)
        ):
            raise SddError(
                f"{reference['name']} 的内容已变化但 version 没有升级；"
                "请升 version 并重新生成 manifest"
            )
        return preset

    config = load_config(root)
    preset = load_workflow_preset(
        root,
        str(config.get("workflow") or DEFAULT_WORKFLOW),
    )
    return preset


def workflow_stages(workflow: Optional[dict[str, Any]]) -> list[str]:
    if workflow:
        stages = workflow.get("stages")
        if isinstance(stages, list) and stages:
            return [str(stage) for stage in stages]
    return list(STAGE_ORDER)


def next_declared_stage(
    workflow: Optional[dict[str, Any]], target: str
) -> str:
    stages = workflow_stages(workflow)
    if target in stages:
        return target
    target_index = STAGE_ORDER.index(target)
    for stage in stages:
        if STAGE_ORDER.index(stage) >= target_index:
            return stage
    return stages[-1]


def resolve_declared_transition(
    workflow: Optional[dict[str, Any]], canonical_target: str
) -> str:
    return next_declared_stage(workflow, canonical_target)


def effective_risk_stop(
    config: dict[str, Any],
    workflow: Optional[dict[str, Any]] = None,
) -> list[str]:
    values = [
        str(item).strip()
        for item in config.get("risk_stop", [])
        if str(item).strip()
    ]
    if workflow:
        values.extend(
            str(item).strip()
            for item in workflow.get("risk_stop", []) or []
            if str(item).strip()
        )
    return sorted(set(values))


def workflow_risk_error(
    preset: dict[str, Any],
    risk: str,
    risk_labels: Iterable[str],
    config: dict[str, Any],
) -> Optional[str]:
    policy = preset.get("risk_policy")
    if not isinstance(policy, dict):
        policy = {}
    profile_stops = preset.get("risk_stop")
    if not isinstance(profile_stops, list):
        profile_stops = []
    max_risk = str(policy.get("max_risk") or "high")
    if RISK_RANK.get(risk, 0) > RISK_RANK.get(max_risk, 2):
        return (
            f"工作流 {preset['name']} 只允许 risk<={max_risk}，"
            f"当前是 {risk}"
        )
    if policy.get("deny_risk_stop") or profile_stops:
        labels = {str(item) for item in risk_labels}
        stopped = labels & set(effective_risk_stop(config, preset))
        if stopped:
            return (
                f"工作流 {preset['name']} 不允许命中风险标签："
                + ", ".join(sorted(stopped))
            )
    return None


def workflow_gate_policy(
    config: dict[str, Any], preset: dict[str, Any], gate: str
) -> str:
    checkpoints = preset.get("human_checkpoints")
    if isinstance(checkpoints, list):
        mapped = {
            "spec": "G0",
            "design": "G2",
            "tasks": "G3",
            "implement": "G4",
            "implementation": "G4",
            "verify": "G5",
        }
        human_gates = {
            mapped.get(str(item), str(item))
            for item in checkpoints
        }
        if gate in human_gates:
            return "human"
    overrides = config.get("gate_overrides")
    if isinstance(overrides, dict) and gate in overrides:
        policy = str(overrides[gate])
        if policy not in WORKFLOW_POLICIES:
            raise SddError(
                f"config.json.gate_overrides.{gate} 必须是 "
                + ", ".join(sorted(WORKFLOW_POLICIES))
            )
        return policy
    legacy = config.get("gates")
    if isinstance(legacy, dict) and legacy and legacy != LEGACY_STANDARD_GATES:
        policy = str(legacy.get(gate, ""))
        if policy in WORKFLOW_POLICIES:
            return policy
    gates = preset.get("gates")
    if isinstance(gates, dict) and gate in gates:
        return str(gates[gate])
    return str(config.get("gates", {}).get(gate, "auto"))


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
    seq: int,
    entry: dict[str, Any],
    from_state: Optional[str],
    history_index: Optional[int] = None,
) -> dict[str, Any]:
    evidence = str(entry.get("evidence") or "")
    event_name = entry.get("action") or (
        "spec_created" if evidence == "created" else "state_transition"
    )
    event: dict[str, Any] = {
        "schema": EVENT_SCHEMA,
        "seq": seq,
        "at": entry.get("at"),
        "event": event_name,
        "from_state": from_state,
        "to_state": entry.get("state"),
        "evidence": evidence,
        "next": entry.get("next") or NEXT_ACTION_BY_STATE.get(
            str(entry.get("state") or ""),
            "",
        ),
    }
    if history_index is not None:
        event["history_index"] = history_index
    for key in (
        "task",
        "commit",
        "pr_url",
        "gate",
        "reason",
        "actor",
        "source",
        "role",
        "session",
        "session_source",
        "executor",
        "model",
        "approver",
        "artifacts",
        "workflow",
        "rewind",
        "usage",
    ):
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


def event_hash(event: dict[str, Any]) -> str:
    payload = {
        key: value
        for key, value in event.items()
        if key != "event_sha256"
    }
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def last_event_hash(events: list[dict[str, Any]]) -> str:
    for event in reversed(events):
        digest = str(event.get("event_sha256") or "")
        if digest:
            return digest
    return ""


def verify_event_chain(events: list[dict[str, Any]]) -> dict[str, Any]:
    previous = ""
    hashed_events = 0
    legacy_events = 0
    errors: list[str] = []
    chain_started = False
    for event in events:
        digest = str(event.get("event_sha256") or "")
        if not digest:
            if chain_started:
                errors.append(
                    f"事件 seq={event.get('seq')} 缺少 event_sha256"
                )
            else:
                legacy_events += 1
            continue
        chain_started = True
        hashed_events += 1
        if str(event.get("prev_sha256") or "") != previous:
            errors.append(
                f"事件 seq={event.get('seq')} 的 prev_sha256 不连续"
            )
        if event_hash(event) != digest:
            errors.append(
                f"事件 seq={event.get('seq')} 的内容与 event_sha256 不一致"
            )
        previous = digest
    return {
        "valid": not errors,
        "events": len(events),
        "hashed_events": hashed_events,
        "legacy_events": legacy_events,
        "errors": errors,
    }


def check_event_chain(directory: Path) -> list[str]:
    result = verify_event_chain(read_event_log(directory))
    if result["valid"]:
        return []
    return [
        "审计事件链无效：" + " / ".join(result["errors"])
    ]


def derive_events(state: dict[str, Any]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    previous_state: Optional[str] = None
    for index, entry in enumerate(state.get("history", [])):
        if not isinstance(entry, dict):
            continue
        event = _event_from_history(index + 1, entry, previous_state, index)
        events.append(event)
        previous_state = entry.get("state")
    return events


def append_event_log(directory: Path, state: dict[str, Any]) -> None:
    """Append new history entries to events.jsonl without rewriting old events."""
    history = [entry for entry in state.get("history", []) if isinstance(entry, dict)]
    existing = read_event_log(directory)
    indexed = [
        event
        for event in existing
        if isinstance(event.get("history_index"), int)
    ]
    if indexed:
        emitted = {int(event["history_index"]) for event in indexed}
        start = 0
    else:
        emitted = set()
        audit_only = {
            "gate_result",
            "check_failed",
            "waiver_created",
            "waiver_rejected",
        }
        start = len(
            [
                event
                for event in existing
                if event.get("event") not in audit_only
            ]
        )
    if start >= len(history) and emitted >= set(range(len(history))):
        return
    next_seq = max((int(event.get("seq", 0)) for event in existing), default=0) + 1
    previous_hash = last_event_hash(existing)
    path = directory / "events.jsonl"
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        for index, entry in enumerate(history):
            if index < start or index in emitted:
                continue
            from_state = (
                history[index - 1].get("state") if index > 0 else None
            )
            event = _event_from_history(next_seq, entry, from_state, index)
            event["prev_sha256"] = previous_hash
            event["event_sha256"] = event_hash(event)
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")
            previous_hash = str(event["event_sha256"])
            next_seq += 1


def add_history(
    state: dict[str, Any], state_name: str, evidence: str, **extra: Any
) -> None:
    entry: dict[str, Any] = {
        "state": state_name,
        "at": now(),
        "evidence": evidence,
    }
    entry.update(history_meta())
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


def spec_metadata_errors(
    text: str,
    spec_id: Optional[str] = None,
    require_feat: bool = False,
) -> list[str]:
    errors: list[str] = []
    if spec_id:
        declared = metadata_value(text, "Spec ID", "SpecID")
        if declared != spec_id:
            errors.append(
                f"spec.md 元数据 Spec ID 必须是 {spec_id}，当前是 {declared or '空'}"
            )
    work_item = metadata_value(text, "工作项 ID", "工作项ID", "Work Item ID")
    if is_placeholder_value(work_item):
        errors.append("spec.md 缺少有效的工作项 ID")
    elif work_item.startswith("%"):
        errors.append("spec.md 的工作项 ID 不能带前导 %")
    feat = metadata_value(
        text,
        "FEAT ID",
        "FEAT",
        "Feature ID",
        "FeatureID",
    )
    if require_feat and not FEAT_RE.fullmatch(feat):
        errors.append(f"G0-04 spec.md 缺少有效 FEAT ID（当前 {feat or '空'}）")
    return errors

def spec_scope_errors(text: str) -> list[str]:
    errors: list[str] = []
    scope = section_body(text, ("范围声明", "Scope"))
    in_scope = re.search(r"(?im)^\s*[-*]?\s*In-Scope\s*[：:]\s*(.+)$", scope)
    out_scope = re.search(r"(?im)^\s*[-*]?\s*Out-of-Scope\s*[：:]\s*(.+)$", scope)
    if not in_scope or is_placeholder_value(in_scope.group(1)):
        errors.append("spec.md 的 In-Scope 未填写")
    if not out_scope or is_placeholder_value(out_scope.group(1)):
        errors.append("spec.md 的 Out-of-Scope 未填写")
    return errors


def spec_section_errors(text: str) -> list[str]:
    return [
        f"spec.md 缺少章节：{aliases[0]}"
        for aliases in SPEC_SECTIONS
        if not has_section(text, aliases)
    ]


def spec_fr_ac_errors(text: str) -> list[str]:
    errors: list[str] = []
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
        suffix = ac[3:].split("-", 1)[0]
        if f"FR-{suffix}" not in frs:
            errors.append(f"{ac} 没有对应的 FR-{suffix}")
    fr_defs = re.findall(r"(?m)^#{1,6}\s+(FR-\d{3})\b", text)
    ac_defs = re.findall(
        r"(?m)^\s*[-*]?\s*(AC-\d{3}-[1-9]\d*)\s*[:：]", text
    )
    if len(fr_defs) != len(set(fr_defs)):
        errors.append("spec.md 存在重复 FR 定义")
    if len(ac_defs) != len(set(ac_defs)):
        errors.append("spec.md 存在重复 AC 定义")
    return errors


def spec_ac_testability_errors(text: str) -> list[str]:
    errors: list[str] = []
    for ac in extract_acs(text):
        line = ""
        for raw in text.splitlines():
            if ac in raw:
                line = raw
                break
        if not all(word in line for word in ("Given", "When", "Then")):
            errors.append(f"{ac} 必须在同一条验收定义中包含 Given/When/Then")
        if "执行路径" not in line:
            errors.append(f"{ac} 缺少【执行路径：...】标注")
    return errors


def check_spec(
    text: str,
    spec_id: Optional[str] = None,
    require_feat: bool = False,
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    errors.extend(spec_section_errors(text))
    errors.extend(placeholder_errors("spec.md", text))
    errors.extend(spec_metadata_errors(text, spec_id, require_feat))
    errors.extend(spec_scope_errors(text))
    errors.extend(spec_fr_ac_errors(text))
    errors.extend(spec_ac_testability_errors(text))
    return errors, extract_acs(text)


def check_design(
    text: str,
    spec_acs: list[str],
    workflow: Optional[dict[str, Any]] = None,
) -> list[str]:
    if workflow and str(workflow.get("design_mode") or "full") == "lite":
        return check_design_lite(text, spec_acs)
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
    risk_body = section_body(text, ("依赖与风险", "风险", "Risks"))
    if "负责人" not in risk_body or "缓解" not in risk_body:
        errors.append(
            "G2-04 design.md 的风险表缺少负责人或缓解措施"
        )
    if not section_has_content(text, ("回滚方案", "Rollback")):
        errors.append("design.md 的“回滚方案”没有实际内容")
    return errors


def check_design_lite(text: str, spec_acs: list[str]) -> list[str]:
    errors: list[str] = []
    for aliases in DESIGN_LITE_SECTIONS:
        if not has_section(text, aliases):
            errors.append(f"design.md 缺少轻量设计章节：{aliases[0]}")
    errors.extend(placeholder_errors("design.md", text))
    covered = set(extract_acs(text))
    missing = sorted(set(spec_acs) - covered)
    if missing:
        errors.append("design.md 没有覆盖以下 AC：" + ", ".join(missing))
    for section in (
        ("根因", "Root Cause"),
        ("修复策略", "Fix Strategy"),
        ("影响范围", "Impact"),
        ("回滚方案", "Rollback"),
    ):
        if not section_has_content(text, section):
            errors.append(f"design.md 的“{section[0]}”没有实际内容")
    return errors


def check_tasks(
    text: str,
    spec_acs: list[str],
    config: Optional[dict[str, Any]] = None,
    root: Optional[Path] = None,
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
    if root is not None:
        test_files = collect_test_files(root, config or {})
        definitions = scan_test_definitions(
            [
                (path.relative_to(root).as_posix(), read_text(path))
                for path in test_files
            ]
        )
        errors.extend(
            test_reference_errors(
                text,
                definitions,
                test_files_present=bool(test_files),
            )
        )

    mapping = section_body(
        text, ("AC—Task—单元测试映射", "AC-Task-单元测试映射", "AC Coverage")
    )
    for ac in spec_acs:
        if ac not in mapping:
            errors.append(f"tasks.md 的 AC—Task—单元测试映射缺少 {ac}")
    if not re.search(r"(?im)^\s*```mermaid", section_body(text, ("依赖图", "Dependency Graph"))):
        errors.append("tasks.md 的依赖图像缺少 Mermaid 图")
    return errors


def unquote_field(value: str) -> str:
    cleaned = value.strip()
    if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] == "`":
        cleaned = cleaned[1:-1]
    return cleaned.strip()


def parse_command_evidence(text: str) -> list[dict[str, Any]]:
    lines = text.splitlines()
    blocks: list[dict[str, Any]] = []
    index = 0
    while index < len(lines):
        match = re.match(r"^\s*-\s*Command:\s*(.+?)\s*$", lines[index], re.I)
        if not match:
            index += 1
            continue
        block: dict[str, Any] = {"command": unquote_field(match.group(1))}
        index += 1
        while index < len(lines):
            field = re.match(
                r"^\s*-\s*(CWD|Exit|Head|Plan-Hash|At|Output):\s*(.*)$",
                lines[index],
                re.I,
            )
            if field:
                block[field.group(1).lower()] = unquote_field(field.group(2))
                index += 1
                continue
            if not lines[index].strip():
                index += 1
                continue
            break
        while index < len(lines) and not lines[index].strip():
            index += 1
        if index < len(lines) and lines[index].strip().startswith("```"):
            index += 1
            output: list[str] = []
            while index < len(lines) and not lines[index].strip().startswith("```"):
                output.append(lines[index])
                index += 1
            block["output"] = "\n".join(output).strip()
            index += 1
        blocks.append(block)
    return blocks


def verification_evidence_errors(
    text: str,
    config: dict[str, Any],
    state: dict[str, Any],
    directory: Optional[Path] = None,
) -> list[str]:
    if is_legacy_merged(state):
        return []
    commands = [
        str(item).strip()
        for item in config.get("test_commands", [])
        if str(item).strip()
    ]
    errors: list[str] = []
    if not commands:
        errors.append(
            "config.test_commands 为空；G5 为 manual/unverified，"
            "必须配置可执行测试命令后才能进入 PR_READY"
        )
    blocks = parse_command_evidence(text)
    if not blocks:
        errors.append(
            "verification.md 缺少结构化命令证据；"
            "需要 Command/CWD/Exit/Head/Plan-Hash/At"
        )
        return errors
    blocks = blocks[:1]
    success = False
    structured_evidence = False
    if directory is not None:
        records, _ = load_verification_evidence(directory)
        structured_evidence = any(
            record.get("exit_code") == 0 and not record.get("timed_out")
            for record in records
        )
    for block in blocks:
        command = str(block.get("command") or "")
        exit_value = str(block.get("exit") or "").strip()
        if not re.fullmatch(r"-?\d+", exit_value):
            errors.append(f"命令证据缺少有效 Exit：{command or '(empty)'}")
            continue
        missing = [
            field
            for field in (
                ("cwd",)
                if structured_evidence
                else ("cwd", "head", "plan-hash", "at")
            )
            if not str(block.get(field) or "").strip()
        ]
        if missing:
            errors.append(
                f"命令证据 {command or '(empty)'} 缺少字段：" + ", ".join(missing)
            )
        if int(exit_value) != 0:
            errors.append(
                f"命令证据退出码非 0（exit {exit_value}）：{command or '(empty)'}"
            )
        else:
            success = True
    if not success:
        errors.append("verification.md 没有 exit=0 的成功命令证据")
    return errors


def requires_independent_review(
    config: dict[str, Any],
    state: dict[str, Any],
    workflow: Optional[dict[str, Any]],
) -> bool:
    if workflow and workflow.get("review_required"):
        return True
    risk = str(state.get("risk") or "low").strip().lower()
    if risk in {"medium", "high", "critical"}:
        return True
    labels = {
        str(item).strip().lower()
        for item in state.get("risk_labels", [])
        if str(item).strip()
    }
    stops = {
        str(item).strip().lower()
        for item in effective_risk_stop(config, workflow)
        if str(item).strip()
    }
    return bool(labels & stops)


def check_verification(
    text: str,
    spec_acs: list[str],
    workflow: Optional[dict[str, Any]] = None,
    state: Optional[dict[str, Any]] = None,
    config: Optional[dict[str, Any]] = None,
    directory: Optional[Path] = None,
) -> list[str]:
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
    errors.extend(
        verification_evidence_errors(
            text,
            config or {},
            state or {},
            directory,
        )
    )
    merged = str((state or {}).get("state") or "") == "MERGED"
    if not merged and requires_independent_review(config or {}, state or {}, workflow):
        errors.extend(check_independent_review(text, state or {}))
    return errors


def is_legacy_merged(state: dict[str, Any]) -> bool:
    return (
        str(state.get("state") or "") == "MERGED"
        and not state.get("delivery_confirmed_at")
    )


def review_fields(text: str) -> dict[str, str]:
    body = section_body(text, ("独立审查", "Independent Review"))
    fields: dict[str, str] = {}
    for cells in table_rows(body):
        if len(cells) >= 2 and cells[0]:
            fields[normalize_heading(cells[0])] = cells[1].strip()
    for line in body.splitlines():
        match = re.match(r"^\s*[-*]?\s*([^:：]+)[:：]\s*(.+)$", line)
        if match:
            fields.setdefault(
                normalize_heading(match.group(1)),
                match.group(2).strip(),
            )
    return fields


def check_independent_review(
    text: str, state: dict[str, Any]
) -> list[str]:
    errors: list[str] = []
    if not has_section(text, ("独立审查", "Independent Review")):
        errors.append(
            "中高风险或 l2-strict 要求 verification.md 包含“独立审查”章节"
        )
        return errors
    fields = review_fields(text)
    required = {
        "reviewer": ("Reviewer", "审查人"),
        "session": ("Session", "会话"),
        "model": ("Model", "模型"),
        "scope": ("Scope", "检查范围", "审查范围"),
        "findings": ("Findings", "审查发现", "问题"),
        "blocking issues": ("Blocking issues", "Blocking Issues", "阻断问题"),
    }
    values: dict[str, str] = {}
    for key, aliases in required.items():
        value = next(
            (
                fields.get(normalize_heading(alias), "")
                for alias in aliases
                if fields.get(normalize_heading(alias))
            ),
            "",
        )
        values[key] = value
        if is_placeholder_value(value):
            errors.append(f"独立审查缺少有效字段：{aliases[0]}")
    blocking = values.get("blocking issues", "")
    if blocking and not re.fullmatch(
        r"(?i)\s*(none|no|无|没有|0)\s*[。.]?\s*",
        blocking,
    ):
        errors.append(
            "独立审查的 Blocking issues 必须是 none/无；"
            "有阻断问题则不能进入 PR_READY"
        )
    reviewer_session = values.get("session", "").strip()
    implementer_sessions = {
        str(entry.get("session"))
        for entry in state.get("history", [])
        if isinstance(entry, dict)
        and entry.get("role") == "implementer"
        and entry.get("session")
    }
    if (
        reviewer_session
        and not is_placeholder_value(reviewer_session)
        and reviewer_session in implementer_sessions
    ):
        errors.append(
            "独立审查的 Session 与实现会话相同；"
            "要求独立 reviewer"
        )
    return errors


def review_reports_no_findings(value: str) -> bool:
    return bool(
        re.search(
            r"(?i)未发现可执行问题|no\s+actionable\s+(?:issues|findings)",
            value,
        )
    )


def check_review_evidence(
    directory: Path,
    state: dict[str, Any],
    workflow: dict[str, Any],
) -> list[str]:
    if str(state.get("state") or "") == "MERGED":
        return []
    if not review_required_for(workflow, state):
        return []
    text = read_text(directory / "verification.md")
    errors = check_independent_review(text, state)
    fields = review_fields(text)
    findings_text = next(
        (
            fields.get(normalize_heading(alias), "")
            for alias in ("Findings", "审查发现", "问题")
            if fields.get(normalize_heading(alias))
        ),
        "",
    )
    no_findings = review_reports_no_findings(findings_text)
    path = directory / "review-findings.json"
    if not no_findings and not path.is_file():
        errors.append(
            "Review 发现问题时必须提供 review-findings.json，"
            "并为每个 finding 写齐九个字段"
        )
    if not path.is_file():
        return errors
    try:
        payload = load_json(path)
    except SddError as exc:
        errors.append(f"Review findings JSON 无效：{exc}")
        return errors
    schema_errors, unresolved = validate_review_findings(payload)
    errors.extend(schema_errors)
    if unresolved:
        errors.append(
            "Review 仍有未关闭阻断 finding："
            + ", ".join(unresolved)
            + "；关闭并复核后才能通过 G4/G5"
        )
    if no_findings and isinstance(payload, list) and payload:
        errors.append(
            "独立审查结论称“未发现可执行问题”，"
            "但 review-findings.json 仍包含 finding"
        )
    if not no_findings and isinstance(payload, list) and not payload:
        errors.append(
            "Review 结论记录了问题，但 review-findings.json 为空数组"
        )
    return list(dict.fromkeys(errors))


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


def parse_test_reference(reference: str) -> dict[str, str]:
    value = reference.strip().strip("`")
    file_hint = ""
    class_name = ""
    method = ""
    if "::" in value:
        pieces = [piece for piece in value.split("::") if piece]
        if len(pieces) >= 3:
            file_hint = pieces[0]
            class_name = pieces[-2]
            method = pieces[-1]
        elif len(pieces) == 2:
            file_hint, method = pieces
        elif pieces:
            method = pieces[0]
    elif "#" in value:
        left, method = value.split("#", 1)
        parts = [part for part in left.replace("/", ".").split(".") if part]
        if parts and parts[-1][:1].isupper():
            class_name = parts[-1]
            module = parts[:-1]
        else:
            module = parts
        if module:
            file_hint = "/".join(module) + ".py"
    else:
        parts = [part for part in value.split(".") if part]
        if parts:
            method = parts[-1]
            if len(parts) >= 2 and parts[-2][:1].isupper():
                class_name = parts[-2]
                module = parts[:-2]
            else:
                module = parts[:-1]
            if module:
                file_hint = "/".join(module) + ".py"
    return {
        "file": file_hint.replace("\\", "/"),
        "class": class_name,
        "method": method,
    }


def task_test_references(value: str) -> list[str]:
    refs = re.findall(r"`([^`]+)`", value)
    if not refs:
        refs = [part for part in re.split(r"[、,，;\s]+", value) if part]
    resolved: list[str] = []
    base = ""
    for ref in refs:
        cleaned = ref.strip()
        if not cleaned:
            continue
        if cleaned.startswith("#") and base:
            cleaned = base + cleaned
        elif "#" in cleaned:
            base = cleaned.split("#", 1)[0]
        resolved.append(cleaned)
    return resolved


def locate_test_reference(
    root: Path, config: dict[str, Any], reference: str
) -> bool:
    parsed = parse_test_reference(reference)
    method = parsed["method"]
    if not method:
        return False
    files = collect_test_files(root, config)
    if parsed["file"]:
        relative = parsed["file"].lstrip("./")
        files = [
            path
            for path in files
            if path.relative_to(root).as_posix().endswith(relative)
        ]
    class_pattern = (
        re.compile(rf"^\s*class\s+{re.escape(parsed['class'])}\b", re.M)
        if parsed["class"]
        else None
    )
    method_pattern = re.compile(
        rf"^\s*(?:async\s+)?def\s+{re.escape(method)}\s*\(", re.M
    )
    for path in files:
        text = read_text(path)
        if class_pattern is not None and not class_pattern.search(text):
            continue
        if method_pattern.search(text):
            return True
    return False


def task_test_name_errors(
    root: Path, config: dict[str, Any], tasks: list[dict[str, Any]]
) -> list[str]:
    if not collect_test_files(root, config):
        return ["没有找到测试文件；请按 config.json 的 test_globs 添加测试"]
    errors: list[str] = []
    for task in tasks:
        for reference in task_test_references(str(task.get("test") or "")):
            if not locate_test_reference(root, config, reference):
                errors.append(
                    f"{task['id']} 的测试名无法定位：{reference}"
                )
    return errors


def fallback_test_function_acs(text: str) -> dict[str, set[str]]:
    results: dict[str, set[str]] = {}
    current: Optional[str] = None
    indent = 0
    body: list[str] = []
    for line in text.splitlines():
        match = re.match(
            r"^(?P<indent>[ \t]*)(?:async\s+)?def\s+(?P<name>test\w*)\s*\(",
            line,
        )
        if match:
            if current:
                results[current] = set(extract_acs("\n".join(body)))
            current = match.group("name")
            indent = len(match.group("indent").expandtabs(8))
            body = []
            continue
        if current is None:
            continue
        stripped = line.strip()
        current_indent = len(line) - len(line.lstrip())
        if stripped and current_indent <= indent:
            results[current] = set(extract_acs("\n".join(body)))
            current = None
            body = []
        else:
            body.append(line)
    if current:
        results[current] = set(extract_acs("\n".join(body)))
    return results


def test_function_acs(text: str) -> dict[str, set[str]]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return fallback_test_function_acs(text)
    results: dict[str, set[str]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not node.name.startswith("test"):
            continue
        meaningful = [
            statement
            for statement in node.body
            if not (
                isinstance(statement, ast.Expr)
                and isinstance(statement.value, ast.Constant)
                and isinstance(statement.value.value, str)
            )
            and not isinstance(statement, ast.Pass)
        ]
        if not meaningful:
            results[node.name] = set()
            continue
        segment = ast.get_source_segment(text, node) or ""
        results[node.name] = set(extract_acs(segment))
    return results


def check_test_coverage(root: Path, config: dict[str, Any], spec_acs: list[str]) -> list[str]:
    files = collect_test_files(root, config)
    if not files:
        return ["没有找到测试文件；请按 config.json 的 test_globs 添加测试"]
    covered: set[str] = set()
    for path in files:
        for acs in test_function_acs(read_text(path)).values():
            covered.update(acs)
    missing = sorted(set(spec_acs) - covered)
    if missing:
        return [
            "测试函数的函数体内没有关联以下 AC：" + ", ".join(missing)
        ]
    return []


EVIDENCE_SCHEMA = 1
EVIDENCE_REQUIRED_FIELDS = (
    "schema",
    "spec",
    "command",
    "cwd",
    "started_at",
    "finished_at",
    "exit_code",
    "duration_ms",
    "output_sha256",
    "output_excerpt",
    "artifact_hashes",
)


def evidence_path(directory: Path) -> Path:
    return directory / "verification-evidence.jsonl"


def load_verification_evidence(directory: Path) -> tuple[list[dict[str, Any]], list[str]]:
    path = evidence_path(directory)
    if not path.is_file():
        return [], []
    records: list[dict[str, Any]] = []
    errors: list[str] = []
    for number, line in enumerate(read_text(path).splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"G5-03 证据文件第 {number} 行不是有效 JSON：{exc}")
            continue
        if not isinstance(value, dict):
            errors.append(f"G5-03 证据文件第 {number} 行不是对象")
            continue
        records.append(value)
    return records, errors


def latest_evidence_run(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not records:
        return []
    run_id = records[-1].get("run_id")
    if run_id:
        return [record for record in records if record.get("run_id") == run_id]
    return [records[-1]]


def check_verification_evidence(
    root: Path,
    directory: Path,
    config: dict[str, Any],
    spec_id: str,
    spec_text: str,
    design_text: str,
    tasks_text: str,
    state: Optional[dict[str, Any]] = None,
) -> list[str]:
    if (
        state is not None
        and str(state.get("state") or "") == "MERGED"
        and not evidence_path(directory).is_file()
    ):
        return []
    code_paths = list(
        dict.fromkeys(
            [
                *declared_code_paths(tasks_text),
                *declared_code_paths(design_text),
                *declared_code_paths(spec_text),
            ]
        )
    )
    records, errors = load_verification_evidence(directory)
    path = evidence_path(directory).relative_to(root).as_posix()
    check_id = "G5-03" if code_paths else "G5-09"
    if not records and not errors:
        if code_paths:
            errors.append(
                "G5-03 代码变更缺少可复验的测试命令证据："
                f"{path} 不存在或没有记录"
            )
        else:
            errors.append(
                "G5-09 纯文档/配置变更未执行测试命令；"
                "请运行 sdd verify 或由人创建带范围的显式豁免"
            )
    run = latest_evidence_run(records)
    if records and not run:
        errors.append(f"{check_id} 没有可复验的验证运行记录")
    if run:
        for record in run:
            missing = [
                field
                for field in EVIDENCE_REQUIRED_FIELDS
                if field not in record or record.get(field) in (None, "")
            ]
            if missing:
                errors.append(
                    f"{check_id} 证据记录字段不完整："
                    + ", ".join(missing)
                )
            if str(record.get("spec") or "") != spec_id:
                errors.append(
                    f"{check_id} 证据绑定的 Spec 不是 {spec_id}"
                )
        successes = [
            record
            for record in run
            if record.get("exit_code") == 0 and not record.get("timed_out")
        ]
        if not successes:
            errors.append(
                f"{check_id} 最近一次验证没有成功执行的测试命令；"
                "非零退出码、超时或未执行都不能作为 PASS 证据"
            )
        elif len(successes) != len(run):
            errors.append(
                f"{check_id} 最近一次验证存在失败或超时的命令，不能判定为 PASS"
            )
    return list(dict.fromkeys(errors))


WAIVER_REQUIRED_FIELDS = (
    "id",
    "check_id",
    "spec",
    "scope",
    "reason",
    "approver",
    "created_at",
    "expires_at",
    "evidence",
)


def waiver_is_expired(waiver: dict[str, Any], at: Optional[datetime] = None) -> bool:
    expires = parse_timestamp(waiver.get("expires_at"))
    if expires is None:
        return True
    return (at or datetime.now().astimezone()) > expires


def waiver_applies(
    waiver: dict[str, Any],
    check_id: str,
    spec_id: str,
    contexts: Iterable[str],
) -> bool:
    if str(waiver.get("check_id") or "") != check_id:
        return False
    if str(waiver.get("spec") or "") not in {"", "*", spec_id}:
        return False
    artifact_contexts = {
        str(item)
        for item in waiver.get("artifact_contexts", []) or []
        if str(item)
    }
    if artifact_contexts and not artifact_contexts & {
        str(item) for item in contexts
    }:
        return False
    scopes = {
        item.strip()
        for item in re.split(r"[,;，；]", str(waiver.get("scope") or ""))
        if item.strip()
    }
    if not scopes:
        return False
    contexts = {str(item) for item in contexts}
    return bool(scopes & {"*", spec_id}) or bool(scopes & contexts)


def find_waiver(
    state: dict[str, Any],
    check_id: str,
    spec_id: str,
    contexts: Iterable[str],
) -> tuple[Optional[dict[str, Any]], bool]:
    waivers = state.get("waivers")
    if not isinstance(waivers, list):
        return None, False
    expired: Optional[dict[str, Any]] = None
    for waiver in reversed(waivers):
        if not isinstance(waiver, dict):
            continue
        if not waiver_applies(waiver, check_id, spec_id, contexts):
            continue
        if waiver_is_expired(waiver):
            expired = waiver
            continue
        return waiver, False
    return None, expired is not None


def waiver_contexts(
    directory: Path,
    stage: str,
) -> list[str]:
    base = {
        "spec": ["spec"],
        "design": ["design"],
        "tasks": ["tasks"],
        "verify": ["verification", "ci"],
        "ci": ["ci", "verification"],
    }.get(stage, ["spec", "design", "tasks", "verification", "ci"])
    tasks = parse_tasks(read_text(directory / "tasks.md"))
    contexts = [
        *base,
        *[f"task:{task['id']}" for task in tasks],
    ]
    gates = {
        "spec": ("G0", "G1"),
        "design": ("G2",),
        "tasks": ("G3", "G4"),
        "verify": ("G5",),
        "ci": ("G0", "G1", "G2", "G3", "G4", "G5"),
    }.get(stage, tuple(GATE_STAGES))
    root = directory.parents[2] if len(directory.parents) >= 3 else directory
    for gate in gates:
        for artifact in gate_artifact_entries(root, directory, gate):
            contexts.append(
                f"artifact:{artifact['path']}:{artifact['sha256']}"
            )
    return contexts


def apply_check_waivers(
    checks: list[dict[str, Any]],
    state: dict[str, Any],
    spec_id: str,
    contexts: Iterable[str],
) -> list[dict[str, Any]]:
    for item in checks:
        if item.get("result") != "block":
            continue
        waiver, expired = find_waiver(
            state,
            str(item.get("id")),
            spec_id,
            contexts,
        )
        if waiver:
            item["result"] = "waived"
            item["waiver_id"] = waiver.get("id")
            item["detail"] = (
                str(item.get("detail") or "")
                + "；已由人工豁免 "
                + str(waiver.get("id") or "")
            )
        elif expired:
            item["detail"] = str(item.get("detail") or "") + "；豁免已过期"
    return checks


def partition_waived_errors(
    errors: Iterable[str],
    gate: str,
    state: dict[str, Any],
    spec_id: str,
    contexts: Iterable[str],
) -> tuple[list[str], list[dict[str, Any]]]:
    blocking: list[str] = []
    waived: list[dict[str, Any]] = []
    for error in errors:
        check_id = check_id_for_error(gate, str(error))
        definition = EXT_CHECK_REGISTRY.get(check_id, {})
        if definition.get("level") == "advisory":
            continue
        waiver, expired = find_waiver(
            state,
            check_id,
            spec_id,
            contexts,
        )
        if waiver and definition.get("waivable"):
            waived.append(
                {
                    "check_id": check_id,
                    "waiver_id": waiver.get("id"),
                    "error": str(error),
                }
            )
            continue
        suffix = "（豁免已过期）" if expired else ""
        blocking.append(str(error) + suffix)
    return blocking, waived


def partition_stage_errors(
    errors: Iterable[str],
    stage: str,
    state: dict[str, Any],
    spec_id: str,
    directory: Path,
) -> tuple[list[str], list[dict[str, Any]]]:
    gates = {
        "spec": ["G0", "G1"],
        "design": ["G2"],
        "tasks": ["G3"],
        "verify": ["G5"],
        "ci": ["G0", "G1", "G2", "G3", "G4", "G5"],
    }.get(stage, ["G0", "G1", "G2", "G3", "G4", "G5"])
    contexts = waiver_contexts(directory, stage)
    blocking: list[str] = []
    waived: list[dict[str, Any]] = []
    for error in errors:
        gate = gates[0]
        matched_gate: Optional[str] = None
        for candidate in GATE_STAGES:
            check_id = check_id_for_error(candidate, str(error))
            if not check_id.endswith("-99"):
                gate = candidate
                matched_gate = candidate
                break
        if matched_gate:
            definition = EXT_CHECK_REGISTRY.get(
                check_id_for_error(matched_gate, str(error)),
                {},
            )
            if definition.get("level") == "advisory":
                continue
        item_blocking, item_waived = partition_waived_errors(
            [error],
            gate,
            state,
            spec_id,
            contexts,
        )
        blocking.extend(item_blocking)
        waived.extend(item_waived)
    return blocking, waived


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
        if re.match(r"^##\s*(FEAT\s*映射|FEAT\s*Mapping)\s*$", stripped, re.I):
            break
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


def parse_feat_map(text: str) -> list[dict[str, str]]:
    body = section_body(text, ("FEAT 映射", "FEAT Mapping"))
    if not body:
        return []
    header_index: Optional[dict[str, int]] = None
    rows: list[dict[str, str]] = []
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            continue
        cells = split_table_row(stripped)
        if not cells:
            continue
        if all(
            re.fullmatch(r":?-{3,}:?", cell.replace(" ", ""))
            for cell in cells
        ):
            continue
        normalized = {normalize_column(cell): index for index, cell in enumerate(cells)}
        if "feat" in normalized and "specid" in normalized:
            header_index = normalized
            continue
        if header_index is None:
            continue

        def cell(*aliases: str) -> str:
            for alias in aliases:
                index = header_index.get(normalize_column(alias))
                if index is not None and index < len(cells):
                    return cells[index].strip()
            return ""

        row = {
            "feat": cell("FEAT"),
            "work_item": cell("工作项 ID", "工作项"),
            "spec": cell("Spec ID", "Spec"),
            "fr": cell("FR"),
            "acs": cell("AC", "ACS"),
        }
        if any(row.values()):
            rows.append(row)
    return rows


def allocate_feat(root: Path, config: dict[str, Any]) -> str:
    text = read_text(prd_index_path(root, config))
    numbers = [int(match.group(1)) for match in re.finditer(r"\bFEAT-([0-9]{3})\b", text)]
    return f"FEAT-{max(numbers, default=0) + 1:03d}"


def ensure_prd_index(
    root: Path,
    config: dict[str, Any],
    spec_id: str,
    work_item: str,
    title: str,
    issue: Optional[str],
    feat: Optional[str] = None,
    feat_id: Optional[str] = None,
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
        feat = feat or feat_id or allocate_feat_id(root, config)
        safe_title = " ".join(title.split()).replace("|", "\\|")
        link = (issue or "N/A").replace("|", "\\|")
        row = (
            f"| {work_item} | {link} | current | {feat} | {spec_id} | "
            f"{safe_title} | 0 |"
        )
        marker = re.search(
            r"(?im)^##\s*(FEAT\s*映射|FEAT\s*Mapping)\s*$", text
        )
        if marker:
            head = text[: marker.start()].rstrip("\n")
            tail = text[marker.start():].lstrip("\n")
            text = head + "\n" + row + "\n\n" + tail
        else:
            text = text.rstrip("\n") + "\n" + row + "\n"
        write_text(path, text)
    return path


def allocate_feat_id(root: Path, config: dict[str, Any]) -> str:
    text = read_text(prd_index_path(root, config))
    return f"FEAT-{next_feat_number(text):03d}"


def prd_index_structure_errors(
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
    if not re.search(r"(?im)^\s*(?:[-*]\s*)?updated\s*[:：]\s*\S+", text):
        errors.append("docs/prd-index.md 头部缺少 updated 时间")
    if not prd_index_rows(text):
        errors.append("docs/prd-index.md 没有可解析的映射表行")
    if source == "repo":
        prd_path = root / "docs" / "prd.md"
        if not prd_path.is_file():
            errors.append("source: repo 时必须存在 docs/prd.md")
    return errors


def prd_index_clarify_errors(
    root: Path,
    config: dict[str, Any],
    state: dict[str, Any],
    spec_text: str,
) -> list[str]:
    if not config.get("require_prd_index"):
        return []
    text = read_text(prd_index_path(root, config))
    if CLARIFY_RE.search(text):
        return ["docs/prd-index.md 还有 [NEEDS CLARIFICATION] 标记"]
    spec_id = str(state.get("spec_id", ""))
    for row in prd_index_rows(text):
        if row.get("specid") != spec_id:
            continue
        raw = str(row.get("澄清标记", "0")).strip()
        try:
            count = int(raw or "0")
        except ValueError:
            count = 1
        if count:
            return [f"docs/prd-index.md 的澄清标记为 {count}，必须清零"]
    return []


def prd_index_registration_errors(
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
    spec_id = str(state.get("spec_id", ""))
    work_item = metadata_value(spec_text, "工作项 ID", "工作项ID") or str(
        state.get("work_item") or state.get("issue") or ""
    )
    rows = prd_index_rows(text)
    if spec_id and not any(row.get("specid") == spec_id for row in rows):
        errors.append(f"docs/prd-index.md 没有登记 Spec {spec_id}")
    if work_item and not any(row.get("工作项id") == work_item for row in rows):
        errors.append(f"docs/prd-index.md 没有登记工作项 {work_item}")
    return errors


def check_prd_index(
    root: Path,
    config: dict[str, Any],
    state: dict[str, Any],
    spec_text: str,
    require_feat: bool = False,
) -> list[str]:
    errors: list[str] = []
    errors.extend(prd_index_structure_errors(root, config, state, spec_text))
    errors.extend(prd_index_clarify_errors(root, config, state, spec_text))
    errors.extend(prd_index_registration_errors(root, config, state, spec_text))
    if require_feat:
        errors.extend(feat_identity_errors(root, config, state, spec_text))
    return errors


def feat_metadata(spec_text: str) -> str:
    return metadata_value(spec_text, "FEAT ID", "FEATID", "FEAT")


def is_legacy_feat_spec(state: dict[str, Any], spec_text: str) -> bool:
    return state.get("state") == "MERGED" and not feat_metadata(spec_text)


def feat_identity_errors(
    root: Path,
    config: dict[str, Any],
    state: dict[str, Any],
    spec_text: str,
) -> list[str]:
    if not config.get("require_prd_index"):
        return []
    if is_legacy_feat_spec(state, spec_text):
        return []
    errors: list[str] = []
    declared = feat_metadata(spec_text)
    if not re.fullmatch(r"FEAT-\d{3}", declared or ""):
        errors.append("spec.md 元数据缺少有效 FEAT ID（格式 FEAT-xxx）")
    spec_id = str(state.get("spec_id", ""))
    rows = prd_index_rows(read_text(prd_index_path(root, config)))
    spec_rows = [row for row in rows if row.get("specid") == spec_id]
    if spec_id and not spec_rows:
        errors.append(f"docs/prd-index.md 没有登记 Spec {spec_id} 的 FEAT 行")
    row_feats = {
        row.get("feat", "")
        for row in spec_rows
        if re.fullmatch(r"FEAT-\d{3}", row.get("feat", "") or "")
    }
    if len(spec_rows) > 1:
        errors.append(
            f"docs/prd-index.md 重复登记 Spec {spec_id}，共 {len(spec_rows)} 行"
        )
    row_counts: dict[tuple[str, str], int] = {}
    for row in spec_rows:
        row_feat = row.get("feat", "")
        row_work = row.get("工作项id", "") or row.get("workitemid", "")
        if re.fullmatch(r"FEAT-\d{3}", row_feat or ""):
            key = (row_work, row_feat)
            row_counts[key] = row_counts.get(key, 0) + 1
    for (row_work, row_feat), count in sorted(row_counts.items()):
        if count > 1:
            errors.append(
                f"FEAT {row_feat} 重复登记：工作项 {row_work or '(空)'} "
                f"在 {spec_id} 下出现 {count} 行"
            )
    if declared and row_feats and declared not in row_feats:
        errors.append(
            f"spec.md FEAT ID={declared} 与 docs/prd-index.md 的 "
            f"{', '.join(sorted(row_feats))} 不一致"
        )
    feat_to_specs: dict[str, set[str]] = {}
    for row in rows:
        row_feat = row.get("feat", "")
        row_spec = row.get("specid", "")
        if re.fullmatch(r"FEAT-\d{3}", row_feat or "") and row_spec:
            feat_to_specs.setdefault(row_feat, set()).add(row_spec)
    for row_feat, specs in sorted(feat_to_specs.items()):
        if len(specs) > 1:
            errors.append(
                f"FEAT {row_feat} 被多个 Spec 使用：" + ", ".join(sorted(specs))
            )
    return errors


def feat_coverage_errors(
    root: Path,
    config: dict[str, Any],
    state: dict[str, Any],
    spec_text: str,
) -> list[str]:
    if not config.get("require_prd_index"):
        return []
    if is_legacy_feat_spec(state, spec_text):
        return []
    errors: list[str] = []
    declared = feat_metadata(spec_text)
    spec_id = str(state.get("spec_id", ""))
    work_item = str(state.get("work_item") or "")
    rows = [
        row
        for row in parse_feat_map(read_text(prd_index_path(root, config)))
        if row.get("spec") == spec_id
    ]
    if not rows:
        errors.append(
            "docs/prd-index.md 缺少当前 Spec 的 FEAT 映射表行；"
            "请在 ## FEAT 映射 下登记 FR/AC"
        )
        return errors
    mapped_frs: set[str] = set()
    mapped_acs: set[str] = set()
    for row in rows:
        if declared and row.get("feat") and row.get("feat") != declared:
            errors.append(
                f"FEAT 映射行的 FEAT={row.get('feat')} 与 spec.md 的 {declared} 不一致"
            )
        if work_item and row.get("work_item") and row.get("work_item") != work_item:
            errors.append(
                f"FEAT 映射行的工作项={row.get('work_item')} 与 state.work_item={work_item} 不一致"
            )
        mapped_frs.update(extract_frs(row.get("fr", "")))
        mapped_acs.update(extract_acs(row.get("acs", "")))
    spec_frs = set(extract_frs(spec_text))
    spec_acs = set(extract_acs(spec_text))
    orphan_frs = sorted(spec_frs - mapped_frs)
    orphan_acs = sorted(spec_acs - mapped_acs)
    if orphan_frs:
        errors.append("FEAT 映射缺少 FR：" + ", ".join(orphan_frs))
    if orphan_acs:
        errors.append("FEAT 映射缺少 AC：" + ", ".join(orphan_acs))
    unknown_frs = sorted(mapped_frs - spec_frs)
    unknown_acs = sorted(mapped_acs - spec_acs)
    if unknown_frs:
        errors.append("FEAT 映射包含 Spec 中不存在的 FR：" + ", ".join(unknown_frs))
    if unknown_acs:
        errors.append("FEAT 映射包含 Spec 中不存在的 AC：" + ", ".join(unknown_acs))
    return errors


def check_feat_trace(
    root: Path,
    config: dict[str, Any],
    state: dict[str, Any],
    spec_text: str,
) -> list[str]:
    errors: list[str] = []
    errors.extend(feat_identity_errors(root, config, state, spec_text))
    errors.extend(feat_coverage_errors(root, config, state, spec_text))
    return errors


def render_feat_map(rows: list[dict[str, str]]) -> str:
    lines = [
        "## FEAT 映射",
        "",
        "| FEAT | 工作项 ID | Spec ID | FR | AC |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        cells = [
            str(row.get("feat") or ""),
            str(row.get("work_item") or ""),
            str(row.get("spec") or ""),
            str(row.get("fr") or ""),
            str(row.get("acs") or ""),
        ]
        safe = [" ".join(cell.split()).replace("|", "\\|") for cell in cells]
        lines.append("| " + " | ".join(safe) + " |")
    return "\n".join(lines)


def sync_feat_map(
    root: Path,
    config: dict[str, Any],
    state: dict[str, Any],
    spec_text: str,
) -> str:
    if not config.get("require_prd_index"):
        return "prd-index disabled"
    if is_legacy_feat_spec(state, spec_text):
        return "legacy spec: FEAT mapping skipped"
    feat = feat_metadata(spec_text)
    if not re.fullmatch(r"FEAT-\d{3}", feat or ""):
        return "skipped: spec.md missing valid FEAT ID"
    spec_id = str(state.get("spec_id", ""))
    work_item = metadata_value(spec_text, "工作项 ID", "工作项ID") or str(
        state.get("work_item") or ""
    )
    frs = sorted(set(extract_frs(spec_text)))
    acs = sorted(set(extract_acs(spec_text)))
    new_rows: list[dict[str, str]] = []
    for fr in frs:
        suffix = fr[3:]
        fr_acs = [ac for ac in acs if ac.startswith(f"AC-{suffix}-")]
        new_rows.append(
            {
                "feat": feat,
                "work_item": work_item,
                "spec": spec_id,
                "fr": fr,
                "acs": ", ".join(fr_acs),
            }
        )
    path = prd_index_path(root, config)
    text = read_text(path)
    existing = parse_feat_map(text)
    kept = [row for row in existing if row.get("spec") != spec_id]
    section = render_feat_map(kept + new_rows)
    marker = re.search(r"(?im)^##\s*(FEAT\s*映射|FEAT\s*Mapping)\s*$", text)
    if marker:
        tail = text[marker.end():]
        next_heading = re.search(r"(?m)^##\s+", tail)
        end = marker.end() + (next_heading.start() if next_heading else len(tail))
        new_text = text[: marker.start()] + section + "\n"
        if end < len(text):
            new_text += "\n" + text[end:].lstrip("\n")
    else:
        new_text = text.rstrip() + "\n\n" + section + "\n"
    write_text(path, new_text)
    return f"feat={feat}; rows={len(new_rows)}"


def validate_check_registry(
    registry: Optional[tuple[dict[str, Any], ...]] = None,
) -> list[str]:
    if registry is None:
        registry = CHECK_REGISTRY_ALL
    errors: list[str] = []
    seen: set[str] = set()
    for item in registry:
        if not isinstance(item, dict):
            errors.append("检查项必须是对象")
            continue
        missing = [field for field in CHECK_REQUIRED_FIELDS if field not in item]
        if missing:
            errors.append(
                f"{item.get('id') or '(unknown)'} 缺少字段：" + ", ".join(missing)
            )
        check_id = str(item.get("id") or "")
        if not check_id:
            errors.append("检查项缺少非空 ID")
        elif check_id in seen:
            errors.append(f"检查 ID 重复：{check_id}")
        elif not re.fullmatch(r"G[0-5]-\d{2}", check_id):
            errors.append(f"{check_id} 的 ID 必须符合 G[0-5]-NN")
        seen.add(check_id)
        if str(item.get("gate") or "") not in GATE_STAGES:
            errors.append(f"{check_id or '(unknown)'} 的 Gate 非法：{item.get('gate')}")
        elif check_id and not check_id.startswith(
            f"{item.get('gate')}-"
        ):
            errors.append(
                f"{check_id} 的 ID 前缀必须与 Gate {item.get('gate')} 一致"
            )
        if str(item.get("level") or "") not in CHECK_LEVELS:
            errors.append(
                f"{check_id or '(unknown)'} 的级别必须是 required 或 advisory"
            )
        if str(item.get("trigger") or "") not in CHECK_TRIGGERS:
            errors.append(
                f"{check_id or '(unknown)'} 的 trigger 必须是 "
                + ", ".join(sorted(CHECK_TRIGGERS))
            )
        for field in ("waivable", "redline"):
            if not isinstance(item.get(field), bool):
                errors.append(
                    f"{check_id or '(unknown)'} 的 {field} 必须是布尔值"
                )
        if item.get("waivable") is True and item.get("redline") is True:
            errors.append(
                f"{check_id or '(unknown)'} 不能同时 waivable=true 和 redline=true"
            )
    return errors


def gate_context(
    root: Path,
    config: dict[str, Any],
    directory: Path,
    state: dict[str, Any],
) -> dict[str, Any]:
    spec_id = str(state.get("spec_id", directory.name))
    spec_text = read_text(directory / "spec.md")
    _, spec_acs = check_spec(spec_text, spec_id)
    return {
        "root": root,
        "config": config,
        "directory": directory,
        "state": state,
        "spec_id": spec_id,
        "spec_text": spec_text,
        "spec_acs": spec_acs,
    }


def gate_g0_work_item(ctx: dict[str, Any]) -> tuple[list[str], str]:
    state = ctx["state"]
    spec_text = ctx["spec_text"]
    errors: list[str] = []
    declared = metadata_value(spec_text, "工作项 ID", "工作项ID", "Work Item ID")
    state_item = str(state.get("work_item") or "")
    if is_placeholder_value(declared):
        errors.append("spec.md 缺少有效的工作项 ID")
    elif declared.startswith("%"):
        errors.append("spec.md 的工作项 ID 不能带前导 %")
    if state_item and declared and declared != state_item:
        errors.append(
            f"spec.md 工作项 ID={declared} 与 state.work_item={state_item} 不一致"
        )
    work_item = declared or state_item
    rows = prd_index_rows(read_text(prd_index_path(ctx["root"], ctx["config"])))
    if work_item and not any(row.get("工作项id") == work_item for row in rows):
        errors.append(f"docs/prd-index.md 没有登记工作项 {work_item}")
    return errors, f"work_item={work_item or '(empty)'}"


def gate_g0_structure(ctx: dict[str, Any]) -> tuple[list[str], str]:
    errors = prd_index_structure_errors(
        ctx["root"], ctx["config"], ctx["state"], ctx["spec_text"]
    )
    return errors, "source/updated/table parsed"


def gate_g0_clarify(ctx: dict[str, Any]) -> tuple[list[str], str]:
    errors = prd_index_clarify_errors(
        ctx["root"], ctx["config"], ctx["state"], ctx["spec_text"]
    )
    if CLARIFY_RE.search(ctx["spec_text"]):
        errors.append("spec.md 还有 [NEEDS CLARIFICATION] 标记")
    return errors, "clarification markers = 0"


def gate_g0_feat_identity(ctx: dict[str, Any]) -> tuple[list[str], str]:
    errors = feat_identity_errors(
        ctx["root"], ctx["config"], ctx["state"], ctx["spec_text"]
    )
    declared = feat_metadata(ctx["spec_text"])
    return errors, f"feat={declared or '(missing)'}"


def gate_g0_feat_coverage(ctx: dict[str, Any]) -> tuple[list[str], str]:
    errors = feat_coverage_errors(
        ctx["root"], ctx["config"], ctx["state"], ctx["spec_text"]
    )
    return errors, f"{len(ctx['spec_acs'])} AC mapped"


def gate_g0_feat_legacy(ctx: dict[str, Any]) -> tuple[list[str], str]:
    if is_legacy_feat_spec(ctx["state"], ctx["spec_text"]):
        return [], "legacy spec: FEAT mapping not enforced"
    return [], "strict FEAT mapping"


def gate_g0_scope(ctx: dict[str, Any]) -> tuple[list[str], str]:
    errors = spec_scope_errors(ctx["spec_text"])
    return errors, "In-Scope / Out-of-Scope"


def gate_g1_sections(ctx: dict[str, Any]) -> tuple[list[str], str]:
    errors = spec_section_errors(ctx["spec_text"])
    return errors, f"{len(SPEC_SECTIONS)} core sections"


def gate_g1_fr_ac(ctx: dict[str, Any]) -> tuple[list[str], str]:
    errors = spec_fr_ac_errors(ctx["spec_text"])
    return errors, f"{len(extract_frs(ctx['spec_text']))} FR / {len(ctx['spec_acs'])} AC"


def gate_g1_testability(ctx: dict[str, Any]) -> tuple[list[str], str]:
    errors = spec_ac_testability_errors(ctx["spec_text"])
    return errors, f"{len(ctx['spec_acs'])} AC checked"


def gate_g1_placeholders(ctx: dict[str, Any]) -> tuple[list[str], str]:
    errors = placeholder_errors("spec.md", ctx["spec_text"])
    return errors, "TODO/placeholder/clarification = 0"


GATE_CHECK_FUNCS = {
    "G0-01": gate_g0_work_item,
    "G0-02": gate_g0_structure,
    "G0-03": gate_g0_clarify,
    "G0-04": gate_g0_feat_identity,
    "G0-05": gate_g0_feat_coverage,
    "G0-06": gate_g0_scope,
    "G0-07": gate_g0_feat_legacy,
    "G1-01": gate_g1_sections,
    "G1-02": gate_g1_fr_ac,
    "G1-03": gate_g1_testability,
    "G1-04": gate_g1_placeholders,
}


def run_gate_checks(
    gate: str,
    ctx: dict[str, Any],
    workflow: Optional[dict[str, Any]] = None,
) -> list[dict[str, Any]]:
    registry_errors = validate_check_registry()
    if registry_errors:
        raise SddError("检查项注册表无效：" + "；".join(registry_errors))
    selected: Optional[set[str]] = None
    if isinstance(workflow, dict):
        gate_checks = workflow.get("gate_checks")
        if (
            isinstance(gate_checks, dict)
            and isinstance(gate_checks.get(gate), list)
        ):
            selected = {str(item) for item in gate_checks[gate]}
    rows: list[dict[str, Any]] = []
    for item in CHECK_REGISTRY:
        if str(item.get("gate")) != gate:
            continue
        if selected is not None and str(item["id"]) not in selected:
            continue
        func = GATE_CHECK_FUNCS.get(str(item["id"]))
        if func is None:
            item_errors = [f"检查项 {item['id']} 没有实现"]
            detail = "missing check function"
        else:
            item_errors, detail = func(ctx)
        rows.append(
            {
                "id": item["id"],
                "name": item["name"],
                "level": item["level"],
                "trigger": item["trigger"],
                "waivable": item["waivable"],
                "redline": bool(
                    item.get("redline")
                    or item["id"] in SECURITY_CHECK_IDS
                ),
                "owner": item["owner"],
                "result": classify_check_result(item, item_errors),
                "detail": detail,
                "errors": item_errors,
                "waiver": "",
            }
        )
    return rows


def classify_check_result(
    item: dict[str, Any],
    errors: list[str],
    waiver: Optional[dict[str, Any]] = None,
) -> str:
    if not errors:
        return "pass"
    if item.get("redline") or str(item.get("id") or "") in SECURITY_CHECK_IDS:
        return "block"
    if str(item.get("level") or "") == "advisory":
        return "warn"
    if waiver is not None:
        return "waived"
    return "block"


def gate_rows_errors(rows: list[dict[str, Any]]) -> list[str]:
    return [
        error
        for row in rows
        if str(row.get("result") or "").lower() == "block"
        for error in row.get("errors", [])
    ]


def gate_rows_warnings(rows: list[dict[str, Any]]) -> list[str]:
    return [
        error
        for row in rows
        if str(row.get("result") or "").lower() in {"warn", "waived"}
        for error in row.get("errors", [])
    ]


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


def required_gates(
    state_name: str,
    workflow: Optional[dict[str, Any]] = None,
) -> list[str]:
    if workflow:
        required = workflow.get("required_gates")
        if isinstance(required, dict):
            value = required.get(state_name)
            if isinstance(value, list):
                return [str(gate) for gate in value]
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


GATE_REPORT_RESULT_ALIASES = {
    "PASS": "pass",
    "OK": "pass",
    "WARN": "warn",
    "WARNING": "warn",
    "WAIVED": "waived",
    "BLOCK": "block",
    "FAIL": "block",
    "FAILED": "block",
}


def parse_gate_report_checks(
    report: str,
    gate: str = "",
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    in_section = False
    for line in report.splitlines():
        if re.match(r"^##\s*2\.\s*检查项", line):
            in_section = True
            continue
        if in_section and re.match(r"^##\s+", line):
            break
        if not in_section or not line.strip().startswith("|"):
            continue
        cells = split_table_row(line)
        if len(cells) < 4:
            continue
        check_id = cells[0].strip().strip("`")
        if not re.fullmatch(r"G[0-5]-\d{2}", check_id):
            continue
        raw_result = cells[3].strip().strip("`").upper()
        result = GATE_REPORT_RESULT_ALIASES.get(raw_result)
        if result is None:
            continue
        waiver = cells[5].strip() if len(cells) > 5 else ""
        if waiver in {"—", "-", "N/A", "n/a"}:
            waiver = ""
        if result == "warn" and waiver:
            result = "waived"
        rows.append(
            {
                "gate": gate,
                "check_id": check_id,
                "name": cells[1].strip(),
                "level": cells[2].strip().lower() or "required",
                "result": result,
                "detail": cells[4].strip() if len(cells) > 4 else "",
                "waiver": waiver,
            }
        )
    return rows


def collect_gate_check_rows(
    root: Path,
    config: dict[str, Any],
    spec_id: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for gate in GATE_STAGES:
        path = gate_report_path(root, config, spec_id, gate)
        if not path.is_file():
            continue
        report_path = path.relative_to(root).as_posix()
        for row in parse_gate_report_checks(read_text(path), gate):
            row["spec"] = spec_id
            row["report"] = report_path
            rows.append(row)
    return rows


def summarize_gate_checks(
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    checks: dict[str, dict[str, Any]] = {}
    for row in rows:
        check_id = str(row.get("check_id") or "")
        result = str(row.get("result") or "")
        if not check_id or result not in {"pass", "warn", "block", "waived"}:
            continue
        item = checks.setdefault(
            check_id,
            {
                "check_id": check_id,
                "gate": str(row.get("gate") or ""),
                "name": str(row.get("name") or ""),
                "level": str(row.get("level") or "required"),
                "pass": 0,
                "warn": 0,
                "block": 0,
                "waived": 0,
                "total": 0,
            },
        )
        item[result] += 1
        item["total"] += 1
    for item in checks.values():
        total = int(item["total"])
        for result, rate_name in (
            ("pass", "pass_rate"),
            ("warn", "warn_rate"),
            ("block", "block_rate"),
            ("waived", "waiver_rate"),
        ):
            item[rate_name] = (
                round(int(item[result]) / total, 4) if total else 0.0
            )
    return [checks[key] for key in sorted(checks)]


def gate_warning_items(
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {
            "spec": row["spec"],
            "gate": row["gate"],
            "check_id": row["check_id"],
            "level": row["level"],
            "result": str(row["result"]).upper(),
            "detail": row["detail"],
            "waiver": row["waiver"],
            "report": row["report"],
        }
        for row in rows
        if row["result"] in {"warn", "waived"}
    ]


def parse_artifact_hashes(report: str) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    in_section = False
    for line in report.splitlines():
        if re.match(r"^##\s*4\.\s*产物", line):
            in_section = True
            continue
        if in_section and re.match(r"^##\s+", line):
            break
        if not in_section or not line.strip().startswith("|"):
            continue
        cells = split_table_row(line)
        if len(cells) < 2:
            continue
        first = cells[0].strip().strip("`")
        if not first or first.lower() in {"产物", "artifact"}:
            continue
        if set(first) <= {"-", ":", " "}:
            continue
        digest = cells[1].strip().strip("`")
        if digest.upper() == "MISSING":
            continue
        rows.append((first, digest))
    return rows


def check_gates(
    root: Path, config: dict[str, Any], directory: Path, state_name: str
) -> list[str]:
    errors: list[str] = []
    state = load_json(directory / "state.json")
    workflow = resolve_workflow(root, directory, state)
    spec_id = str(state.get("spec_id", directory.name))
    for gate in required_gates(state_name, workflow):
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
            continue
        hashes = parse_artifact_hashes(report)
        if not hashes:
            if config.get("require_artifact_hash"):
                errors.append(
                    f"{path.relative_to(root).as_posix()} 缺少产物哈希；"
                    f"请重新记录 {gate}"
                )
            continue
        expected_paths = set()
        for name in GATE_ARTIFACTS.get(gate, ()):
            is_plan = name.endswith("#plan")
            artifact_name = name[: -len("#plan")] if is_plan else name
            relative = (directory / artifact_name).relative_to(root).as_posix()
            expected_paths.add(relative + ("#plan" if is_plan else ""))
        reported_paths = {relative for relative, _ in hashes}
        for missing in sorted(expected_paths - reported_paths):
            errors.append(
                f"{path.relative_to(root).as_posix()} 缺少产物哈希：{missing}"
            )
        for relative, expected in hashes:
            is_plan = relative.endswith("#plan")
            artifact_path = root / (relative[: -len("#plan")] if is_plan else relative)
            if not artifact_path.is_file():
                errors.append(f"Gate 产物不存在：{relative}")
                continue
            if is_plan:
                matches = task_plan_hash(read_text(artifact_path)) == expected
            else:
                matches = artifact_hash_matches(artifact_path, expected)
            if not matches:
                errors.append(
                    f"{gate} 绑定的 {relative} 已被修改；"
                    "请重新执行对应 Gate 或 rewind"
                )
    errors.extend(approval_digest_errors(root, directory, state))
    errors.extend(change_set_errors(root, directory, state))
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


def normalize_check_rows(
    gate: str, checks: list[Any]
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for index, item in enumerate(checks, 1):
        if isinstance(item, dict):
            rows.append(
                {
                    "id": str(item.get("id") or f"{gate}-{index:02d}"),
                    "name": str(item.get("name") or "检查项"),
                    "level": str(item.get("level") or "required"),
                    "result": str(item.get("result") or "pass").upper(),
                    "detail": str(item.get("detail") or ""),
                }
            )
            continue
        name, result, detail = item
        rows.append(
            {
                "id": f"{gate}-{index:02d}",
                "name": str(name),
                "level": "required",
                "result": str(result).upper(),
                "detail": str(detail),
            }
        )
    return rows


def write_gate_report(
    root: Path,
    config: dict[str, Any],
    directory: Path,
    state: dict[str, Any],
    gate: str,
    state_name: str,
    mode: str,
    evidence: str,
    checks: list[Any],
    errors: Optional[list[str]] = None,
    approver: Optional[str] = None,
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

    check_rows = normalize_check_rows(gate, checks)
    warning_rows = [
        row for row in check_rows if row["result"] == "WARN"
    ]
    approval_digest = ""
    if gate in {"G0", "G1"}:
        approval_digest = (
            str(state.get("approved_spec_digest") or "").strip()
            or current_spec_digest(directory)
            or "MISSING"
        )
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
        f"| 告警数 | {len(warning_rows)} |",
        *(
            [f"| 审批 Spec 摘要 | `{approval_digest}` |"]
            if gate in {"G0", "G1"}
            else []
        ),
        "",
        "## 2. 检查项",
        "",
        "| 检查 ID | 检查项 | 级别 | 结果 | 证据 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in check_rows:
        safe_name = " ".join(row["name"].split()).replace("|", "\\|")
        safe_detail = " ".join(row["detail"].split()).replace("|", "\\|")
        lines.append(
            f"| {row['id']} | {safe_name} | {row['level']} | "
            f"{row['result']} | {safe_detail} |"
        )
    if not check_rows:
        lines.append(
            f"| {gate}-00 | 无自动检查项 | required | PASS | 由人工评审 |"
        )

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
            "| 产物 | SHA-256 | 字节 |",
            "| --- | --- | --- |",
        ]
    )
    for name in GATE_ARTIFACTS.get(gate, ()):
        relative, digest, size = artifact_digest(root, directory, name)
        if digest == "MISSING":
            lines.append(f"| `{relative}` | MISSING | 0 |")
        else:
            lines.append(f"| `{relative}` | `{digest}` | {size} |")

    lines.extend(
        [
            "",
            "## 5. 证据与人工确认",
            "",
            f"- 执行证据：{evidence.strip() or 'N/A'}",
            f"- 执行模式：{mode}",
            f"- 人工确认：{'已确认' if mode == 'manual' else '无需额外人工确认'}",
            f"- 确认人：{approver or 'N/A'}",
            "",
            "## 6. 问题与建议",
            "",
        ]
    )
    blocking_messages = list(errors or [])
    warning_messages = [
        f"{row['id']}：{row['detail'] or '检查失败'}"
        for row in warning_rows
    ]
    if blocking_messages or warning_messages:
        lines.extend(["| 级别 | 问题 |", "| --- | --- |"])
        lines.extend(f"| BLOCK | {error} |" for error in blocking_messages)
        lines.extend(f"| WARN | {message} |" for message in warning_messages)
    else:
        lines.extend(
            [
                "| 级别 | 问题 |",
                "| --- | --- |",
                "| PASS | 无阻断问题。 |",
            ]
        )
    lines.append("")
    write_text(report_path, "\n".join(lines))
    return report_path


def selected_checks(
    workflow: Optional[dict[str, Any]],
    gate: str,
) -> list[str]:
    mapping = (workflow or {}).get("gate_checks")
    if isinstance(mapping, dict):
        selected = mapping.get(gate)
        if isinstance(selected, list):
            known = set(check_ids_for_gate(gate))
            values = [str(item) for item in selected if str(item) in known]
            if values:
                return list(dict.fromkeys(values))
    return check_ids_for_gate(gate)


def gate_check_results(
    gate: str,
    errors: list[str],
    workflow: Optional[dict[str, Any]] = None,
    state: Optional[dict[str, Any]] = None,
    spec_id: Optional[str] = None,
    contexts: Optional[Iterable[str]] = None,
) -> list[dict[str, Any]]:
    results = build_check_results(
        gate,
        errors,
        selected_checks(workflow, gate),
    )
    if state is not None:
        results = apply_check_waivers(
            results,
            state,
            spec_id or str(state.get("spec_id") or ""),
            contexts or [],
        )
    return results


def gate_check_rows(
    gate: str,
    errors: list[str],
    workflow: Optional[dict[str, Any]] = None,
    state: Optional[dict[str, Any]] = None,
    spec_id: Optional[str] = None,
    contexts: Optional[Iterable[str]] = None,
) -> list[tuple[str, str, str]]:
    results = gate_check_results(
        gate,
        errors,
        workflow,
        state,
        spec_id,
        contexts,
    )
    return [
        (
            f"{item['id']} {item['title']}",
            str(item["result"]).upper(),
            str(item["detail"]),
        )
        for item in results
    ]


def stage_check_results(
    stage: str,
    errors: list[str],
    workflow: Optional[dict[str, Any]] = None,
) -> list[dict[str, Any]]:
    gate_map = {
        "spec": ("G0", "G1"),
        "design": ("G2",),
        "tasks": ("G3",),
        "verify": ("G5",),
        "ci": ("G0", "G1", "G2", "G3", "G4", "G5"),
    }
    base_gates = list(gate_map.get(stage, ()))
    explicit: dict[str, list[str]] = {}
    for error in errors:
        match = re.match(r"^\s*(G\d-\d{2})\b", str(error))
        if not match:
            continue
        check_id = match.group(1)
        definition = EXT_CHECK_REGISTRY.get(check_id)
        if definition is None:
            continue
        gate = str(definition["gate"])
        explicit.setdefault(gate, [])
        if check_id not in explicit[gate]:
            explicit[gate].append(check_id)

    results: list[dict[str, Any]] = []
    for gate in base_gates:
        selected = selected_checks(workflow, gate)
        for check_id in explicit.get(gate, []):
            if check_id not in selected:
                selected.append(check_id)
        results.extend(
            build_check_results(
                gate,
                errors,
                selected,
            )
        )
    for gate, check_ids in explicit.items():
        if gate in base_gates:
            continue
        results.extend(build_check_results(gate, errors, check_ids))
    return results


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
    approver: Optional[str] = None,
) -> None:
    workflow = resolve_workflow(root, directory, state)
    spec_id = str(state.get("spec_id") or directory.name)
    contexts = waiver_contexts(
        directory,
        {
            "G0": "spec",
            "G1": "spec",
            "G2": "design",
            "G3": "tasks",
            "G4": "tasks",
            "G5": "verify",
        }.get(gate, "ci"),
    )
    blocking, waived = partition_waived_errors(
        errors or [],
        gate,
        state,
        spec_id,
        contexts,
    )
    if blocking:
        status = "FAILED"
    elif waived:
        status = "PASS_WITH_WAIVER"
    else:
        status = "PASS"
    append_gate(directory, gate, state_name, mode, evidence, status)
    check_results = gate_check_results(
        gate,
        errors or [],
        workflow,
        state,
        spec_id,
        contexts,
    )
    if not checks:
        checks = [
            (
                f"{item['id']} {item['title']}",
                str(item["result"]).upper(),
                str(item["detail"]),
            )
            for item in check_results
        ]
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
        blocking,
        approver,
    )
    hashes: dict[str, str] = {}
    for name in GATE_ARTIFACTS.get(gate, ()):
        relative, digest, _ = artifact_digest(root, directory, name)
        if digest != "MISSING":
            hashes[relative] = digest
    if hashes:
        state.setdefault("artifact_hashes", {})[gate] = hashes
    append_audit_event(
        directory,
        {
            "event": "gate_result",
            "gate": gate,
            "state": state_name,
            "from_state": state.get("state"),
            "to_state": state_name,
            "next": NEXT_ACTION_BY_STATE.get(state_name, ""),
            "mode": mode,
            "status": status,
            "evidence": evidence,
            "checks": check_results,
            "artifacts": gate_artifact_entries(root, directory, gate),
            "actor": "system",
            "role": "system",
        },
    )


def gate_artifact_entries(
    root: Path, directory: Path, gate: str
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for name in GATE_ARTIFACTS.get(gate, ()):
        relative, digest, size = artifact_digest(root, directory, name)
        if digest == "MISSING":
            continue
        entries.append({"path": relative, "sha256": digest, "bytes": size})
    return entries


def record_gate_approval(
    root: Path,
    directory: Path,
    state: dict[str, Any],
    gate: str,
    approver: str,
    evidence: str,
) -> None:
    state.setdefault("approvals", []).append(
        {
            "action": "manual_gate",
            "gate": gate,
            "approver": approver,
            "at": now(),
            "evidence": evidence,
            "artifacts": gate_artifact_entries(root, directory, gate),
        }
    )
    state["last_approver"] = approver


def gate_requires_human(
    config: dict[str, Any],
    gate: str,
    state: dict[str, Any],
    workflow: Optional[dict[str, Any]] = None,
) -> bool:
    policy = (
        workflow_gate_policy(config, workflow, gate)
        if workflow
        else str(config.get("gates", {}).get(gate, "auto"))
    )
    if policy == "human":
        return True
    risk_labels = set(str(item) for item in state.get("risk_labels", []))
    stop_labels = set(effective_risk_stop(config, workflow))
    is_risky = state.get("risk") == "high" or bool(risk_labels & stop_labels)
    return policy == "auto_if_no_risk" and is_risky


def gate_mode(
    config: dict[str, Any],
    gate: str,
    state: dict[str, Any],
    human: bool,
    workflow: Optional[dict[str, Any]] = None,
) -> str:
    if human:
        return "manual"
    if gate_requires_human(config, gate, state, workflow):
        raise SddError(
            f"{gate} 需要人工审批；重跑时加 --human"
        )
    return "auto"


CODE_COMMIT_TYPES = {"feat", "fix", "perf", "hotfix"}


def git_read(root: Path, args: list[str]) -> tuple[int, str, str]:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def resolve_merge_base(root: Path) -> tuple[str, str]:
    for ref in ("origin/main", "main", "master"):
        code, output, _ = git_read(root, ["merge-base", "HEAD", ref])
        if code == 0 and output:
            return output.splitlines()[0].strip(), ref
    return "", ""


def git_commits_since(root: Path, base: str) -> list[str]:
    code, output, _ = git_read(root, ["rev-list", f"{base}..HEAD"])
    if code != 0:
        return []
    return [line.strip() for line in output.splitlines() if line.strip()]


def commit_parents(root: Path, sha: str) -> list[str]:
    code, output, _ = git_read(
        root, ["rev-list", "--parents", "-n", "1", sha]
    )
    if code != 0 or not output:
        return []
    return output.split()[1:]


def commit_body(root: Path, sha: str) -> str:
    code, output, _ = git_read(root, ["show", "-s", "--format=%B", sha])
    return output if code == 0 else ""


def parse_commit_trailers(text: str) -> dict[str, Any]:
    spec_ids = re.findall(
        r"(?im)^Spec-Id:\s*(SPEC-[A-Z][A-Z0-9]*-[0-9]{3})\s*$", text
    )
    task_ids = re.findall(r"(?im)^Task-Id:\s*(T-[A-Za-z0-9_-]+)\s*$", text)
    lines = text.splitlines()
    header = lines[0] if lines else ""
    match = COMMIT_HEADER_RE.match(header)
    return {
        "spec_ids": spec_ids,
        "task_ids": task_ids,
        "header": match,
        "work_item": match.group("work") if match else "",
        "type": match.group("type") if match else "",
        "subject": header,
    }


def audit_commit(
    root: Path,
    config: dict[str, Any],
    sha: str,
) -> tuple[list[str], Optional[dict[str, Any]]]:
    parents = commit_parents(root, sha)
    if len(parents) >= 2:
        return [], None
    text = commit_body(root, sha)
    if not text:
        return [f"{sha[:7]} 无法读取 commit message"], None
    parsed = parse_commit_trailers(text)
    short = sha[:7]
    errors: list[str] = []
    header = parsed["header"]
    if header is None:
        errors.append(
            f"{short} 首行必须匹配 %<工作项ID> <type>(<scope>): <描述>"
        )
    spec_ids = parsed["spec_ids"]
    task_ids = parsed["task_ids"]
    if len(spec_ids) != 1:
        errors.append(f"{short} 必须包含且只包含一个合法 Spec-Id Trailer")
    commit_type = str(parsed["type"])
    if commit_type in CODE_COMMIT_TYPES and len(task_ids) != 1:
        errors.append(
            f"{short} 代码 Commit 必须包含且只包含一个 Task-Id"
        )
    if commit_type == "docs" and task_ids:
        errors.append(f"{short} 文档 Commit 不得包含 Task-Id")
    if len(task_ids) > 1:
        errors.append(f"{short} 只能包含一个 Task-Id")
    spec_id = spec_ids[0] if len(spec_ids) == 1 else ""
    task_id = task_ids[0] if len(task_ids) == 1 else ""
    if spec_id:
        directory = spec_dir_for(root, config, spec_id)
        spec_text = read_text(directory / "spec.md")
        if not spec_text:
            errors.append(f"{short} Spec-Id 对应的 spec.md 不存在：{spec_id}")
        else:
            declared = metadata_value(spec_text, "Spec ID", "SpecID")
            if declared != spec_id:
                errors.append(f"{short} Spec 目录与元数据中的 Spec ID 不一致")
            work_item = metadata_value(spec_text, "工作项 ID", "工作项ID")
            if parsed["work_item"] and work_item != parsed["work_item"]:
                errors.append(
                    f"{short} Commit 工作项 {parsed['work_item']} "
                    f"与 Spec 元数据 {work_item} 不一致"
                )
        if task_id:
            tasks_text = read_text(directory / "tasks.md")
            if task_id not in tasks_text:
                errors.append(
                    f"{short} Task-Id 在 tasks.md 中不存在：{task_id}"
                )
    record = {
        "sha": sha,
        "short": short,
        "subject": parsed["subject"],
        "type": commit_type,
        "spec_id": spec_id,
        "task_id": task_id,
        "work_item": parsed["work_item"],
    }
    return errors, record


def check_git(root: Path, spec_id: str, state: str = "DRAFT") -> list[str]:
    if not (root / ".git").exists():
        return ["--check-git 需要 Git 仓库"]
    if state == "MERGED":
        return []
    base, _ = resolve_merge_base(root)
    if not base:
        return [
            "无法确定 merge-base；需要 origin/main、main 或 master 之一"
        ]
    try:
        config = load_config(root)
    except SddError:
        config = {
            "spec_root": "docs/specs",
            "prd_index": "docs/prd-index.md",
            "prd_mode": "workitem",
        }
    shas = git_commits_since(root, base)
    if not shas:
        _, recent, _ = git_read(root, ["log", "-20", "--pretty=%B"])
        if f"Spec-Id: {spec_id}" in recent:
            return []
        return [
            f"merge-base {base[:7]} 之后没有 `Spec-Id: {spec_id}` 的 commit"
        ]
    errors: list[str] = []
    seen_spec = False
    for sha in shas:
        commit_errors, record = audit_commit(root, config, sha)
        errors.extend(commit_errors)
        if record and record["spec_id"] == spec_id:
            seen_spec = True
    if not seen_spec:
        errors.append(
            f"merge-base {base[:7]} 之后没有 `Spec-Id: {spec_id}` 的 commit"
        )
    return list(dict.fromkeys(errors))


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
    workflow = resolve_workflow(root, directory, state)
    ctx = gate_context(root, config, directory, state)
    spec_acs = ctx["spec_acs"]
    legacy_merged = is_legacy_merged(state)
    errors: list[str] = []

    if stage in {"spec", "design", "tasks", "verify", "ci"}:
        g0_rows = run_gate_checks("G0", ctx, workflow)
        if stage == "spec":
            g0_rows = [row for row in g0_rows if row.get("id") != "G0-05"]
        errors.extend(gate_rows_errors(g0_rows))
        errors.extend(gate_rows_errors(run_gate_checks("G1", ctx, workflow)))
    if stage in {"spec", "design", "tasks", "verify"}:
        errors.extend(
            check_prd_index(
                root,
                config,
                state,
                spec_text,
                require_feat=not legacy_merged,
            )
        )
    if stage in {"design", "tasks", "verify", "ci"}:
        errors.extend(check_design(design_text, spec_acs, workflow))
    if stage in {"tasks", "verify", "ci"}:
        errors.extend(
            check_tasks(
                tasks_text,
                spec_acs,
                config,
                root if not legacy_merged else None,
            )
        )
        errors.extend(check_knowledge_assets(root))
        parsed_tasks = parse_tasks(tasks_text)
        if stage in {"verify", "ci"} or (
            stage == "tasks"
            and parsed_tasks
            and all(task["done"] for task in parsed_tasks)
        ):
            errors.extend(
                check_review_evidence(directory, state, workflow)
            )
    if stage in {"verify", "ci"}:
        errors.extend(
            check_verification(
                verification_text,
                spec_acs,
                workflow,
                state,
                config,
                directory,
            )
        )
        errors.extend(check_event_chain(directory))
        if not legacy_merged:
            errors.extend(check_test_coverage(root, config, spec_acs))
        errors.extend(
            check_verification_evidence(
                root,
                directory,
                config,
                spec_id,
                spec_text,
                design_text,
                tasks_text,
                state=state,
            )
        )
    if stage in {"design", "tasks", "verify", "ci"}:
        errors.extend(approval_digest_errors(root, directory, state))
        errors.extend(change_set_errors(root, directory, state))
    if stage == "ci":
        if state.get("state") not in {"PR_READY", "MERGED"}:
            errors.append("CI 检查要求状态为 PR_READY 或 MERGED")
        errors.extend(check_pr_body(read_text(directory / "PR_BODY.md"), spec_id))
        errors.extend(
            check_gates(root, config, directory, str(state.get("state", "DRAFT")))
        )
        if config.get("require_approver"):
            approvals = [
                item
                for item in state.get("approvals", [])
                if isinstance(item, dict)
                and str(item.get("approver") or "").strip().lower()
                not in {"", "unknown"}
            ]
            if not approvals:
                errors.append(
                    "require_approver=true，但 state.json 没有有效审批人记录"
                )
        errors.extend(
            check_prd_index(
                root,
                config,
                state,
                spec_text,
                require_feat=str(state.get("state")) != "MERGED",
            )
        )
        errors.extend(check_duplicate_spec_files(root, config))
        if check_git_trailer:
            errors.extend(
                check_git(root, spec_id, str(state.get("state", "DRAFT")))
            )

    return list(dict.fromkeys(errors)), stage


CONTEXT_BUNDLE_SCHEMA = 1


def empty_context_bundle(spec_id: str) -> dict[str, Any]:
    return {
        "schema": CONTEXT_BUNDLE_SCHEMA,
        "spec": spec_id,
        "task": None,
        "frs": [],
        "acs": [],
        "requirements": {"frs": [], "acs": []},
        "design_sections": [],
        "contracts": [],
        "contract_details": [],
        "project_constraints": [],
        "constraints": [],
        "review_overlays": [],
        "fix_patterns": [],
        "knowledge": [],
        "allowed_paths": [],
        "exclude": [],
        "scope_policy": "只读取当前 Spec 与当前 Task 所需内容；不得静默扩大改动范围。",
        "blocked": False,
        "empty": True,
        "notes": [],
    }


def _task_requirement_rows(
    spec_text: str,
    task: dict[str, Any],
) -> dict[str, list[dict[str, str]]]:
    frs: list[dict[str, str]] = []
    acs: list[dict[str, str]] = []
    fr_titles = {
        match.group(1): match.group(2).strip()
        for match in re.finditer(
            r"(?m)^#{1,6}\s+(FR-\d{3})\s*(.*)$",
            spec_text,
        )
    }
    for fr in task.get("frs", []):
        frs.append({"id": fr, "title": fr_titles.get(fr, "")})
    for ac in task.get("acs", []):
        line = next(
            (
                raw.strip().lstrip("-* ").strip()
                for raw in spec_text.splitlines()
                if ac in raw
            ),
            ac,
        )
        acs.append({"id": ac, "text": line})
    return {"frs": frs, "acs": acs}


def _design_context_sections(
    design_text: str,
    acs: Iterable[str],
    frs: Iterable[str],
) -> list[dict[str, Any]]:
    wanted = [*acs, *frs]
    sections: list[dict[str, Any]] = []
    for heading, lines in iter_sections(design_text):
        body = "\n".join(lines).strip()
        matched = [item for item in wanted if item and item in body]
        if not matched:
            continue
        if len(body) > 2500 or "覆盖" in heading or "接口" in heading:
            relevant = [
                line
                for line in lines
                if any(item and item in line for item in matched)
            ]
            content = "\n".join(relevant).strip() or body[:2500]
        else:
            content = body
        sections.append(
            {
                "heading": heading,
                "reason": "覆盖 " + ", ".join(dict.fromkeys(matched)),
                "content": content[:6000],
                "requirements": list(dict.fromkeys(matched)),
                "truncated": len(content) > 6000,
            }
        )
    return sections


def check_knowledge_assets(root: Path) -> list[str]:
    errors: list[str] = []
    index_path = root / "docs" / "knowledge" / "index.md"
    if index_path.is_file():
        header: Optional[list[str]] = None
        ids: set[str] = set()
        for line in read_text(index_path).splitlines():
            stripped = line.strip()
            if not stripped.startswith("|") or not stripped.endswith("|"):
                continue
            cells = split_table_row(stripped)
            if not cells:
                continue
            normalized = [normalize_column(cell) for cell in cells]
            if "id" in normalized and "type" in normalized:
                header = normalized
                required_columns = {
                    "id",
                    "type",
                    "statement",
                    "source",
                    "version",
                    "scope",
                    "owner",
                    "status",
                    "links",
                }
                missing = sorted(required_columns - set(header))
                if missing:
                    errors.append(
                        "知识索引缺少列：" + ", ".join(missing)
                    )
                continue
            if header is None:
                continue
            row = {
                header[index]: cells[index].strip()
                for index in range(min(len(header), len(cells)))
            }
            record_id = row.get("id", "")
            if not record_id or set(record_id) <= {"-", ":", " "}:
                continue
            if record_id in ids:
                errors.append(f"知识记录 ID 重复：{record_id}")
            ids.add(record_id)
            errors.extend(knowledge_record_errors(row))
        if header is None:
            errors.append(
                "docs/knowledge/index.md 缺少结构化知识表"
            )

    pattern_root = root / "docs" / "knowledge" / "patterns"
    if pattern_root.is_dir():
        for path in sorted(pattern_root.glob("FP-*.md")):
            data = parse_front_matter(read_text(path))
            if not data:
                errors.append(
                    f"{path.relative_to(root).as_posix()} 缺少 front matter"
                )
                continue
            errors.extend(fix_pattern_errors(data))
    return list(dict.fromkeys(errors))


def _knowledge_context(
    root: Path,
    task: dict[str, Any],
    feat_id: str,
    allowed_paths: list[str],
) -> tuple[list[dict[str, Any]], list[str]]:
    path = root / "docs" / "knowledge" / "index.md"
    if not path.is_file():
        return [], []
    records: list[dict[str, Any]] = []
    conflicts: list[str] = []
    header: Optional[list[str]] = None
    links_wanted = {
        feat_id,
        *[str(item) for item in task.get("frs", [])],
        *[str(item) for item in task.get("acs", [])],
    }
    for line in read_text(path).splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            continue
        cells = split_table_row(stripped)
        if not cells:
            continue
        normalized = [normalize_column(cell) for cell in cells]
        if "id" in normalized and "type" in normalized:
            header = normalized
            continue
        if header is None:
            continue
        row = {
            header[index]: cells[index].strip()
            for index in range(min(len(header), len(cells)))
        }
        record_id = row.get("id", "")
        if not record_id or set(record_id) <= {"-", ":", " "}:
            continue
        links = row.get("links", "")
        linked = any(link and link in links for link in links_wanted)
        scope = row.get("scope", "").replace("\\", "/")
        path_match = any(
            allowed and (allowed in scope or scope in allowed)
            for allowed in allowed_paths
        )
        if not linked and not path_match:
            continue
        record = {
            "id": record_id,
            "type": row.get("type", ""),
            "statement": row.get("statement", ""),
            "source": row.get("source", ""),
            "version": row.get("version", ""),
            "scope": scope,
            "owner": row.get("owner", ""),
            "status": row.get("status", ""),
            "links": links,
        }
        records.append(record)
        if (
            record["type"].upper() == "CONFLICT"
            and record["status"].upper() not in {"RESOLVED", "CLOSED", "CONFIRMED"}
        ):
            conflicts.append(record_id)
    return records, conflicts


def _pattern_context(
    root: Path,
    allowed_paths: list[str],
) -> list[dict[str, Any]]:
    pattern_root = root / "docs" / "knowledge" / "patterns"
    if not pattern_root.is_dir():
        return []
    patterns: list[dict[str, Any]] = []
    for path in sorted(pattern_root.glob("FP-*.md")):
        text = read_text(path)
        data = parse_front_matter(text)
        if not pattern_applies(data, allowed_paths):
            continue
        symptom = ""
        lines = text.replace("\r\n", "\n").splitlines()
        for index, line in enumerate(lines):
            if re.match(r"^#{1,6}\s+症状", line):
                symptom = next(
                    (item.strip() for item in lines[index + 1 :] if item.strip()),
                    "",
                )
                break
        status = str(data.get("status") or "draft").strip().lower()
        raw_checks = data.get("checks") or data.get("check") or []
        checks = (
            raw_checks
            if isinstance(raw_checks, list)
            else ([raw_checks] if str(raw_checks).strip() else [])
        )
        patterns.append(
            {
                "id": str(data.get("id") or path.stem),
                "path": path.relative_to(root).as_posix(),
                "status": status,
                "summary": symptom,
                "checks": checks,
                "check_command": data.get("check_command") or "",
                "reference_only": status not in {"verified", "active", "confirmed"},
            }
        )
    return patterns


def _review_overlay_context(
    root: Path,
    allowed_paths: list[str],
    review_required: bool,
) -> list[dict[str, str]]:
    if not review_required:
        return []
    wanted: list[tuple[str, str]] = []
    lowered = [path.lower() for path in allowed_paths]
    if any(path.endswith(".py") for path in lowered):
        wanted.append(("python", "sdd/prompts/review/python.md"))
    if any(path.endswith(".java") for path in lowered):
        wanted.append(("java-spring", "sdd/prompts/review/java-spring.md"))
    if any(
        path.endswith((".ts", ".tsx", ".js", ".jsx", ".css", ".html", ".vue"))
        for path in lowered
    ):
        wanted.append(("frontend", "sdd/prompts/review/frontend.md"))
    overlays: list[dict[str, str]] = []
    common = root / "sdd" / "prompts" / "review" / "contract.md"
    if common.is_file():
        overlays.append(
            {
                "id": "common",
                "path": "sdd/prompts/review/contract.md",
                "load_when": "当前风险或 Profile 要求独立审查",
            }
        )
    for overlay_id, relative in wanted:
        path = root / relative
        if path.is_file():
            overlays.append(
                {
                    "id": overlay_id,
                    "path": relative,
                    "load_when": "当前任务允许路径命中该技术栈",
                }
            )
    return overlays


def context_rule_paths(
    root: Path,
    spec_dir: str,
    context_rules: dict[str, Any],
) -> tuple[list[str], list[str], list[str]]:
    """Resolve declarative context_rules into concrete workspace paths."""
    allowed: set[str] = set()
    contracts: set[str] = set()
    excludes = [
        str(pattern).replace("\\", "/")
        for pattern in context_rules.get("exclude", []) or []
    ]
    for raw in context_rules.get("allowed_paths", []) or []:
        value = str(raw).replace("\\", "/").strip()
        if value:
            allowed.add(value)
    includes = [
        str(pattern).replace("\\", "/")
        for pattern in context_rules.get("include", []) or []
    ]
    matched: list[str] = []
    for pattern in includes:
        if ".." in pattern.split("/"):
            continue
        for raw in glob.glob(str(root / pattern), recursive=True):
            path = Path(raw)
            if not path.is_file():
                continue
            relative = path.relative_to(root).as_posix()
            if relative == "docs/prd.md" or is_other_spec_path(relative, spec_dir):
                continue
            if any(fnmatch.fnmatch(relative, item) for item in excludes):
                continue
            try:
                if path.stat().st_size > 200 * 1024:
                    continue
            except OSError:
                continue
            matched.append(relative)
    allowed.update(sorted(set(matched))[:50])
    contracts.update(
        value for value in allowed if value.lower().endswith(CONTRACT_SUFFIXES)
    )
    if excludes:
        allowed = {
            value
            for value in allowed
            if not any(fnmatch.fnmatch(value, item) for item in excludes)
        }
        contracts = {
            value
            for value in contracts
            if not any(fnmatch.fnmatch(value, item) for item in excludes)
        }
    return sorted(allowed), sorted(contracts), excludes


def build_context_bundle(
    root: Path,
    directory: Path,
    state: dict[str, Any],
    action: Optional[dict[str, Any]] = None,
    workflow: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    spec_id = str(state.get("spec_id", directory.name))
    bundle = empty_context_bundle(spec_id)
    if workflow is None:
        try:
            workflow = resolve_workflow(root, directory, state)
        except SddError:
            workflow = None
    context_rules = (workflow or {}).get("context_rules")
    if not isinstance(context_rules, dict):
        context_rules = {}
    spec_dir = directory.relative_to(root).as_posix()
    direct_task: Optional[dict[str, Any]] = None
    task_id = ""
    if action:
        raw_task = action.get("task")
        if isinstance(raw_task, str):
            task_id = raw_task
        elif isinstance(raw_task, dict):
            direct_task = raw_task
            task_id = str(raw_task.get("id") or "")
        elif action.get("id"):
            direct_task = action
            task_id = str(action.get("id") or "")
    if not task_id:
        if any(context_rules.get(key) for key in ("include", "allowed_paths", "exclude")):
            rule_allowed, rule_contracts, rule_excludes = context_rule_paths(
                root, spec_dir, context_rules
            )
            bundle["allowed_paths"] = rule_allowed
            bundle["contracts"] = rule_contracts
            bundle["contract_details"] = [
                {"path": path, "purpose": "工作流 context_rules 引入"}
                for path in rule_contracts
            ]
            bundle["exclude"] = list(dict.fromkeys(rule_excludes))
        bundle["empty"] = True
        return bundle

    spec_text = read_text(directory / "spec.md")
    design_text = read_text(directory / "design.md")
    tasks_text = read_text(directory / "tasks.md")
    task = direct_task or next(
        (item for item in parse_tasks(tasks_text) if item["id"] == task_id),
        None,
    )
    if task is None:
        bundle["notes"].append(f"当前任务 {task_id} 在 tasks.md 中不存在")
        return bundle

    feat_id = str(
        state.get("feat_id")
        or metadata_value(spec_text, "FEAT ID", "FEAT", "Feature ID")
    )
    allowed = list(task_scope_paths(task))
    allowed.extend(design_scope_paths(design_text, spec_dir))
    allowed.extend(extract_backtick_paths(str(task.get("description") or "")))
    rule_allowed, rule_contracts, rule_excludes = context_rule_paths(
        root, spec_dir, context_rules
    )
    allowed.extend(rule_allowed)
    allowed = [
        value
        for value in dict.fromkeys(allowed)
        if value != "docs/prd.md" and not is_other_spec_path(value, spec_dir)
    ]
    allowed = [
        value
        for value in allowed
        if not any(fnmatch.fnmatch(value, item) for item in rule_excludes)
    ]

    exclude = list(CONTEXT_EXCLUDES)
    exclude.extend(
        [
        ".git",
        ".sdd",
        "docs/prd.md",
        "历史聊天",
        "其他 Spec 正文",
        "docs/specs/*",
        f"docs/specs/{spec_id} 之外的 Spec",
        ]
    )
    exclude.extend(rule_excludes)
    exclude = list(dict.fromkeys(exclude))

    requirements = _task_requirement_rows(spec_text, task)
    design_sections = _design_context_sections(
        design_text,
        task.get("acs", []),
        task.get("frs", []),
    )
    candidate_text = "\n".join(
        [str(task.get("description") or ""), design_text, spec_text]
    )
    contract_paths = list(design_contract_paths(design_text, spec_dir))
    contract_paths.extend(context_contract_paths(root))
    contract_paths.extend(rule_contracts)
    for relative in extract_backtick_paths(candidate_text):
        path = root / relative
        if not path.is_file():
            continue
        if (
            relative.startswith("sdd/context/contracts/")
            or "/api/" in f"/{relative}"
            or relative.endswith((".yaml", ".yml", ".json", ".proto"))
        ):
            contract_paths.append(relative)
    contracts = [
        {"path": path, "purpose": "任务或设计引用的契约"}
        for path in dict.fromkeys(contract_paths)
    ]

    constraints: list[dict[str, str]] = []
    agents_path = root / "AGENTS.md"
    if agents_path.is_file():
        agents_text = read_text(agents_path)
        constraints.append(
            {
                "path": "AGENTS.md",
                "excerpt": agents_text[:6000],
                "truncated": str(len(agents_text) > 6000).lower(),
            }
        )
    config_path = root / "sdd" / "config.json"
    if config_path.is_file():
        config_data = load_json(config_path)
        constraints.append(
            {
                "path": "sdd/config.json",
                "excerpt": json.dumps(
                    {
                        "sdd_level": config_data.get("sdd_level"),
                        "prd_mode": config_data.get("prd_mode"),
                        "workflow": config_data.get("workflow"),
                        "test_commands": config_data.get("test_commands", []),
                        "risk_stop": config_data.get("risk_stop", []),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                "truncated": "false",
            }
        )

    knowledge, conflicts = _knowledge_context(
        root,
        task,
        feat_id,
        allowed,
    )
    bundle.update(
        {
            "task": {
                "id": task["id"],
                "description": task["description"],
                "status": task["status"],
            },
            "frs": [item["id"] for item in requirements["frs"]],
            "acs": [item["id"] for item in requirements["acs"]],
            "requirements": requirements,
            "design_sections": design_sections,
            "contracts": [item["path"] for item in contracts],
            "contract_details": contracts,
            "project_constraints": [
                {"path": "AGENTS.md", "scope": "."},
                *[
                    {"path": item["path"], "scope": "."}
                    for item in constraints
                    if item["path"] != "AGENTS.md"
                ],
            ],
            "constraints": constraints,
            "review_overlays": _review_overlay_context(
                root,
                allowed,
                review_required_for(workflow, state),
            ),
            "fix_patterns": _pattern_context(root, allowed),
            "knowledge": knowledge,
            "allowed_paths": allowed,
            "exclude": exclude,
            "blocked": bool(conflicts),
            "empty": False,
        }
    )
    if conflicts:
        bundle["notes"].append(
            "存在未解决知识冲突：" + ", ".join(conflicts) + "；相关决策必须先裁决。"
        )
    if not allowed:
        bundle["notes"].append(
            "任务未声明具体改动路径；实施前应先补充允许范围。"
        )
    if not design_sections:
        bundle["notes"].append("未找到与当前 FR/AC 直接关联的设计章节。")
    return bundle


CONTEXT_BUNDLE_FIELDS = (
    "task",
    "frs",
    "acs",
    "design_sections",
    "contracts",
    "project_constraints",
    "fix_patterns",
    "allowed_paths",
    "exclude",
)

CONTEXT_EXCLUDES = [
    "docs/prd.md",
    "docs/specs/*（其他 Spec）",
    ".sdd/runtime/**",
    "历史聊天",
]

CONTEXT_SCOPE_SECTIONS = (
    ("Spec 覆盖关系", "Spec Coverage"),
    ("影响范围", "Impact"),
    ("接口契约", "Interfaces", "Interface Contracts"),
    ("契约文件", "Contracts", "Contract Files"),
)

CONTRACT_SUFFIXES = (
    ".yaml",
    ".yml",
    ".json",
    ".proto",
    ".avsc",
    ".graphql",
    ".wsdl",
    ".xsd",
    ".md",
)

PATH_ROOTS = {
    "app",
    "cmd",
    "deploy",
    "docs",
    "dsh",
    "internal",
    "lib",
    "pkg",
    "scripts",
    "sdd",
    "src",
    "test",
    "tests",
}


def normalize_relative_path(value: str) -> str:
    cleaned = value.strip().strip("`'\"")
    cleaned = cleaned.replace("\\", "/")
    while cleaned.startswith("./"):
        cleaned = cleaned[2:]
    return cleaned


def is_path_like(value: str) -> bool:
    if not value:
        return False
    if any(char in value for char in " \t\r\n（）()[]{}<>|"):
        return False
    if value.startswith(("http://", "https://", "www.")):
        return False
    if re.match(r"^[A-Za-z]:/", value) or value.startswith(("../", "/")):
        return False
    if "/" not in value:
        return False
    if not re.search(r"[A-Za-z0-9]", value):
        return False
    root = value.split("/", 1)[0]
    last = value.rstrip("/").rsplit("/", 1)[-1]
    return root in PATH_ROOTS or "." in last


def extract_paths(text: str) -> list[str]:
    candidates = re.findall(r"`([^`\n]+)`", text)
    candidates.extend(
        re.findall(
            r"(?<![\w/.-])((?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.*-]+)",
            text,
        )
    )
    paths: set[str] = set()
    for candidate in candidates:
        value = normalize_relative_path(candidate)
        if is_path_like(value):
            paths.add(value)
    return sorted(paths)


def is_other_spec_path(value: str, spec_dir: str) -> bool:
    if not value.startswith("docs/specs/"):
        return False
    spec_dir = spec_dir.rstrip("/")
    return value != spec_dir and not value.startswith(spec_dir + "/")


def design_section_refs(
    text: str, frs: list[str], acs: list[str]
) -> list[dict[str, str]]:
    wanted_frs = set(frs)
    wanted_acs = set(acs)
    refs: list[dict[str, str]] = []
    for heading, body in iter_sections(text):
        body_text = "\n".join(body)
        hit_acs = sorted(set(extract_acs(body_text)) & wanted_acs)
        hit_frs = sorted(set(extract_frs(body_text)) & wanted_frs)
        if not hit_acs and not hit_frs:
            continue
        reasons: list[str] = []
        if hit_acs:
            reasons.append("覆盖 " + ", ".join(hit_acs))
        if hit_frs:
            reasons.append("关联 " + ", ".join(hit_frs))
        refs.append({"heading": heading, "reason": "；".join(reasons)})
    return refs


def design_scope_paths(text: str, spec_dir: str) -> list[str]:
    wanted = {
        normalize_heading(alias)
        for aliases in CONTEXT_SCOPE_SECTIONS
        for alias in aliases
    }
    chunks: list[str] = []
    for heading, body in iter_sections(text):
        if normalize_heading(heading) in wanted:
            chunks.append("\n".join(body))
    for line in text.splitlines():
        if re.search(r"(?i)(契约文件|contract\s*file)", line):
            chunks.append(line)
    paths: set[str] = set()
    for chunk in chunks:
        for value in extract_paths(chunk):
            if value == "docs/prd.md" or is_other_spec_path(value, spec_dir):
                continue
            paths.add(value)
    return sorted(paths)


def design_contract_paths(text: str, spec_dir: str) -> list[str]:
    paths = {
        value
        for value in design_scope_paths(text, spec_dir)
        if value.lower().endswith(CONTRACT_SUFFIXES)
    }
    return sorted(paths)


def context_contract_paths(root: Path) -> list[str]:
    base = root / "sdd" / "context" / "contracts"
    if not base.is_dir():
        return []
    return sorted(
        path.relative_to(root).as_posix()
        for path in base.rglob("*")
        if path.is_file()
    )


def module_token_to_path(token: str) -> str:
    value = token.strip().strip("`")
    value = re.split(r"[#:]", value, maxsplit=1)[0].strip()
    if not value:
        return ""
    if "/" in value or "\\" in value:
        path = normalize_relative_path(value)
        return path if is_path_like(path) else ""
    parts = [part for part in value.split(".") if part]
    while parts and parts[-1][:1].isupper():
        parts.pop()
    if len(parts) < 2 or not all(re.fullmatch(r"[A-Za-z_]\w*", part) for part in parts):
        return ""
    return "/".join(parts) + ".py"


def task_scope_paths(task: dict[str, Any]) -> list[str]:
    paths: set[str] = set()
    test_value = str(task.get("test") or "")
    for token in re.split(r"[、,，;\s]+", test_value):
        path = module_token_to_path(token)
        if path:
            paths.add(path)
    command = str(task.get("command") or "")
    for match in re.finditer(
        r"(?<![\w.-])([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+)", command
    ):
        token = match.group(1)
        if token.startswith("unittest."):
            token = token[len("unittest.") :]
        path = module_token_to_path(token)
        if path:
            paths.add(path)
    for match in re.finditer(r"(?:^|\s)-s\s+([\w./-]+)", command):
        value = normalize_relative_path(match.group(1)).rstrip("/")
        if value:
            paths.add(value + "/")
    return sorted(paths)


def build_next_action(
    root: Path, directory: Path, state: dict[str, Any]
) -> dict[str, Any]:
    state_name = str(state.get("state", "DRAFT"))
    spec_id = str(state.get("spec_id", directory.name))
    relative_dir = directory.relative_to(root).as_posix()
    base: dict[str, Any] = {
        "spec": spec_id,
        "state": state_name,
        "workflow": (
            state.get("workflow")
            if isinstance(state.get("workflow"), dict)
            else None
        ),
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
        try:
            config = load_config(root)
            tasks_done = (
                gate_report_status(
                    gate_report_path(root, config, spec_id, "G3")
                )
                == "PASS"
            )
        except SddError:
            tasks_done = True
        if tasks_done:
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
        else:
            base.update(
                {
                    "action": "write_tasks",
                    "kind": "artifact",
                    "step_id": f"{spec_id}:tasks",
                    "expected_result": "artifact_submitted",
                    "prompt": "sdd/prompts/tasks.md",
                    "artifact": f"{relative_dir}/tasks.md",
                    "done_when": (
                        "sdd check --stage tasks 通过，然后 sdd complete --evidence ..."
                    ),
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
                "action": "confirm_merge",
                "kind": "human_checkpoint",
                "step_id": f"{spec_id}:delivery_confirmation",
                "expected_result": "human_confirmation",
                "prompt": "sdd/prompts/delivery.md",
                "artifact": f"{relative_dir}/PR_BODY.md",
                "done_when": (
                    "人工确认交付并运行 sdd merge --human；确认前不要创建 PR"
                ),
            }
        )
    elif state_name == "MERGED":
        if state.get("delivery_confirmed_at") and not state.get("pr_url"):
            base.update(
                {
                    "action": "open_pr",
                    "kind": "artifact",
                    "step_id": f"{spec_id}:open_pr",
                    "expected_result": "pr_recorded",
                    "prompt": "sdd/prompts/pr.md",
                    "artifact": f"{relative_dir}/PR_BODY.md",
                    "done_when": (
                        "提交并推送交付确认，用 PR_BODY.md 开 PR，"
                        "运行 sdd pr --url <URL> 记录；不要合并"
                    ),
                }
            )
        else:
            base.update(
                {
                    "action": "done",
                    "kind": "done",
                    "step_id": f"{spec_id}:done",
                    "expected_result": "done",
                    "done_when": "Spec 已交付",
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
    try:
        workflow = resolve_workflow(root, directory, state)
    except SddError:
        workflow = None
    base["context_bundle"] = build_context_bundle(
        root, directory, state, base, workflow
    )
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

    workflow_name = (
        getattr(args, "workflow", None)
        or str(config.get("workflow") or DEFAULT_WORKFLOW)
    ).strip()
    workflow = load_workflow_preset(root, workflow_name)
    risk_error = workflow_risk_error(
        workflow,
        str(args.risk or "low"),
        args.risk_label or [],
        config,
    )
    if risk_error:
        raise SddError(risk_error)

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
    feat_id = allocate_feat_id(root, config)

    product_type = args.product_type or "传统产品"
    adapt = {
        "传统产品": "核心骨架",
        "AI辅助·L2": "核心骨架＋AI扩展",
        "AI增强·L3": "核心骨架＋AI扩展",
        "AI原生·L4": "核心骨架＋AI扩展＋AI原生扩展",
    }.get(product_type, "核心骨架")
    feat_id = allocate_feat(root, config)
    context = {
        "SPEC_ID": spec_id,
        "TITLE": args.title,
        "WORK_ITEM": work_item,
        "FEAT_ID": feat_id,
        "ISSUE": args.issue or "N/A",
        "DATE": now(),
        "PRODUCT_TYPE": product_type,
        "TEMPLATE_ADAPT": adapt,
        "AUTHOR": args.author or "SDD Agent",
        "FEAT_ID": feat_id,
        "WORKFLOW": str(workflow.get("name") or workflow_name),
    }
    directory.mkdir(parents=True, exist_ok=False)
    design_template = (
        "design-lite.md"
        if str(workflow.get("design_mode") or "full") == "lite"
        else "design.md"
    )
    verification_template = (
        "verification-strict.md"
        if review_required_for(workflow, {"risk": args.risk})
        else "verification.md"
    )
    for name in ("spec.md", design_template, "tasks.md", verification_template):
        target_name = {
            "design-lite.md": "design.md",
            "verification-strict.md": "verification.md",
        }.get(name, name)
        write_text(
            directory / target_name,
            render_template(root, name, context),
        )
    write_text(directory / "gates.md", render_template(root, "gates.md", context))
    write_text(directory / "decisions.md", render_template(root, "decisions.md", context))
    (directory / "adrs").mkdir(exist_ok=True)
    (directory / "api").mkdir(exist_ok=True)
    state = {
        "spec_id": spec_id,
        "title": args.title,
        "work_item": work_item,
        "feat_id": feat_id,
        "schema": 2,
        "issue": args.issue,
        "product_type": product_type,
        "risk": args.risk,
        "risk_labels": args.risk_label or [],
        "workflow": create_workflow_snapshot(
            root,
            config,
            directory,
            workflow_name,
        ),
        "state": "DRAFT",
        "created_at": now(),
        "updated_at": now(),
        "pr_url": None,
        "history": [
            {
                "state": "DRAFT",
                "at": now(),
                "evidence": "created",
                "role": "planner",
            }
        ],
    }
    save_state(directory, state)
    ensure_prd_index(
        root,
        config,
        spec_id,
        work_item,
        args.title,
        args.issue,
        feat_id=feat_id,
    )
    print(f"[sdd] created {directory.relative_to(root)}")
    print(f"[sdd] work item: {work_item}")
    print(f"[sdd] workflow: {workflow_name}@{workflow['version']}")
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
    workflow = state.get("workflow") or {}
    if workflow.get("name"):
        print(
            f"Flow:   {workflow.get('name')}@{workflow.get('version')}"
        )
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
        "audit": verify_event_chain(events),
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
                "workflow": state.get("workflow"),
                "next": action,
                "events_count": len(events),
                "last_event": events[-1] if events else None,
                "tasks": [
                    {
                        "id": task["id"],
                        "description": task["description"],
                        "status": task.get("status", "Todo"),
                        "acs": task.get("acs", []),
                        "commit": task.get("commit", ""),
                        "test": task.get("test", ""),
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


def parse_timestamp(value: Any) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime.now().astimezone().tzinfo)
    return parsed


def spec_events(directory: Path, state: dict[str, Any]) -> list[dict[str, Any]]:
    events = read_event_log(directory)
    history_count = len(
        [entry for entry in state.get("history", []) if isinstance(entry, dict)]
    )
    if len(events) < history_count:
        events = derive_events(state)
    return events


def latest_event_at(directory: Path, state: dict[str, Any]) -> str:
    events = spec_events(directory, state)
    if events:
        return str(events[-1].get("at") or state.get("updated_at") or state.get("created_at") or "")
    return str(state.get("updated_at") or state.get("created_at") or "")


def pending_manual_gate(
    root: Path, config: dict[str, Any], directory: Path, state: dict[str, Any]
) -> Optional[str]:
    workflow = resolve_workflow(root, directory, state)
    state_name = str(state.get("state", ""))
    tasks: list[dict[str, Any]] = []
    if state_name == "SPEC_READY":
        gate, stage = "G2", "design"
    elif state_name == "DESIGN_READY":
        gate, stage = "G3", "tasks"
    elif state_name == "TASKS_READY":
        gate, stage = "G3", "tasks"
    elif state_name == "IMPLEMENTING":
        tasks = parse_tasks(read_text(directory / "tasks.md"))
        if not tasks or not all(task["done"] for task in tasks):
            return None
        gate, stage = "G4", "tasks"
    elif state_name == "VERIFYING":
        gate, stage = "G5", "verify"
    else:
        return None

    spec_id = str(state.get("spec_id", directory.name))
    if gate_report_status(
        gate_report_path(root, config, spec_id, gate)
    ) == "PASS":
        return None
    if not gate_requires_human(config, gate, state, workflow):
        return None

    errors, _ = run_checks(root, config, directory, state, stage)
    if state_name == "VERIFYING":
        errors.extend(check_gates(root, config, directory, "VERIFYING"))
    if state_name == "IMPLEMENTING":
        verification_text = read_text(directory / "verification.md")
        missing = [task["id"] for task in tasks if task["id"] not in verification_text]
        if missing:
            errors.append("以下 Task 没有验证证据：" + ", ".join(missing))
    return gate if not errors else None


def build_inbox_item(
    root: Path,
    config: dict[str, Any],
    directory: Path,
    state: dict[str, Any],
    stale_days: Optional[int],
) -> Optional[dict[str, Any]]:
    spec_id = str(state.get("spec_id", directory.name))
    state_name = str(state.get("state", "UNKNOWN"))
    since = latest_event_at(directory, state) or str(state.get("created_at") or "")
    item: Optional[dict[str, Any]] = None
    warnings = (
        []
        if state_name == "MERGED"
        else gate_warning_items(
            collect_gate_check_rows(root, config, spec_id)
        )
    )

    if state_name == "BLOCKED":
        item = {
            "spec": spec_id,
            "state": state_name,
            "priority": 0,
            "action": "unblock",
            "reason": str(state.get("blocked_reason") or "阻塞等待人工处理"),
            "since": since,
            "artifact": None,
            "command": (
                f"python -m sdd unblock --spec {spec_id} --human "
                '--evidence "阻塞已解除"'
            ),
        }
    elif state_name == "PR_READY":
        item = {
            "spec": spec_id,
            "state": state_name,
            "priority": 10,
            "action": "confirm_merge",
            "reason": "交付待人工确认；确认后才创建 PR",
            "since": since,
            "artifact": f"{directory.relative_to(root).as_posix()}/PR_BODY.md",
            "command": (
                f"python -m sdd merge --spec {spec_id} --human "
                '--evidence "交付已确认"'
            ),
        }
    elif state_name == "DRAFT":
        item = {
            "spec": spec_id,
            "state": state_name,
            "priority": 20,
            "action": "approve_spec",
            "reason": "G0 等待人工确认需求",
            "since": since,
            "artifact": f"{directory.relative_to(root).as_posix()}/spec.md",
            "command": (
                f"python -m sdd approve --spec {spec_id} --human "
                '--evidence "需求已确认"'
            ),
        }
    else:
        gate = pending_manual_gate(root, config, directory, state)
        if gate:
            artifact_name = {
                "G2": "design.md",
                "G3": "tasks.md",
                "G4": "tasks.md",
                "G5": "verification.md",
            }.get(gate)
            item = {
                "spec": spec_id,
                "state": state_name,
                "priority": 30,
                "action": "manual_gate",
                "gate": gate,
                "reason": f"{gate} 等待人工确认",
                "since": since,
                "artifact": (
                    f"{directory.relative_to(root).as_posix()}/{artifact_name}"
                    if artifact_name
                    else None
                ),
                "command": (
                    f"python -m sdd complete --spec {spec_id} --human "
                    '--evidence "人工 Gate 已确认"'
                ),
            }

    if warnings:
        if item is None:
            item = {
                "spec": spec_id,
                "state": state_name,
                "priority": 50,
                "action": "review_warning",
                "reason": f"{len(warnings)} 条 Gate 告警待复核",
                "since": since,
                "artifact": warnings[0]["report"],
                "command": None,
            }
        item["warnings"] = warnings

    if item is None and stale_days is not None:
        since_dt = parse_timestamp(since)
        if since_dt is not None:
            age_days = (datetime.now().astimezone() - since_dt).total_seconds() / 86400
            if age_days > stale_days:
                item = {
                    "spec": spec_id,
                    "state": state_name,
                    "priority": 40,
                    "action": "stale",
                    "reason": f"{int(age_days)} 天没有新事件",
                    "since": since,
                    "artifact": None,
                    "command": None,
                }
    return item


def build_inbox_extras(
    root: Path,
    config: dict[str, Any],
    directory: Path,
    state: dict[str, Any],
) -> list[dict[str, Any]]:
    spec_id = str(state.get("spec_id", directory.name))
    items: list[dict[str, Any]] = []
    waivers = state.get("waivers")
    if isinstance(waivers, list):
        for waiver in waivers:
            if not isinstance(waiver, dict):
                continue
            expired = waiver_is_expired(waiver)
            items.append(
                {
                    "spec": spec_id,
                    "state": state.get("state"),
                    "priority": 5 if expired else 55,
                    "action": "waiver_expired" if expired else "waiver",
                    "check_id": waiver.get("check_id"),
                    "waiver_id": waiver.get("id"),
                    "reason": (
                        f"{waiver.get('check_id')} 豁免已过期"
                        if expired
                        else f"{waiver.get('check_id')} 豁免有效至 "
                        f"{waiver.get('expires_at')}"
                    ),
                    "since": waiver.get("created_at"),
                    "artifact": None,
                    "command": (
                        f"python -m sdd check --spec {spec_id} --stage verify --json"
                    ),
                }
            )
    stage = {
        "SPEC_READY": "design",
        "DESIGN_READY": "tasks",
        "TASKS_READY": "tasks",
        "IMPLEMENTING": "tasks",
        "VERIFYING": "verify",
        "PR_READY": "ci",
    }.get(str(state.get("state")), None)
    if stage:
        errors, resolved_stage = run_checks(
            root,
            config,
            directory,
            state,
            stage,
        )
        checks = apply_check_waivers(
            stage_check_results(
                resolved_stage,
                errors,
                resolve_workflow(root, directory, state),
            ),
            state,
            spec_id,
            waiver_contexts(directory, resolved_stage),
        )
        for check in checks:
            if check.get("result") != "warn":
                continue
            items.append(
                {
                    "spec": spec_id,
                    "state": state.get("state"),
                    "priority": 60,
                    "action": "warn",
                    "check_id": check.get("id"),
                    "reason": f"{check.get('id')} {check.get('detail')}",
                    "since": latest_event_at(directory, state),
                    "artifact": None,
                    "command": (
                        f"python -m sdd check --spec {spec_id} "
                        f"--stage {resolved_stage} --json"
                    ),
                }
            )
    history = state.get("workflow_history") or []
    latest = history[-1] if history and isinstance(history[-1], dict) else {}
    pending_gates = [
        str(gate) for gate in latest.get("pending_gates") or [] if str(gate)
    ]
    if pending_gates:
        preset = latest.get("to_preset") or {}
        gate_modes = preset.get("gates") if isinstance(preset, dict) else {}
        gate_modes = gate_modes if isinstance(gate_modes, dict) else {}
        target = latest.get("to") or {}
        target_label = (
            f"{target.get('name')}@{target.get('version')}"
            if isinstance(target, dict) and target.get("name")
            else "新预设"
        )
        for gate in pending_gates:
            if (
                gate_report_status(
                    gate_report_path(root, config, spec_id, gate)
                )
                == "PASS"
            ):
                continue
            if str(gate_modes.get(gate) or "") == "human":
                command = (
                    f"python -m sdd complete --spec {spec_id} --human "
                    f'--evidence "{gate} 人工确认"'
                )
            else:
                command = (
                    f"python -m sdd check --spec {spec_id} "
                    f"--stage {stage or 'ci'} --json"
                )
            items.append(
                {
                    "spec": spec_id,
                    "state": state.get("state"),
                    "priority": 35,
                    "action": "workflow_gate_missing",
                    "gate": gate,
                    "reason": (
                        f"{gate} 在升级到 {target_label} 后仍无 PASS 报告"
                    ),
                    "since": latest.get("at"),
                    "artifact": None,
                    "command": command,
                }
            )
    return items


def command_inbox(args: argparse.Namespace, root: Path, config: dict[str, Any]) -> int:
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
    items: list[dict[str, Any]] = []
    for directory in directories:
        state = load_json(directory / "state.json")
        item = build_inbox_item(
            root, config, directory, state, args.stale_days
        )
        if item:
            items.append(item)
        items.extend(build_inbox_extras(root, config, directory, state))
    items.sort(
        key=lambda item: (
            int(item["priority"]),
            parse_timestamp(item.get("since")) or datetime.now().astimezone(),
        )
    )
    payload = {
        "ok": True,
        "kind": "inbox",
        "generated_at": now(),
        "items": items,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    if not items:
        print("[sdd] no human actions waiting")
        return 0
    for item in items:
        print(
            f"{item['spec']}  [{item['state']}]  {item['action']}  "
            f"priority={item['priority']}  {item['reason']}"
        )
        if item.get("command"):
            print(f"  {item['command']}")
    return 0


def compute_spec_metrics(
    root: Path,
    config: dict[str, Any],
    directory: Path,
    state: dict[str, Any],
    since: Optional[datetime],
) -> Optional[dict[str, Any]]:
    events = spec_events(directory, state)
    if since is not None:
        events = [
            event
            for event in events
            if (parse_timestamp(event.get("at")) or since) >= since
        ]
        if not events:
            return None

    spec_id = str(state.get("spec_id", directory.name))
    transition_events = [event for event in events if event.get("to_state")]
    first_at = (
        parse_timestamp(transition_events[0].get("at"))
        if transition_events
        else parse_timestamp(state.get("created_at"))
    )
    merged_at = parse_timestamp(
        state.get("merged_at")
        or next(
            (
                event.get("at")
                for event in reversed(events)
                if event.get("to_state") == "MERGED"
            ),
            None,
        )
    )
    lead_time_hours = (
        round((merged_at - first_at).total_seconds() / 3600, 2)
        if merged_at and first_at
        else None
    )

    stage_hours: dict[str, float] = {}
    previous_at: Optional[datetime] = None
    previous_state: Optional[str] = None
    for event in transition_events:
        at = parse_timestamp(event.get("at"))
        if previous_at and previous_state and at:
            stage_hours[previous_state] = round(
                stage_hours.get(previous_state, 0.0)
                + (at - previous_at).total_seconds() / 3600,
                2,
            )
        previous_at = at
        previous_state = str(event.get("to_state"))

    task_starts: dict[str, datetime] = {}
    task_hours: dict[str, float] = {}
    for event in events:
        task = str(event.get("task") or "")
        at = parse_timestamp(event.get("at"))
        if not task or at is None:
            continue
        if event.get("event") == "task_start":
            task_starts[task] = at
        elif event.get("event") == "task_done" and task in task_starts:
            task_hours[task] = round(
                (at - task_starts[task]).total_seconds() / 3600, 2
            )

    spec_text = read_text(directory / "spec.md")
    _, spec_acs = check_spec(spec_text, spec_id)
    verification_text = read_text(directory / "verification.md")
    covered = sum(1 for ac in spec_acs if ac in verification_text)

    artifacts: dict[str, set[str]] = {}
    for event in events:
        for artifact in event.get("artifacts", []) or []:
            if not isinstance(artifact, dict):
                continue
            path = str(artifact.get("path") or "")
            digest = str(artifact.get("sha256") or "")
            if path and digest:
                artifacts.setdefault(path, set()).add(digest)

    check_stats: dict[str, dict[str, Any]] = {}
    gate_first_seen: dict[str, str] = {}
    for event in events:
        if event.get("event") != "gate_result":
            continue
        gate = str(event.get("gate") or "")
        status = str(event.get("status") or "").upper()
        if gate and gate not in gate_first_seen:
            gate_first_seen[gate] = status
        for check in event.get("checks", []) or []:
            if not isinstance(check, dict):
                continue
            check_id = str(check.get("id") or "")
            result = str(check.get("result") or "").lower()
            if not check_id or result not in {"pass", "warn", "block", "waived"}:
                continue
            bucket = check_stats.setdefault(
                check_id,
                {
                    "id": check_id,
                    "pass": 0,
                    "warn": 0,
                    "block": 0,
                    "waived": 0,
                    "total": 0,
                },
            )
            bucket[result] += 1
            bucket["total"] += 1
    for bucket in check_stats.values():
        total = int(bucket["total"])
        bucket["pass_rate"] = (
            round(bucket["pass"] / total, 4) if total else 0.0
        )
        bucket["waiver_rate"] = (
            round(bucket["waived"] / total, 4) if total else 0.0
        )

    waiver_count = sum(
        1 for event in events if event.get("event") == "waiver_created"
    )
    checks_total = sum(int(item["total"]) for item in check_stats.values())
    first_pass_gates = sum(
        1
        for status in gate_first_seen.values()
        if status in {"PASS", "PASS_WITH_WAIVER"}
    )
    audit = verify_event_chain(events)

    return {
        "spec": spec_id,
        "title": state.get("title", ""),
        "state": state.get("state", "UNKNOWN"),
        "lead_time_hours": lead_time_hours,
        "stage_hours": stage_hours,
        "reworks": sum(1 for event in events if event.get("event") == "rewind"),
        "human_interventions": sum(
            1
            for event in events
            if event.get("actor") == "human"
            and event.get("event") != "spec_created"
        ),
        "gate_failures": sum(
            1 for event in events if event.get("event") == "check_failed"
        ),
        "task_hours": task_hours,
        "ac_coverage": (
            round(covered / len(spec_acs), 4) if spec_acs else None
        ),
        "artifact_changes": sum(
            1 for hashes in artifacts.values() if len(hashes) > 1
        ),
        "waivers": {
            "count": waiver_count,
            "rate": (
                round(waiver_count / checks_total, 4)
                if checks_total
                else 0.0
            ),
        },
        "gate_first_pass": {
            "first_pass": first_pass_gates,
            "total": len(gate_first_seen),
            "rate": (
                round(first_pass_gates / len(gate_first_seen), 4)
                if gate_first_seen
                else None
            ),
        },
        "reopened": any(
            event.get("event") == "rewind" for event in events
        ),
        "check_stats": sorted(check_stats.values(), key=lambda item: item["id"]),
        "checks": summarize_gate_checks(
            collect_gate_check_rows(root, config, spec_id)
        ),
        "audit": audit,
    }


def escaped_defect_count(root: Path) -> int:
    bar_root = root / "docs" / "knowledge" / "bar"
    if not bar_root.is_dir():
        return 0
    count = 0
    for path in sorted(bar_root.glob("BAR-*.md")):
        data = parse_front_matter(read_text(path))
        value = str(data.get("escaped") or data.get("detected_after_merge") or "")
        if value.strip().lower() == "true":
            count += 1
    return count


def command_metrics(
    args: argparse.Namespace, root: Path, config: dict[str, Any]
) -> int:
    since = parse_timestamp(args.since)
    if args.since and since is None:
        raise SddError("--since 需要 ISO 日期或日期时间，例如 2026-11-01")
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
    all_check_rows: list[dict[str, Any]] = []
    for directory in directories:
        state = load_json(directory / "state.json")
        item = compute_spec_metrics(
            root, config, directory, state, since
        )
        if item:
            specs.append(item)
            all_check_rows.extend(
                collect_gate_check_rows(
                    root,
                    config,
                    str(state.get("spec_id", directory.name)),
                )
            )

    lead_times = [
        item["lead_time_hours"]
        for item in specs
        if item["lead_time_hours"] is not None
    ]
    reworks = [item["reworks"] for item in specs]
    check_stats: dict[str, dict[str, Any]] = {}
    for item in specs:
        for bucket in item.get("check_stats", []):
            aggregate = check_stats.setdefault(
                bucket["id"],
                {
                    "id": bucket["id"],
                    "pass": 0,
                    "warn": 0,
                    "block": 0,
                    "waived": 0,
                    "total": 0,
                },
            )
            for key in ("pass", "warn", "block", "waived", "total"):
                aggregate[key] += int(bucket.get(key, 0))
    for bucket in check_stats.values():
        total = int(bucket["total"])
        bucket["pass_rate"] = (
            round(bucket["pass"] / total, 4) if total else 0.0
        )
        bucket["waiver_rate"] = (
            round(bucket["waived"] / total, 4) if total else 0.0
        )
    checks_total = sum(int(item["total"]) for item in check_stats.values())
    waiver_count = sum(item["waivers"]["count"] for item in specs)
    first_pass = sum(item["gate_first_pass"]["first_pass"] for item in specs)
    gate_total = sum(item["gate_first_pass"]["total"] for item in specs)
    reopened_specs = sum(1 for item in specs if item["reopened"])
    completed_specs = sum(1 for item in specs if item["state"] == "MERGED")
    escaped_defects = escaped_defect_count(root)
    audit_errors = [
        f"{item['spec']}: {error}"
        for item in specs
        for error in item["audit"]["errors"]
    ]
    quality = {
        "waiver_rate": (
            round(waiver_count / checks_total, 4)
            if checks_total
            else 0.0
        ),
        "escaped_defects": escaped_defects,
        "escaped_defect_rate": (
            round(escaped_defects / len(specs), 4) if specs else 0.0
        ),
        "reopened_specs": reopened_specs,
        "reopen_rate": (
            round(reopened_specs / completed_specs, 4)
            if completed_specs
            else 0.0
        ),
        "gate_first_pass_rate": (
            round(first_pass / gate_total, 4) if gate_total else None
        ),
        "definitions": {
            "waiver_rate": "waiver_created 事件数 / 已记录检查结果总数",
            "escaped_defects": "BAR front matter 中 escaped=true 的缺陷数",
            "escaped_defect_rate": "逃逸缺陷数 / 统计范围内 Spec 数",
            "reopen_rate": "发生 rewind 的 Spec 数 / MERGED Spec 数",
            "gate_first_pass_rate": "每个 Spec 每个 Gate 首次结果为 PASS 或 PASS_WITH_WAIVER 的比例",
        },
        "sources": {
            "events": "events.jsonl gate_result / waiver_created / rewind",
            "defects": "docs/knowledge/bar/BAR-*.md front matter",
        },
    }
    payload = {
        "ok": True,
        "kind": "metrics",
        "since": args.since,
        "specs": specs,
        "check_stats": sorted(check_stats.values(), key=lambda item: item["id"]),
        "quality": quality,
        "audit": {
            "valid": not audit_errors,
            "errors": audit_errors,
        },
        "aggregate": {
            "specs": len(specs),
            "median_lead_time_hours": (
                round(statistics.median(lead_times), 2) if lead_times else None
            ),
            "median_reworks": (
                round(statistics.median(reworks), 2) if reworks else 0.0
            ),
            "human_interventions": sum(
                item["human_interventions"] for item in specs
            ),
            "gate_failures": sum(item["gate_failures"] for item in specs),
            "checks": summarize_gate_checks(all_check_rows),
            "quality": quality,
        },
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    if not specs:
        print("[sdd] no specs found")
        return 0
    for item in specs:
        lead = item["lead_time_hours"]
        print(
            f"{item['spec']}  [{item['state']}]  "
            f"lead_time={lead if lead is not None else 'running'}h  "
            f"reworks={item['reworks']}  "
            f"human={item['human_interventions']}  "
            f"gate_failures={item['gate_failures']}"
        )
    aggregate = payload["aggregate"]
    print(
        f"[sdd] specs={aggregate['specs']}  "
        f"median_lead_time={aggregate['median_lead_time_hours']}h  "
        f"median_reworks={aggregate['median_reworks']}"
    )
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
            workflow = resolve_workflow(root, directory, state)
            contexts = waiver_contexts(directory, resolved_stage)
            checks = apply_check_waivers(
                stage_check_results(resolved_stage, errors, workflow),
                state,
                spec_id,
                contexts,
            )
            blocking, waived = partition_stage_errors(
                errors,
                resolved_stage,
                state,
                spec_id,
                directory,
            )
            if blocking:
                record_check_failure(directory, resolved_stage, blocking)
            results.append(
                {
                    "spec": spec_id,
                    "stage": resolved_stage,
                    "ok": not blocking,
                    "errors": blocking,
                    "waived": waived,
                    "checks": checks,
                    "summary": {
                        "pass": sum(item["result"] == "pass" for item in checks),
                        "warn": sum(item["result"] == "warn" for item in checks),
                        "block": sum(item["result"] == "block" for item in checks),
                        "waived": sum(item["result"] == "waived" for item in checks),
                    },
                }
            )
            if not args.json:
                if blocking:
                    print(f"[sdd] {spec_id} check failed (stage={resolved_stage})")
                    for error in blocking:
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
    workflow = resolve_workflow(root, directory, state)
    spec_id = str(state.get("spec_id", directory.name))
    contexts = waiver_contexts(directory, resolved_stage)
    checks = apply_check_waivers(
        stage_check_results(resolved_stage, errors, workflow),
        state,
        spec_id,
        contexts,
    )
    blocking, waived = partition_stage_errors(
        errors,
        resolved_stage,
        state,
        spec_id,
        directory,
    )
    if blocking:
        record_check_failure(directory, resolved_stage, blocking)
    if args.json:
        print(
            json.dumps(
                {
                    "ok": not blocking,
                    "stage": resolved_stage,
                    "errors": blocking,
                    "waived": waived,
                    "checks": checks,
                    "summary": {
                        "pass": sum(item["result"] == "pass" for item in checks),
                        "warn": sum(item["result"] == "warn" for item in checks),
                        "block": sum(item["result"] == "block" for item in checks),
                        "waived": sum(item["result"] == "waived" for item in checks),
                    },
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    elif blocking:
        print(f"[sdd] check failed (stage={resolved_stage})")
        for error in blocking:
            print(f"- {error}")
    else:
        print(f"[sdd] check passed (stage={resolved_stage})")
    return 1 if blocking else 0


def command_waive(
    args: argparse.Namespace, root: Path, config: dict[str, Any]
) -> int:
    if not getattr(args, "human", False):
        raise SddError("Gate 豁免是人工动作；必须显式传入 --human")
    spec_id, directory, state = resolve_spec(root, config, args.spec)
    check_id = str(args.check or "").strip()
    definition = EXT_CHECK_REGISTRY.get(check_id)
    if definition is None:
        raise SddError(f"未知检查 ID：{check_id}")
    if check_id in SECURITY_CHECK_IDS or not definition.get("waivable"):
        reason = "安全红线" if check_id in SECURITY_CHECK_IDS else "不允许豁免"
        append_audit_event(
            directory,
            {
                "event": "waiver_rejected",
                "check_id": check_id,
                "reason": reason,
                "requested_scope": args.scope,
                **history_meta(),
            },
        )
        raise SddError(f"{check_id} 属于{reason}，拒绝创建豁免")
    expires = parse_timestamp(args.expires_at)
    if expires is None:
        raise SddError("--expires-at 需要 ISO 日期或日期时间，例如 2026-12-31")
    if expires <= datetime.now().astimezone():
        raise SddError("--expires-at 必须是未来时间")
    approver = resolve_approver(root, args.approver)
    if config.get("require_approver") and approver == "unknown":
        raise SddError("require_approver=true；请用 --approver 提供审批人")
    waivers = state.setdefault("waivers", [])
    if not isinstance(waivers, list):
        raise SddError("state.json.waivers 不是数组；请修复状态文件")
    next_number = max(
        (
            int(str(item.get("id", "")).lstrip("W-") or 0)
            for item in waivers
            if isinstance(item, dict)
        ),
        default=0,
    ) + 1
    gate = str(definition.get("gate") or "")
    artifacts = gate_artifact_entries(root, directory, gate)
    artifact_contexts = [
        f"artifact:{item['path']}:{item['sha256']}"
        for item in artifacts
    ]
    record = {
        "id": f"W-{next_number:03d}",
        "check_id": check_id,
        "gate": gate,
        "spec": spec_id,
        "scope": str(args.scope or "spec").strip(),
        "artifacts": artifacts,
        "artifact_contexts": artifact_contexts,
        "reason": str(args.reason or "").strip(),
        "approver": approver,
        "at": now(),
        "created_at": now(),
        "expires_at": str(args.expires_at),
        "evidence": str(args.evidence or "").strip(),
    }
    for field in WAIVER_REQUIRED_FIELDS:
        if not str(record.get(field) or "").strip():
            flag = {
                "scope": "--scope",
                "reason": "--reason",
                "expires_at": "--expires-at",
                "evidence": "--evidence",
            }.get(field, field)
            raise SddError(f"豁免字段 {flag} 不能为空")
    waivers.append(record)
    add_history(
        state,
        str(state.get("state") or ""),
        f"waiver {check_id} until {record['expires_at']}",
        action="waiver",
        check_id=check_id,
        gate=gate,
        expires_at=record["expires_at"],
        role="approver",
        actor="human",
        approver=approver,
    )
    state.setdefault("approvals", []).append(
        {
            "action": "waiver",
            **record,
        }
    )
    state["last_approver"] = approver
    append_audit_event(
        directory,
        {
            "event": "waiver_created",
            "waiver": record,
            "role": "approver",
            **history_meta(),
        },
    )
    save_state(directory, state)
    payload = {
        "ok": True,
        "kind": "waiver",
        "spec": spec_id,
        "check": check_id,
        "gate": gate,
        "expires_at": record["expires_at"],
        "waiver": record,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(
            f"[sdd] {spec_id} waiver {record['id']} created for "
            f"{check_id} until {record['expires_at']}"
        )
    return 0


def command_index(
    args: argparse.Namespace, root: Path, config: dict[str, Any]
) -> int:
    spec_id, directory, state = resolve_spec(root, config, args.spec)
    spec_text = read_text(directory / "spec.md")
    message = sync_feat_map(root, config, state, spec_text)
    if args.json:
        print(
            json.dumps(
                {"ok": True, "kind": "index", "spec": spec_id, "message": message},
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print(f"[sdd] {spec_id} index synced: {message}")
    return 0


APPROVAL_ACTIVE_STATES = (
    "SPEC_READY",
    "DESIGN_READY",
    "TASKS_READY",
    "IMPLEMENTING",
    "VERIFYING",
    "PR_READY",
)

CHANGE_STATUSES = {"pending", "approved", "docs-only"}

CHANGE_FIELD_KEYS = {
    "status": "status",
    "reason": "reason",
    "created-at": "created_at",
    "impact-feat": "feat",
    "impact-fr": "fr",
    "impact-ac": "ac",
    "impact-task": "task",
    "impact-tests": "tests",
    "impact-code-paths": "code_paths",
    "risk": "risk",
    "rollback": "rollback",
    "approval": "approval",
    "approved-by": "approved_by",
    "approved-at": "approved_at",
    "approved-spec-digest": "approved_spec_digest",
}

CHANGE_REQUIRED_FIELDS = (
    "status",
    "reason",
    "feat",
    "fr",
    "ac",
    "task",
    "tests",
    "code_paths",
    "risk",
    "rollback",
    "approval",
)


def change_set_path(directory: Path) -> Path:
    return directory / "change-set.md"


def split_change_refs(value: str) -> list[str]:
    items: list[str] = []
    for raw in re.split(r"[,，、;；]+", str(value or "")):
        item = raw.strip().strip("`").strip()
        if item and item not in {"-", "—"}:
            items.append(item)
    return items


def parse_change_set(text: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    current: Optional[dict[str, Any]] = None
    for line in text.splitlines():
        heading = re.match(r"^##\s+(CHG-\d{3})\b\s*(.*)$", line.strip())
        if heading:
            current = {
                "id": heading.group(1),
                "title": heading.group(2).strip(),
                "fields": {},
            }
            records.append(current)
            continue
        if current is None:
            continue
        match = re.match(r"^\s*-\s*([A-Za-z0-9-]+)\s*:\s*(.*)$", line)
        if match:
            key = match.group(1).strip().lower()
            current["fields"][key] = match.group(2).strip()
    parsed: list[dict[str, Any]] = []
    for record in records:
        fields = record["fields"]
        item: dict[str, Any] = {
            "id": record["id"],
            "title": record["title"],
        }
        for raw_key, value in fields.items():
            key = CHANGE_FIELD_KEYS.get(raw_key)
            if key and key not in item:
                if key in {"feat", "fr", "ac", "task", "tests", "code_paths"}:
                    item[key] = split_change_refs(value)
                else:
                    item[key] = value
        for key in CHANGE_REQUIRED_FIELDS:
            item.setdefault(key, [] if key in {
                "feat", "fr", "ac", "task", "tests", "code_paths"
            } else "")
        parsed.append(item)
    return parsed


def change_set_records(directory: Path) -> list[dict[str, Any]]:
    path = change_set_path(directory)
    if not path.is_file():
        return []
    return parse_change_set(read_text(path))


def pending_change_records(directory: Path) -> list[dict[str, Any]]:
    return [
        record
        for record in change_set_records(directory)
        if str(record.get("status")) == "pending"
    ]


def docs_only_change_records(directory: Path) -> list[dict[str, Any]]:
    return [
        record
        for record in change_set_records(directory)
        if str(record.get("status")) == "docs-only"
    ]


def current_spec_digest(directory: Path) -> str:
    path = directory / "spec.md"
    if not path.is_file():
        return ""
    return artifact_sha256(path)


def approval_digest_errors(
    root: Path,
    directory: Path,
    state: dict[str, Any],
) -> list[str]:
    state_name = str(state.get("state") or "")
    if state_name in {"DRAFT", "MERGED"}:
        return []
    spec_id = str(state.get("spec_id") or directory.name)
    expected = str(state.get("approved_spec_digest") or "").strip()
    relative = (directory / "spec.md").relative_to(root).as_posix()
    if not expected:
        return [
            f"G1-08 旧 Spec {spec_id} 缺少审批版本绑定"
            f"（approved_spec_digest）；请人类执行 "
            f"`python -m sdd reapprove --spec {spec_id} --human "
            f"--reason legacy-migration --evidence \"迁移审批版本\"`"
        ]
    actual = current_spec_digest(directory)
    if not actual:
        return [f"G1-08 审批绑定的 Spec 文件不存在：{relative}"]
    if actual != expected:
        return [
            f"G1-08 Spec {spec_id} 在审批后被修改"
            f"（审批摘要 {expected[:12]}…，当前 {actual[:12]}…）；"
            f"请先执行 `python -m sdd change --spec {spec_id} "
            f"--reason \"...\"` 登记变更，再由人类执行 "
            f"`python -m sdd reapprove --spec {spec_id} --human "
            f"--reason \"...\" --evidence \"...\"`"
        ]
    return []


def change_set_errors(
    root: Path,
    directory: Path,
    state: dict[str, Any],
) -> list[str]:
    state_name = str(state.get("state") or "")
    if state_name in {"DRAFT", "MERGED"}:
        return []
    pending = pending_change_records(directory)
    if not pending:
        return []
    spec_id = str(state.get("spec_id") or directory.name)
    ids = ", ".join(str(record["id"]) for record in pending)
    return [
        f"G1-09 存在未批准的 change-set：{ids}；"
        f"请先更新文档与 change-set，再由人类执行 "
        f"`python -m sdd reapprove --spec {spec_id} --human "
        f"--reason \"...\" --evidence \"...\"`"
    ]


def active_approval_specs(
    root: Path, config: dict[str, Any]
) -> list[tuple[Path, dict[str, Any]]]:
    base = spec_root(root, config)
    if not base.is_dir():
        return []
    active: list[tuple[Path, dict[str, Any]]] = []
    for directory in sorted(base.iterdir()):
        if not directory.is_dir():
            continue
        state_path = directory / "state.json"
        if not state_path.is_file():
            continue
        state = load_json(state_path)
        if str(state.get("state") or "") in APPROVAL_ACTIVE_STATES:
            active.append((directory, state))
    return active


def test_selectors_from_tasks(tasks: list[dict[str, Any]]) -> list[str]:
    selectors: list[str] = []
    for task in tasks:
        for item in split_change_refs(str(task.get("test") or "")):
            if item and item not in selectors:
                selectors.append(item)
    return selectors


def build_impact(
    root: Path,
    config: dict[str, Any],
    directory: Path,
    state: dict[str, Any],
) -> dict[str, Any]:
    spec_text = read_text(directory / "spec.md")
    design_text = read_text(directory / "design.md")
    tasks_text = read_text(directory / "tasks.md")
    tasks = parse_tasks(tasks_text)
    feat_ids = sorted(set(FEAT_RE.findall(spec_text)))
    fr_ids = sorted(set(extract_frs(spec_text)))
    ac_ids = sorted(set(extract_acs(spec_text)))
    task_ids = [str(task["id"]) for task in tasks]
    test_selectors = test_selectors_from_tasks(tasks)
    code_paths = sorted(
        set(
            [
                *declared_code_paths(tasks_text),
                *declared_code_paths(design_text),
                *declared_code_paths(spec_text),
            ]
        )
    )
    records = change_set_records(directory)
    pending_ids = [
        str(record["id"])
        for record in records
        if str(record.get("status")) == "pending"
    ]
    actual = current_spec_digest(directory)
    expected = str(state.get("approved_spec_digest") or "")
    digest_changed = bool(
        expected
        and actual
        and expected != actual
    ) or (
        str(state.get("state") or "") not in {"DRAFT", "MERGED"}
        and not expected
    )
    missing: list[str] = []
    for task in tasks:
        for fr in task.get("frs", []):
            if fr not in fr_ids:
                missing.append(fr)
        for ac in task.get("acs", []):
            if ac not in ac_ids:
                missing.append(ac)
    for record in records:
        for feat in record.get("feat", []):
            if feat not in feat_ids:
                missing.append(feat)
        for fr in record.get("fr", []):
            if fr not in fr_ids:
                missing.append(fr)
        for ac in record.get("ac", []):
            if ac not in ac_ids:
                missing.append(ac)
        for task_id in record.get("task", []):
            if task_id not in task_ids:
                missing.append(task_id)
    spec_id = str(state.get("spec_id") or directory.name)
    relative_change_set = (
        change_set_path(directory).relative_to(root).as_posix()
    )
    return {
        "schema": 1,
        "spec": spec_id,
        "feat_ids": feat_ids,
        "fr_ids": fr_ids,
        "ac_ids": ac_ids,
        "task_ids": task_ids,
        "test_selectors": test_selectors,
        "code_paths": code_paths,
        "approval_required": bool(pending_ids or digest_changed),
        "digest_changed": digest_changed,
        "approved_spec_digest": expected or None,
        "current_spec_digest": actual or None,
        "pending_change_ids": pending_ids,
        "missing": sorted(set(missing)),
        "change_set": relative_change_set,
    }


def render_change_record(record: dict[str, Any]) -> str:
    def joined(key: str) -> str:
        values = record.get(key) or []
        if not values:
            return "-"
        if key in {"tests", "code_paths"}:
            return ", ".join(f"`{value}`" for value in values)
        return ", ".join(str(value) for value in values)

    title = str(record.get("title") or "").strip()
    heading = f"## {record['id']}" + (f" {title}" if title else "")
    return "\n".join(
        [
            heading,
            f"- Status: {record.get('status') or 'pending'}",
            f"- Reason: {record.get('reason') or '-'}",
            f"- Created-At: {record.get('created_at') or now()}",
            f"- Impact-FEAT: {joined('feat')}",
            f"- Impact-FR: {joined('fr')}",
            f"- Impact-AC: {joined('ac')}",
            f"- Impact-Task: {joined('task')}",
            f"- Impact-Tests: {joined('tests')}",
            f"- Impact-Code-Paths: {joined('code_paths')}",
            f"- Risk: {record.get('risk') or 'low'}",
            f"- Rollback: {record.get('rollback') or '-'}",
            f"- Approval: {record.get('approval') or 'pending'}",
            f"- Approved-By: {record.get('approved_by') or '-'}",
            f"- Approved-At: {record.get('approved_at') or '-'}",
            "- Approved-Spec-Digest: "
            + (record.get("approved_spec_digest") or "-"),
        ]
    )


def render_change_set(records: list[dict[str, Any]]) -> str:
    lines = [
        "# 变更集（Change Set）",
        "",
        "> 本文件由 `python -m sdd change` 生成或更新；审批状态由人工 "
        "`reapprove` 回写。",
        "",
    ]
    for record in records:
        lines.append(render_change_record(record))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def validate_change_record(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in CHANGE_REQUIRED_FIELDS:
        value = record.get(key)
        if isinstance(value, list):
            if not value and key in {"feat", "fr", "ac"}:
                errors.append(f"{record.get('id', 'CHG')} 缺少字段：{key}")
        elif not str(value or "").strip():
            errors.append(f"{record.get('id', 'CHG')} 缺少字段：{key}")
    return errors


def approve_pending_changes(
    directory: Path,
    approver: str,
    digest: str,
    reason: str,
) -> list[str]:
    records = change_set_records(directory)
    approved: list[str] = []
    changed = False
    for record in records:
        if str(record.get("status")) != "pending":
            continue
        record["status"] = "approved"
        record["approval"] = "approved"
        record["approved_by"] = approver
        record["approved_at"] = now()
        record["approved_spec_digest"] = digest
        record["reason"] = record.get("reason") or reason
        approved.append(str(record["id"]))
        changed = True
    if changed:
        write_text(change_set_path(directory), render_change_set(records))
    return approved


def refresh_approval_reports(
    root: Path,
    config: dict[str, Any],
    directory: Path,
    state: dict[str, Any],
    evidence: str,
    approver: str,
    g0_rows: list[dict[str, Any]],
    g1_rows: list[dict[str, Any]],
) -> None:
    state_name = str(state.get("state") or "SPEC_READY")
    workflow = resolve_workflow(root, directory, state)
    for gate, rows in (("G0", g0_rows), ("G1", g1_rows)):
        checks = [
            (
                f"{row['id']} {row['name']}",
                "PASS" if row["result"] == "pass" else "FAILED",
                str(row["detail"]),
            )
            for row in rows
        ]
        write_gate_report(
            root,
            config,
            directory,
            state,
            gate,
            state_name,
            "manual",
            evidence,
            checks,
            [],
            approver,
        )
        hashes: dict[str, str] = {}
        for name in GATE_ARTIFACTS.get(gate, ()):
            relative, digest, _ = artifact_digest(root, directory, name)
            if digest != "MISSING":
                hashes[relative] = digest
        if hashes:
            state.setdefault("artifact_hashes", {})[gate] = hashes
    _ = workflow


def command_impact(
    args: argparse.Namespace, root: Path, config: dict[str, Any]
) -> int:
    spec_id, directory, state = resolve_spec(root, config, args.spec)
    payload = build_impact(root, config, directory, state)
    payload["ok"] = True
    payload["kind"] = "impact"
    if getattr(args, "json", False):
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"[sdd] {spec_id} impact")
        print(
            "  FEAT=" + (", ".join(payload["feat_ids"]) or "-")
            + "  FR=" + (", ".join(payload["fr_ids"]) or "-")
            + "  AC=" + str(len(payload["ac_ids"]))
        )
        print(
            "  Tasks=" + (", ".join(payload["task_ids"]) or "-")
            + "  approval_required="
            + str(payload["approval_required"]).lower()
        )
        if payload["missing"]:
            print("  missing=" + "; ".join(payload["missing"]))
    return 0


def command_change(
    args: argparse.Namespace, root: Path, config: dict[str, Any]
) -> int:
    spec_id, directory, state = resolve_spec(root, config, args.spec)
    current = str(state.get("state") or "DRAFT")
    if current == "DRAFT":
        raise SddError("Spec 还没有审批；先由人类执行 approve 再登记 change-set")
    if current == "MERGED":
        raise SddError("MERGED Spec 不允许新建 change-set")
    reason = str(args.reason or "").strip()
    if not reason:
        raise SddError("change 需要非空 --reason")
    impact = build_impact(root, config, directory, state)
    if impact["missing"]:
        raise SddError(
            "change-set 引用了不存在的对象："
            + "; ".join(impact["missing"])
        )
    records = change_set_records(directory)
    next_number = 1 + max(
        [
            int(str(record["id"]).split("-")[1])
            for record in records
            if re.fullmatch(r"CHG-\d{3}", str(record["id"]))
        ]
        or [0]
    )
    change_id = f"CHG-{next_number:03d}"
    docs_only = bool(getattr(args, "docs_only", False))
    record: dict[str, Any] = {
        "id": change_id,
        "title": "纯文档/配置变更" if docs_only else "",
        "status": "docs-only" if docs_only else "pending",
        "reason": reason,
        "created_at": now(),
        "feat": impact["feat_ids"],
        "fr": impact["fr_ids"],
        "ac": impact["ac_ids"],
        "task": impact["task_ids"],
        "tests": impact["test_selectors"],
        "code_paths": impact["code_paths"],
        "risk": getattr(args, "risk", None) or state.get("risk") or "low",
        "rollback": getattr(args, "rollback", None)
        or "回退本次变更相关 commit",
        "approval": "exempt" if docs_only else "pending",
        "approved_by": "",
        "approved_at": "",
        "approved_spec_digest": "",
    }
    errors = validate_change_record(record)
    if errors:
        raise SddError("change-set 字段不完整：" + "; ".join(errors))
    records.append(record)
    path = change_set_path(directory)
    write_text(path, render_change_set(records))
    append_audit_event(
        directory,
        {
            "event": "change_recorded",
            "change_id": change_id,
            "status": record["status"],
            "reason": reason,
            "actor": "agent",
            "role": "implementer",
        },
    )
    payload = {
        "ok": True,
        "kind": "change",
        "spec": spec_id,
        "change_id": change_id,
        "status": record["status"],
        "approval_required": not docs_only,
        "change_set": path.relative_to(root).as_posix(),
    }
    if getattr(args, "json", False):
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(
            f"[sdd] {spec_id} change {change_id} "
            f"status={record['status']}"
        )
    return 0


def command_reapprove(
    args: argparse.Namespace, root: Path, config: dict[str, Any]
) -> int:
    spec_id, directory, state = resolve_spec(root, config, args.spec)
    current = str(state.get("state") or "DRAFT")
    if current == "DRAFT":
        raise SddError("DRAFT Spec 需要先执行 approve，不能直接 reapprove")
    if current == "MERGED":
        raise SddError("MERGED Spec 不允许 reapprove")
    if not args.human:
        raise SddError(
            "reapprove 需要 --human；agent 不允许代替人类重新确认需求"
        )
    reason = str(args.reason or "").strip()
    evidence = str(args.evidence or "").strip()
    if not reason:
        raise SddError("reapprove 需要非空 --reason")
    if not evidence:
        raise SddError("reapprove 需要非空 --evidence")
    approver = resolve_approver(root, getattr(args, "approver", None))
    if config.get("require_approver") and approver == "unknown":
        raise SddError("require_approver=true；请用 --approver 提供审批人")
    spec_text = read_text(directory / "spec.md")
    sync_feat_map(root, config, state, spec_text)
    workflow = resolve_workflow(root, directory, state)
    ctx = gate_context(root, config, directory, state)
    g0_rows = run_gate_checks("G0", ctx, workflow)
    g1_rows = run_gate_checks("G1", ctx, workflow)
    errors = list(gate_rows_errors(g0_rows)) + list(gate_rows_errors(g1_rows))
    errors.extend(
        check_prd_index(root, config, state, spec_text, require_feat=True)
    )
    if errors:
        for error in errors:
            eprint(f"- {error}")
        record_check_failure(directory, "spec", errors, gate="G0/G1")
        raise SddError("reapprove 的 G0/G1 校验失败")
    spec_path = directory / "spec.md"
    digest = artifact_sha256(spec_path)
    previous = str(state.get("approved_spec_digest") or "")
    approved_at = now()
    state["approved_spec_digest"] = digest
    state["approved_at"] = approved_at
    state["approved_by"] = approver
    state["approval_evidence"] = evidence
    state.setdefault("approvals", []).append(
        {
            "action": "reapprove_spec",
            "approver": approver,
            "at": approved_at,
            "reason": reason,
            "evidence": evidence,
            "previous_digest": previous,
            "sha256": digest,
            "artifact": spec_path.relative_to(root).as_posix(),
        }
    )
    approved_changes = approve_pending_changes(
        directory, approver, digest, reason
    )
    state["last_approver"] = approver
    refresh_approval_reports(
        root,
        config,
        directory,
        state,
        evidence,
        approver,
        g0_rows,
        g1_rows,
    )
    save_state(directory, state)
    append_audit_event(
        directory,
        {
            "event": "reapprove_spec",
            "reason": reason,
            "evidence": evidence,
            "previous_digest": previous,
            "approved_spec_digest": digest,
            "approved_change_ids": approved_changes,
            "approver": approver,
            "actor": "human",
            "role": "approver",
        },
    )
    payload = {
        "ok": True,
        "kind": "reapprove",
        "spec": spec_id,
        "approved_spec_digest": digest,
        "approved_change_ids": approved_changes,
        "next": build_next_action(root, directory, state),
    }
    if getattr(args, "json", False):
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(
            f"[sdd] {spec_id} reapproved; "
            f"changes={', '.join(approved_changes) or '-'}"
        )
    return 0


def spec_directories(
    root: Path, config: dict[str, Any]
) -> list[Path]:
    base = spec_root(root, config)
    if not base.is_dir():
        return []
    return sorted(
        path
        for path in base.iterdir()
        if path.is_dir() and (path / "state.json").is_file()
    )


def resolve_trace_test(
    root: Path,
    config: dict[str, Any],
    selector: str,
) -> tuple[Optional[dict[str, Any]], list[str]]:
    parsed = parse_test_reference(selector)
    method = parsed["method"]
    if not method:
        return None, [f"无法解析测试选择器：{selector}"]
    files = collect_test_files(root, config)
    definitions = scan_test_definitions(
        [
            (path.relative_to(root).as_posix(), read_text(path))
            for path in files
        ]
    )
    candidates: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for record in definitions.values():
        key = (
            str(record.get("path") or ""),
            str(record.get("class") or ""),
            str(record.get("name") or ""),
        )
        if key in seen:
            continue
        seen.add(key)
        if record.get("name") != method:
            continue
        if parsed["class"] and record.get("class") != parsed["class"]:
            continue
        if parsed["file"] and not str(record.get("path") or "").endswith(
            parsed["file"]
        ):
            continue
        candidates.append(record)
    if not candidates:
        return None, [f"测试定义不存在：{selector}"]
    if len(candidates) > 1:
        return None, [f"测试选择器命中多个测试，请更精确：{selector}"]
    return candidates[0], []


def find_spec_for_acs(
    root: Path,
    config: dict[str, Any],
    acs: Iterable[str],
) -> tuple[Optional[tuple[Path, dict[str, Any]]], list[str]]:
    wanted = set(acs)
    matches: list[tuple[Path, dict[str, Any]]] = []
    for directory in spec_directories(root, config):
        state = load_json(directory / "state.json")
        spec_acs = set(extract_acs(read_text(directory / "spec.md")))
        if spec_acs & wanted:
            matches.append((directory, state))
    if not matches:
        return None, [
            "找不到包含 AC 的 Spec：" + ", ".join(sorted(wanted))
        ]
    if len(matches) > 1:
        return None, [
            "AC 命中多个 Spec，请改用 --commit 或更精确的入口："
            + ", ".join(str(state.get("spec_id")) for _, state in matches)
        ]
    return matches[0], []


def trace_commits(
    root: Path,
    config: dict[str, Any],
    spec_id: str,
) -> list[dict[str, Any]]:
    base, _ = resolve_merge_base(root)
    if not base:
        return []
    commits: list[dict[str, Any]] = []
    for sha in git_commits_since(root, base):
        _, record = audit_commit(root, config, sha)
        if record and record.get("spec_id") == spec_id:
            commits.append(record)
    return commits


def build_trace(
    root: Path,
    config: dict[str, Any],
    entry_type: str,
    entry_value: str,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema": 1,
        "kind": "trace",
        "ok": False,
        "entry": {"type": entry_type, "value": entry_value},
        "spec": None,
        "task": None,
        "acs": [],
        "feat": None,
        "work_item": None,
        "prd": {"path": "docs/prd-index.md", "registered": False},
        "approval": {
            "approved": False,
            "digest_bound": False,
            "approved_by": None,
            "approved_at": None,
        },
        "change_set": {"path": None, "records": []},
        "commits": [],
        "evidence": {"path": None, "records": []},
        "missing": [],
        "chain": [],
    }
    missing: list[dict[str, str]] = []
    acs: list[str] = []
    task_id = ""
    spec_choice: Optional[tuple[Path, dict[str, Any]]] = None
    if entry_type == "test":
        record, errors = resolve_trace_test(root, config, entry_value)
        if errors:
            missing.extend({"link": "test", "detail": e} for e in errors)
        elif record:
            acs = list(record.get("acs") or [])
            if not acs:
                missing.append(
                    {"link": "ac", "detail": "测试函数体内没有 AC 标签"}
                )
            payload["chain"].append(
                {
                    "link": "test",
                    "value": f"{record.get('path')}::{record.get('class')}#{record.get('name')}",
                }
            )
    elif entry_type == "ac":
        acs = [entry_value]
    elif entry_type == "commit":
        base, _ = resolve_merge_base(root)
        if not base:
            missing.append(
                {"link": "commit", "detail": "无法确定 merge-base"}
            )
        text = commit_body(root, entry_value)
        parsed = parse_commit_trailers(text)
        if len(parsed["spec_ids"]) != 1:
            missing.append(
                {
                    "link": "commit",
                    "detail": f"{entry_value} 没有唯一 Spec-Id",
                }
            )
        else:
            directory = spec_dir_for(
                root, config, parsed["spec_ids"][0]
            )
            if not (directory / "spec.md").is_file():
                missing.append(
                    {
                        "link": "spec",
                        "detail": parsed["spec_ids"][0],
                    }
                )
            else:
                spec_choice = (
                    directory,
                    load_json(directory / "state.json"),
                )
                task_id = (
                    parsed["task_ids"][0]
                    if len(parsed["task_ids"]) == 1
                    else ""
                )
                payload["chain"].append(
                    {"link": "commit", "value": entry_value}
                )
    if acs:
        payload["chain"].append(
            {"link": "ac", "value": ", ".join(sorted(set(acs)))}
        )
    if spec_choice is None and acs:
        spec_choice, errors = find_spec_for_acs(root, config, acs)
        missing.extend(
            {"link": "spec", "detail": error} for error in errors
        )
    if spec_choice is None:
        payload["missing"] = missing
        return payload
    directory, state = spec_choice
    spec_id = str(state.get("spec_id") or directory.name)
    spec_text = read_text(directory / "spec.md")
    tasks_text = read_text(directory / "tasks.md")
    tasks = parse_tasks(tasks_text)
    if not task_id:
        matched = [
            task
            for task in tasks
            if set(task.get("acs") or []) & set(acs)
        ]
        if matched:
            task_id = str(matched[0]["id"])
    task = next((item for item in tasks if item["id"] == task_id), None)
    if task is None:
        missing.append(
            {
                "link": "task",
                "detail": "找不到覆盖 AC 的 Task：" + ", ".join(acs),
            }
        )
    else:
        if not acs:
            acs = list(task.get("acs") or [])
        payload["chain"].append(
            {"link": "task", "value": task_id}
        )
    payload["spec"] = spec_id
    payload["task"] = task_id or None
    payload["acs"] = sorted(set(acs))
    payload["feat"] = metadata_value(spec_text, "FEAT ID", "FEATID", "FEAT")
    payload["work_item"] = metadata_value(
        spec_text, "工作项 ID", "工作项ID"
    )
    payload["chain"].append({"link": "spec", "value": spec_id})
    payload["chain"].append({"link": "feat", "value": payload["feat"]})
    payload["chain"].append(
        {"link": "work_item", "value": payload["work_item"]}
    )
    rows = prd_index_rows(read_text(prd_index_path(root, config)))
    payload["prd"]["registered"] = any(
        row.get("specid") == spec_id
        and row.get("工作项id", row.get("workitemid", ""))
        == payload["work_item"]
        for row in rows
    )
    if not payload["prd"]["registered"]:
        missing.append(
            {"link": "prd", "detail": "docs/prd-index.md 未登记当前 Spec"}
        )
    approvals = [
        item
        for item in state.get("approvals", [])
        if isinstance(item, dict)
        and item.get("action") in {"approve_spec", "reapprove_spec"}
    ]
    payload["approval"] = {
        "approved": bool(approvals),
        "digest_bound": bool(
            state.get("approved_spec_digest")
            and current_spec_digest(directory)
            == state.get("approved_spec_digest")
        ),
        "approved_by": state.get("approved_by"),
        "approved_at": state.get("approved_at"),
    }
    if not approvals:
        missing.append(
            {"link": "approval", "detail": "缺少 approve/reapprove 记录"}
        )
    elif not payload["approval"]["digest_bound"]:
        missing.append(
            {
                "link": "approval",
                "detail": "审批摘要与当前 Spec 不一致",
            }
        )
    payload["chain"].append(
        {
            "link": "approval",
            "value": payload["approval"]["approved_by"] or "-",
        }
    )
    change_path = change_set_path(directory)
    payload["change_set"] = {
        "path": change_path.relative_to(root).as_posix(),
        "records": change_set_records(directory),
    }
    payload["chain"].append(
        {
            "link": "change_set",
            "value": payload["change_set"]["path"],
        }
    )
    payload["commits"] = trace_commits(root, config, spec_id)
    if not payload["commits"]:
        missing.append(
            {"link": "commit", "detail": "merge-base 后没有关联 commit"}
        )
    for record in payload["commits"]:
        payload["chain"].append(
            {"link": "commit", "value": record["short"]}
        )
    evidence_file = evidence_path(directory)
    records, _ = load_verification_evidence(directory)
    filtered = [
        record
        for record in records
        if str(record.get("spec") or "") == spec_id
        and (
            not task_id
            or str(record.get("task") or "") in {"", task_id}
        )
    ]
    payload["evidence"] = {
        "path": evidence_file.relative_to(root).as_posix(),
        "records": filtered,
    }
    payload["chain"].append(
        {
            "link": "evidence",
            "value": f"{len(filtered)} record(s)",
        }
    )
    if not filtered:
        missing.append(
            {"link": "evidence", "detail": "缺少 verification-evidence 记录"}
        )
    payload["missing"] = missing
    payload["ok"] = not missing
    return payload


def command_trace(
    args: argparse.Namespace, root: Path, config: dict[str, Any]
) -> int:
    entry_type = ""
    entry_value = ""
    for name in ("test", "ac", "commit"):
        value = getattr(args, name, None)
        if value:
            entry_type = name
            entry_value = str(value)
            break
    if not entry_type:
        raise SddError("trace 需要 --test、--ac 或 --commit 之一")
    payload = build_trace(root, config, entry_type, entry_value)
    if getattr(args, "json", False):
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(
            f"[sdd] trace {entry_type}={entry_value} "
            f"ok={str(payload['ok']).lower()}"
        )
        for item in payload["chain"]:
            print(f"  {item['link']}: {item['value']}")
        for item in payload["missing"]:
            print(f"  missing {item['link']}: {item['detail']}")
    return 0 if payload["ok"] else 1


def command_approve(
    args: argparse.Namespace, root: Path, config: dict[str, Any]
) -> int:
    spec_id, directory, state = resolve_spec(root, config, args.spec)
    workflow = resolve_workflow(root, directory, state)
    if state.get("state") != "DRAFT":
        raise SddError(f"只有 DRAFT 状态可以 approve，当前是 {state.get('state')}")
    if not args.human:
        raise SddError("approve 需要 --human；agent 不允许代替人类确认需求")
    approver = resolve_approver(root, getattr(args, "approver", None))
    if config.get("require_approver") and approver == "unknown":
        raise SddError(
            "require_approver=true；请用 --approver 提供审批人"
        )
    evidence = args.evidence or "requirement confirmed by human"
    sync_feat_map(root, config, state, read_text(directory / "spec.md"))
    ctx = gate_context(root, config, directory, state)
    g0_rows = run_gate_checks("G0", ctx, workflow)
    g1_rows = run_gate_checks("G1", ctx, workflow)
    g0_errors = gate_rows_errors(g0_rows)
    g1_errors = gate_rows_errors(g1_rows)
    spec_text = read_text(directory / "spec.md")
    errors = list(g0_errors) + list(g1_errors)
    errors.extend(
        check_prd_index(
            root,
            config,
            state,
            spec_text,
            require_feat=True,
        )
    )
    try:
        g1_mode = gate_mode(config, "G1", state, False, workflow)
    except SddError:
        g1_mode = "manual"
    if errors:
        for error in errors:
            eprint(f"- {error}")
        record_check_failure(directory, "spec", errors, gate="G0/G1")
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
            (
                f"{row['id']} {row['name']}",
                "PASS" if row["result"] == "pass" else "FAILED",
                str(row["detail"]),
            )
            for row in g0_rows
        ],
        g0_errors,
        approver,
    )
    record_gate(
        root,
        config,
        directory,
        state,
        "G1",
        "SPEC_READY",
        g1_mode,
        "spec check passed" if not g1_errors else "spec check failed",
        [
            (
                f"{row['id']} {row['name']}",
                "PASS" if row["result"] == "pass" else "FAILED",
                str(row["detail"]),
            )
            for row in g1_rows
        ],
        g1_errors,
        approver if g1_mode == "manual" else None,
    )
    if g0_errors or g1_errors:
        raise SddError("spec 校验失败，不能 approve")
    spec_path = directory / "spec.md"
    approved_at = now()
    approved_digest = artifact_sha256(spec_path) if spec_path.is_file() else ""
    state["approved_spec_digest"] = approved_digest
    state["approved_at"] = approved_at
    state["approved_by"] = approver
    state["approval_evidence"] = evidence
    state.setdefault("approvals", []).append(
        {
            "action": "approve_spec",
            "approver": approver,
            "at": approved_at,
            "artifact": spec_path.relative_to(root).as_posix(),
            "sha256": approved_digest,
        }
    )
    state["last_approver"] = approver
    if g1_mode == "manual":
        record_gate_approval(
            root, directory, state, "G1", approver, "spec check passed"
        )
    transition(
        state,
        "SPEC_READY",
        evidence,
        gate="G0/G1",
        actor="human",
        role="approver",
        approver=approver,
        artifacts=gate_artifact_entries(root, directory, "G1"),
    )
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
    section = list(lines[start:end])
    while section and not section[-1].strip():
        section.pop()
    after = lines[end:]
    merged = before + section + [""] + content.strip().splitlines() + [""] + after
    return "\n".join(merged).rstrip() + "\n"


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
    workflow = resolve_workflow(root, directory, state)
    evidence = args.evidence.strip()
    if not evidence:
        raise SddError("complete 需要 --evidence，记录实际做了什么/检查了什么")
    approver = (
        resolve_approver(root, getattr(args, "approver", None))
        if args.human
        else None
    )
    actor = "human" if args.human else "agent"
    if args.human and config.get("require_approver") and approver == "unknown":
        raise SddError(
            "require_approver=true；请用 --approver 提供审批人"
        )

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
        add_history(
            state,
            "IMPLEMENTING",
            evidence,
            action="task_done",
            task=args.task,
            commit=args.commit,
            role="implementer",
        )
        tasks = parse_tasks(updated)
        save_state(directory, state)
        if tasks and all(task["done"] for task in tasks):
            human_required = gate_requires_human(
                config, "G4", state, workflow
            )
            mode = (
                "manual"
                if human_required and not args.human
                else gate_mode(config, "G4", state, args.human, workflow)
            )
            verification_text = read_text(directory / "verification.md")
            missing_evidence = [
                task["id"] for task in tasks if task["id"] not in verification_text
            ]
            errors = []
            if missing_evidence:
                errors.append(
                    "以下 Task 没有验证证据：" + ", ".join(missing_evidence)
                )
            errors.extend(
                check_review_evidence(directory, state, workflow)
            )
            errors.extend(task_table_error(tasks, check_spec(
                read_text(directory / "spec.md"), spec_id
            )[1], config))
            contexts = waiver_contexts(directory, "tasks")
            blocking, waived = partition_waived_errors(
                errors,
                "G4",
                state,
                spec_id,
                contexts,
            )
            if blocking:
                record_check_failure(directory, "tasks", blocking, gate="G4")
                record_gate(
                    root,
                    config,
                    directory,
                    state,
                    "G4",
                    "VERIFYING",
                    mode,
                    evidence,
                    [],
                    errors,
                    approver,
                )
                for error in blocking:
                    eprint(f"- {error}")
                save_state(directory, state)
                raise SddError("Gate 4 校验失败")
            if human_required and not args.human:
                print(
                    f"[sdd] {spec_id} task {args.task} completed; "
                    f"G4 awaits human approval"
                )
                print(
                    f"[sdd] next: python -m sdd complete --spec {spec_id} "
                    '--human --evidence "代码评审通过"'
                )
                return 0
            if mode == "manual" and approver:
                record_gate_approval(
                    root, directory, state, "G4", approver, evidence
                )
            record_gate(
                root,
                config,
                directory,
                state,
                "G4",
                "VERIFYING",
                mode,
                "all tasks completed",
                [],
                errors,
                approver=approver if mode == "manual" else None,
            )
            transition(
                state,
                resolve_declared_transition(workflow, "VERIFYING"),
                "all tasks completed",
                gate="G4",
                actor=actor,
                role="implementer",
                approver=approver,
                artifacts=gate_artifact_entries(root, directory, "G4"),
            )
        save_state(directory, state)
        print(f"[sdd] {spec_id} task {args.task} completed -> {state['state']}")
        return 0

    current = str(state.get("state", "DRAFT"))
    if current == "DRAFT":
        raise SddError(
            "DRAFT 状态需要人类运行 `python -m sdd approve --human --evidence ...`"
        )
    if current == "SPEC_READY":
        errors, _ = run_checks(root, config, directory, state, "design")
        contexts = waiver_contexts(directory, "design")
        blocking, waived = partition_waived_errors(
            errors,
            "G2",
            state,
            spec_id,
            contexts,
        )
        if blocking:
            for error in blocking:
                eprint(f"- {error}")
            record_check_failure(directory, "design", blocking, gate="G2")
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
                approver,
            )
            raise SddError("design 校验失败")
        mode = gate_mode(config, "G2", state, args.human, workflow)
        if mode == "manual" and approver:
            record_gate_approval(root, directory, state, "G2", approver, evidence)
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
            errors,
            approver=approver if mode == "manual" else None,
        )
        transition(
            state,
            resolve_declared_transition(workflow, "DESIGN_READY"),
            evidence,
            gate="G2",
            actor=actor,
            role="designer",
            approver=approver,
            artifacts=gate_artifact_entries(root, directory, "G2"),
        )
    elif current == "DESIGN_READY":
        errors, _ = run_checks(root, config, directory, state, "tasks")
        contexts = waiver_contexts(directory, "tasks")
        blocking, waived = partition_waived_errors(
            errors,
            "G3",
            state,
            spec_id,
            contexts,
        )
        if blocking:
            for error in blocking:
                eprint(f"- {error}")
            record_check_failure(directory, "tasks", blocking, gate="G3")
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
                approver,
            )
            raise SddError("tasks 校验失败")
        mode = gate_mode(config, "G3", state, args.human, workflow)
        if mode == "manual" and approver:
            record_gate_approval(root, directory, state, "G3", approver, evidence)
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
            approver=approver if mode == "manual" else None,
        )
        transition(
            state,
            resolve_declared_transition(workflow, "TASKS_READY"),
            evidence,
            gate="G3",
            actor=actor,
            role="planner",
            approver=approver,
            artifacts=gate_artifact_entries(root, directory, "G3"),
        )
    elif current == "TASKS_READY":
        errors, _ = run_checks(root, config, directory, state, "tasks")
        contexts = waiver_contexts(directory, "tasks")
        blocking, waived = partition_waived_errors(
            errors,
            "G3",
            state,
            spec_id,
            contexts,
        )
        if blocking:
            for error in blocking:
                eprint(f"- {error}")
            record_check_failure(directory, "tasks", blocking, gate="G3")
            raise SddError("tasks 校验失败")
        if gate_report_status(
            gate_report_path(root, config, spec_id, "G3")
        ) != "PASS":
            mode = gate_mode(config, "G3", state, args.human, workflow)
            if mode == "manual" and approver:
                record_gate_approval(
                    root, directory, state, "G3", approver, evidence
                )
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
                approver=approver if mode == "manual" else None,
            )
        transition(
            state,
            resolve_declared_transition(workflow, "IMPLEMENTING"),
            evidence,
            actor=actor,
            role="implementer",
        )
    elif current == "IMPLEMENTING":
        tasks = parse_tasks(read_text(directory / "tasks.md"))
        if not tasks or not all(task["done"] for task in tasks):
            raise SddError("还有未完成的 task；用 `sdd complete --task T-xxx` 逐个完成")
        mode = gate_mode(config, "G4", state, args.human, workflow)
        verification_text = read_text(directory / "verification.md")
        missing_evidence = [
            task["id"] for task in tasks if task["id"] not in verification_text
        ]
        errors, _ = run_checks(root, config, directory, state, "tasks")
        if missing_evidence:
            errors.append("以下 Task 没有验证证据：" + ", ".join(missing_evidence))
        contexts = waiver_contexts(directory, "tasks")
        blocking, waived = partition_waived_errors(
            errors,
            "G4",
            state,
            spec_id,
            contexts,
        )
        if blocking:
            record_check_failure(directory, "tasks", blocking, gate="G4")
            record_gate(
                root,
                config,
                directory,
                state,
                "G4",
                "VERIFYING",
                mode,
                evidence,
                [],
                errors,
                approver,
            )
            for error in blocking:
                eprint(f"- {error}")
            raise SddError("Gate 4 校验失败")
        if mode == "manual" and approver:
            record_gate_approval(root, directory, state, "G4", approver, evidence)
        record_gate(
            root,
            config,
            directory,
            state,
            "G4",
            "VERIFYING",
            mode,
            evidence,
            [],
            errors,
            approver=approver if mode == "manual" else None,
        )
        transition(
            state,
            resolve_declared_transition(workflow, "VERIFYING"),
            evidence,
            gate="G4",
            actor=actor,
            role="implementer",
            approver=approver,
            artifacts=gate_artifact_entries(root, directory, "G4"),
        )
    elif current == "VERIFYING":
        errors, _ = run_checks(root, config, directory, state, "verify")
        errors.extend(
            check_gates(root, config, directory, "VERIFYING")
        )
        contexts = waiver_contexts(directory, "verify")
        blocking, waived = partition_waived_errors(
            errors,
            "G5",
            state,
            spec_id,
            contexts,
        )
        if blocking:
            for error in blocking:
                eprint(f"- {error}")
            record_check_failure(directory, "verify", blocking, gate="G5")
            record_gate(
                root,
                config,
                directory,
                state,
                "G5",
                "PR_READY",
                "auto",
                evidence,
                [],
                errors,
                approver,
            )
            raise SddError("verification 校验失败")
        mode = gate_mode(config, "G5", state, args.human, workflow)
        if mode == "manual" and approver:
            record_gate_approval(root, directory, state, "G5", approver, evidence)
        record_gate(
            root,
            config,
            directory,
            state,
            "G5",
            "PR_READY",
            mode,
            evidence,
            [],
            errors,
            approver=approver if mode == "manual" else None,
        )
        write_report(root, directory, state)
        transition(
            state,
            resolve_declared_transition(workflow, "PR_READY"),
            evidence,
            gate="G5",
            actor=actor,
            role="verifier",
            approver=approver,
            artifacts=gate_artifact_entries(root, directory, "G5"),
        )
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

    timeout = args.timeout
    if timeout is None:
        timeout = int(config.get("verify_timeout_seconds", 1800) or 1800)
    run_id = datetime.now().strftime("%Y%m%dT%H%M%S%f") + f"-{os.getpid()}"
    tasks_text = read_text(directory / "tasks.md")
    active_task = next(
        (
            task["id"]
            for task in parse_tasks(tasks_text)
            if "in progress" in str(task.get("status", "")).lower()
        ),
        None,
    )
    artifact_hashes = {
        path.relative_to(root).as_posix(): sha256_file(path)
        for path in (
            directory / "spec.md",
            directory / "design.md",
            directory / "tasks.md",
            directory / "verification.md",
        )
        if path.is_file()
    }
    failed = False
    for command in commands:
        print(f"[sdd] run: {command}")
        started_at = datetime.now().astimezone().isoformat(timespec="seconds")
        started_clock = time.monotonic()
        timed_out = False
        try:
            result = subprocess.run(
                command,
                cwd=root,
                shell=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                timeout=timeout,
            )
            exit_code: Optional[int] = result.returncode
            output = (result.stdout or "") + (result.stderr or "")
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            exit_code = None
            stdout = exc.stdout or ""
            stderr = exc.stderr or ""
            if isinstance(stdout, bytes):
                stdout = stdout.decode("utf-8", errors="replace")
            if isinstance(stderr, bytes):
                stderr = stderr.decode("utf-8", errors="replace")
            output = (
                f"{stdout}{stderr}\n[sdd] command timed out after {timeout}s"
            )
        duration_ms = int((time.monotonic() - started_clock) * 1000)
        finished_at = datetime.now().astimezone().isoformat(timespec="seconds")
        output = output.strip()
        if len(output) > 20000:
            output = output[:20000] + "\n... (truncated)"
        output_sha256 = hashlib.sha256(output.encode("utf-8")).hexdigest()
        if len(output) > 4000:
            excerpt = (
                output[:1500]
                + "\n... (truncated) ...\n"
                + output[-2500:]
            )
        else:
            excerpt = output
        record = {
            "schema": EVIDENCE_SCHEMA,
            "run_id": run_id,
            "spec": spec_id,
            "task": active_task,
            "command": command,
            "cwd": root.as_posix(),
            "started_at": started_at,
            "finished_at": finished_at,
            "exit_code": exit_code,
            "timed_out": timed_out,
            "duration_ms": duration_ms,
            "output_sha256": output_sha256,
            "output_excerpt": excerpt,
            "artifact_hashes": artifact_hashes,
        }
        path = evidence_path(directory)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(
                json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
            )
        head = git_head_sha(root) or "unknown"
        plan_hash = task_plan_hash(read_text(directory / "tasks.md"))
        body = (
            f"- Command: `{command}`\n"
            f"- CWD: `{root}`\n"
            f"- Exit: `{exit_code}`\n\n"
            f"- Head: `{head[:12]}`\n"
            f"- Plan-Hash: `sha256:{plan_hash}`\n"
            f"- At: `{now()}`\n\n"
            f"- Timed out: `{str(timed_out).lower()}`\n\n"
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
        if exit_code != 0:
            failed = True
            eprint(f"[sdd] command failed ({exit_code}): {command}")
            record_check_failure(
                directory,
                "verify",
                [f"测试命令失败（exit {exit_code}）：{command}"],
                gate="G5",
            )
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
    if args.url and state.get("state") != "MERGED":
        raise SddError(
            "只有 MERGED（交付已确认）后才能记录 PR URL；确认前不要创建 PR"
        )
    if args.url:
        if (root / ".git").exists():
            spec_dir = directory.relative_to(root).as_posix()
            status = subprocess.run(
                [
                    "git",
                    "status",
                    "--porcelain",
                    "--",
                    f"{spec_dir}/state.json",
                    f"{spec_dir}/events.jsonl",
                ],
                cwd=root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            if status.returncode != 0:
                raise SddError(
                    "无法检查交付确认是否已提交：" + status.stderr.strip()
                )
            if status.stdout.strip():
                raise SddError(
                    "交付确认尚未提交；先 commit state.json / events.jsonl "
                    "再记录 PR URL"
                )
        state["pr_url"] = args.url
        add_history(
            state,
            str(state.get("state")),
            "PR recorded",
            pr_url=args.url,
            role="orchestrator",
        )
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
    add_history(state, "BLOCKED", args.reason, role="orchestrator")
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
    approver = resolve_approver(root, getattr(args, "approver", None))
    if config.get("require_approver") and approver == "unknown":
        raise SddError(
            "require_approver=true；请用 --approver 提供审批人"
        )
    state.setdefault("approvals", []).append(
        {
            "action": "unblock",
            "approver": approver,
            "at": now(),
        }
    )
    state["last_approver"] = approver
    previous = state.get("blocked_from") or "TASKS_READY"
    state["state"] = previous
    state.pop("blocked_from", None)
    state.pop("blocked_reason", None)
    add_history(
        state,
        previous,
        args.evidence or "unblocked",
        actor="human",
        role="approver",
        approver=approver,
    )
    save_state(directory, state)
    print(f"[sdd] {spec_id} unblocked -> {previous}")
    return 0


def dirty_spec_paths(root: Path, directory: Path) -> list[str]:
    if not (root / ".git").exists():
        return []
    relative = directory.relative_to(root).as_posix()
    result = subprocess.run(
        ["git", "status", "--porcelain", "--", relative],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def unique_history_dir(directory: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    candidate = directory / "history" / stamp
    index = 1
    while candidate.exists():
        candidate = directory / "history" / f"{stamp}-{index}"
        index += 1
    return candidate


def command_rewind(
    args: argparse.Namespace, root: Path, config: dict[str, Any]
) -> int:
    spec_id, directory, state = resolve_spec(root, config, args.spec)
    workflow = resolve_workflow(root, directory, state)
    current = str(state.get("state", "UNKNOWN"))
    target = str(args.to)
    reason = str(args.reason or "").strip()

    if not args.human:
        raise SddError("rewind 需要 --human；agent 不允许回退阶段")
    if not reason:
        raise SddError("rewind 需要 --reason，记录为什么回退")
    if current == "MERGED":
        raise SddError("MERGED 不能 rewind")
    if current == "BLOCKED":
        raise SddError("BLOCKED 状态先 unblock，再 rewind")
    if current not in STAGE_ORDER or target not in STAGE_ORDER:
        raise SddError(f"未知阶段：{current} -> {target}")
    if target == current:
        raise SddError("已经在目标状态，不需要 rewind")
    if STAGE_ORDER.index(target) > STAGE_ORDER.index(current):
        raise SddError("rewind 只能回到更早阶段，不能去未来")
    if target not in REWIND_PLANS:
        raise SddError(f"不支持回退到 {target}；可选目标是更早的 DRAFT 到 VERIFYING")
    allowed_targets = [
        str(item) for item in workflow.get("allow_rewind_to", [])
    ]
    if allowed_targets and target not in allowed_targets:
        raise SddError(
            f"工作流 {workflow.get('name')} 不允许回退到 {target}；"
            "可选：" + ", ".join(allowed_targets)
        )
    if args.reopen_task and target != "IMPLEMENTING":
        raise SddError("--reopen-task 只能用于回退到 IMPLEMENTING")
    if args.reset_tasks and target != "IMPLEMENTING":
        raise SddError("--reset-tasks 只能用于回退到 IMPLEMENTING")
    if args.reopen_task and args.reset_tasks:
        raise SddError("--reopen-task 与 --reset-tasks 不能同时使用")

    approver = resolve_approver(root, getattr(args, "approver", None))
    if config.get("require_approver") and approver == "unknown":
        raise SddError("require_approver=true；请用 --approver 提供审批人")

    dirty = dirty_spec_paths(root, directory)
    if dirty and not args.force:
        raise SddError(
            "Spec 目录有未提交改动；先提交，或加 --force 继续：\n- "
            + "\n- ".join(dirty)
        )

    archived_names, invalidated_gates, task_mode = REWIND_PLANS[target]
    history_dir = unique_history_dir(directory)
    manifest: dict[str, Any] = {
        "at": now(),
        "from": current,
        "to": target,
        "reason": reason,
        "approver": approver,
        "files": [],
    }
    archived: list[str] = []
    for name in archived_names:
        source = directory / name
        if not source.is_file():
            continue
        destination = history_dir / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        archived.append(destination.relative_to(root).as_posix())
        manifest["files"].append(
            {
                "kind": "artifact",
                "source": source.relative_to(root).as_posix(),
                "archived": destination.relative_to(root).as_posix(),
                "sha256": artifact_sha256(destination),
                "bytes": destination.stat().st_size,
            }
        )

    report_history = (
        report_root(root, config) / spec_id / "history" / history_dir.name
    )
    for gate in invalidated_gates:
        source = gate_report_path(root, config, spec_id, gate)
        if not source.is_file():
            continue
        destination = report_history / source.name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(destination))
        archived.append(destination.relative_to(root).as_posix())
        manifest["files"].append(
            {
                "kind": "gate_report",
                "gate": gate,
                "source": source.relative_to(root).as_posix(),
                "archived": destination.relative_to(root).as_posix(),
            }
        )

    if manifest["files"]:
        write_json(history_dir / "manifest.json", manifest)

    tasks_text = read_text(directory / "tasks.md")
    tasks = parse_tasks(tasks_text)
    reopened: list[str] = []
    if task_mode == "reset_all":
        reopened = [str(task["id"]) for task in tasks]
    elif task_mode == "implementation":
        if args.reset_tasks:
            reopened = [str(task["id"]) for task in tasks]
        elif args.reopen_task:
            if not any(str(task["id"]) == args.reopen_task for task in tasks):
                raise SddError(f"找不到 Task：{args.reopen_task}")
            reopened = [args.reopen_task]
        else:
            reopened = [
                str(task["id"])
                for task in tasks
                if str(task.get("status", "")).lower() == "in progress"
            ]
            if not reopened and tasks and all(task["done"] for task in tasks):
                reopened = [str(tasks[-1]["id"])]
    for task_id in reopened:
        tasks_text, _ = mark_task_status(tasks_text, task_id, "Todo")
    if reopened:
        write_text(directory / "tasks.md", tasks_text)

    for gate in invalidated_gates:
        append_gate(directory, gate, target, "rewind", reason, "SUPERSEDED")

    hashes = state.get("artifact_hashes", {})
    if isinstance(hashes, dict):
        for gate in invalidated_gates:
            hashes.pop(gate, None)

    rework = {
        "from": current,
        "to": target,
        "reason": reason,
        "at": now(),
        "approver": approver,
        "archived": archived,
        "invalidated_gates": list(invalidated_gates),
        "tasks_reset": bool(reopened),
        "reopened_tasks": reopened,
    }
    state.setdefault("reworks", []).append(rework)
    state.setdefault("approvals", []).append(
        {
            "action": "rewind",
            "approver": approver,
            "at": now(),
            "from": current,
            "to": target,
            "reason": reason,
        }
    )
    state["last_approver"] = approver
    transition(
        state,
        target,
        reason,
        action="rewind",
        actor="human",
        role="approver",
        approver=approver,
        reason=reason,
        rewind=rework,
    )
    save_state(directory, state)

    payload = {
        "ok": True,
        "kind": "rewind",
        "spec": spec_id,
        "from": current,
        "to": target,
        "archived": archived,
        "invalidated_gates": list(invalidated_gates),
        "tasks_reset": bool(reopened),
        "reopened_tasks": reopened,
        "next": build_next_action(root, directory, state),
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    print(f"[sdd] {spec_id} rewind {current} -> {target}")
    print(f"[sdd] archived {len(archived)} file(s); invalidated: {', '.join(invalidated_gates)}")
    if reopened:
        print(f"[sdd] reopened tasks: {', '.join(reopened)}")
    print(f"[sdd] next: {payload['next'].get('action')}")
    return 0


def parse_workflow_target(value: str) -> tuple[str, int]:
    match = re.fullmatch(r"([a-z][a-z0-9-]*)@(\d+)", str(value).strip())
    if not match:
        raise SddError("--to 必须是 <name>@<version>，例如 l2-standard@2")
    return match.group(1), int(match.group(2))


def pending_required_gates(
    root: Path,
    config: dict[str, Any],
    directory: Path,
    state: dict[str, Any],
    preset: dict[str, Any],
) -> list[str]:
    state_name = str(state.get("state") or "")
    required = preset.get("required_gates", {}).get(state_name, [])
    spec_id = str(state.get("spec_id") or directory.name)
    return [
        str(gate)
        for gate in required
        if gate_report_status(gate_report_path(root, config, spec_id, str(gate)))
        != "PASS"
    ]


def workflow_preset_version(
    root: Path,
    state: dict[str, Any],
    name: str,
    version: int,
) -> Optional[dict[str, Any]]:
    path = workflow_root(root) / f"{name}.json"
    candidates: list[dict[str, Any]] = []
    if path.is_file():
        candidates.append(load_json(path))
    for record in reversed(state.get("workflow_history") or []):
        if not isinstance(record, dict):
            continue
        for key in ("to_preset", "from_preset"):
            preset = record.get(key)
            if (
                isinstance(preset, dict)
                and preset.get("name") == name
                and int(preset.get("version") or 0) == version
            ):
                candidates.append(preset)
    for preset in candidates:
        if validate_workflow_preset(preset, f"{name}.json"):
            continue
        if int(preset.get("version") or 0) == version:
            return preset
    return None


def command_upgrade_workflow(
    args: argparse.Namespace, root: Path, config: dict[str, Any]
) -> int:
    spec_id, directory, state = resolve_spec(root, config, args.spec)
    if not args.human:
        raise SddError("upgrade-workflow 需要 --human；agent 不允许切换工作流")
    reason = str(args.reason or "").strip()
    if not reason:
        raise SddError("upgrade-workflow 需要 --reason，记录升级原因")
    current_state = str(state.get("state") or "UNKNOWN")
    if current_state == "MERGED":
        raise SddError("MERGED Spec 不能升级工作流")
    if current_state == "BLOCKED":
        raise SddError("BLOCKED 状态先 unblock，再升级工作流")

    current = state.get("workflow") or {}
    if not isinstance(current, dict) or not current.get("name"):
        raise SddError("当前 Spec 缺少 workflow 引用，无法升级")
    current_name = str(current.get("name"))
    current_version = int(current.get("version") or 0)
    target_name, target_version = parse_workflow_target(args.to)
    if target_name == current_name and target_version == current_version:
        raise SddError(
            f"{spec_id} 已经固定在 {current_name}@{current_version}，无需升级"
        )

    preset = workflow_preset_version(
        root, state, target_name, target_version
    )
    if preset is None:
        path = workflow_root(root) / f"{target_name}.json"
        available = "无"
        if path.is_file():
            available = f"@{load_json(path).get('version')}"
        raise SddError(
            f"找不到 {target_name}@{target_version}；仓库当前版本：{available}。"
            "降级只能使用 workflow_history 中保留过的版本"
        )

    downgrade = target_version < current_version
    if downgrade and not args.allow_downgrade:
        raise SddError(
            f"拒绝降级 {current_version} -> {target_version}；"
            "如确需降级，请加 --allow-downgrade --design-change <引用>"
        )
    if args.allow_downgrade and not downgrade:
        raise SddError("--allow-downgrade 只能用于版本降低的升级")
    design_change = str(args.design_change or "").strip()
    if downgrade and not design_change:
        raise SddError("降级必须用 --design-change 提供设计变更引用")

    approver = resolve_approver(root, getattr(args, "approver", None))
    if config.get("require_approver") and approver == "unknown":
        raise SddError("require_approver=true；请用 --approver 提供审批人")

    new_reference = workflow_reference(preset)
    old_reference = {
        "name": current_name,
        "version": current_version,
        "digest": str(current.get("digest") or ""),
    }
    pending_gates = pending_required_gates(
        root, config, directory, state, preset
    )
    gate_errors = check_gates(root, config, directory, current_state)
    entry: dict[str, Any] = {
        "from": old_reference,
        "to": {
            "name": new_reference["name"],
            "version": new_reference["version"],
            "digest": new_reference["digest"],
        },
        "approver": approver,
        "reason": reason,
        "at": now(),
        "pending_gates": pending_gates,
    }
    snapshot_path = directory / "workflow.json"
    if snapshot_path.is_file():
        entry["from_preset"] = load_json(snapshot_path)
    entry["to_preset"] = preset
    if design_change:
        entry["design_change"] = design_change

    old_snapshot = snapshot_path.read_bytes() if snapshot_path.is_file() else None
    old_state = json.loads(json.dumps(state))
    try:
        atomic_write_json(snapshot_path, preset)
        state["workflow"] = new_reference
        state.setdefault("workflow_history", []).append(entry)
        state["last_approver"] = approver
        add_history(
            state,
            current_state,
            f"workflow upgraded: {current_name}@{current_version} "
            f"-> {target_name}@{target_version}",
            action="workflow_upgraded",
            actor="human",
            role="approver",
            approver=approver,
            reason=reason,
            workflow=entry,
        )
        save_state(directory, state)
    except Exception:
        if old_snapshot is None:
            snapshot_path.unlink(missing_ok=True)
        else:
            snapshot_path.write_bytes(old_snapshot)
        write_json(directory / "state.json", old_state)
        raise

    payload = {
        "ok": True,
        "kind": "workflow_upgrade",
        "spec": spec_id,
        "from": old_reference,
        "to": entry["to"],
        "approver": approver,
        "reason": reason,
        "pending_gates": pending_gates,
        "gate_errors": gate_errors,
        "history": entry,
        "next": build_next_action(root, directory, state),
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    print(
        f"[sdd] {spec_id} workflow "
        f"{current_name}@{current_version} -> {target_name}@{target_version}"
    )
    if pending_gates:
        print("[sdd] pending gates: " + ", ".join(pending_gates))
    print(f"[sdd] next: {payload['next'].get('action')}")
    return 0


def command_merge(
    args: argparse.Namespace, root: Path, config: dict[str, Any]
) -> int:
    spec_id, directory, state = resolve_spec(root, config, args.spec)
    if state.get("state") != "PR_READY":
        raise SddError("只有 PR_READY 状态可以确认交付")
    if not args.human:
        raise SddError("确认交付需要 --human；agent 不允许自己确认")
    approver = resolve_approver(root, getattr(args, "approver", None))
    if config.get("require_approver") and approver == "unknown":
        raise SddError(
            "require_approver=true；请用 --approver 提供审批人"
        )
    errors, _ = run_checks(root, config, directory, state, "ci")
    if errors:
        for error in errors:
            eprint(f"- {error}")
        raise SddError("CI 检查未通过，不能确认交付")
    pr_body = directory / "PR_BODY.md"
    confirmed_at = now()
    state.setdefault("approvals", []).append(
        {
            "action": "confirm_delivery",
            "approver": approver,
            "at": confirmed_at,
            "artifact": pr_body.relative_to(root).as_posix(),
            "sha256": artifact_sha256(pr_body) if pr_body.is_file() else "",
            "head_sha": git_head_sha(root),
        }
    )
    state["last_approver"] = approver
    state["delivery_confirmed_at"] = confirmed_at
    state["merged_at"] = confirmed_at
    transition(
        state,
        "MERGED",
        args.evidence,
        actor="human",
        role="approver",
        approver=approver,
    )
    save_state(directory, state)
    print(f"[sdd] {spec_id} -> MERGED (交付已确认；下一步创建 PR)")
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
    add_history(
        state,
        "IMPLEMENTING",
        "task started",
        action="task_start",
        task=args.task,
        role="implementer",
    )
    save_state(directory, state)
    print(f"[sdd] {spec_id} {args.task} -> In Progress")
    return 0


def command_init(
    args: argparse.Namespace, root: Path, config: dict[str, Any]
) -> int:
    json_mode = bool(getattr(args, "json", False))
    actions: list[dict[str, Any]] = []
    warnings: list[str] = []
    preserved: list[str] = []

    def say(message: str) -> None:
        if not json_mode:
            print(message)

    layout_paths = (
        spec_root(root, config),
        report_root(root, config),
        prd_index_path(root, config).parent,
    )
    missing_layout = [path for path in layout_paths if not path.exists()]
    ensure_layout(root, config)
    for path in missing_layout:
        actions.append(
            {
                "action": "create-layout",
                "path": path.relative_to(root).as_posix(),
            }
        )
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
        actions.append(
            {
                "action": "create-prd-index",
                "path": index.relative_to(root).as_posix(),
            }
        )
        say(f"[sdd] created {index.relative_to(root)}")
    if args.prd_mode:
        config["prd_mode"] = args.prd_mode
        write_json(root / "sdd" / "config.json", config)
        actions.append(
            {
                "action": "update-config",
                "path": "sdd/config.json",
                "key": "prd_mode",
            }
        )
        say(f"[sdd] prd_mode -> {args.prd_mode}")

    if args.hooks:
        hooks_dir = root / ".githooks"
        hooks_dir.mkdir(exist_ok=True)
        for name in ("pre-commit", "commit-msg"):
            source = root / "sdd" / "hooks" / name
            target = hooks_dir / name
            relative = target.relative_to(root).as_posix()
            if not source.is_file():
                raise SddError(f"缺少 hook 模板：{source.relative_to(root)}")
            if target.exists() and not args.force:
                preserved.append(relative)
                say(f"[sdd] keep existing {target.relative_to(root)}")
            else:
                write_text(target, read_text(source))
                try:
                    target.chmod(0o755)
                except OSError:
                    pass
                actions.append({"action": "install-hook", "path": relative})
                say(f"[sdd] wrote {target.relative_to(root)}")
        if (root / ".git").exists():
            current = subprocess.run(
                ["git", "config", "--get", "core.hooksPath"],
                cwd=root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            if (
                current.returncode == 0
                and current.stdout.strip() == ".githooks"
            ):
                say("[sdd] git core.hooksPath already .githooks")
            else:
                result = subprocess.run(
                    ["git", "config", "core.hooksPath", ".githooks"],
                    cwd=root,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
                if result.returncode == 0:
                    actions.append(
                        {"action": "set-git-hooks", "path": ".githooks"}
                    )
                    say("[sdd] git core.hooksPath = .githooks")
                else:
                    warnings.append(
                        "未能自动设置 core.hooksPath；请手动执行 "
                        "git config core.hooksPath .githooks"
                    )
                    say("[sdd] 未能自动设置 core.hooksPath，请手动执行：")
                    say("       git config core.hooksPath .githooks")
        else:
            warnings.append("当前不是 Git 仓库；提交前请配置 .githooks")
            say("[sdd] 当前不是 Git 仓库；提交前请配置 .githooks")

    if args.ci in {"github", "both"}:
        target = root / ".github" / "workflows" / "sdd.yml"
        source = root / "sdd" / "ci" / "github-actions.yml"
        relative = target.relative_to(root).as_posix()
        if not source.is_file():
            raise SddError(f"缺少 CI 模板：{source.relative_to(root)}")
        if target.exists() and not args.force:
            preserved.append(relative)
            say(f"[sdd] keep existing {target.relative_to(root)}")
        else:
            write_text(target, read_text(source))
            actions.append({"action": "install-ci", "path": relative})
            say(f"[sdd] wrote {target.relative_to(root)}")
    if args.ci in {"gitlab", "both"}:
        target = root / ".gitlab-ci.yml"
        source = root / "sdd" / "ci" / "gitlab-ci.yml"
        relative = target.relative_to(root).as_posix()
        if not source.is_file():
            raise SddError(f"缺少 CI 模板：{source.relative_to(root)}")
        if target.exists() and not args.force:
            preserved.append(relative)
            say(f"[sdd] keep existing {target.relative_to(root)}")
            say(
                "[sdd] 请把 sdd/ci/gitlab-ci.yml 的 job "
                "合并进现有 .gitlab-ci.yml"
            )
            warnings.append(
                "保留现有 .gitlab-ci.yml；请手动合并 "
                "sdd/ci/gitlab-ci.yml 的 job"
            )
        else:
            write_text(target, read_text(source))
            actions.append({"action": "install-ci", "path": relative})
            say(f"[sdd] wrote {target.relative_to(root)}")

    if json_mode:
        print(
            json.dumps(
                {
                    "ok": True,
                    "kind": "init_engine",
                    "actions": actions,
                    "warnings": warnings,
                    "preserved": preserved,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
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
    staged_code = [path for path in paths if is_code_path(path)]
    for directory, state in active_approval_specs(root, config):
        spec_id = str(state.get("spec_id") or directory.name)
        errors.extend(approval_digest_errors(root, directory, state))
        if staged_code:
            errors.extend(change_set_errors(root, directory, state))
            if docs_only_change_records(directory):
                errors.append(
                    f"G1-09 {spec_id} 的 change-set 声明 docs-only，"
                    "但暂存区包含代码：" + ", ".join(staged_code)
                )
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


def workflow_error_path(message: str) -> str:
    match = re.search(
        r"的 (\$[^\s]+|[A-Za-z0-9_]+(?:\[[0-9]+\])?(?:\.[A-Za-z0-9_]+)*) ",
        message,
    )
    return match.group(1) if match else "$"


def workflow_validate_payload(
    args: argparse.Namespace, root: Path
) -> dict[str, Any]:
    raw = Path(args.file)
    path = raw if raw.is_absolute() else root / raw
    if not path.is_file():
        return {
            "ok": False,
            "kind": "workflow_validate",
            "file": str(path),
            "errors": [
                {"path": str(path), "message": f"文件不存在：{args.file}"}
            ],
        }
    try:
        preset = load_json(path)
    except SddError as exc:
        return {
            "ok": False,
            "kind": "workflow_validate",
            "file": str(path),
            "errors": [{"path": str(path), "message": str(exc)}],
        }
    try:
        relative = path.relative_to(root).as_posix()
    except ValueError:
        relative = Path(os.path.relpath(path, root)).as_posix()
    errors = validate_workflow_preset(preset, relative)
    if preset.get("name") and path.stem != preset.get("name"):
        errors.append(f"{relative}.name 必须与文件名一致")
    payload: dict[str, Any] = {
        "ok": not errors,
        "kind": "workflow_validate",
        "file": relative,
        "name": preset.get("name"),
        "schema": preset.get("schema"),
        "version": preset.get("version"),
        "digest": workflow_digest(preset),
    }
    if errors:
        payload["errors"] = [
            {"path": workflow_error_path(error), "message": error}
            for error in errors
        ]
    return payload


def command_workflow_validate(
    args: argparse.Namespace, root: Path, config: dict[str, Any]
) -> int:
    payload = workflow_validate_payload(args, root)
    errors = payload.get("errors", [])
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    elif errors:
        for error in errors:
            eprint(f"- {error['message']}")
    else:
        print(
            f"[sdd] workflow {payload['name']}@{payload['version']} "
            f"(schema {payload['schema']}) is valid"
        )
    return 0 if not errors else 1


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
    p.add_argument("--json", action="store_true")
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
    p.add_argument(
        "--workflow",
        default=None,
        help="workflow preset name; default: sdd/config.json workflow",
    )
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

    p = sub.add_parser("inbox", help="show work waiting for a human")
    p.add_argument("--stale-days", type=int, default=None)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=command_inbox)

    p = sub.add_parser("metrics", help="show lead time, rework and gate metrics")
    p.add_argument("--since", default=None)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=command_metrics)

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

    p = sub.add_parser("index", help="sync FEAT mapping rows into docs/prd-index.md")
    add_spec_option(p)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=command_index)

    p = sub.add_parser("approve", help="human approval: DRAFT -> SPEC_READY")
    add_spec_option(p)
    p.add_argument("--evidence", default="requirement confirmed by human")
    p.add_argument("--approver", help="approver identity, default: git config user")
    p.add_argument("--human", action="store_true")
    p.set_defaults(func=command_approve)

    p = sub.add_parser(
        "reapprove",
        help="human-only re-approval after the approved Spec changes",
    )
    add_spec_option(p)
    p.add_argument("--reason", required=True)
    p.add_argument("--evidence", required=True)
    p.add_argument("--approver", help="approver identity, default: git config user")
    p.add_argument("--human", action="store_true")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=command_reapprove)

    p = sub.add_parser(
        "impact",
        help="read-only FEAT/FR/AC/Task/test/code impact view",
    )
    add_spec_option(p)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=command_impact)

    p = sub.add_parser(
        "change",
        help="record a change-set before code changes",
    )
    add_spec_option(p)
    p.add_argument("--reason", required=True)
    p.add_argument("--docs-only", action="store_true")
    p.add_argument("--risk", choices=["low", "medium", "high"])
    p.add_argument("--rollback")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=command_change)

    p = sub.add_parser(
        "trace",
        help="read-only trace by test, AC or commit",
    )
    trace_group = p.add_mutually_exclusive_group(required=True)
    trace_group.add_argument("--test")
    trace_group.add_argument("--ac")
    trace_group.add_argument("--commit")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=command_trace)

    p = sub.add_parser("waive", help="human-only Gate check waiver")
    add_spec_option(p)
    p.add_argument("--check", required=True, help="check id, e.g. G5-09")
    p.add_argument("--scope", required=True, help="e.g. verification or task:T-001")
    p.add_argument("--reason", required=True)
    p.add_argument("--expires-at", "--expires", dest="expires_at", required=True)
    p.add_argument("--evidence", required=True)
    p.add_argument("--approver", help="approver identity, default: git config user")
    p.add_argument("--human", action="store_true")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=command_waive)

    p = sub.add_parser("complete", help="complete current stage or task")
    add_spec_option(p)
    p.add_argument("--task", help="mark T-xxx done")
    p.add_argument("--evidence", required=True)
    p.add_argument("--commit", help="fill Commit SHA for the task")
    p.add_argument("--approver", help="approver identity for a manual gate")
    p.add_argument("--human", action="store_true", help="manual approval for a human gate")
    p.set_defaults(func=command_complete)

    p = sub.add_parser("start", help="mark a task In Progress")
    add_spec_option(p)
    p.add_argument("--task", required=True)
    p.set_defaults(func=command_start)

    p = sub.add_parser("verify", help="run configured test commands and record evidence")
    add_spec_option(p)
    p.add_argument("--command", action="append", help="override test_commands; repeatable")
    p.add_argument(
        "--timeout",
        type=int,
        default=None,
        help="per-command timeout in seconds; defaults to verify_timeout_seconds or 1800",
    )
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
    p.add_argument("--approver", help="approver identity, default: git config user")
    p.add_argument("--human", action="store_true")
    p.set_defaults(func=command_unblock)

    p = sub.add_parser("rewind", help="human rewind to an earlier SDD stage")
    add_spec_option(p)
    p.add_argument("--to", required=True)
    p.add_argument("--reason", required=True)
    p.add_argument("--approver", help="approver identity, default: git config user")
    p.add_argument("--force", action="store_true")
    p.add_argument("--reopen-task", default=None)
    p.add_argument("--reset-tasks", action="store_true")
    p.add_argument("--human", action="store_true")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=command_rewind)

    p = sub.add_parser(
        "upgrade-workflow",
        help="human upgrade to a fixed workflow preset version",
    )
    add_spec_option(p)
    p.add_argument("--to", required=True, help="target preset, e.g. l2-standard@2")
    p.add_argument("--reason", required=True)
    p.add_argument("--approver", help="approver identity, default: git config user")
    p.add_argument("--allow-downgrade", action="store_true")
    p.add_argument("--design-change", default=None)
    p.add_argument("--human", action="store_true")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=command_upgrade_workflow)

    p = sub.add_parser(
        "merge",
        help="human delivery confirmation: PR_READY -> MERGED (before PR creation)",
    )
    add_spec_option(p)
    p.add_argument("--evidence", required=True)
    p.add_argument("--approver", help="approver identity, default: git config user")
    p.add_argument("--human", action="store_true")
    p.set_defaults(func=command_merge)

    p = sub.add_parser("hook", help="run repository git hooks")
    p.add_argument("hook_name", choices=["pre-commit", "commit-msg"])
    p.add_argument("--message-file", default=None)
    p.set_defaults(func=command_hook)

    p = sub.add_parser("workflow", help="validate declarative workflow profiles")
    workflow_sub = p.add_subparsers(dest="workflow_command", required=True)
    w = workflow_sub.add_parser("validate", help="validate a profile file")
    w.add_argument("--file", required=True)
    w.add_argument("--json", action="store_true")
    w.set_defaults(func=command_workflow_validate)
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        root = find_root(args.root)
        config = load_config(root)
        return int(args.func(args, root, config))
    except SddError as exc:
        if args.command == "init" and getattr(args, "json", False):
            print(
                json.dumps(
                    {
                        "ok": False,
                        "kind": "init_engine",
                        "actions": [],
                        "warnings": [],
                        "preserved": [],
                        "errors": [str(exc)],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
        else:
            eprint(f"[sdd] {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
