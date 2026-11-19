"""Copy the SDD kit into a target repository and initialize hooks/CI.

This is intentionally a one-shot onboarding helper. It copies only the
repository-local core; the shared MCP server stays in this kit and is deployed
once for all projects.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from sdd.agents import sync_agents
from sdd.core import write_manifest


KIT_ROOT = Path(__file__).resolve().parent


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bootstrap.py",
        description="Install the repository-local SDD core into a project",
    )
    parser.add_argument("--target", required=True, help="target project root")
    parser.add_argument("--project", required=True, help="project id in sdd/config.json")
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
        "--force",
        action="store_true",
        help="overwrite files inside an existing sdd/ directory; specs are kept",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print planned actions without writing",
    )
    return parser


def _ignore(_directory: str, names: list[str]) -> set[str]:
    return {
        name
        for name in names
        if name == "__pycache__" or name.endswith(".pyc")
    }


def _ensure_gitignore(target: Path) -> None:
    path = target / ".gitignore"
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    lines = {line.strip() for line in text.splitlines()}
    additions = [
        line
        for line in (
            ".sdd/runtime/",
            ".sdd-allocations.json",
            ".sdd-allocations.lock",
        )
        if line not in lines
    ]
    if additions:
        suffix = "" if not text or text.endswith("\n") else "\n"
        path.write_text(text + suffix + "\n".join(additions) + "\n", encoding="utf-8")


def bootstrap(args: argparse.Namespace) -> int:
    target = Path(args.target).expanduser().resolve()
    if not target.is_dir():
        raise SystemExit(f"target is not a directory: {target}")

    sdd_target = target / "sdd"
    if sdd_target.exists() and not args.force:
        raise SystemExit(
            f"{sdd_target} already exists; use --force to refresh the core "
            "(existing specs and context are preserved)"
        )

    if args.dry_run:
        print(f"[dry-run] copy {KIT_ROOT / 'sdd'} -> {sdd_target}")
        print(f"[dry-run] write {target / 'sdd' / 'config.json'}")
        print("[dry-run] merge the managed SDD block into AGENTS.md")
        print("[dry-run] write sdd/manifest.json")
        print(f"[dry-run] init hooks={not args.no_hooks} ci={args.ci}")
        return 0

    config_path = sdd_target / "config.json"
    existing_config = (
        json.loads(config_path.read_text(encoding="utf-8"))
        if config_path.is_file()
        else {}
    )
    sdd_target.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        KIT_ROOT / "sdd",
        sdd_target,
        dirs_exist_ok=True,
        ignore=_ignore,
    )

    config = json.loads(config_path.read_text(encoding="utf-8"))
    config.update(existing_config)
    config["project"] = args.project
    config["sdd_level"] = "L2"
    if not existing_config:
        config["require_approver"] = True
        config["require_artifact_hash"] = True
        config["workflow"] = "l2-standard"
    if args.test_command:
        config["test_commands"] = args.test_command
    config_path.write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    agents_result = sync_agents(target)
    if agents_result.get("created"):
        print("[sdd] created AGENTS.md with the SDD managed block")
    elif agents_result.get("changed"):
        print("[sdd] updated the SDD managed block in AGENTS.md")
    else:
        print("[sdd] AGENTS.md managed block already up to date")

    for relative in (
        "docs",
        "sdd/context/services",
        "sdd/context/contracts",
        "sdd/context/adr",
    ):
        (target / relative).mkdir(parents=True, exist_ok=True)
    _ensure_gitignore(target)
    manifest = write_manifest(target)
    print(
        f"[sdd] wrote sdd/manifest.json "
        f"(version {manifest.get('version')}, {len(manifest.get('files', {}))} files)"
    )

    command = [
        sys.executable,
        str(sdd_target / "scripts" / "sdd.py"),
        "--root",
        str(target),
        "init",
        "--ci",
        args.ci,
    ]
    if not args.no_hooks:
        command.append("--hooks")
    result = subprocess.run(
        command,
        cwd=target,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        return result.returncode

    print("")
    print("[sdd] bootstrap complete")
    print("[sdd] next: fill project facts in AGENTS.md (stack, build, test commands)")
    if not args.test_command:
        print("[sdd] warning: test_commands is empty; add it before sdd verify")
    print(
        "[sdd] first spec: python -m sdd start-work "
        '--work-item srdcloud-123 --title "..." --json'
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    return bootstrap(build_parser().parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
