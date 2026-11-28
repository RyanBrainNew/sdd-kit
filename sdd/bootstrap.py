"""Shared implementation for the public ``sdd init`` entry point.

The low-level state machine stays in ``sdd/scripts/sdd.py``. This module only
installs or repairs the repository-local workspace; it never creates SDD state
or audit events.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterator

from .agents import merge_managed_block, sync_agents, verify_agents
from .core import manifest_payload, verify_core, write_manifest


KIT_ROOT = Path(__file__).resolve().parents[1]

SKIP_COPY_TOP_LEVEL = {"config.json", "manifest.json", "reports"}
PRESERVED_TOP_LEVEL = {"config.json", "context", "reports"}

INSTALL_DEFAULTS = {
    "sdd_level": "L2",
    "require_approver": True,
    "require_artifact_hash": True,
    "workflow": "l2-standard",
}

GITIGNORE_ENTRIES = (
    ".sdd/runtime/",
    ".sdd-allocations.json",
    ".sdd-allocations.lock",
)


def add_init_arguments(parser: argparse.ArgumentParser) -> None:
    """Add the shared ``sdd init`` arguments to an existing parser."""
    parser.add_argument(
        "--target",
        default=".",
        help="target project root (default: current directory)",
    )
    parser.add_argument(
        "--project",
        help=(
            "project id in sdd/config.json "
            "(default: existing value, otherwise the target directory name)"
        ),
    )
    parser.add_argument(
        "--test-command",
        action="append",
        default=[],
        help="test command for sdd verify; repeatable",
    )
    parser.add_argument(
        "--ci",
        choices=["none", "github", "gitlab", "both"],
        default="none",
        help="CI template to install",
    )
    parser.add_argument(
        "--no-hooks",
        action="store_true",
        help="do not install .githooks",
    )
    parser.add_argument(
        "--no-agent",
        action="store_true",
        help="do not merge the managed block into AGENTS.md",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="refresh the repository-local core; specs and context are kept",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print planned actions without writing",
    )
    parser.add_argument(
        "--source",
        help="sdd-kit checkout or sdd directory to install from",
    )
    parser.add_argument("--json", action="store_true")


def build_parser(prog: str = "sdd init") -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=prog,
        description="Install or repair the repository-local SDD workspace",
    )
    add_init_arguments(parser)
    return parser


def run_init(args: argparse.Namespace) -> dict[str, Any]:
    """Public CLI adapter used by ``sdd/cli.py``."""
    return init_repository(args)


def init_repository(args: argparse.Namespace) -> dict[str, Any]:
    """Install or repair a repository without touching SDD state or events."""
    target = Path(args.target).expanduser().resolve()
    payload: dict[str, Any] = {
        "ok": True,
        "kind": "init",
        "mode": None,
        "target": str(target),
        "project": None,
        "actions": [],
        "warnings": [],
        "preserved": [],
        "checks": [],
        "errors": [],
        "dry_run": bool(args.dry_run),
        "next": {
            "action": "start-work",
            "command": (
                "python -m sdd start-work --work-item <id> --json"
            ),
        },
    }

    error = _validate_target(target)
    if error:
        return _fail(payload, error)

    try:
        source, kit_root = _resolve_source(args.source)
    except ValueError as exc:
        return _fail(payload, str(exc))

    if args.source or _looks_like_kit_root(kit_root):
        if target == kit_root or kit_root in target.parents:
            return _fail(
                payload,
                (
                    "target is inside the sdd-kit source repository; "
                    "run sdd init from the project directory or pass a "
                    "project path"
                ),
                command=f'python -m sdd init --target "<repo>"',
            )

    try:
        _validate_source(source)
    except ValueError as exc:
        return _fail(payload, str(exc))

    config_path = target / "sdd" / "config.json"
    if config_path.is_file():
        mode = "repair"
    else:
        mode = "install"
        if (target / "sdd").exists() and not args.force:
            return _fail(
                payload,
                (
                    f"{target / 'sdd'} exists but sdd/config.json is missing; "
                    "this looks like a half-initialized workspace. "
                    "Re-run with --force to repair it"
                ),
                command=(
                    f'python -m sdd init --target "{target}" --force'
                ),
            )
    payload["mode"] = mode

    try:
        source_config = _load_config(source / "config.json")
        existing_config = _load_config(config_path)
    except ValueError as exc:
        return _fail(payload, str(exc))

    project = args.project
    if not project and mode == "repair":
        project = str(existing_config.get("project") or "") or None
    project = project or target.name
    if not project:
        return _fail(
            payload,
            "could not derive a project id from the target directory; "
            "pass --project <id>",
        )
    payload["project"] = project

    apply = not args.dry_run
    same_source = _same_path(source, target / "sdd")
    if same_source and mode == "install":
        return _fail(
            payload,
            (
                "source and target are the same; run sdd init from the "
                "sdd-kit checkout, or pass --source <kit>"
            ),
            command=f'python -m sdd init --target "{target}" --source "<kit>"',
        )
    if same_source:
        payload["warnings"].append(
            "source and target are the same; core files were not refreshed "
            "(pass --source <kit> to refresh)"
        )

    if mode == "repair":
        for relative in ("sdd/config.json", "sdd/context", "sdd/reports"):
            if (target / relative).exists():
                payload["preserved"].append(relative)

    copy_files = _select_core_files(source, target, mode, args.force, same_source)
    if copy_files:
        verb = "install-core" if mode == "install" else (
            "refresh-core" if args.force else "repair-core"
        )
        payload["actions"].append(
            {"action": verb, "path": "sdd", "files": len(copy_files)}
        )
        if apply:
            _apply_core_files(copy_files)

    desired_config = _desired_config(
        mode,
        source_config,
        existing_config,
        project,
        args.test_command,
        explicit_project=bool(args.project),
    )
    if desired_config != existing_config or not config_path.is_file():
        payload["actions"].append(
            {"action": "write-config", "path": "sdd/config.json"}
        )
        if apply:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(
                json.dumps(desired_config, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
    config = desired_config if apply or desired_config else existing_config
    if not config.get("test_commands"):
        payload["warnings"].append(
            "test_commands is empty; add it before sdd verify"
        )
    elif not args.test_command:
        payload["warnings"].append(
            "test commands: "
            + " | ".join(str(item) for item in config["test_commands"])
            + " (override with --test-command)"
        )

    if not args.no_agent:
        changed, agents_error = _sync_managed_block(
            source, target, mode, args.force, apply
        )
        if agents_error:
            payload["errors"].append(agents_error)
        elif changed:
            payload["actions"].append(
                {"action": "sync-agent", "path": "AGENTS.md"}
            )
    else:
        payload["warnings"].append(
            "AGENTS.md was not updated (--no-agent); verify-agent is skipped"
        )

    additions, gitignore_text = _gitignore_plan(target)
    if additions:
        payload["actions"].append(
            {"action": "update-gitignore", "path": ".gitignore"}
        )
        if apply:
            (target / ".gitignore").write_text(
                gitignore_text, encoding="utf-8"
            )

    missing_layout = _layout_plan(target)
    for relative in missing_layout:
        payload["actions"].append(
            {"action": "create-layout", "path": relative}
        )
        if apply:
            (target / relative).mkdir(parents=True, exist_ok=True)

    engine = _run_engine_init(target, args, apply)
    payload["actions"].extend(engine["actions"])
    payload["warnings"].extend(engine["warnings"])
    payload["preserved"].extend(engine["preserved"])
    payload["errors"].extend(engine["errors"])

    manifest_changed, manifest_error = _sync_manifest(target, apply)
    if manifest_error:
        payload["errors"].append(manifest_error)
    elif manifest_changed:
        payload["actions"].append(
            {"action": "write-manifest", "path": "sdd/manifest.json"}
        )

    _run_checks(target, args, apply, payload)

    payload["ok"] = not payload["errors"]
    payload["warnings"] = _dedupe(payload["warnings"])
    payload["preserved"] = _dedupe(payload["preserved"])
    if args.dry_run:
        payload["warnings"].append("dry-run: no files were changed")
    if not payload["ok"]:
        payload["next"] = None
    return payload


def render_payload(payload: dict[str, Any]) -> None:
    """Render a human-readable init result for the compatibility shim."""
    if payload.get("ok"):
        print(
            f"[sdd] init {payload.get('mode')}: {payload.get('target')} "
            f"(project {payload.get('project')})"
        )
        for action in payload.get("actions", []):
            suffix = ""
            if action.get("files"):
                suffix = f" ({action['files']} files)"
            print(f"[sdd] {action.get('action')}: {action.get('path')}{suffix}")
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
        return
    for error in payload.get("errors", []):
        print(f"[sdd] {error}", file=sys.stderr)


def _fail(
    payload: dict[str, Any],
    message: str,
    command: str | None = None,
) -> dict[str, Any]:
    payload["ok"] = False
    payload["errors"].append(message)
    if command:
        payload["next"] = {"action": "fix", "command": command}
    return payload


def _validate_target(target: Path) -> str | None:
    if not target.exists():
        return f"target is not a directory: {target}"
    if not target.is_dir():
        return f"target is not a directory: {target}"
    if target.parent == target:
        return f"refusing to initialize a drive root: {target}"
    if not os.access(target, os.W_OK):
        return f"target is not writable: {target}"
    return None


def _resolve_source(raw: str | None) -> tuple[Path, Path]:
    if raw:
        base = Path(raw).expanduser().resolve()
        if (base / "sdd" / "scripts" / "sdd.py").is_file():
            return (base / "sdd").resolve(), base.resolve()
        if (base / "scripts" / "sdd.py").is_file():
            return base, base.parent
        raise ValueError(
            f"not an sdd-kit source: {base} (expected sdd/scripts/sdd.py)"
        )
    source = Path(__file__).resolve().parent
    return source, source.parent


def _looks_like_kit_root(path: Path) -> bool:
    return (
        (path / "bootstrap.py").is_file()
        and (path / "sdd" / "scripts" / "sdd.py").is_file()
    )


def _validate_source(source: Path) -> None:
    required = (
        "scripts/sdd.py",
        "agent-block.md",
        "agent-contract.md",
        "VERSION",
        "config.json",
        "templates",
        "workflows",
        "prompts",
        "hooks",
        "ci",
        "context",
    )
    missing = [name for name in required if not (source / name).exists()]
    if missing:
        raise ValueError(
            f"incomplete SDD core at {source}: missing {', '.join(missing)}"
        )


def _load_config(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def _same_path(left: Path, right: Path) -> bool:
    try:
        return left.resolve() == right.resolve()
    except OSError:
        return False


def _iter_core_files(source: Path) -> Iterator[tuple[Path, Path]]:
    for path in sorted(source.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(source)
        if "__pycache__" in relative.parts or path.suffix == ".pyc":
            continue
        if relative.parts and relative.parts[0] in SKIP_COPY_TOP_LEVEL:
            continue
        yield path, relative


def _select_core_files(
    source: Path,
    target: Path,
    mode: str,
    force: bool,
    same_source: bool,
) -> list[tuple[Path, Path]]:
    if same_source:
        return []
    selected: list[tuple[Path, Path]] = []
    for source_path, relative in _iter_core_files(source):
        top_level = relative.parts[0] if relative.parts else ""
        if (
            top_level in PRESERVED_TOP_LEVEL
            and (target / "sdd" / top_level).exists()
        ):
            continue
        destination = target / "sdd" / relative
        if mode == "repair" and not force and destination.exists():
            continue
        selected.append((source_path, destination))
    return selected


def _apply_core_files(files: list[tuple[Path, Path]]) -> None:
    for source_path, destination in files:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination)


def _desired_config(
    mode: str,
    source_config: dict[str, Any],
    existing_config: dict[str, Any],
    project: str,
    test_commands: list[str],
    explicit_project: bool,
) -> dict[str, Any]:
    if mode == "install":
        config = dict(source_config)
        config.pop("project", None)
        config["project"] = project
        config.update(INSTALL_DEFAULTS)
        config["test_commands"] = list(test_commands) if test_commands else []
        return config
    config = dict(existing_config)
    if explicit_project or not config.get("project"):
        config["project"] = project
    if test_commands:
        config["test_commands"] = list(test_commands)
    return config


def _sync_managed_block(
    source: Path,
    target: Path,
    mode: str,
    force: bool,
    apply: bool,
) -> tuple[bool, str | None]:
    try:
        if apply:
            result = sync_agents(target)
            return bool(result.get("changed")), None
        block_path = target / "sdd" / "agent-block.md"
        if mode == "install" or force or not block_path.is_file():
            block_path = source / "agent-block.md"
        block = block_path.read_text(encoding="utf-8")
        agents_path = target / "AGENTS.md"
        existing = (
            agents_path.read_text(encoding="utf-8")
            if agents_path.is_file()
            else ""
        )
        expected = merge_managed_block(existing, block)
        return expected != existing, None
    except OSError as exc:
        return False, f"cannot update AGENTS.md: {exc}"


def _gitignore_plan(target: Path) -> tuple[list[str], str]:
    path = target / ".gitignore"
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    lines = {line.strip() for line in text.splitlines()}
    additions = [line for line in GITIGNORE_ENTRIES if line not in lines]
    if not additions:
        return [], text
    suffix = "" if not text or text.endswith("\n") else "\n"
    return additions, text + suffix + "\n".join(additions) + "\n"


def _layout_plan(target: Path) -> list[str]:
    relative_paths = (
        "docs",
        "sdd/context/services",
        "sdd/context/contracts",
        "sdd/context/adr",
    )
    return [item for item in relative_paths if not (target / item).exists()]


def _engine_plan(target: Path, args: argparse.Namespace) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    if not (target / "docs" / "specs").exists():
        actions.append({"action": "create-layout", "path": "docs/specs"})
    if not (target / "docs" / "prd-index.md").exists():
        actions.append({"action": "create-prd-index", "path": "docs/prd-index.md"})
    if not args.no_hooks:
        for name in ("pre-commit", "commit-msg"):
            relative = f".githooks/{name}"
            if not (target / relative).exists():
                actions.append({"action": "install-hook", "path": relative})
    if args.ci in {"github", "both"}:
        relative = ".github/workflows/sdd.yml"
        if not (target / relative).exists():
            actions.append({"action": "install-ci", "path": relative})
    if args.ci in {"gitlab", "both"}:
        relative = ".gitlab-ci.yml"
        if not (target / relative).exists():
            actions.append({"action": "install-ci", "path": relative})
    return actions


def _run_engine_init(
    target: Path, args: argparse.Namespace, apply: bool
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "actions": [],
        "warnings": [],
        "preserved": [],
        "errors": [],
    }
    if not apply:
        result["actions"] = _engine_plan(target, args)
        return result

    script = target / "sdd" / "scripts" / "sdd.py"
    command = [
        sys.executable,
        str(script),
        "--root",
        str(target),
        "init",
        "--ci",
        args.ci,
        "--json",
    ]
    if not args.no_hooks:
        command.append("--hooks")
    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    completed = subprocess.run(
        command,
        cwd=target,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    if (
        completed.returncode != 0
        and "--json" in command
        and "unrecognized arguments" in (
            completed.stdout + completed.stderr
        )
    ):
        command.remove("--json")
        completed = subprocess.run(
            command,
            cwd=target,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )
        result["warnings"].append(
            "target SDD core predates `sdd init --json`; used text mode"
        )

    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        result["errors"].append(
            f"low-level sdd init failed (exit {completed.returncode})"
            + (f": {detail}" if detail else "")
        )
        return result

    parsed = _parse_engine_json(completed.stdout)
    if parsed is None:
        changed = any(
            marker in completed.stdout
            for marker in ("wrote ", "created ", "prd_mode ->", "core.hooksPath")
        )
        if changed:
            result["actions"].append(
                {"action": "init-engine", "path": "sdd/scripts/sdd.py"}
            )
        return result

    result["actions"].extend(parsed.get("actions", []))
    result["warnings"].extend(parsed.get("warnings", []))
    result["preserved"].extend(parsed.get("preserved", []))
    return result


def _parse_engine_json(text: str) -> dict[str, Any] | None:
    stripped = text.strip()
    if not stripped:
        return None
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            payload = json.loads(stripped[start : end + 1])
        except json.JSONDecodeError:
            return None
    return payload if isinstance(payload, dict) else None


def _sync_manifest(target: Path, apply: bool) -> tuple[bool, str | None]:
    path = target / "sdd" / "manifest.json"
    previous = path.read_text(encoding="utf-8") if path.is_file() else ""
    try:
        expected = manifest_payload(target)
    except (OSError, FileNotFoundError) as exc:
        if apply:
            return False, f"cannot build sdd/manifest.json: {exc}"
        return True, None
    rendered = json.dumps(expected, ensure_ascii=False, indent=2) + "\n"
    changed = rendered != previous
    if changed and apply:
        try:
            write_manifest(target)
        except OSError as exc:
            return False, f"cannot write sdd/manifest.json: {exc}"
    return changed, None


def _run_checks(
    target: Path,
    args: argparse.Namespace,
    apply: bool,
    payload: dict[str, Any],
) -> None:
    if not apply:
        payload["checks"] = [
            {"name": "verify-core", "ok": None, "skipped": True},
            {"name": "verify-agent", "ok": None, "skipped": True},
        ]
        return
    core_errors = verify_core(target)
    payload["checks"].append(
        {
            "name": "verify-core",
            "ok": not core_errors,
            "errors": core_errors,
        }
    )
    for error in core_errors:
        payload["errors"].append(f"verify-core: {error}")
    if args.no_agent:
        payload["checks"].append(
            {"name": "verify-agent", "ok": None, "skipped": True}
        )
        return
    agent_errors = verify_agents(target)
    payload["checks"].append(
        {
            "name": "verify-agent",
            "ok": not agent_errors,
            "errors": agent_errors,
        }
    )
    for error in agent_errors:
        payload["errors"].append(f"verify-agent: {error}")


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
