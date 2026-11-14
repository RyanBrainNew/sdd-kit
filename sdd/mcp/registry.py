from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class RegistryError(Exception):
    """Raised when the project registry cannot be loaded or resolved."""


@dataclass(frozen=True)
class Project:
    id: str
    path: Path
    description: str = ""
    tags: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "path": str(self.path),
            "description": self.description,
            "tags": list(self.tags),
        }


class Registry:
    def __init__(self, path: Path, workspace_root: Path, projects: dict[str, Project]):
        self.path = path
        self.workspace_root = workspace_root
        self.projects = projects

    @property
    def mode(self) -> str:
        """Return 'registry' for a shared server, 'local' for a single repo."""
        return "registry" if self.path.is_file() else "local"

    @classmethod
    def load(cls, path: str | Path | None = None) -> "Registry":
        configured = path or os.environ.get("SDD_MCP_REGISTRY")
        registry_path = Path(configured).expanduser() if configured else Path.cwd() / "sdd-mcp.json"
        registry_path = registry_path.resolve()
        if not registry_path.is_file():
            raise RegistryError(
                f"registry not found: {registry_path}; set SDD_MCP_REGISTRY or pass --registry"
            )
        try:
            data = json.loads(registry_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RegistryError(f"cannot read registry {registry_path}: {exc}") from exc

        root_value = data.get("workspace_root")
        workspace_root = (
            Path(root_value).expanduser()
            if root_value
            else registry_path.parent
        )
        if not workspace_root.is_absolute():
            workspace_root = (registry_path.parent / workspace_root).resolve()
        else:
            workspace_root = workspace_root.resolve()

        raw_projects = data.get("projects")
        if not isinstance(raw_projects, dict) or not raw_projects:
            raise RegistryError("registry must contain a non-empty 'projects' object")

        projects: dict[str, Project] = {}
        for project_id, value in raw_projects.items():
            if not isinstance(value, dict):
                raise RegistryError(f"project {project_id!r} must be an object")
            raw_path = value.get("path")
            if not raw_path:
                raise RegistryError(f"project {project_id!r} is missing 'path'")
            project_path = Path(raw_path).expanduser()
            if not project_path.is_absolute():
                project_path = workspace_root / project_path
            project_path = project_path.resolve()
            projects[project_id] = Project(
                id=project_id,
                path=project_path,
                description=str(value.get("description", "")),
                tags=tuple(str(tag) for tag in value.get("tags", [])),
            )

        return cls(registry_path, workspace_root, projects)

    @classmethod
    def single(cls, root: str | Path, project_id: str | None = None) -> "Registry":
        """Build an in-memory registry for one local repository.

        This is the local-clone mode: the MCP server runs on the developer's
        machine, sees that developer's working tree, and never needs a shared
        registry file or server-side checkout.
        """
        project_path = Path(root).expanduser().resolve()
        if not project_path.is_dir():
            raise RegistryError(f"project root does not exist: {project_path}")
        if not cls._is_sdd_project(project_path):
            raise RegistryError(
                f"project is not SDD-enabled: "
                f"{project_path / 'sdd' / 'scripts' / 'sdd.py'} not found"
            )
        config_path = project_path / "sdd" / "config.json"
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RegistryError(f"cannot read {config_path}: {exc}") from exc
        resolved_id = project_id or str(config.get("project") or project_path.name)
        project = Project(
            id=resolved_id,
            path=project_path,
            description="local working tree",
            tags=("local",),
        )
        return cls(
            path=project_path / "sdd-mcp.local.json",
            workspace_root=project_path,
            projects={resolved_id: project},
        )

    def list_projects(self) -> list[dict[str, Any]]:
        result = []
        for project in sorted(self.projects.values(), key=lambda item: item.id):
            item = project.as_dict()
            item["valid"] = self._is_sdd_project(project.path)
            result.append(item)
        return result

    def resolve(self, project_id: str) -> Project:
        project = self.projects.get(project_id)
        if project is None:
            known = ", ".join(sorted(self.projects)) or "(none)"
            raise RegistryError(f"unknown project {project_id!r}; known projects: {known}")
        if not project.path.is_dir():
            raise RegistryError(f"project path does not exist: {project.path}")
        if not self._is_sdd_project(project.path):
            raise RegistryError(
                f"project {project_id!r} is not SDD-enabled: "
                f"{project.path / 'sdd' / 'scripts' / 'sdd.py'} not found"
            )
        return project

    @staticmethod
    def _is_sdd_project(path: Path) -> bool:
        return (path / "sdd" / "scripts" / "sdd.py").is_file() and (
            path / "sdd" / "config.json"
        ).is_file()
