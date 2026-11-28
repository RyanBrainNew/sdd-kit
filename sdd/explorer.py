"""Read-only repository fact map for one or more code repositories.

The explorer deliberately does not participate in the SDD state machine. It
only reads declarative repository metadata (and, with ``--deep``, bounded
entry/contract files) and returns a stable JSON document plus an optional
Markdown report. It never executes build/test commands, never clones, and
never writes ``state.json`` or ``events.jsonl``.
"""

from __future__ import annotations

import fnmatch
import json
import os
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

try:  # Python 3.11+
    import tomllib
except ImportError:  # pragma: no cover - fallback for older interpreters
    tomllib = None


SCHEMA_VERSION = 1
MAX_REPOS = 20
DEFAULT_MAX_FILES = 20000
DEFAULT_MAX_FILE_BYTES = 262144

EXCLUDED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "vendor",
    "dist",
    "build",
    "target",
    ".venv",
    "venv",
    "__pycache__",
    ".next",
    ".cache",
    "coverage",
    ".pytest_cache",
    ".mypy_cache",
}

LARGE_DIRS = {
    "node_modules",
    "vendor",
    "dist",
    "build",
    "target",
    ".venv",
    "venv",
    ".next",
    ".cache",
    "coverage",
}

SECRET_NAMES = (".env",)
SECRET_SUFFIXES = {".pem", ".key", ".p12", ".pfx"}
SECRET_PREFIXES = ("credentials", "secrets", "secret")

LANGUAGE_BY_SUFFIX = {
    ".py": "python",
    ".pyi": "python",
    ".ipynb": "python",
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".go": "go",
    ".rs": "rust",
    ".cs": "csharp",
    ".fs": "fsharp",
    ".vb": "vbnet",
    ".php": "php",
    ".rb": "ruby",
    ".c": "c",
    ".h": "c",
    ".cc": "cpp",
    ".cpp": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".swift": "swift",
    ".scala": "scala",
    ".sh": "shell",
    ".bash": "shell",
    ".ps1": "powershell",
    ".sql": "sql",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".scss": "css",
    ".sass": "css",
    ".less": "css",
    ".md": "markdown",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
    ".toml": "toml",
}

TEST_COMMAND_RE = re.compile(
    r"(?:^|[\s;&|])("
    r"pytest|py\.test|unittest|tox|nox|"
    r"npm\s+(?:run\s+)?test|pnpm\s+(?:run\s+)?test|yarn\s+(?:run\s+)?test|"
    r"npx\s+(?:jest|vitest|mocha|playwright)|"
    r"go\s+test|mvn\s+[^\n]*\btest|gradlew?\s+[^\n]*\btest|"
    r"dotnet\s+test|ctest|make\s+test|"
    r"rspec|phpunit|jest|vitest|mocha"
    r")(?=$|[\s;&|])",
    re.IGNORECASE,
)

TEST_FILE_RE = re.compile(
    r"(^|/)(tests?|__tests__|spec)/|"
    r"(^|/)test_[^/]+\.py$|(^|/)[^/]+_test\.py$|"
    r"(^|/)[^/]+_test\.go$|"
    r"(^|/)[^/]+\.(test|spec)\.[A-Za-z0-9]+$|"
    r"(^|/)[^/]+\.(test|spec)\.(js|jsx|ts|tsx)$"
)

CONFIDENCE_RANK = {"low": 0, "medium": 1, "high": 2}


class ExplorerError(ValueError):
    """A user-facing explorer input error."""


@dataclass
class ScanOptions:
    depth: int | None
    max_files: int
    max_file_bytes: int
    includes: list[str] = field(default_factory=list)
    excludes: list[str] = field(default_factory=list)
    deep: bool = False


@dataclass
class Root:
    id: str
    path: Path
    display: str
    role: str | None = None
    depends_on: list[str] = field(default_factory=list)
    source: str | None = None


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _posix(value: str) -> str:
    return value.replace("\\", "/")


def _run_git(root: Path, *args: str) -> subprocess.CompletedProcess[bytes] | None:
    try:
        return subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None


def _git_is_worktree(root: Path) -> bool:
    probe = _run_git(root, "rev-parse", "--is-inside-work-tree")
    return bool(
        probe
        and probe.returncode == 0
        and probe.stdout.decode("utf-8", "replace").strip().lower() == "true"
    )


def _git_text(root: Path, *args: str) -> str | None:
    result = _run_git(root, *args)
    if result is None or result.returncode != 0:
        return None
    return result.stdout.decode("utf-8", "replace").strip()


def _git_identity(root: Path, state: dict[str, Any]) -> dict[str, Any] | None:
    if not _git_is_worktree(root):
        return None
    branch = _git_text(root, "rev-parse", "--abbrev-ref", "HEAD")
    head = _git_text(root, "rev-parse", "--short", "HEAD")
    toplevel = _git_text(root, "rev-parse", "--show-toplevel")
    status = _git_text(root, "status", "--porcelain", "--untracked-files=normal")
    if status is None:
        state["warnings"].append(
            {
                "repo": state["id"],
                "path": "",
                "message": "git status 读取失败，dirty 标记为 unknown",
            }
        )
    return {
        "root": _posix(toplevel) if toplevel else None,
        "branch": branch if branch and branch != "HEAD" else None,
        "head": head,
        "dirty": bool(status) if status is not None else None,
    }


def _git_inventory(
    root: Path, state: dict[str, Any]
) -> list[str] | None:
    if not _git_is_worktree(root):
        return None
    result = _run_git(
        root,
        "ls-files",
        "-z",
        "--cached",
        "--others",
        "--exclude-standard",
    )
    if result is None or result.returncode != 0:
        state["warnings"].append(
            {
                "repo": state["id"],
                "path": "",
                "message": "git ls-files 失败，改用有界目录遍历",
            }
        )
        return None
    paths: list[str] = []
    for raw in result.stdout.split(b"\0"):
        if not raw:
            continue
        try:
            rel = raw.decode("utf-8")
        except UnicodeDecodeError:
            state["warnings"].append(
                {
                    "repo": state["id"],
                    "path": "",
                    "message": "git 返回了非 UTF-8 路径，已跳过",
                }
            )
            continue
        paths.append(_posix(rel))
    return paths


def _walk_inventory(
    root: Path, state: dict[str, Any], options: ScanOptions
) -> tuple[list[str], list[str]]:
    paths: list[str] = []
    skipped_dirs: list[str] = []

    def visit(directory: Path, relative_dir: str) -> None:
        try:
            entries = sorted(os.scandir(directory), key=lambda item: item.name)
        except OSError as exc:
            state["warnings"].append(
                {
                    "repo": state["id"],
                    "path": relative_dir,
                    "message": f"目录读取失败：{exc.__class__.__name__}",
                }
            )
            return
        for entry in entries:
            relative = (
                f"{relative_dir}/{entry.name}" if relative_dir else entry.name
            )
            try:
                if entry.is_symlink():
                    continue
                if entry.is_dir(follow_symlinks=False):
                    if entry.name.lower() in EXCLUDED_DIRS:
                        skipped_dirs.append(relative)
                        continue
                    if options.depth is not None and len(
                        PurePosixPath(relative).parts
                    ) >= options.depth:
                        continue
                    visit(Path(entry.path), relative)
                elif entry.is_file(follow_symlinks=False):
                    paths.append(relative)
            except OSError as exc:
                state["warnings"].append(
                    {
                        "repo": state["id"],
                        "path": relative,
                        "message": f"文件状态读取失败：{exc.__class__.__name__}",
                    }
                )

    visit(root, "")
    return paths, skipped_dirs


def _glob_match(relative: str, pattern: str) -> bool:
    pattern = _posix(pattern).strip()
    if not pattern:
        return False
    relative = _posix(relative)
    if pattern.endswith("/"):
        return relative == pattern.rstrip("/") or relative.startswith(
            pattern.rstrip("/") + "/"
        )
    name = relative.rsplit("/", 1)[-1]
    if "/" in pattern:
        return fnmatch.fnmatchcase(relative, pattern)
    return fnmatch.fnmatchcase(name, pattern) or fnmatch.fnmatchcase(
        relative, pattern
    )


def _selected(relative: str, options: ScanOptions) -> bool:
    parts = PurePosixPath(relative).parts
    if any(part.lower() in EXCLUDED_DIRS for part in parts[:-1]):
        return False
    if options.depth is not None and len(parts) > options.depth:
        return False
    if options.includes and not any(
        _glob_match(relative, pattern) for pattern in options.includes
    ):
        return False
    if any(_glob_match(relative, pattern) for pattern in options.excludes):
        return False
    return True


def _same_path(left: Path, right: Path) -> bool:
    return os.path.normcase(str(left)) == os.path.normcase(str(right))


def _validate_root(path: Path, label: str) -> Path:
    try:
        resolved = path.expanduser().resolve()
    except OSError as exc:
        raise ExplorerError(f"{label} 无法解析：{exc}") from exc
    if not resolved.is_dir():
        raise ExplorerError(f"{label} 不是目录：{path}")
    if resolved.parent == resolved:
        raise ExplorerError(f"拒绝扫描文件系统根目录：{path}")
    if _same_path(resolved, Path.home()):
        raise ExplorerError(f"拒绝扫描用户主目录：{path}")
    if any(part.lower() == ".git" for part in resolved.parts):
        raise ExplorerError(f"拒绝扫描 .git 目录：{path}")
    return resolved


def _default_id(path: Path) -> str:
    name = path.name.strip()
    return name or "repo"


def _validate_id(repo_id: Any, label: str) -> str:
    if not isinstance(repo_id, str) or not repo_id.strip():
        raise ExplorerError(f"{label} 的 id 必须是非空字符串")
    value = repo_id.strip()
    if "/" in value or "\\" in value:
        raise ExplorerError(f"{label} 的 id 不能包含路径分隔符：{value}")
    return value


def _load_roots(
    repos: Iterable[str],
    workspace: str | None,
    default_root: Path,
) -> list[Root]:
    roots: list[Root] = []
    if workspace:
        manifest = Path(workspace).expanduser()
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ExplorerError(f"workspace 清单不存在：{workspace}") from exc
        except (OSError, json.JSONDecodeError) as exc:
            raise ExplorerError(f"workspace 清单无法读取：{exc}") from exc
        if not isinstance(data, dict):
            raise ExplorerError("workspace 清单必须是 JSON 对象")
        if data.get("version") != 1:
            raise ExplorerError("workspace.version 必须为 1")
        items = data.get("repos")
        if not isinstance(items, list) or not items:
            raise ExplorerError("workspace.repos 必须是非空数组")
        if len(items) > MAX_REPOS:
            raise ExplorerError(f"workspace 最多支持 {MAX_REPOS} 个仓库")
        base = manifest.resolve().parent
        for index, item in enumerate(items):
            label = f"workspace.repos[{index}]"
            if not isinstance(item, dict):
                raise ExplorerError(f"{label} 必须是对象")
            repo_id = _validate_id(item.get("id"), label)
            path_value = item.get("path")
            if not isinstance(path_value, str) or not path_value.strip():
                raise ExplorerError(f"{label}.path 必须是非空字符串")
            role = item.get("role")
            if role is not None and not isinstance(role, str):
                raise ExplorerError(f"{label}.role 必须是字符串")
            depends_on = item.get("depends_on") or []
            if not isinstance(depends_on, list) or not all(
                isinstance(value, str) and value.strip()
                for value in depends_on
            ):
                raise ExplorerError(f"{label}.depends_on 必须是字符串数组")
            resolved = _validate_root(
                (base / path_value).expanduser(), label
            )
            roots.append(
                Root(
                    id=repo_id,
                    path=resolved,
                    display=_posix(path_value),
                    role=role,
                    depends_on=[value.strip() for value in depends_on],
                    source=_posix(str(manifest)),
                )
            )
    else:
        values = list(repos)
        using_default = not values
        if not values:
            values = [str(default_root)]
        if len(values) > MAX_REPOS:
            raise ExplorerError(f"最多支持 {MAX_REPOS} 个仓库")
        for index, value in enumerate(values):
            label = f"--repo[{index}]"
            resolved = _validate_root(Path(value), label)
            roots.append(
                Root(
                    id=_default_id(resolved),
                    path=resolved,
                    display="." if using_default else _posix(value),
                )
            )

    seen_ids: dict[str, int] = {}
    seen_paths: dict[str, int] = {}
    for index, root in enumerate(roots):
        if root.id in seen_ids:
            raise ExplorerError(
                f"重复的仓库 id：{root.id}（第 {seen_ids[root.id] + 1} 和第 {index + 1} 项）"
            )
        seen_ids[root.id] = index
        key = os.path.normcase(str(root.path))
        if key in seen_paths:
            raise ExplorerError(
                f"重复的仓库路径：{root.display}（第 {seen_paths[key] + 1} 和第 {index + 1} 项）"
            )
        seen_paths[key] = index
    return roots


def _read_text(
    state: dict[str, Any],
    relative: str,
    limit: int,
    *,
    quiet_truncate: bool = False,
) -> str | None:
    if _is_secret(relative):
        return None
    path = state["path"] / Path(relative)
    try:
        if path.is_symlink():
            return None
        with path.open("rb") as handle:
            data = handle.read(limit + 1)
    except OSError as exc:
        state["warnings"].append(
            {
                "repo": state["id"],
                "path": relative,
                "message": f"读取失败：{exc.__class__.__name__}",
            }
        )
        return None
    state["bytes_read"] += len(data)
    truncated = len(data) > limit
    data = data[:limit]
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        state["warnings"].append(
            {
                "repo": state["id"],
                "path": relative,
                "message": f"UTF-8 解码失败：{exc.reason}",
            }
        )
        return None
    if truncated and not quiet_truncate:
        state["warnings"].append(
            {
                "repo": state["id"],
                "path": relative,
                "message": f"文件超过 --max-file-bytes={limit}，已截断",
            }
        )
    return text


def _read_json(state: dict[str, Any], relative: str, limit: int) -> Any | None:
    text = _read_text(state, relative, limit)
    if text is None:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        state["warnings"].append(
            {
                "repo": state["id"],
                "path": relative,
                "message": f"JSON 解析失败：{exc.msg}（第 {exc.lineno} 行）",
            }
        )
        return None


def _fallback_toml(text: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    current: dict[str, Any] = data
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            current = data
            for part in line[1:-1].strip().split("."):
                key = part.strip().strip('"\'')
                if key:
                    value = current.get(key)
                    if not isinstance(value, dict):
                        value = {}
                        current[key] = value
                    current = value
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip().strip('"\'')
        value = value.strip()
        if value.startswith(('"', "'")) and value.endswith(('"', "'")):
            current[key] = value[1:-1]
        elif value.lower() in {"true", "false"}:
            current[key] = value.lower() == "true"
        elif value.startswith("[") and value.endswith("]"):
            items = [
                item.strip().strip('"\'')
                for item in value[1:-1].split(",")
                if item.strip()
            ]
            current[key] = items
        else:
            current[key] = value
    return data


def _read_toml(state: dict[str, Any], relative: str, limit: int) -> dict[str, Any] | None:
    text = _read_text(state, relative, limit)
    if text is None:
        return None
    if tomllib is not None:
        try:
            return tomllib.loads(text)
        except Exception as exc:  # tomllib raises TOMLDecodeError
            state["warnings"].append(
                {
                    "repo": state["id"],
                    "path": relative,
                    "message": f"TOML 解析失败：{exc.__class__.__name__}",
                }
            )
            return None
    return _fallback_toml(text)


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _read_xml(state: dict[str, Any], relative: str, limit: int):
    import xml.etree.ElementTree as ET

    text = _read_text(state, relative, limit)
    if text is None:
        return None
    try:
        return ET.fromstring(text)
    except ET.ParseError as exc:
        state["warnings"].append(
            {
                "repo": state["id"],
                "path": relative,
                "message": f"XML 解析失败：{exc}",
            }
        )
        return None


def _max_confidence(left: str, right: str) -> str:
    return left if CONFIDENCE_RANK[left] >= CONFIDENCE_RANK[right] else right


def _merge_fact(
    facts: list[dict[str, Any]],
    name: str,
    evidence: Iterable[str],
    confidence: str,
) -> None:
    values = sorted({value for value in evidence if value})
    for item in facts:
        if item.get("name") == name:
            item["evidence"] = sorted(set(item.get("evidence", [])) | set(values))
            item["confidence"] = _max_confidence(
                str(item.get("confidence", "low")), confidence
            )
            return
    facts.append(
        {"name": name, "evidence": values, "confidence": confidence}
    )


def _merge_command(
    commands: list[dict[str, Any]],
    command: str,
    evidence: Iterable[str],
    confidence: str,
) -> None:
    values = sorted({value for value in evidence if value})
    for item in commands:
        if item.get("command") == command:
            item["evidence"] = sorted(set(item.get("evidence", [])) | set(values))
            item["confidence"] = _max_confidence(
                str(item.get("confidence", "low")), confidence
            )
            return
    commands.append(
        {
            "command": command,
            "evidence": values,
            "confidence": confidence,
        }
    )


def _root_relatives(files: Iterable[str]) -> list[str]:
    return sorted(
        path for path in files if "/" not in path and "\\" not in path
    )


def _basename(path: str) -> str:
    return path.rsplit("/", 1)[-1]


def _package_name_from_python(data: dict[str, Any]) -> str | None:
    project = data.get("project")
    if isinstance(project, dict) and isinstance(project.get("name"), str):
        return project["name"]
    tool = data.get("tool")
    if isinstance(tool, dict):
        poetry = tool.get("poetry")
        if isinstance(poetry, dict) and isinstance(poetry.get("name"), str):
            return poetry["name"]
    return None


def _python_dependencies(data: dict[str, Any]) -> list[str]:
    values: list[str] = []
    project = data.get("project")
    if isinstance(project, dict):
        dependencies = project.get("dependencies")
        if isinstance(dependencies, list):
            values.extend(str(item) for item in dependencies)
        optional = project.get("optional-dependencies")
        if isinstance(optional, dict):
            for items in optional.values():
                if isinstance(items, list):
                    values.extend(str(item) for item in items)
    tool = data.get("tool")
    if isinstance(tool, dict):
        poetry = tool.get("poetry")
        if isinstance(poetry, dict):
            dependencies = poetry.get("dependencies")
            if isinstance(dependencies, dict):
                values.extend(str(name) for name in dependencies)
    build = data.get("build-system")
    if isinstance(build, dict):
        requires = build.get("requires")
        if isinstance(requires, list):
            values.extend(str(item) for item in requires)
    return values


def _dependency_names(values: Iterable[str]) -> set[str]:
    names: set[str] = set()
    for value in values:
        match = re.match(r"\s*([A-Za-z0-9_.-]+)", str(value))
        if match:
            names.add(match.group(1).lower().replace("_", "-"))
    return names


def _detect_python(
    state: dict[str, Any],
    root_files: list[str],
    files: list[str],
    options: ScanOptions,
    stack: list[dict[str, Any]],
    frameworks: list[dict[str, Any]],
    commands: dict[str, list[dict[str, Any]]],
    tests: dict[str, Any],
) -> None:
    limit = options.max_file_bytes
    pyprojects = [path for path in files if _basename(path) == "pyproject.toml"]
    requirements = [
        path
        for path in files
        if re.search(r"(^|/)requirements[^/]*\.txt$", path)
    ]
    setup_files = [
        path
        for path in files
        if _basename(path) in {"setup.py", "setup.cfg"}
    ]
    pytest_inis = [path for path in files if _basename(path) == "pytest.ini"]
    tox_files = [path for path in files if _basename(path) == "tox.ini"]
    evidence = sorted(
        set(pyprojects + requirements + setup_files + pytest_inis + tox_files)
    )
    if not evidence:
        return

    _merge_fact(stack, "python", evidence, "high")
    dependencies: set[str] = set()
    pytest_configured = bool(pytest_inis)
    pytest_evidence: set[str] = set(pytest_inis)

    for relative in pyprojects:
        data = _read_toml(state, relative, limit)
        if not isinstance(data, dict):
            continue
        dependencies |= _dependency_names(_python_dependencies(data))
        tool = data.get("tool")
        if isinstance(tool, dict):
            pytest_config = tool.get("pytest")
            if isinstance(pytest_config, dict):
                pytest_configured = True
                pytest_evidence.add(relative)
            for name in ("ruff", "black", "mypy", "flake8", "isort", "pylint"):
                if name in tool:
                    _merge_fact(frameworks, name, [relative], "high")
            coverage = tool.get("coverage")
            if isinstance(coverage, dict):
                tests["coverage"].append(relative)
        if "pytest" in dependencies:
            pytest_evidence.add(relative)

    for relative in requirements:
        text = _read_text(state, relative, limit)
        if text is None:
            continue
        for raw in text.splitlines():
            line = raw.split("#", 1)[0].strip()
            if line and not line.startswith("-"):
                dependencies.add(
                    re.split(r"[<>=!~;\[]", line, maxsplit=1)[0]
                    .strip()
                    .lower()
                    .replace("_", "-")
                )

    for relative in tox_files:
        text = _read_text(state, relative, limit)
        if text and re.search(r"\bpytest\b", text):
            pytest_configured = True
            pytest_evidence.add(relative)

    for name in (
        "django",
        "flask",
        "fastapi",
        "starlette",
        "sqlalchemy",
        "pydantic",
        "celery",
        "click",
    ):
        if name in dependencies:
            _merge_fact(frameworks, name, evidence, "medium")
    if "pytest" in dependencies:
        pytest_evidence.update(evidence)

    if pytest_configured or "pytest" in dependencies:
        tests["frameworks"].append("pytest")
        _merge_fact(tests["framework_facts"], "pytest", pytest_evidence or evidence, "high" if pytest_configured else "medium")
        _merge_command(
            commands["test"],
            "python -m pytest -q",
            pytest_evidence or evidence,
            "high" if pytest_configured else "medium",
        )
    elif any(path.startswith(("tests/", "test/")) for path in files):
        tests["frameworks"].append("unittest")
        test_evidence = sorted(
            {
                path.split("/", 1)[0]
                for path in files
                if path.startswith(("tests/", "test/"))
            }
            | set(evidence)
        )
        _merge_fact(tests["framework_facts"], "unittest", test_evidence, "low")
        _merge_command(
            commands["test"],
            "python -m unittest discover -s tests -v",
            test_evidence,
            "low",
        )

    if any(name in dependencies for name in ("ruff", "black", "flake8", "pylint")):
        _merge_command(commands["lint"], "python -m ruff check .", evidence, "low")
    if pyprojects:
        _merge_command(
            commands["build"],
            "python -m build",
            pyprojects,
            "medium",
        )


def _detect_sdd_config(
    state: dict[str, Any],
    files: list[str],
    options: ScanOptions,
    commands: dict[str, list[dict[str, Any]]],
    tests: dict[str, Any],
) -> None:
    if "sdd/config.json" not in files:
        return
    data = _read_json(state, "sdd/config.json", options.max_file_bytes)
    if not isinstance(data, dict):
        return
    configured = data.get("test_commands")
    if not isinstance(configured, list):
        return
    for command in configured:
        if isinstance(command, str) and command.strip():
            _merge_command(
                commands["test"],
                command.strip(),
                ["sdd/config.json"],
                "high",
            )


def _node_runner(root: Path, files: list[str]) -> str:
    names = {_basename(path) for path in files}
    if "pnpm-lock.yaml" in names:
        return "pnpm"
    if "yarn.lock" in names:
        return "yarn"
    return "npm"


def _detect_node(
    state: dict[str, Any],
    root_files: list[str],
    files: list[str],
    options: ScanOptions,
    stack: list[dict[str, Any]],
    frameworks: list[dict[str, Any]],
    commands: dict[str, list[dict[str, Any]]],
    tests: dict[str, Any],
) -> set[str]:
    limit = options.max_file_bytes
    packages = [
        path
        for path in files
        if _basename(path) == "package.json"
        and (
            "/" not in path
            or re.match(r"^(packages|apps|services)/[^/]+/package\.json$", path)
        )
    ]
    configs = [
        path
        for path in root_files
        if re.match(r"^(vite\.config\.|next\.config\.)", _basename(path))
    ]
    workspace_files = [
        path
        for path in root_files
        if _basename(path)
        in {"pnpm-workspace.yaml", "pnpm-workspace.yml", "lerna.json"}
    ]
    if not packages and not configs and not workspace_files:
        return set()

    evidence = sorted(set(packages + configs + workspace_files))
    _merge_fact(stack, "node", evidence, "high")
    runner = _node_runner(state["path"], files)
    package_names: set[str] = set()
    dependencies: set[str] = set()
    for relative in packages:
        data = _read_json(state, relative, limit)
        if not isinstance(data, dict):
            continue
        name = data.get("name")
        if isinstance(name, str):
            package_names.add(name)
        for key in ("dependencies", "devDependencies", "peerDependencies"):
            values = data.get(key)
            if isinstance(values, dict):
                dependencies.update(str(item).lower() for item in values)
        scripts = data.get("scripts")
        if isinstance(scripts, dict):
            if isinstance(scripts.get("test"), str):
                _merge_command(
                    commands["test"],
                    f"{runner} test",
                    [relative],
                    "high",
                )
                _merge_fact(
                    tests["framework_facts"],
                    _node_test_framework(dependencies),
                    [relative],
                    "medium",
                )
            if isinstance(scripts.get("build"), str):
                _merge_command(
                    commands["build"],
                    f"{runner} run build",
                    [relative],
                    "high",
                )
            if isinstance(scripts.get("lint"), str):
                _merge_command(
                    commands["lint"],
                    f"{runner} run lint",
                    [relative],
                    "high",
                )
        workspaces = data.get("workspaces")
        if isinstance(workspaces, (list, dict)):
            _merge_fact(frameworks, "workspaces", [relative], "high")

    for name in (
        "react",
        "vue",
        "svelte",
        "next",
        "nuxt",
        "vite",
        "typescript",
        "express",
        "nestjs",
        "angular",
        "jest",
        "vitest",
        "mocha",
        "playwright",
        "cypress",
    ):
        if name in dependencies:
            _merge_fact(
                frameworks,
                name,
                evidence,
                "high" if packages else "medium",
            )
    for name in ("jest", "vitest", "mocha", "playwright", "cypress", "node:test"):
        if name == "node:test":
            continue
        if name in dependencies:
            tests["frameworks"].append(name)
            _merge_fact(
                tests["framework_facts"],
                name,
                evidence,
                "high",
            )
    for relative in files:
        name = _basename(relative)
        if name.startswith(("jest.config.", "vitest.config.", "playwright.config.")):
            tests["coverage"].append(relative)
        if name in {".nycrc", ".nycrc.json", "codecov.yml", ".codecov.yml"}:
            tests["coverage"].append(relative)
    if packages and not commands["test"]:
        tests["frameworks"].append("node")
        _merge_fact(tests["framework_facts"], "node", packages, "low")
    return package_names


def _node_test_framework(dependencies: set[str]) -> str:
    for name in ("vitest", "jest", "mocha", "playwright", "cypress"):
        if name in dependencies:
            return name
    return "node"


def _detect_java(
    state: dict[str, Any],
    root_files: list[str],
    files: list[str],
    options: ScanOptions,
    stack: list[dict[str, Any]],
    frameworks: list[dict[str, Any]],
    commands: dict[str, list[dict[str, Any]]],
    tests: dict[str, Any],
) -> None:
    limit = options.max_file_bytes
    poms = [path for path in files if _basename(path) == "pom.xml"]
    gradles = [
        path
        for path in files
        if _basename(path) in {"build.gradle", "build.gradle.kts"}
        or _basename(path) in {"settings.gradle", "settings.gradle.kts"}
    ]
    if not poms and not gradles:
        return
    evidence = sorted(set(poms + gradles))
    _merge_fact(stack, "java", evidence, "high")
    gradlew = any(_basename(path) in {"gradlew", "gradlew.bat"} for path in files)

    for relative in poms:
        root = _read_xml(state, relative, limit)
        if root is None:
            continue
        artifacts = {
            (element.text or "").strip().lower()
            for element in root.iter()
            if _local_name(element.tag) in {"artifactId", "groupId"}
        }
        if any("spring" in value for value in artifacts):
            _merge_fact(frameworks, "spring", [relative], "high")
        if any(
            value in {"junit", "junit-jupiter", "testng"}
            or value.startswith("junit")
            for value in artifacts
        ):
            tools = (
                "junit"
                if any(value.startswith("junit") for value in artifacts)
                else "testng"
            )
            tests["frameworks"].append(tools)
            _merge_fact(tests["framework_facts"], tools, [relative], "high")
        for name in ("surefire", "failsafe", "jacoco", "checkstyle", "spotbugs"):
            if name in artifacts:
                _merge_fact(frameworks, name, [relative], "high")
        _merge_command(commands["test"], "mvn test", [relative], "medium")
        _merge_command(commands["build"], "mvn package", [relative], "medium")
        if "checkstyle" in artifacts:
            _merge_command(
                commands["lint"],
                "mvn checkstyle:check",
                [relative],
                "high",
            )

    for relative in gradles:
        text = _read_text(state, relative, limit)
        if text is None:
            continue
        lowered = text.lower()
        if "spring" in lowered:
            _merge_fact(frameworks, "spring", [relative], "high")
        if "junit" in lowered:
            tests["frameworks"].append("junit")
            _merge_fact(tests["framework_facts"], "junit", [relative], "high")
        command_evidence = [relative]
        if gradlew:
            wrapper = next(
                (
                    path
                    for path in files
                    if _basename(path) in {"gradlew", "gradlew.bat"}
                ),
                None,
            )
            prefix = "./gradlew" if wrapper == "gradlew" else "gradlew.bat"
            confidence = "medium"
            if wrapper:
                command_evidence.append(wrapper)
        else:
            prefix = "gradle"
            confidence = "medium"
        _merge_command(
            commands["test"], f"{prefix} test", command_evidence, confidence
        )
        _merge_command(
            commands["build"], f"{prefix} build", command_evidence, confidence
        )


def _detect_go(
    state: dict[str, Any],
    root_files: list[str],
    files: list[str],
    options: ScanOptions,
    stack: list[dict[str, Any]],
    frameworks: list[dict[str, Any]],
    commands: dict[str, list[dict[str, Any]]],
    tests: dict[str, Any],
) -> set[str]:
    limit = options.max_file_bytes
    mods = [path for path in files if _basename(path) == "go.mod"]
    works = [path for path in files if _basename(path) == "go.work"]
    if not mods and not works:
        return set()
    evidence = sorted(set(mods + works))
    _merge_fact(stack, "go", evidence, "high")
    module_name: str | None = None
    dependencies: set[str] = set()
    for relative in mods:
        text = _read_text(state, relative, limit)
        if text is None:
            continue
        for raw in text.splitlines():
            line = raw.strip()
            if line.startswith("module "):
                module_name = line.split(None, 1)[1].strip()
            elif line and not line.startswith("//") and not line.startswith(
                ("module", "go ", "require", "replace", "exclude", "retract")
            ):
                dependencies.add(line.split()[0].lower())
        for name in ("gin-gonic", "echo", "fiber", "gorm", "grpc"):
            if any(name in dependency for dependency in dependencies):
                _merge_fact(frameworks, name, [relative], "medium")
    tests["frameworks"].append("go test")
    _merge_fact(tests["framework_facts"], "go test", evidence, "high")
    _merge_command(commands["test"], "go test ./...", evidence, "medium")
    _merge_command(commands["build"], "go build ./...", evidence, "medium")
    _merge_command(commands["lint"], "go vet ./...", evidence, "medium")
    return {module_name.rsplit("/", 1)[-1].lower()} if module_name else set()


def _detect_rust(
    state: dict[str, Any],
    root_files: list[str],
    files: list[str],
    options: ScanOptions,
    stack: list[dict[str, Any]],
    frameworks: list[dict[str, Any]],
    commands: dict[str, list[dict[str, Any]]],
    tests: dict[str, Any],
) -> set[str]:
    limit = options.max_file_bytes
    manifests = [path for path in files if _basename(path) == "Cargo.toml"]
    locks = [path for path in files if _basename(path) == "Cargo.lock"]
    if not manifests:
        return set()
    evidence = sorted(set(manifests + locks))
    _merge_fact(stack, "rust", evidence, "high")
    package_names: set[str] = set()
    for relative in manifests:
        data = _read_toml(state, relative, limit)
        if not isinstance(data, dict):
            continue
        package = data.get("package")
        if isinstance(package, dict) and isinstance(package.get("name"), str):
            package_names.add(package["name"].lower())
        if isinstance(data.get("workspace"), dict):
            _merge_fact(frameworks, "workspaces", [relative], "high")
    tests["frameworks"].append("cargo test")
    _merge_fact(tests["framework_facts"], "cargo test", evidence, "high")
    _merge_command(commands["test"], "cargo test", evidence, "medium")
    _merge_command(commands["build"], "cargo build", evidence, "medium")
    _merge_command(
        commands["lint"], "cargo clippy -- -D warnings", evidence, "medium"
    )
    return package_names


def _detect_dotnet(
    state: dict[str, Any],
    root_files: list[str],
    files: list[str],
    options: ScanOptions,
    stack: list[dict[str, Any]],
    frameworks: list[dict[str, Any]],
    commands: dict[str, list[dict[str, Any]]],
    tests: dict[str, Any],
) -> None:
    limit = options.max_file_bytes
    solutions = [
        path for path in files if _basename(path).lower().endswith(".sln")
    ]
    projects = [
        path for path in files if _basename(path).lower().endswith(".csproj")
    ]
    if not solutions and not projects:
        return
    evidence = sorted(set(solutions + projects))
    _merge_fact(stack, "dotnet", evidence, "high")
    for relative in projects:
        root = _read_xml(state, relative, limit)
        if root is None:
            continue
        text = (root.findtext(".//TargetFramework") or "").strip()
        if text:
            _merge_fact(frameworks, text.lower(), [relative], "high")
        for element in root.iter():
            if _local_name(element.tag) != "PackageReference":
                continue
            name = (element.attrib.get("Include") or "").lower()
            if name in {"xunit", "nunit", "mstest.testframework"}:
                tests["frameworks"].append(name)
                _merge_fact(tests["framework_facts"], name, [relative], "high")
    _merge_command(commands["test"], "dotnet test", evidence, "medium")
    _merge_command(commands["build"], "dotnet build", evidence, "medium")


def _detect_other(
    state: dict[str, Any],
    root_files: list[str],
    files: list[str],
    options: ScanOptions,
    stack: list[dict[str, Any]],
    frameworks: list[dict[str, Any]],
    commands: dict[str, list[dict[str, Any]]],
    tests: dict[str, Any],
) -> set[str]:
    limit = options.max_file_bytes
    package_names: set[str] = set()
    composer = [path for path in files if _basename(path) == "composer.json"]
    gemfiles = [path for path in files if _basename(path) == "Gemfile"]
    makefiles = [
        path
        for path in files
        if _basename(path) in {"Makefile", "makefile"}
    ]
    for relative in composer:
        _merge_fact(stack, "php", [relative], "high")
        data = _read_json(state, relative, limit)
        if isinstance(data, dict):
            name = data.get("name")
            if isinstance(name, str):
                package_names.add(name.lower())
            scripts = data.get("scripts")
            if isinstance(scripts, dict):
                if isinstance(scripts.get("test"), (str, list)):
                    _merge_command(
                        commands["test"], "composer test", [relative], "high"
                    )
                if isinstance(scripts.get("lint"), (str, list)):
                    _merge_command(
                        commands["lint"], "composer lint", [relative], "high"
                    )
            require = data.get("require")
            require_dev = data.get("require-dev")
            dependencies: set[str] = set()
            for values in (require, require_dev):
                if isinstance(values, dict):
                    dependencies.update(str(key).lower() for key in values)
            if "phpunit/phpunit" in dependencies:
                tests["frameworks"].append("phpunit")
                _merge_fact(
                    tests["framework_facts"],
                    "phpunit",
                    [relative],
                    "high",
                )
                _merge_command(
                    commands["test"],
                    "vendor/bin/phpunit",
                    [relative],
                    "medium",
                )
    for relative in gemfiles:
        _merge_fact(stack, "ruby", [relative], "high")
        text = _read_text(state, relative, limit) or ""
        if re.search(r"\brspec\b", text):
            tests["frameworks"].append("rspec")
            _merge_fact(tests["framework_facts"], "rspec", [relative], "high")
            _merge_command(
                commands["test"], "bundle exec rspec", [relative], "medium"
            )
        if re.search(r"\brails\b", text):
            _merge_fact(frameworks, "rails", [relative], "high")
    for relative in makefiles:
        text = _read_text(state, relative, limit) or ""
        targets = {
            match.group(1)
            for match in re.finditer(
                r"^([A-Za-z0-9_.-]+)\s*:(?!=)", text, re.MULTILINE
            )
        }
        for target in ("test", "build", "lint"):
            if target in targets:
                _merge_command(
                    commands[target], f"make {target}", [relative], "high"
                )
        if "test" in targets:
            tests["frameworks"].append("make")
            _merge_fact(tests["framework_facts"], "make", [relative], "high")
    return package_names


def _detect_docker(
    state: dict[str, Any],
    root_files: list[str],
    files: list[str],
    options: ScanOptions,
    stack: list[dict[str, Any]],
    entrypoints: list[dict[str, Any]],
    services: list[dict[str, Any]],
    data: dict[str, Any],
) -> None:
    limit = options.max_file_bytes
    dockerfiles = [
        path
        for path in files
        if _basename(path) == "Dockerfile"
        or _basename(path).startswith("Dockerfile.")
    ]
    compose_files = [
        path
        for path in files
        if re.match(r"^(docker-)?compose[^/]*\.ya?ml$", _basename(path))
    ]
    for relative in dockerfiles:
        _merge_fact(stack, "docker", [relative], "high")
        text = _read_text(state, relative, limit) or ""
        for line in text.splitlines():
            match = re.match(
                r"^\s*(CMD|ENTRYPOINT)\s+(.+)$", line, re.IGNORECASE
            )
            if not match:
                continue
            command = match.group(2).strip()
            entrypoints.append(
                {
                    "path": relative,
                    "kind": "docker",
                    "command": command,
                    "confidence": "high",
                    "evidence": [relative],
                }
            )
            break
    for relative in compose_files:
        _merge_fact(stack, "docker-compose", [relative], "high")
        text = _read_text(state, relative, limit)
        if text is None:
            continue
        parsed = _parse_compose(text, relative)
        for service in parsed:
            services.append(service)
            image = (service.get("image") or "").lower()
            for kind in (
                "postgres",
                "postgresql",
                "mysql",
                "mariadb",
                "redis",
                "kafka",
                "rabbitmq",
                "mongo",
                "elasticsearch",
                "minio",
            ):
                if kind in image:
                    _merge_fact(data["infra"], kind, [relative], "high")


def _parse_compose(text: str, relative: str) -> list[dict[str, Any]]:
    services: dict[str, dict[str, Any]] = {}
    in_services = False
    current: dict[str, Any] | None = None
    current_key: str | None = None
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()
        if indent == 0:
            in_services = stripped == "services:"
            current = None
            current_key = None
            continue
        if not in_services:
            continue
        if indent == 2 and stripped.endswith(":") and not stripped.startswith("-"):
            name = stripped[:-1].strip().strip("\"'")
            current = {
                "name": name,
                "image": None,
                "ports": [],
                "depends_on": [],
                "evidence": [relative],
                "confidence": "high",
            }
            services[name] = current
            current_key = None
            continue
        if current is None:
            continue
        if indent == 4:
            if stripped.endswith(":"):
                current_key = stripped[:-1].strip()
                continue
            if ":" in stripped:
                key, value = stripped.split(":", 1)
                key = key.strip()
                value = value.strip().strip("\"'")
                current_key = None
                if key == "image":
                    current["image"] = value
                elif key in {"ports", "depends_on"}:
                    current[key] = _inline_list(value) or current[key]
            continue
        if stripped.startswith("-") and current_key in {"ports", "depends_on"}:
            value = stripped[1:].strip().strip("\"'")
            if current_key == "ports":
                current["ports"].append(value)
            else:
                current["depends_on"].append(value.split(":", 1)[0].strip())
        elif (
            current_key == "depends_on"
            and indent == 6
            and stripped.endswith(":")
        ):
            current["depends_on"].append(stripped[:-1].strip().strip("\"'"))
    return [services[name] for name in sorted(services)]


def _inline_list(value: str) -> list[str]:
    if value.startswith("[") and value.endswith("]"):
        return [
            item.strip().strip("\"'")
            for item in value[1:-1].split(",")
            if item.strip()
        ]
    return []


def _detect_files(
    root: Path,
    state: dict[str, Any],
    root_files: list[str],
    files: list[str],
    options: ScanOptions,
    payload: dict[str, Any],
) -> None:
    tests = payload["tests"]
    test_dirs = sorted(
        {
            part
            for path in files
            for part in [path.split("/", 1)[0]]
            if part in {"tests", "test", "__tests__", "spec"}
        }
    )
    for name in ("tests", "test", "__tests__", "spec"):
        if (root / name).is_dir() and name not in test_dirs:
            test_dirs.append(name)
    tests["directories"] = sorted(test_dirs)
    tests["files"] = sorted(path for path in files if TEST_FILE_RE.search(path))

    for name in (".coveragerc", "coverage.xml", ".nycrc", ".nycrc.json"):
        if (root / name).is_file():
            tests["coverage"].append(name)
    for path in files:
        basename = _basename(path)
        if basename.startswith(
            ("jest.config.", "vitest.config.", "playwright.config.")
        ):
            tests["coverage"].append(path)
    tests["coverage"] = sorted(set(tests["coverage"]))
    tests["frameworks"] = sorted(set(tests["frameworks"]))


def _detect_contracts(
    state: dict[str, Any],
    files: list[str],
    options: ScanOptions,
) -> list[dict[str, Any]]:
    contracts: list[dict[str, Any]] = []
    for relative in files:
        name = _basename(relative).lower()
        stem = name.rsplit(".", 1)[0]
        kind: str | None = None
        if name.endswith((".yaml", ".yml", ".json")) and (
            "openapi" in stem or "swagger" in stem
        ):
            kind = "openapi"
        elif name.endswith(".proto"):
            kind = "protobuf"
        elif name.endswith((".graphql", ".gql")):
            kind = "graphql"
        elif "asyncapi" in stem and name.endswith((".yaml", ".yml", ".json")):
            kind = "asyncapi"
        elif name.endswith(".json") and (
            "schema" in stem or "/schemas/" in relative.lower()
        ):
            kind = "json-schema"
        if kind is None:
            continue
        item: dict[str, Any] = {
            "type": kind,
            "path": relative,
            "confidence": "high",
            "evidence": [f"{state['prefix']}{relative}"],
        }
        if options.deep:
            text = _read_text(state, relative, options.max_file_bytes)
            if text is not None:
                item["format"] = (
                    "json"
                    if name.endswith(".json")
                    else "yaml"
                    if name.endswith((".yaml", ".yml"))
                    else "text"
                )
                version = _contract_version(kind, text)
                if version:
                    item["version"] = version
        contracts.append(item)
    return contracts


def _contract_version(kind: str, text: str) -> str | None:
    if kind == "openapi":
        match = re.search(r'["\']?openapi["\']?\s*:\s*["\']?([0-9][^,\s"\']*)', text)
        return match.group(1) if match else None
    if kind == "asyncapi":
        match = re.search(r'["\']?asyncapi["\']?\s*:\s*["\']?([0-9][^,\s"\']*)', text)
        return match.group(1) if match else None
    return None


def _detect_entrypoints(
    state: dict[str, Any],
    files: list[str],
    options: ScanOptions,
) -> list[dict[str, Any]]:
    patterns: list[tuple[re.Pattern[str], str, str]] = [
        (re.compile(r"(^|/)(main|app|manage)\.py$"), "python", "medium"),
        (re.compile(r"^src/main/java/.+/Application\.java$"), "java", "medium"),
        (re.compile(r"(^|/)cmd/.+/main\.go$"), "go", "medium"),
        (re.compile(r"(^|/)(main|Program)\.cs$"), "dotnet", "medium"),
        (re.compile(r"^src/(index|main)\.ts$"), "typescript", "medium"),
        (re.compile(r"^src/(index|main)\.js$"), "javascript", "medium"),
        (re.compile(r"(^|/)main\.go$"), "go", "low"),
    ]
    entrypoints: list[dict[str, Any]] = []
    seen: set[str] = set()
    for relative in files:
        for pattern, kind, confidence in patterns:
            if not pattern.search(relative) or relative in seen:
                continue
            seen.add(relative)
            item: dict[str, Any] = {
                "path": relative,
                "kind": kind,
                "confidence": confidence,
                "evidence": [f"{state['prefix']}{relative}"],
            }
            if options.deep:
                text = _read_text(state, relative, options.max_file_bytes)
                signals = _entry_signals(kind, text or "")
                if signals:
                    item["signals"] = signals
            entrypoints.append(item)
            break
    return entrypoints


def _entry_signals(kind: str, text: str) -> list[str]:
    signals: list[str] = []
    if kind == "python" and re.search(
        r"if\s+__name__\s*==\s*[\"']__main__[\"']", text
    ):
        signals.append("python_main_guard")
    if kind == "java" and "@SpringBootApplication" in text:
        signals.append("spring_boot")
    if kind == "go" and re.search(r"func\s+main\s*\(", text):
        signals.append("go_main")
    if kind == "dotnet" and re.search(
        r"static\s+(?:async\s+)?(?:void|Task(?:<int>)?)\s+Main\s*\(", text
    ):
        signals.append("dotnet_main")
    if kind in {"typescript", "javascript"} and re.search(
        r"\.listen\s*\(", text
    ):
        signals.append("node_listen")
    return signals


def _detect_data(
    root: Path,
    state: dict[str, Any],
    files: list[str],
    payload: dict[str, Any],
) -> None:
    data = payload["data"]
    migrations = sorted(
        {
            path
            for path in files
            if any(
                part.lower()
                in {"migrations", "migration", "migrate", "alembic", "flyway"}
                for part in PurePosixPath(path).parts[:-1]
            )
        }
    )
    if migrations:
        data["migrations"] = sorted(
            {
                str(PurePosixPath(path).parent)
                for path in migrations
                if str(PurePosixPath(path).parent) != "."
            }
        )
    orm_patterns = {
        "alembic.ini": "alembic",
        "prisma/schema.prisma": "prisma",
        "ormconfig.json": "typeorm",
        "ormconfig.js": "typeorm",
        "ormconfig.ts": "typeorm",
        "hibernate.cfg.xml": "hibernate",
        "mybatis-config.xml": "mybatis",
        "knexfile.js": "knex",
        "knexfile.ts": "knex",
        "drizzle.config.ts": "drizzle",
        "drizzle.config.js": "drizzle",
    }
    found: dict[str, list[str]] = {}
    for relative in files:
        kind = orm_patterns.get(relative)
        if kind is None and relative.endswith("/schema.prisma"):
            kind = "prisma"
        if kind is None and _basename(relative).startswith("sequelize"):
            kind = "sequelize"
        if kind is None and _basename(relative).startswith("typeorm"):
            kind = "typeorm"
        if kind:
            found.setdefault(kind, []).append(relative)
    data["orm"] = [
        {
            "kind": kind,
            "path": path,
            "confidence": "high",
            "evidence": [f"{state['prefix']}{path}"],
        }
        for kind in sorted(found)
        for path in sorted(found[kind])
    ]


def _detect_docs(
    root: Path,
    state: dict[str, Any],
    files: list[str],
    options: ScanOptions,
) -> dict[str, Any]:
    specs: list[dict[str, Any]] = []
    specs_root = root / "docs" / "specs"
    if specs_root.is_dir() and not specs_root.is_symlink():
        try:
            spec_dirs = sorted(
                path
                for path in specs_root.iterdir()
                if path.is_dir()
                and path.name.startswith("SPEC-")
                and not path.is_symlink()
            )
        except OSError:
            spec_dirs = []
        for spec_dir in spec_dirs:
            spec_state: dict[str, Any] = {}
            state_path = spec_dir / "state.json"
            if state_path.is_file() and not state_path.is_symlink():
                parsed = _read_json(
                    state,
                    f"docs/specs/{spec_dir.name}/state.json",
                    options.max_file_bytes,
                )
                if isinstance(parsed, dict):
                    spec_state = parsed
            updated_at = spec_state.get("updated_at")
            if not isinstance(updated_at, str):
                latest = _latest_file_mtime(spec_dir)
                if latest is not None:
                    updated_at = (
                        datetime.fromtimestamp(latest)
                        .astimezone()
                        .isoformat(timespec="seconds")
                    )
            specs.append(
                {
                    "id": spec_dir.name,
                    "path": f"docs/specs/{spec_dir.name}",
                    "state": spec_state.get("state"),
                    "title": spec_state.get("title"),
                    "updated_at": updated_at,
                }
            )

    def existing(*candidates: str) -> list[str]:
        result = [
            relative
            for relative in candidates
            if (root / relative).is_file()
            and not (root / relative).is_symlink()
        ]
        return result

    prd_index = existing("docs/prd-index.md")
    agents = existing("AGENTS.md")
    readme = existing("README.md", "README.rst")
    codeowners = existing(
        "CODEOWNERS", ".github/CODEOWNERS", "docs/CODEOWNERS"
    )
    contributing = existing(
        "CONTRIBUTING.md",
        "CONTRIBUTING.rst",
        ".github/CONTRIBUTING.md",
        "docs/CONTRIBUTING.md",
    )
    context_root = root / "sdd" / "context"
    context_files = sorted(
        path
        for path in files
        if path.startswith("sdd/context/") and not _basename(path).startswith(".")
    )
    services_yaml = next(
        (
            path
            for path in context_files
            if path in {"sdd/context/services.yaml", "sdd/context/services.yml"}
        ),
        None,
    )

    def under(prefix: str) -> list[str]:
        return sorted(
            path
            for path in context_files
            if path.startswith(prefix) and _basename(path) != ".gitkeep"
        )

    return {
        "specs": specs,
        "prd_index": bool(prd_index),
        "prd_index_path": prd_index[0] if prd_index else None,
        "context_files": context_files,
        "services_yaml": services_yaml,
        "service_cards": under("sdd/context/services/"),
        "contracts": under("sdd/context/contracts/"),
        "adrs": under("sdd/context/adr/"),
        "agents_md": agents,
        "readme": readme,
        "codeowners": codeowners,
        "contributing": contributing,
        "sdd_initialized": (root / "sdd" / "config.json").is_file(),
    }


def _latest_file_mtime(directory: Path) -> float | None:
    latest: float | None = None
    for dirpath, dirnames, filenames in os.walk(
        directory, followlinks=False
    ):
        base = Path(dirpath)
        dirnames[:] = [
            name for name in dirnames if not (base / name).is_symlink()
        ]
        for name in filenames:
            path = base / name
            if path.is_symlink():
                continue
            try:
                value = path.stat().st_mtime
            except OSError:
                continue
            if latest is None or value > latest:
                latest = value
    return latest


def _detect_ci(
    state: dict[str, Any],
    files: list[str],
    options: ScanOptions,
) -> list[dict[str, Any]]:
    ci: list[dict[str, Any]] = []
    github = [
        path
        for path in files
        if re.match(r"^\.github/workflows/[^/]+\.ya?ml$", path)
    ]
    for relative in github:
        text = _read_text(state, relative, options.max_file_bytes)
        if text is None:
            continue
        ci.append(
            {
                "provider": "github-actions",
                "path": relative,
                "jobs": _parse_github_jobs(text, relative),
            }
        )
    if ".gitlab-ci.yml" in files:
        text = _read_text(state, ".gitlab-ci.yml", options.max_file_bytes)
        if text is not None:
            ci.append(
                {
                    "provider": "gitlab-ci",
                    "path": ".gitlab-ci.yml",
                    "jobs": _parse_gitlab_jobs(text, ".gitlab-ci.yml"),
                }
            )
    if "Jenkinsfile" in files:
        text = _read_text(state, "Jenkinsfile", options.max_file_bytes)
        if text is not None:
            ci.append(
                {
                    "provider": "jenkins",
                    "path": "Jenkinsfile",
                    "jobs": _parse_jenkins_jobs(text, "Jenkinsfile"),
                }
            )
    return ci


def _parse_github_jobs(text: str, relative: str) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    in_jobs = False
    current: str | None = None
    block: list[str] = []

    def flush() -> None:
        nonlocal current, block
        if current is not None:
            body = "\n".join(block)
            jobs.append(
                {
                    "name": current,
                    "runs_tests": _looks_like_test_job(current, body),
                    "evidence": [relative],
                }
            )
        current = None
        block = []

    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        stripped = raw.strip()
        if indent == 0:
            flush()
            in_jobs = stripped == "jobs:"
            continue
        if not in_jobs:
            continue
        if indent == 2 and stripped.endswith(":") and not stripped.startswith("-"):
            flush()
            current = stripped[:-1].strip().strip("\"'")
        elif current is not None:
            block.append(raw)
    flush()
    return jobs


def _parse_gitlab_jobs(text: str, relative: str) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    reserved = {
        "stages",
        "variables",
        "image",
        "services",
        "before_script",
        "after_script",
        "cache",
        "include",
        "default",
        "workflow",
        "pages",
    }
    current: str | None = None
    block: list[str] = []

    def flush() -> None:
        nonlocal current, block
        if current is not None:
            body = "\n".join(block)
            jobs.append(
                {
                    "name": current,
                    "runs_tests": _looks_like_test_job(current, body),
                    "evidence": [relative],
                }
            )
        current = None
        block = []

    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if not raw.startswith((" ", "\t")):
            stripped = raw.strip()
            if stripped.endswith(":") and not stripped.startswith("-"):
                name = stripped[:-1].strip()
                flush()
                if name and name not in reserved:
                    current = name
                continue
            if stripped == "---":
                flush()
        elif current is not None:
            block.append(raw)
    flush()
    return jobs


def _parse_jenkins_jobs(text: str, relative: str) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    matches = list(re.finditer(r"stage\s*\(\s*['\"]([^'\"]+)['\"]\s*\)", text))
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[start:end]
        jobs.append(
            {
                "name": match.group(1),
                "runs_tests": _looks_like_test_job(match.group(1), body),
                "evidence": [relative],
            }
        )
    if not jobs and TEST_COMMAND_RE.search(text):
        jobs.append(
            {
                "name": "pipeline",
                "runs_tests": True,
                "evidence": [relative],
            }
        )
    return jobs


def _looks_like_test_job(name: str, body: str) -> bool:
    if "test" in name.lower() or name.lower() in {"ci", "unittest"}:
        return True
    return bool(TEST_COMMAND_RE.search(body))


def _is_secret(path: str) -> bool:
    name = _basename(path).lower()
    if name == ".env" or name.startswith(".env."):
        return True
    if any(name.endswith(suffix) for suffix in SECRET_SUFFIXES):
        return True
    if any(name.startswith(prefix) for prefix in SECRET_PREFIXES):
        return True
    return False


def _package_managers(files: list[str]) -> tuple[list[str], list[str]]:
    managers: list[str] = []
    locks: list[str] = []
    names = {_basename(path) for path in files}
    if "package-lock.json" in names:
        managers.append("npm")
        locks.append("package-lock.json")
    if "pnpm-lock.yaml" in names:
        managers.append("pnpm")
        locks.append("pnpm-lock.yaml")
    if "yarn.lock" in names:
        managers.append("yarn")
        locks.append("yarn.lock")
    if "bun.lockb" in names:
        managers.append("bun")
        locks.append("bun.lockb")
    if "poetry.lock" in names:
        managers.append("poetry")
        locks.append("poetry.lock")
    if "Pipfile.lock" in names:
        managers.append("pipenv")
        locks.append("Pipfile.lock")
    if "uv.lock" in names:
        managers.append("uv")
        locks.append("uv.lock")
    return managers, locks


def _compute_languages(files: Iterable[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for path in files:
        suffix = PurePosixPath(path).suffix.lower()
        language = LANGUAGE_BY_SUFFIX.get(suffix)
        if language:
            counts[language] = counts.get(language, 0) + 1
    return {name: counts[name] for name in sorted(counts)}


def _scan_repo(
    root: Root,
    options: ScanOptions,
    multi: bool,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    state: dict[str, Any] = {
        "id": root.id,
        "path": root.path,
        "prefix": f"{root.id}/" if multi else "",
        "warnings": [],
        "bytes_read": 0,
    }
    git = _git_identity(root.path, state)
    if git is None:
        state["warnings"].append(
            {
                "repo": root.id,
                "path": "",
                "message": "目标目录不是 Git 仓库，已使用有界目录遍历",
            }
        )
    git_files = _git_inventory(root.path, state)
    skipped_dirs: list[str] = []
    if git_files is None:
        all_files, skipped_dirs = _walk_inventory(root.path, state, options)
    else:
        all_files = git_files
    all_files = sorted(
        {
            _posix(path)
            for path in all_files
            if path
            and not path.startswith("/")
            and (root.path / path).is_file()
            and not (root.path / path).is_symlink()
        }
    )
    selected = [path for path in all_files if _selected(path, options)]
    scanned = selected[: options.max_files]
    skipped = max(0, len(selected) - len(scanned))
    truncated = skipped > 0
    if truncated:
        state["warnings"].append(
            {
                "repo": root.id,
                "path": "",
                "message": (
                    f"文件数超过 --max-files={options.max_files}，"
                    f"仍有 {skipped} 个文件未扫描"
                ),
            }
        )

    for path in all_files:
        for part in PurePosixPath(path).parts[:-1]:
            if part.lower() in EXCLUDED_DIRS and part.lower() != ".git":
                skipped_dirs.append(str(PurePosixPath(path).parent))
                break
    for name in LARGE_DIRS:
        if (root.path / name).is_dir():
            skipped_dirs.append(name)
    skipped_dirs = sorted(set(skipped_dirs))

    size_bytes = 0
    for path in scanned:
        try:
            stat_result = (root.path / path).stat()
            if not (root.path / path).is_symlink():
                size_bytes += stat_result.st_size
        except OSError as exc:
            state["warnings"].append(
                {
                    "repo": root.id,
                    "path": path,
                    "message": f"文件大小读取失败：{exc.__class__.__name__}",
                }
            )

    root_files = _root_relatives(scanned)
    payload: dict[str, Any] = {
        "id": root.id,
        "role": root.role,
        "path": root.display,
        "git": git,
        "size_bytes": size_bytes,
        "files": len(scanned),
        "languages": _compute_languages(scanned),
        "stack": [],
        "frameworks": [],
        "entrypoints": [],
        "services": [],
        "tests": {
            "frameworks": [],
            "framework_facts": [],
            "directories": [],
            "files": [],
            "coverage": [],
            "commands": [],
        },
        "commands": {"build": [], "test": [], "lint": []},
        "contracts": [],
        "data": {"migrations": [], "orm": [], "infra": []},
        "docs": {},
        "sdd": {},
        "ci": [],
    }
    stack = payload["stack"]
    frameworks = payload["frameworks"]
    commands = payload["commands"]
    tests = payload["tests"]
    package_names: set[str] = set()

    _detect_python(
        state, root_files, scanned, options, stack, frameworks, commands, tests
    )
    _detect_sdd_config(state, scanned, options, commands, tests)
    package_names |= _detect_node(
        state, root_files, scanned, options, stack, frameworks, commands, tests
    )
    _detect_java(
        state, root_files, scanned, options, stack, frameworks, commands, tests
    )
    package_names |= _detect_go(
        state, root_files, scanned, options, stack, frameworks, commands, tests
    )
    package_names |= _detect_rust(
        state, root_files, scanned, options, stack, frameworks, commands, tests
    )
    _detect_dotnet(
        state, root_files, scanned, options, stack, frameworks, commands, tests
    )
    package_names |= _detect_other(
        state, root_files, scanned, options, stack, frameworks, commands, tests
    )
    _detect_docker(
        state,
        root_files,
        scanned,
        options,
        stack,
        payload["entrypoints"],
        payload["services"],
        payload["data"],
    )
    payload["entrypoints"].extend(
        _detect_entrypoints(state, scanned, options)
    )
    payload["contracts"] = _detect_contracts(state, scanned, options)
    _detect_files(root.path, state, root_files, scanned, options, payload)
    _detect_data(root.path, state, scanned, payload)
    payload["docs"] = _detect_docs(
        root.path, state, scanned, options
    )
    payload["sdd"] = {
        "initialized": payload["docs"]["sdd_initialized"],
        "specs": payload["docs"]["specs"],
        "prd_index": payload["docs"]["prd_index"],
        "context_files": payload["docs"]["context_files"],
        "agents_md": payload["docs"]["agents_md"],
        "readme": payload["docs"]["readme"],
    }
    payload["ci"] = _detect_ci(state, scanned, options)
    payload["entrypoints"] = sorted(
        {json.dumps(item, sort_keys=True): item for item in payload["entrypoints"]}.values(),
        key=lambda item: (item["path"], item["kind"], item.get("command", "")),
    )
    payload["services"] = sorted(
        payload["services"], key=lambda item: item["name"]
    )
    payload["commands"]["test"] = sorted(
        commands["test"], key=lambda item: item["command"]
    )
    payload["tests"]["commands"] = list(payload["commands"]["test"])
    payload["stack"] = sorted(stack, key=lambda item: item["name"])
    payload["frameworks"] = sorted(
        frameworks, key=lambda item: item["name"]
    )
    payload["tests"]["framework_facts"] = sorted(
        tests["framework_facts"], key=lambda item: item["name"]
    )
    payload["contracts"] = sorted(
        payload["contracts"], key=lambda item: (item["type"], item["path"])
    )
    payload["data"]["orm"] = sorted(
        payload["data"]["orm"], key=lambda item: (item["kind"], item["path"])
    )
    payload["data"]["infra"] = sorted(
        payload["data"]["infra"], key=lambda item: item["name"]
    )
    payload["ci"] = sorted(
        payload["ci"], key=lambda item: (item["provider"], item["path"])
    )
    secrets = sorted(path for path in scanned if _is_secret(path))
    package_managers, locks = _package_managers(scanned)
    _attach_risks(
        root,
        payload,
        git,
        truncated,
        skipped,
        options,
        skipped_dirs,
        secrets,
        package_managers,
        locks,
        multi,
    )
    manifest_names, manifest_dependencies, dependency_evidence = (
        _collect_manifest_facts(state, scanned, options)
    )
    payload["_package_names"] = sorted(package_names | manifest_names)
    payload["_package_dependencies"] = manifest_dependencies
    payload["_package_dependency_evidence"] = dependency_evidence
    payload["_test_command_count"] = len(payload["commands"]["test"])
    payload["_files_skipped"] = skipped
    payload["_bytes_read"] = state["bytes_read"]
    payload["_truncated"] = truncated
    payload["_secrets"] = secrets
    return payload, state["warnings"], payload["_risks"]


def _attach_risks(
    root: Root,
    payload: dict[str, Any],
    git: dict[str, Any] | None,
    truncated: bool,
    skipped: int,
    options: ScanOptions,
    skipped_dirs: list[str],
    secrets: list[str],
    package_managers: list[str],
    locks: list[str],
    multi: bool,
) -> None:
    prefix = f"{root.id}/" if multi else ""
    risks: list[dict[str, Any]] = []

    if git is None:
        risks.append(
            {
                "severity": "info",
                "code": "not_a_git_repo",
                "message": "目标目录不是 Git 仓库，已使用有界目录遍历",
                "evidence": [],
            }
        )
    if not payload["commands"]["test"]:
        risks.append(
            {
                "severity": "warn",
                "code": "test_command_missing",
                "message": "未找到显式测试命令",
                "evidence": [],
            }
        )
    if len(package_managers) > 1:
        risks.append(
            {
                "severity": "warn",
                "code": "package_manager_conflict",
                "message": "同时存在多个包管理器锁文件：" + ", ".join(package_managers),
                "evidence": [f"{prefix}{path}" for path in locks],
            }
        )
    if skipped_dirs:
        risks.append(
            {
                "severity": "info",
                "code": "large_dir_skipped",
                "message": "已跳过依赖/产物目录：" + ", ".join(skipped_dirs[:8]),
                "evidence": [f"{prefix}{path}" for path in skipped_dirs],
            }
        )
    if payload["entrypoints"] and not any(
        item.get("command") for item in payload["entrypoints"]
    ):
        risks.append(
            {
                "severity": "info",
                "code": "entrypoint_unverified",
                "message": "发现候选入口文件，但未找到显式启动命令",
                "evidence": [
                    f"{prefix}{item['path']}" for item in payload["entrypoints"]
                ],
            }
        )
    if secrets:
        risks.append(
            {
                "severity": "warn",
                "code": "secret_file_present",
                "message": "存在环境/密钥文件；仅记录路径，未读取内容",
                "evidence": [f"{prefix}{path}" for path in secrets],
            }
        )
    if not payload["docs"]["readme"]:
        risks.append(
            {
                "severity": "info",
                "code": "readme_missing",
                "message": "仓库没有 README",
                "evidence": [],
            }
        )
    if not payload["docs"]["agents_md"]:
        risks.append(
            {
                "severity": "info",
                "code": "agents_md_missing",
                "message": "仓库没有 AGENTS.md",
                "evidence": [],
            }
        )
    if truncated:
        risks.append(
            {
                "severity": "warn",
                "code": "scan_truncated",
                "message": (
                    f"文件数超过 --max-files={options.max_files}，"
                    f"仍有 {skipped} 个文件未扫描"
                ),
                "evidence": [],
            }
        )
    payload["_risks"] = risks


def _global_contracts(
    repos: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for repo in repos:
        for contract in repo["contracts"]:
            key = (contract["type"], contract["path"])
            item = by_key.setdefault(
                key,
                {
                    "type": contract["type"],
                    "path": contract["path"],
                    "repos": [],
                    "confidence": contract["confidence"],
                    "evidence": [],
                },
            )
            item["repos"].append(repo["id"])
            item["confidence"] = _max_confidence(
                item["confidence"], contract["confidence"]
            )
            item["evidence"].extend(contract.get("evidence", []))
            for extra in ("format", "version"):
                if contract.get(extra) and not item.get(extra):
                    item[extra] = contract[extra]
    contracts = sorted(
        by_key.values(), key=lambda item: (item["type"], item["path"])
    )
    relationships: list[dict[str, Any]] = []
    for contract in contracts:
        contract["repos"] = sorted(set(contract["repos"]))
        contract["evidence"] = sorted(set(contract["evidence"]))
        if len(contract["repos"]) > 1:
            for index, left in enumerate(contract["repos"]):
                for right in contract["repos"][index + 1 :]:
                    relationships.append(
                        {
                            "from": left,
                            "to": right,
                            "kind": "shared_contract",
                            "source": "shared-contract",
                            "confidence": "high",
                            "evidence": contract["evidence"],
                        }
                    )
    return contracts, relationships


def _declared_relationships(
    roots: list[Root],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    known = {root.id for root in roots}
    relationships: list[dict[str, Any]] = []
    unknowns: list[dict[str, Any]] = []
    for root in roots:
        for dependency in root.depends_on:
            relationships.append(
                {
                    "from": root.id,
                    "to": dependency,
                    "kind": "depends_on",
                    "source": "declared",
                    "confidence": "high",
                    "evidence": [root.source] if root.source else [],
                }
            )
            if dependency not in known:
                unknowns.append(
                    {
                        "question": f"{root.id} 依赖的 {dependency} 未出现在本次扫描清单中",
                        "reason": "depends_on 由 workspace 显式声明",
                    }
                )
    return relationships, unknowns


def _package_relationships(
    repos: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    names: dict[str, list[str]] = {}
    for repo in repos:
        for name in repo.get("_package_names", []):
            normalized = name.lower()
            if normalized:
                names.setdefault(normalized, []).append(repo["id"])
    relationships: list[dict[str, Any]] = []
    unknowns: list[dict[str, Any]] = []
    for repo in repos:
        dependencies = repo.get("_package_dependencies", set())
        for dependency in sorted(dependencies):
            owners = names.get(dependency.lower(), [])
            for owner in sorted(set(owners)):
                if owner == repo["id"]:
                    continue
                relationships.append(
                    {
                        "from": repo["id"],
                        "to": owner,
                        "kind": "package_dependency",
                        "source": "package-name",
                        "confidence": "low",
                        "evidence": repo.get(
                            "_package_dependency_evidence", {}
                        ).get(dependency.lower(), []),
                    }
                )
                unknowns.append(
                    {
                        "question": f"{repo['id']} 是否在运行时调用 {owner}？",
                        "reason": "仅从 manifest 包名映射，缺少运行时证据",
                    }
                )
    return relationships, unknowns


def _collect_manifest_facts(
    state: dict[str, Any],
    scanned: list[str],
    options: ScanOptions,
) -> tuple[set[str], set[str], dict[str, list[str]]]:
    """Collect package names and dependencies for cross-repo mapping."""
    package_names: set[str] = set()
    dependencies: set[str] = set()
    evidence: dict[str, list[str]] = {}
    limit = options.max_file_bytes
    for relative in scanned:
        name = _basename(relative)
        if name == "package.json":
            data = _read_json(state, relative, limit)
            if isinstance(data, dict):
                if isinstance(data.get("name"), str):
                    package_names.add(data["name"].lower())
                for key in ("dependencies", "devDependencies"):
                    values = data.get(key)
                    if isinstance(values, dict):
                        for item in values:
                            dependency = str(item).lower()
                            dependencies.add(dependency)
                            evidence.setdefault(dependency, []).append(
                                f"{state['prefix']}{relative}"
                            )
        elif name == "pyproject.toml":
            data = _read_toml(state, relative, limit)
            if isinstance(data, dict):
                package_name = _package_name_from_python(data)
                if package_name:
                    package_names.add(package_name.lower())
                for dependency in _dependency_names(
                    _python_dependencies(data)
                ):
                    dependencies.add(dependency)
                    evidence.setdefault(dependency, []).append(
                        f"{state['prefix']}{relative}"
                    )
        elif name == "go.mod":
            text = _read_text(state, relative, limit)
            if text:
                for raw in text.splitlines():
                    line = raw.strip()
                    if line.startswith("module "):
                        module = line.split(None, 1)[1].strip()
                        package_names.add(module.rsplit("/", 1)[-1].lower())
                        continue
                    if line.startswith("require "):
                        line = line[len("require ") :].strip()
                    if line and not line.startswith(("//", "module", "go ")):
                        dependency = line.split()[0].lower().rsplit("/", 1)[-1]
                        dependencies.add(dependency)
                        evidence.setdefault(dependency, []).append(
                            f"{state['prefix']}{relative}"
                        )
        elif name == "Cargo.toml":
            data = _read_toml(state, relative, limit)
            if isinstance(data, dict):
                package = data.get("package")
                if isinstance(package, dict) and isinstance(
                    package.get("name"), str
                ):
                    package_names.add(package["name"].lower())
                for key in ("dependencies", "dev-dependencies"):
                    values = data.get(key)
                    if isinstance(values, dict):
                        for item in values:
                            dependency = str(item).lower()
                            dependencies.add(dependency)
                            evidence.setdefault(dependency, []).append(
                                f"{state['prefix']}{relative}"
                            )
        elif name == "composer.json":
            data = _read_json(state, relative, limit)
            if isinstance(data, dict):
                if isinstance(data.get("name"), str):
                    package_names.add(data["name"].lower())
                for key in ("require", "require-dev"):
                    values = data.get(key)
                    if isinstance(values, dict):
                        for item in values:
                            dependency = str(item).lower()
                            dependencies.add(dependency)
                            evidence.setdefault(dependency, []).append(
                                f"{state['prefix']}{relative}"
                            )
    return (
        package_names,
        dependencies,
        {name: sorted(set(paths)) for name, paths in sorted(evidence.items())},
    )


def _dedupe(items: Iterable[dict[str, Any]], key_fields: tuple[str, ...]) -> list[dict[str, Any]]:
    seen: set[tuple[Any, ...]] = set()
    result: list[dict[str, Any]] = []
    for item in items:
        key = tuple(
            tuple(value) if isinstance(value, list) else value
            for value in (item.get(field) for field in key_fields)
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def run_explorer(
    *,
    repos: Iterable[str] = (),
    workspace: str | None = None,
    root: Path | None = None,
    depth: int | None = None,
    max_files: int = DEFAULT_MAX_FILES,
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
    includes: Iterable[str] = (),
    excludes: Iterable[str] = (),
    deep: bool = False,
) -> dict[str, Any]:
    """Scan one or more repositories and return the schema v1 fact map."""
    if depth is not None and depth < 1:
        raise ExplorerError("--depth 必须大于等于 1")
    if max_files < 1:
        raise ExplorerError("--max-files 必须大于等于 1")
    if max_file_bytes < 1:
        raise ExplorerError("--max-file-bytes 必须大于等于 1")
    options = ScanOptions(
        depth=depth,
        max_files=max_files,
        max_file_bytes=max_file_bytes,
        includes=list(includes),
        excludes=list(excludes),
        deep=deep,
    )
    roots = _load_roots(
        repos, workspace, root or Path.cwd()
    )
    multi = len(roots) > 1
    repo_payloads: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    risks: list[dict[str, Any]] = []
    truncated = False
    files_scanned = 0
    files_skipped = 0
    bytes_read = 0

    for repo_root in roots:
        payload, repo_warnings, repo_risks = _scan_repo(
            repo_root, options, multi
        )
        repo_payloads.append(payload)
        warnings.extend(repo_warnings)
        risks.extend(repo_risks)
        files_scanned += payload["files"]
        files_skipped += payload.get("_files_skipped", 0)
        bytes_read += payload.get("_bytes_read", 0)
        truncated = truncated or payload.get("_truncated", False)

    contracts, relationships = _global_contracts(repo_payloads)
    declared, declared_unknowns = _declared_relationships(roots)
    package_links, package_unknowns = _package_relationships(repo_payloads)
    relationships.extend(declared)
    relationships.extend(package_links)
    relationships = sorted(
        _dedupe(
            relationships,
            ("from", "to", "kind", "source"),
        ),
        key=lambda item: (
            item["from"],
            item["to"],
            item["kind"],
            item["source"],
        ),
    )

    unknowns = list(declared_unknowns) + list(package_unknowns)
    if any(
        len(contract["repos"]) > 1 for contract in contracts
    ):
        unknowns.append(
            {
                "question": "共享契约的版本与内容是否在各仓库之间保持一致？",
                "reason": "explorer 只按路径识别共享契约，未比较内容语义",
            }
        )
    for payload in repo_payloads:
        if payload["entrypoints"]:
            unknowns.append(
                {
                    "question": (
                        f"{payload['id']} 的候选入口如何启动、监听什么端口？"
                    ),
                    "reason": "仅从文件名/Docker 配置识别，未执行验证",
                }
            )
        if not payload["commands"]["test"]:
            unknowns.append(
                {
                    "question": f"{payload['id']} 的测试如何运行？",
                    "reason": "未找到显式测试命令",
                }
            )
    for payload in repo_payloads:
        for key in (
            "_package_names",
            "_package_dependencies",
            "_package_dependency_evidence",
            "_test_command_count",
            "_risks",
            "_files_skipped",
            "_bytes_read",
            "_truncated",
            "_secrets",
        ):
            payload.pop(key, None)
        payload["tests"]["commands"] = sorted(
            payload["tests"]["commands"], key=lambda item: item["command"]
        )
        payload["tests"]["framework_facts"] = sorted(
            payload["tests"]["framework_facts"], key=lambda item: item["name"]
        )
        payload["tests"]["frameworks"] = sorted(
            set(payload["tests"]["frameworks"])
        )

    aggregate_languages: dict[str, int] = {}
    for payload in repo_payloads:
        for name, count in payload["languages"].items():
            aggregate_languages[name] = aggregate_languages.get(name, 0) + count
    aggregate_languages = {
        name: aggregate_languages[name] for name in sorted(aggregate_languages)
    }

    all_specs = sorted(
        {
            spec["id"]
            for payload in repo_payloads
            for spec in payload["sdd"]["specs"]
        }
    )
    context_files = sorted(
        {
            f"{payload['id']}/{path}" if multi else path
            for payload in repo_payloads
            for path in payload["sdd"]["context_files"]
        }
    )
    agents_md = sorted(
        {
            f"{payload['id']}/{path}" if multi else path
            for payload in repo_payloads
            for path in payload["sdd"]["agents_md"]
        }
    )
    readme = sorted(
        {
            f"{payload['id']}/{path}" if multi else path
            for payload in repo_payloads
            for path in payload["sdd"]["readme"]
        }
    )
    risks = sorted(
        _dedupe(
            risks,
            ("code", "message", "severity", "evidence"),
        ),
        key=lambda item: (
            0 if item.get("severity") == "warn" else 1,
            item.get("code", ""),
            tuple(item.get("evidence", [])),
        ),
    )
    unknowns = sorted(
        _dedupe(unknowns, ("question", "reason")),
        key=lambda item: (item["question"], item["reason"]),
    )

    test_commands = sum(
        len(payload["commands"]["test"]) for payload in repo_payloads
    )
    return {
        "ok": True,
        "schema_version": SCHEMA_VERSION,
        "kind": "explorer",
        "generated_at": _now(),
        "roots": [
            {
                "id": payload["id"],
                "path": payload["path"],
                "role": payload["role"],
                "git": payload["git"],
                "evidence": [".git"] if payload["git"] else [],
            }
            for payload in repo_payloads
        ],
        "summary": {
            "repos": len(repo_payloads),
            "files": files_scanned,
            "languages": aggregate_languages,
            "test_commands": test_commands,
            "contracts": len(contracts),
            "risks": len(risks),
        },
        "repos": repo_payloads,
        "relationships": relationships,
        "contracts": contracts,
        "sdd": {
            "initialized": any(
                payload["sdd"]["initialized"] for payload in repo_payloads
            ),
            "specs": all_specs,
            "context_files": context_files,
            "prd_index": any(
                payload["sdd"]["prd_index"] for payload in repo_payloads
            ),
            "agents_md": agents_md,
            "readme": readme,
        },
        "risks": risks,
        "unknowns": unknowns,
        "scan": {
            "files_scanned": files_scanned,
            "files_skipped": files_skipped,
            "bytes_read": bytes_read,
            "truncated": truncated,
            "max_files": max_files,
            "max_file_bytes": max_file_bytes,
            "depth": depth,
            "deep": deep,
            "warnings": sorted(
                _dedupe(warnings, ("repo", "path", "message")),
                key=lambda item: (
                    item.get("repo", ""),
                    item.get("path", ""),
                    item.get("message", ""),
                ),
            ),
        },
    }


def _escape_markdown(value: Any) -> str:
    return str(value if value is not None else "").replace("|", "\\|")


def _evidence(value: Iterable[str]) -> str:
    items = [item for item in value if item]
    return ", ".join(items) if items else "-"


def render_markdown(payload: dict[str, Any]) -> str:
    lines: list[str] = [
        "# SDD Explorer 事实地图",
        "",
        f"- generated_at: {payload.get('generated_at', '')}",
        f"- schema_version: {payload.get('schema_version', '')}",
    ]
    summary = payload.get("summary", {})
    lines.extend(
        [
            f"- repos: {summary.get('repos', 0)}",
            f"- files: {summary.get('files', 0)}",
            f"- test_commands: {summary.get('test_commands', 0)}",
            f"- contracts: {summary.get('contracts', 0)}",
            f"- risks: {summary.get('risks', 0)}",
            "",
        ]
    )
    for repo in payload.get("repos", []):
        lines.extend(
            [
                f"## 仓库 {repo.get('id')}",
                "",
                f"- path: {repo.get('path')}",
                f"- role: {repo.get('role') or '-'}",
                f"- files: {repo.get('files', 0)}",
                f"- size_bytes: {repo.get('size_bytes', 0)}",
            ]
        )
        git = repo.get("git")
        if git:
            lines.append(
                "- git: "
                f"branch={git.get('branch') or '-'} "
                f"head={git.get('head') or '-'} "
                f"dirty={git.get('dirty')}"
            )
        else:
            lines.append("- git: 非 Git 仓库")
        languages = repo.get("languages", {})
        if languages:
            lines.append(
                "- languages: "
                + ", ".join(
                    f"{name}={count}" for name, count in languages.items()
                )
            )
        lines.extend(["", "### 技术栈", ""])
        if repo.get("stack"):
            for item in repo["stack"]:
                lines.append(
                    f"- {_escape_markdown(item['name'])} "
                    f"({item['confidence']}) evidence: "
                    f"{_evidence(item.get('evidence', []))}"
                )
        else:
            lines.append("- 未找到 manifest")
        lines.extend(["", "### 入口与服务", ""])
        if repo.get("entrypoints"):
            for item in repo["entrypoints"]:
                suffix = f" command={item['command']}" if item.get("command") else ""
                lines.append(
                    f"- {item['path']} ({item['kind']}, "
                    f"{item['confidence']}){suffix}"
                )
        else:
            lines.append("- 未发现候选入口")
        for item in repo.get("services", []):
            lines.append(
                f"- compose service {item['name']}: "
                f"image={item.get('image') or '-'} "
                f"ports={','.join(item.get('ports', [])) or '-'} "
                f"depends_on={','.join(item.get('depends_on', [])) or '-'} "
                f"evidence={_evidence(item.get('evidence', []))}"
            )
        lines.extend(["", "### 测试", ""])
        tests = repo.get("tests", {})
        lines.append(
            "- frameworks: "
            + (", ".join(tests.get("frameworks", [])) or "-")
        )
        lines.append(
            "- directories: "
            + (", ".join(tests.get("directories", [])) or "-")
        )
        if tests.get("commands"):
            for item in tests["commands"]:
                lines.append(
                    f"- command: `{item['command']}` "
                    f"({item['confidence']}) evidence: "
                    f"{_evidence(item.get('evidence', []))}"
                )
        else:
            lines.append("- command: 未找到显式测试命令")
        if tests.get("coverage"):
            lines.append(
                "- coverage: " + ", ".join(tests["coverage"])
            )
        lines.extend(["", "### 契约与数据", ""])
        if repo.get("contracts"):
            for item in repo["contracts"]:
                extra = f" version={item['version']}" if item.get("version") else ""
                lines.append(
                    f"- {item['type']}: {item['path']} "
                    f"({item['confidence']}){extra}"
                )
        else:
            lines.append("- 未发现契约文件")
        data = repo.get("data", {})
        if data.get("migrations"):
            lines.append(
                "- migrations: " + ", ".join(data["migrations"])
            )
        if data.get("orm"):
            lines.append(
                "- orm: "
                + ", ".join(
                    f"{item['kind']}@{item['path']}" for item in data["orm"]
                )
            )
        if data.get("infra"):
            lines.append(
                "- infra: "
                + ", ".join(
                    f"{item['name']}({_evidence(item.get('evidence', []))})"
                    for item in data["infra"]
                )
            )
        lines.extend(["", "### 文档 / SDD / CI", ""])
        sdd = repo.get("sdd", {})
        docs = repo.get("docs", {})
        lines.append(
            "- sdd_initialized: "
            + str(bool(sdd.get("initialized"))).lower()
        )
        if sdd.get("specs"):
            lines.append(
                "- specs: "
                + ", ".join(
                    f"{item['id']}[{item.get('state') or '-'}]"
                    for item in sdd["specs"]
                )
            )
        lines.append(
            "- prd_index: " + str(bool(sdd.get("prd_index"))).lower()
        )
        for label, key in (
            ("AGENTS.md", "agents_md"),
            ("README", "readme"),
            ("CODEOWNERS", "codeowners"),
            ("CONTRIBUTING", "contributing"),
            ("context", "context_files"),
        ):
            values = docs.get(key, [])
            if values:
                lines.append(f"- {label}: " + ", ".join(values))
        for item in repo.get("ci", []):
            test_jobs = [
                job["name"] for job in item.get("jobs", []) if job.get("runs_tests")
            ]
            lines.append(
                f"- ci {item['provider']}: {item['path']} "
                f"test_jobs={','.join(test_jobs) or '-'}"
            )
        lines.append("")
    lines.extend(["## 跨仓关系", ""])
    if payload.get("relationships"):
        for item in payload["relationships"]:
            lines.append(
                f"- {item['from']} -> {item['to']} "
                f"({item['kind']}, source={item['source']}, "
                f"confidence={item['confidence']})"
            )
    else:
        lines.append("- 无显式跨仓关系")
    lines.extend(["", "## 契约", ""])
    if payload.get("contracts"):
        for item in payload["contracts"]:
            extra = f" version={item['version']}" if item.get("version") else ""
            lines.append(
                f"- {item['type']}: {item['path']} "
                f"repos={','.join(item['repos'])} "
                f"({item['confidence']}){extra}"
            )
    else:
        lines.append("- 未发现契约")
    lines.extend(["", "## 风险", ""])
    if payload.get("risks"):
        for item in payload["risks"]:
            lines.append(
                f"- [{item['severity']}] {item['code']}: {item['message']} "
                f"evidence: {_evidence(item.get('evidence', []))}"
            )
    else:
        lines.append("- 无")
    lines.extend(["", "## 未知", ""])
    if payload.get("unknowns"):
        for item in payload["unknowns"]:
            lines.append(
                f"- {item['question']} （{item['reason']}）"
            )
    else:
        lines.append("- 无")
    scan = payload.get("scan", {})
    lines.extend(
        [
            "",
            "## 扫描边界",
            "",
            f"- files_scanned: {scan.get('files_scanned', 0)}",
            f"- files_skipped: {scan.get('files_skipped', 0)}",
            f"- bytes_read: {scan.get('bytes_read', 0)}",
            f"- truncated: {str(bool(scan.get('truncated'))).lower()}",
            f"- deep: {str(bool(scan.get('deep'))).lower()}",
        ]
    )
    if scan.get("warnings"):
        lines.extend(["", "### warnings", ""])
        for item in scan["warnings"]:
            lines.append(
                f"- {item.get('repo')}:{item.get('path') or '-'} "
                f"{item.get('message')}"
            )
    return "\n".join(lines).rstrip() + "\n"


def write_report(payload: dict[str, Any], out: Path) -> str:
    """Write a Markdown or JSON report; return the chosen format."""
    path = out.expanduser()
    if path.parent and not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
    suffix = path.suffix.lower()
    if suffix == ".json":
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return "json"
    path.write_text(render_markdown(payload), encoding="utf-8")
    return "markdown"
