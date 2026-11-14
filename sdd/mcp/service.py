from __future__ import annotations

from typing import Any, Iterable

from ..core import SddCommandError, Workspace
from . import __version__
from .registry import Project, Registry


class SddService:
    """MCP-facing adapter over the repository-local SDD core.

    The MCP server only resolves a project and delegates to that repository's
    ``sdd/core.py`` / ``sdd/scripts/sdd.py``. It deliberately contains no SDD
    stage rules, artifact checks or gate logic of its own.
    """

    AUTOPILOT_CONTRACT = Workspace.AUTOPILOT_CONTRACT
    SUBMIT_TOOL = Workspace.SUBMIT_TOOL
    ARTIFACTS = Workspace.ARTIFACTS
    VERB_KEYS = {
        "start_with",
        "submit_with",
        "resume_with",
        "start_new_with",
        "submit_stage_with",
        "submit_task_with",
    }
    CLI_VERBS = {
        "sdd resume": "sdd_session",
        "sdd start-work": "sdd_start_work",
        "sdd submit": "sdd_submit_artifact",
        "sdd submit-task": "sdd_submit_task",
        "sdd report": "sdd_report",
        "sdd complete": "sdd_complete",
        "sdd next": "sdd_next",
        "sdd status": "sdd_status",
        "sdd check": "sdd_check",
        "sdd context": "sdd_context",
    }

    def __init__(self, registry: Registry):
        self.registry = registry

    def _workspace(self, project_id: str) -> Workspace:
        project = self.resolve(project_id)
        return Workspace(
            project.path,
            project_id=project.id,
            allocation_root=self.registry.workspace_root,
        )

    def _mcp(self, value: Any) -> Any:
        """Translate repository CLI verbs into MCP tool names."""
        if isinstance(value, dict):
            mapped: dict[str, Any] = {}
            for key, item in value.items():
                if key in self.VERB_KEYS and isinstance(item, str):
                    mapped[key] = self.CLI_VERBS.get(item, item)
                else:
                    mapped[key] = self._mcp(item)
            return mapped
        if isinstance(value, list):
            return [self._mcp(item) for item in value]
        return value

    def list_projects(self) -> list[dict[str, Any]]:
        return self.registry.list_projects()

    def resolve(self, project_id: str) -> Project:
        return self.registry.resolve(project_id)

    def status(self, project_id: str, spec: str | None = None) -> dict[str, Any]:
        return self._workspace(project_id).status(spec)

    def next(self, project_id: str, spec: str | None = None) -> dict[str, Any]:
        return self._mcp(self._workspace(project_id).next(spec))

    def list_specs(self, project_id: str) -> list[dict[str, Any]]:
        return self._workspace(project_id).list_specs()

    def board(self, project_id: str) -> dict[str, Any]:
        return self._workspace(project_id).board()

    def session(
        self,
        project_id: str,
        spec: str | None = None,
        max_chars: int = 12000,
    ) -> dict[str, Any]:
        return self._mcp(self._workspace(project_id).session(spec, max_chars))

    def start_work(
        self,
        project_id: str,
        work_item: str,
        issue_url: str | None = None,
        title: str | None = None,
        description: str | None = None,
        domain: str = "REQ",
        risk: str = "low",
        risk_labels: Iterable[str] = (),
        product_type: str = "传统产品",
    ) -> dict[str, Any]:
        return self._mcp(
            self._workspace(project_id).start_work(
                work_item,
                issue_url=issue_url,
                title=title,
                description=description,
                domain=domain,
                risk=risk,
                risk_labels=risk_labels,
                product_type=product_type,
            )
        )

    def submit_artifact(
        self,
        project_id: str,
        spec: str,
        artifact: str,
        content: str,
        run_commands: bool = True,
    ) -> dict[str, Any]:
        return self._mcp(
            self._workspace(project_id).submit_artifact(
                spec, artifact, content, run_commands=run_commands
            )
        )

    def submit_task(
        self,
        project_id: str,
        spec: str,
        task: str,
        evidence: str,
        commit: str | None = None,
    ) -> dict[str, Any]:
        return self._mcp(
            self._workspace(project_id).submit_task(spec, task, evidence, commit)
        )

    def check(
        self,
        project_id: str,
        spec: str | None = None,
        stage: str = "auto",
        check_git: bool = False,
    ) -> dict[str, Any]:
        return self._workspace(project_id).check(
            spec, stage=stage, check_git=check_git
        )

    def create_spec(
        self,
        project_id: str,
        title: str,
        spec_id: str | None = None,
        domain: str | None = None,
        work_item: str | None = None,
        issue_url: str | None = None,
        risk: str = "low",
        risk_labels: Iterable[str] = (),
        product_type: str = "传统产品",
    ) -> dict[str, Any]:
        return self._workspace(project_id).create_spec(
            title=title,
            spec_id=spec_id,
            domain=domain,
            work_item=work_item,
            issue_url=issue_url,
            risk=risk,
            risk_labels=risk_labels,
            product_type=product_type,
        )

    def reserve_spec_id(self, project_id: str, domain: str) -> dict[str, Any]:
        return self._workspace(project_id).reserve_spec_id(domain)

    def start(self, project_id: str, spec: str, task: str) -> dict[str, Any]:
        return self._workspace(project_id).start(spec, task)

    def complete(
        self,
        project_id: str,
        spec: str,
        evidence: str,
        task: str | None = None,
        commit: str | None = None,
    ) -> dict[str, Any]:
        return self._mcp(
            self._workspace(project_id).complete(
                spec, evidence, task=task, commit=commit
            )
        )

    def verify(
        self,
        project_id: str,
        spec: str,
        commands: Iterable[str] = (),
    ) -> dict[str, Any]:
        return self._workspace(project_id).verify(spec, commands)

    def report(self, project_id: str, spec: str) -> dict[str, Any]:
        return self._mcp(self._workspace(project_id).report(spec))

    def record_pr(
        self,
        project_id: str,
        spec: str,
        url: str | None = None,
    ) -> dict[str, Any]:
        return self._mcp(self._workspace(project_id).record_pr(spec, url))

    def block(self, project_id: str, spec: str, reason: str) -> dict[str, Any]:
        return self._workspace(project_id).block(spec, reason)

    def read_artifact(self, project_id: str, spec: str, artifact: str) -> str:
        return self._workspace(project_id).read_artifact(spec, artifact)

    def context(
        self,
        project_id: str,
        spec: str | None = None,
        max_chars: int = 40000,
    ) -> dict[str, Any]:
        return self._workspace(project_id).context(spec, max_chars)

    def health(self) -> dict[str, Any]:
        return {
            "ok": True,
            "version": __version__,
            "mode": self.registry.mode,
            "registry": str(self.registry.path),
            "workspace_root": str(self.registry.workspace_root),
            "projects": len(self.registry.projects),
        }

    def _agent_next(self, project_id: str, spec: str) -> dict[str, Any]:
        return self._mcp(self._workspace(project_id)._agent_next(spec))

    def _human_checkpoint(self, project_id: str, spec: str) -> dict[str, Any]:
        return self._workspace(project_id)._human_checkpoint(spec)
