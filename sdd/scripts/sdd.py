#!/usr/bin/env python3
"""Repo-local SDD workflow.

The script owns the state machine. The coding agent owns the content.
No third-party dependencies; Python 3.9+.
"""

from __future__ import annotations

import argparse
import ast
import glob
import hashlib
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Optional


VERSION = "0.8.0"
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

CHECK_REGISTRY_BY_ID = {str(item["id"]): item for item in CHECK_REGISTRY}

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

WORKFLOW_SCHEMA = 1
DEFAULT_WORKFLOW = "l2-standard"
WORKFLOW_POLICIES = {"human", "auto", "auto_if_no_risk"}
WORKFLOW_DESIGN_MODES = {"full", "lite"}
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


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SddError(f"找不到文件：{path}") from exc
    except json.JSONDecodeError as exc:
        raise SddError(f"JSON 格式错误：{path} ({exc})") from exc


def write_json(path: Path, data: dict[str, Any]) -> None:
    write_text(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
    return relative, sha256_file(path), path.stat().st_size


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
    errors: list[str] = []
    if not isinstance(preset, dict):
        return [f"{source} 必须是 JSON 对象"]
    if preset.get("schema") != WORKFLOW_SCHEMA:
        errors.append(
            f"{source} 的 schema 必须是 {WORKFLOW_SCHEMA}"
        )
    name = str(preset.get("name") or "")
    if not re.fullmatch(r"[a-z][a-z0-9-]*", name):
        errors.append(f"{source} 的 name 必须是小写字母、数字和短横线")
    version = preset.get("version")
    if not isinstance(version, int) or version < 1:
        errors.append(f"{source} 的 version 必须是正整数")
    stages = preset.get("stages")
    if stages != list(STAGE_ORDER):
        errors.append(
            f"{source} 在 0.8.0 只支持完整阶段序列："
            + " -> ".join(STAGE_ORDER)
        )
    gates = preset.get("gates")
    if not isinstance(gates, dict):
        errors.append(f"{source} 缺少 gates 对象")
    else:
        missing = [gate for gate in GATE_STAGES if gate not in gates]
        if missing:
            errors.append(f"{source} 缺少 Gate 策略：" + ", ".join(missing))
        for gate, policy in gates.items():
            if gate not in GATE_STAGES:
                errors.append(f"{source} 包含未知 Gate：{gate}")
            elif str(policy) not in WORKFLOW_POLICIES:
                errors.append(
                    f"{source} 的 {gate} 策略必须是 "
                    + ", ".join(sorted(WORKFLOW_POLICIES))
                )
    required = preset.get("required_gates")
    if not isinstance(required, dict):
        errors.append(f"{source} 缺少 required_gates 对象")
    else:
        expected = workflow_defaults()
        for stage in STAGE_ORDER:
            actual = required.get(stage)
            if actual != expected[stage]:
                errors.append(
                    f"{source} 的 required_gates.{stage} 必须是 "
                    f"{expected[stage]}"
                )
    allow_rewind = preset.get("allow_rewind_to")
    if not isinstance(allow_rewind, list):
        errors.append(f"{source} 缺少 allow_rewind_to 列表")
    else:
        for stage in allow_rewind:
            if stage not in REWIND_PLANS:
                errors.append(
                    f"{source} 的 allow_rewind_to 包含不支持的目标：{stage}"
                )
    artifacts = preset.get("artifacts")
    if not isinstance(artifacts, dict):
        errors.append(f"{source} 缺少 artifacts 对象")
    else:
        for stage, artifact in artifacts.items():
            if stage not in STAGE_ORDER:
                errors.append(f"{source} 的 artifacts 包含未知阶段：{stage}")
            if not isinstance(artifact, str) or not artifact.strip():
                errors.append(f"{source} 的 artifacts.{stage} 必须是非空文件名")
    design_mode = str(preset.get("design_mode") or "full")
    if design_mode not in WORKFLOW_DESIGN_MODES:
        errors.append(
            f"{source} 的 design_mode 必须是 full 或 lite"
        )
    review_required = preset.get("review_required", False)
    if not isinstance(review_required, bool):
        errors.append(f"{source} 的 review_required 必须是布尔值")
    risk_policy = preset.get("risk_policy")
    if risk_policy is not None:
        if not isinstance(risk_policy, dict):
            errors.append(f"{source} 的 risk_policy 必须是对象")
        else:
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

    preset = load_workflow_preset(
        root,
        str(config.get("workflow") or DEFAULT_WORKFLOW),
    )
    return preset


def workflow_risk_error(
    preset: dict[str, Any],
    risk: str,
    risk_labels: Iterable[str],
    config: dict[str, Any],
) -> Optional[str]:
    policy = preset.get("risk_policy")
    if not isinstance(policy, dict):
        return None
    max_risk = str(policy.get("max_risk") or "high")
    if RISK_RANK.get(risk, 0) > RISK_RANK.get(max_risk, 2):
        return (
            f"工作流 {preset['name']} 只允许 risk<={max_risk}，"
            f"当前是 {risk}"
        )
    if policy.get("deny_risk_stop"):
        labels = {str(item) for item in risk_labels}
        stopped = labels & {str(item) for item in config.get("risk_stop", [])}
        if stopped:
            return (
                f"工作流 {preset['name']} 不允许命中风险标签："
                + ", ".join(sorted(stopped))
            )
    return None


def workflow_gate_policy(
    config: dict[str, Any], preset: dict[str, Any], gate: str
) -> str:
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
        start = len(
            [event for event in existing if event.get("event") != "check_failed"]
        )
    if start >= len(history) and emitted >= set(range(len(history))):
        return
    previous_state = next(
        (
            event.get("to_state")
            for event in reversed(existing)
            if event.get("to_state") is not None
        ),
        None,
    )
    next_seq = max((int(event.get("seq", 0)) for event in existing), default=0) + 1
    path = directory / "events.jsonl"
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        for index, entry in enumerate(history):
            if index < start or index in emitted:
                continue
            event = _event_from_history(next_seq, entry, previous_state, index)
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")
            previous_state = entry.get("state")
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


def spec_metadata_errors(text: str, spec_id: Optional[str] = None) -> list[str]:
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


def check_spec(text: str, spec_id: Optional[str] = None) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    errors.extend(spec_section_errors(text))
    errors.extend(placeholder_errors("spec.md", text))
    errors.extend(spec_metadata_errors(text, spec_id))
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
        errors.extend(task_test_name_errors(root, config or {}, tasks))

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
) -> list[str]:
    if str(state.get("state") or "") == "MERGED":
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
    success = False
    for block in blocks:
        command = str(block.get("command") or "")
        exit_value = str(block.get("exit") or "").strip()
        if not re.fullmatch(r"-?\d+", exit_value):
            errors.append(f"命令证据缺少有效 Exit：{command or '(empty)'}")
            continue
        missing = [
            field
            for field in ("cwd", "head", "plan-hash", "at")
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
        for item in config.get("risk_stop", [])
        if str(item).strip()
    }
    return bool(labels & stops)


def check_verification(
    text: str,
    spec_acs: list[str],
    workflow: Optional[dict[str, Any]] = None,
    state: Optional[dict[str, Any]] = None,
    config: Optional[dict[str, Any]] = None,
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
    errors.extend(verification_evidence_errors(text, config or {}, state or {}))
    legacy = str((state or {}).get("state") or "") == "MERGED"
    if not legacy and requires_independent_review(config or {}, state or {}, workflow):
        errors.extend(check_independent_review(text, state or {}))
    return errors


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
            r"^(?P<indent>[ \t]*)(?:async\s+)?def\s+(?P<name>test_\w+)\s*\(",
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
        if not node.name.startswith("test_"):
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
        feat = feat or allocate_feat(root, config)
        safe_title = " ".join(title.split()).replace("|", "\\|")
        link = (issue or "N/A").replace("|", "\\|")
        text += (
            f"| {work_item} | {link} | current | {feat} | {spec_id} | "
            f"{safe_title} | 0 |\n"
        )
        write_text(path, text)
    return path


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
) -> list[str]:
    errors: list[str] = []
    errors.extend(prd_index_structure_errors(root, config, state, spec_text))
    errors.extend(prd_index_clarify_errors(root, config, state, spec_text))
    errors.extend(prd_index_registration_errors(root, config, state, spec_text))
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
    registry: tuple[dict[str, Any], ...] = CHECK_REGISTRY,
) -> list[str]:
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
        seen.add(check_id)
        if str(item.get("gate") or "") not in GATE_STAGES:
            errors.append(f"{check_id or '(unknown)'} 的 Gate 非法：{item.get('gate')}")
        if str(item.get("level") or "") not in {"required", "advisory"}:
            errors.append(
                f"{check_id or '(unknown)'} 的级别必须是 required 或 advisory"
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


def run_gate_checks(gate: str, ctx: dict[str, Any]) -> list[dict[str, Any]]:
    registry_errors = validate_check_registry()
    if registry_errors:
        raise SddError("检查项注册表无效：" + "；".join(registry_errors))
    rows: list[dict[str, Any]] = []
    for item in CHECK_REGISTRY:
        if str(item.get("gate")) != gate:
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
                "owner": item["owner"],
                "result": "block" if item_errors else "pass",
                "detail": detail,
                "errors": item_errors,
            }
        )
    return rows


def gate_rows_errors(rows: list[dict[str, Any]]) -> list[str]:
    return [error for row in rows for error in row.get("errors", [])]


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
            actual = (
                task_plan_hash(read_text(artifact_path))
                if is_plan
                else sha256_file(artifact_path)
            )
            if actual != expected:
                errors.append(
                    f"{gate} 绑定的 {relative} 已被修改；"
                    "请重新执行对应 Gate 或 rewind"
                )
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
    approver: Optional[str] = None,
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
        approver,
    )
    hashes: dict[str, str] = {}
    for name in GATE_ARTIFACTS.get(gate, ()):
        relative, digest, _ = artifact_digest(root, directory, name)
        if digest != "MISSING":
            hashes[relative] = digest
    if hashes:
        state.setdefault("artifact_hashes", {})[gate] = hashes


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
    stop_labels = set(str(item) for item in config.get("risk_stop", []))
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
    workflow = resolve_workflow(root, directory, state)
    ctx = gate_context(root, config, directory, state)
    spec_acs = ctx["spec_acs"]
    legacy_merged = str(state.get("state") or "") == "MERGED"
    errors: list[str] = []

    if stage in {"spec", "design", "tasks", "verify", "ci"}:
        errors.extend(gate_rows_errors(run_gate_checks("G0", ctx)))
        errors.extend(gate_rows_errors(run_gate_checks("G1", ctx)))
    if stage in {"design", "tasks", "verify", "ci"}:
        errors.extend(check_design(design_text, spec_acs, workflow))
    if stage in {"tasks", "verify", "ci"}:
        errors.extend(
            check_tasks(
                tasks_text,
                spec_acs,
                config,
                (
                    root
                    if stage in {"verify", "ci"} and not legacy_merged
                    else None
                ),
            )
        )
    if stage in {"verify", "ci"}:
        errors.extend(
            check_verification(
                verification_text, spec_acs, workflow, state, config
            )
        )
        if not legacy_merged:
            errors.extend(check_test_coverage(root, config, spec_acs))
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
        errors.extend(check_duplicate_spec_files(root, config))
        if check_git_trailer:
            errors.extend(check_git(root, spec_id))

    return errors, stage


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


def build_context_bundle(
    root: Path,
    directory: Path,
    state: dict[str, Any],
    task: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    bundle: dict[str, Any] = {
        "task": None,
        "frs": [],
        "acs": [],
        "design_sections": [],
        "contracts": [],
        "project_constraints": [],
        "fix_patterns": [],
        "allowed_paths": [],
        "exclude": [],
    }
    if not task:
        return bundle

    spec_dir = directory.relative_to(root).as_posix()
    design_text = read_text(directory / "design.md")
    frs = sorted(set(task.get("frs") or []))
    acs = sorted(set(task.get("acs") or []))
    contracts = set(design_contract_paths(design_text, spec_dir))
    contracts.update(context_contract_paths(root))
    allowed = set(design_scope_paths(design_text, spec_dir))
    allowed.update(task_scope_paths(task))
    allowed = {
        value
        for value in allowed
        if value != "docs/prd.md" and not is_other_spec_path(value, spec_dir)
    }

    bundle.update(
        {
            "task": {
                "id": str(task.get("id") or ""),
                "description": str(task.get("description") or ""),
                "status": str(task.get("status") or "Todo"),
            },
            "frs": frs,
            "acs": acs,
            "design_sections": design_section_refs(design_text, frs, acs),
            "contracts": sorted(contracts),
            "project_constraints": [{"path": "AGENTS.md", "scope": "."}],
            "fix_patterns": [],
            "allowed_paths": sorted(allowed),
            "exclude": list(CONTEXT_EXCLUDES),
        }
    )
    return bundle


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
    bundle_task: Optional[dict[str, Any]] = None
    if base.get("kind") == "task" and base.get("task"):
        bundle_task = next(
            (
                task
                for task in parse_tasks(read_text(directory / "tasks.md"))
                if task["id"] == base["task"]
            ),
            None,
        )
    base["context_bundle"] = build_context_bundle(
        root, directory, state, bundle_task
    )
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
    }
    directory.mkdir(parents=True, exist_ok=False)
    design_template = (
        "design-lite.md"
        if str(workflow.get("design_mode") or "full") == "lite"
        else "design.md"
    )
    verification_template = (
        "verification-strict.md"
        if workflow.get("review_required")
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
        root, config, spec_id, work_item, args.title, args.issue, feat=feat_id
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
    elif state_name == "IMPLEMENTING":
        tasks = parse_tasks(read_text(directory / "tasks.md"))
        if not tasks or not all(task["done"] for task in tasks):
            return None
        gate, stage = "G4", "tasks"
    elif state_name == "VERIFYING":
        gate, stage = "G5", "verify"
    else:
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
            "action": "merge_pr",
            "reason": "PR 已就绪，等待人工合并",
            "since": since,
            "artifact": f"{directory.relative_to(root).as_posix()}/PR_BODY.md",
            "command": (
                f"python -m sdd merge --spec {spec_id} --human "
                '--evidence "PR merged"'
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
    }


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
    for directory in directories:
        item = compute_spec_metrics(
            root, directory, load_json(directory / "state.json"), since
        )
        if item:
            specs.append(item)

    lead_times = [
        item["lead_time_hours"]
        for item in specs
        if item["lead_time_hours"] is not None
    ]
    reworks = [item["reworks"] for item in specs]
    payload = {
        "ok": True,
        "kind": "metrics",
        "since": args.since,
        "specs": specs,
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
            if errors:
                record_check_failure(directory, resolved_stage, errors)
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
    if errors:
        record_check_failure(directory, resolved_stage, errors)
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
    g0_rows = run_gate_checks("G0", ctx)
    g1_rows = run_gate_checks("G1", ctx)
    g0_errors = gate_rows_errors(g0_rows)
    g1_errors = gate_rows_errors(g1_rows)
    try:
        g1_mode = gate_mode(config, "G1", state, False, workflow)
    except SddError:
        g1_mode = "manual"
    if g0_errors or g1_errors:
        errors = g0_errors + g1_errors
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
        g0_rows,
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
        g1_rows,
        g1_errors,
        approver if g1_mode == "manual" else None,
    )
    if g0_errors or g1_errors:
        raise SddError("spec 校验失败，不能 approve")
    spec_path = directory / "spec.md"
    state.setdefault("approvals", []).append(
        {
            "action": "approve_spec",
            "approver": approver,
            "at": now(),
            "artifact": spec_path.relative_to(root).as_posix(),
            "sha256": sha256_file(spec_path) if spec_path.is_file() else "",
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
        if (
            tasks
            and all(task["done"] for task in tasks)
            and gate_requires_human(config, "G4", state, workflow)
            and not args.human
        ):
            print(
                f"[sdd] {spec_id} task {args.task} completed; "
                f"G4 awaits human approval"
            )
            print(
                f"[sdd] next: python -m sdd complete --spec {spec_id} "
                '--human --evidence "代码评审通过"'
            )
            return 0
        if tasks and all(task["done"] for task in tasks):
            mode = gate_mode(config, "G4", state, args.human, workflow)
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
                record_check_failure(directory, "tasks", errors, gate="G4")
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
                    approver,
                )
                for error in errors:
                    eprint(f"- {error}")
                save_state(directory, state)
                raise SddError("Gate 4 校验失败")
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
                [
                    ("Task 全部完成", "PASS", f"{len(tasks)} 个 Task 状态均为 Done"),
                    ("Task 验证证据", "PASS", "verification.md 已记录每个 Task"),
                    ("Task 测试映射", "PASS", "每个 Task 有测试类/方法和命令"),
                ],
                approver=approver if mode == "manual" else None,
            )
            transition(
                state,
                "VERIFYING",
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
        spec_text = read_text(directory / "spec.md")
        _, spec_acs = check_spec(spec_text, spec_id)
        errors = check_design(
            read_text(directory / "design.md"),
            spec_acs,
            workflow,
        )
        if errors:
            for error in errors:
                eprint(f"- {error}")
            record_check_failure(directory, "design", errors, gate="G2")
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
            approver=approver if mode == "manual" else None,
        )
        transition(
            state,
            "DESIGN_READY",
            evidence,
            gate="G2",
            actor=actor,
            role="designer",
            approver=approver,
            artifacts=gate_artifact_entries(root, directory, "G2"),
        )
    elif current == "DESIGN_READY":
        _, spec_acs = check_spec(read_text(directory / "spec.md"), spec_id)
        errors = check_tasks(read_text(directory / "tasks.md"), spec_acs, config)
        if errors:
            for error in errors:
                eprint(f"- {error}")
            record_check_failure(directory, "tasks", errors, gate="G3")
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
            "TASKS_READY",
            evidence,
            gate="G3",
            actor=actor,
            role="planner",
            approver=approver,
            artifacts=gate_artifact_entries(root, directory, "G3"),
        )
    elif current == "TASKS_READY":
        _, spec_acs = check_spec(read_text(directory / "spec.md"), spec_id)
        errors = check_tasks(read_text(directory / "tasks.md"), spec_acs, config)
        if errors:
            for error in errors:
                eprint(f"- {error}")
            record_check_failure(directory, "tasks", errors, gate="G3")
            raise SddError("tasks 校验失败")
        transition(
            state,
            "IMPLEMENTING",
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
        _, spec_acs = check_spec(read_text(directory / "spec.md"), spec_id)
        errors = task_table_error(tasks, spec_acs, config)
        errors.extend(task_test_name_errors(root, config, tasks))
        if missing_evidence:
            errors.append("以下 Task 没有验证证据：" + ", ".join(missing_evidence))
        if errors:
            record_check_failure(directory, "tasks", errors, gate="G4")
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
                approver,
            )
            for error in errors:
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
            [
                ("Task 全部完成", "PASS", f"{len(tasks)} 个 Task 状态均为 Done"),
                ("Task 验证证据", "PASS", "verification.md 已记录每个 Task"),
                ("Task 测试映射", "PASS", "每个 Task 有测试类/方法和命令"),
            ],
            approver=approver if mode == "manual" else None,
        )
        transition(
            state,
            "VERIFYING",
            evidence,
            gate="G4",
            actor=actor,
            role="implementer",
            approver=approver,
            artifacts=gate_artifact_entries(root, directory, "G4"),
        )
    elif current == "VERIFYING":
        _, spec_acs = check_spec(read_text(directory / "spec.md"), spec_id)
        errors = check_verification(
            read_text(directory / "verification.md"),
            spec_acs,
            workflow,
            state,
            config,
        )
        errors.extend(check_test_coverage(root, config, spec_acs))
        errors.extend(
            check_gates(root, config, directory, "VERIFYING")
        )
        if errors:
            for error in errors:
                eprint(f"- {error}")
            record_check_failure(directory, "verify", errors, gate="G5")
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
            [
                ("全部 AC 有测试关联", "PASS", "test_globs 命中全部 AC"),
                ("验证命令与结果", "PASS", "verification.md 已填写"),
                ("Gate 5 结论", "PASS", "verification.md 明确 PASS"),
                ("G0–G4 报告", "PASS", "Gate 报告齐备且为 PASS"),
            ],
            approver=approver if mode == "manual" else None,
        )
        write_report(root, directory, state)
        transition(
            state,
            "PR_READY",
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
        head = git_head_sha(root) or "unknown"
        plan_hash = task_plan_hash(read_text(directory / "tasks.md"))
        body = (
            f"- Command: `{command}`\n"
            f"- CWD: `{root}`\n"
            f"- Exit: `{result.returncode}`\n\n"
            f"- Head: `{head[:12]}`\n"
            f"- Plan-Hash: `sha256:{plan_hash}`\n"
            f"- At: `{now()}`\n\n"
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
            record_check_failure(
                directory,
                "verify",
                [f"测试命令失败（exit {result.returncode}）：{command}"],
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
    if args.url:
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
                "sha256": sha256_file(destination),
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


def command_merge(
    args: argparse.Namespace, root: Path, config: dict[str, Any]
) -> int:
    spec_id, directory, state = resolve_spec(root, config, args.spec)
    if state.get("state") != "PR_READY":
        raise SddError("只有 PR_READY 状态可以 merge")
    if not args.human:
        raise SddError("merge 需要 --human；agent 不允许自己合并")
    approver = resolve_approver(root, getattr(args, "approver", None))
    if config.get("require_approver") and approver == "unknown":
        raise SddError(
            "require_approver=true；请用 --approver 提供审批人"
        )
    errors, _ = run_checks(root, config, directory, state, "ci")
    if errors:
        for error in errors:
            eprint(f"- {error}")
        raise SddError("CI 检查未通过，不能登记合并")
    pr_body = directory / "PR_BODY.md"
    state.setdefault("approvals", []).append(
        {
            "action": "merge_pr",
            "approver": approver,
            "at": now(),
            "artifact": pr_body.relative_to(root).as_posix(),
            "sha256": sha256_file(pr_body) if pr_body.is_file() else "",
            "head_sha": git_head_sha(root),
        }
    )
    state["last_approver"] = approver
    state["merged_at"] = now()
    transition(
        state,
        "MERGED",
        args.evidence,
        actor="human",
        role="approver",
        approver=approver,
    )
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

    p = sub.add_parser("merge", help="human merge: PR_READY -> MERGED")
    add_spec_option(p)
    p.add_argument("--evidence", required=True)
    p.add_argument("--approver", help="approver identity, default: git config user")
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
