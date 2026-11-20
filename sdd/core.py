from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator

from . import __version__


class SddCommandError(Exception):
    def __init__(
        self,
        command: str,
        returncode: int,
        stdout: str = "",
        stderr: str = "",
    ):
        self.command = command
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        message = stderr.strip() or stdout.strip() or f"exit code {returncode}"
        super().__init__(f"{command} failed: {message}")


@dataclass(frozen=True)
class CommandResult:
    command: str
    returncode: int
    stdout: str
    stderr: str


class Workspace:
    """Repository-local SDD orchestration shared by CLI and MCP adapters.

    The low-level state machine remains in ``sdd/scripts/sdd.py``. This class
    only adds the session pointer and the high-level verbs an Agent needs:
    resume, start work, submit an artifact, and submit a task.
    """

    AUTOPILOT_CONTRACT = {
        "developer_action": "provide_one_work_item",
        "resume_with": "sdd resume",
        "start_new_with": "sdd start-work",
        "submit_stage_with": "sdd submit",
        "submit_task_with": "sdd submit-task",
        "human_only": ["approve_spec", "confirm_merge", "unblock", "rewind"],
        "rule": (
            "Do not ask the developer which SDD stage the work is in. "
            "Read next.action, execute it, and submit with next.submit_with. "
            "The CLI re-validates every transition and returns the next action."
        ),
    }

    SUBMIT_TOOL = {
        "write_spec": "sdd submit",
        "write_design": "sdd submit",
        "write_tasks": "sdd submit",
        "run_verification": "sdd submit",
        "implement_task": "sdd submit-task",
        "start_implementation": "sdd complete",
        "finish_implementation": "sdd complete",
        "open_pr": "sdd pr --url",
    }

    ARTIFACTS = {
        "spec.md",
        "design.md",
        "tasks.md",
        "verification.md",
        "gates.md",
        "decisions.md",
        "PR_BODY.md",
        "context.md",
        "unknowns.md",
        "change-set.md",
    }

    def __init__(
        self,
        root: str | Path,
        project_id: str | None = None,
        allocation_root: str | Path | None = None,
        session_key: str | None = None,
        source: str = "cli",
    ):
        self.root = Path(root).expanduser().resolve()
        if not (self.root / "sdd" / "config.json").is_file():
            raise ValueError(f"not an SDD workspace: {self.root}")
        self.project_id = project_id or self._config_project()
        self.allocation_root = Path(allocation_root or self.root).expanduser().resolve()
        self._session_key_override = session_key
        self.source = source

    def _config_project(self) -> str:
        try:
            data = json.loads(
                (self.root / "sdd" / "config.json").read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError):
            return self.root.name
        return str(data.get("project") or self.root.name)

    @property
    def config(self) -> dict[str, Any]:
        return json.loads(
            (self.root / "sdd" / "config.json").read_text(encoding="utf-8")
        )

    @property
    def session_key(self) -> str:
        if self._session_key_override:
            return self._session_key_override
        env_key = (
            os.environ.get("SDD_SESSION_KEY")
            or os.environ.get("CODEX_THREAD_ID")
            or os.environ.get("DSH_SESSION_ID")
            or os.environ.get("CLAUDE_CODE_SESSION_ID")
            or os.environ.get("TRELLIS_CONTEXT_ID")
            or os.environ.get("CURSOR_CONVERSATION_ID")
        )
        return env_key or f"local:{self.root}"

    @property
    def session_source(self) -> str:
        if self._session_key_override:
            return "explicit"
        if os.environ.get("SDD_SESSION_KEY"):
            return "SDD_SESSION_KEY"
        for name in (
            "CODEX_THREAD_ID",
            "DSH_SESSION_ID",
            "CLAUDE_CODE_SESSION_ID",
            "TRELLIS_CONTEXT_ID",
            "CURSOR_CONVERSATION_ID",
        ):
            if os.environ.get(name):
                return name
        return "repo-fallback"

    @property
    def session_degraded(self) -> bool:
        return self.session_source == "repo-fallback"

    @property
    def session_path(self) -> Path:
        digest = hashlib.sha256(self.session_key.encode("utf-8")).hexdigest()[:24]
        return self.root / ".sdd" / "runtime" / "sessions" / f"{digest}.json"

    def session_info(self) -> dict[str, Any]:
        return {
            "key": self.session_key,
            "source": self.session_source,
            "degraded": self.session_degraded,
            "path": self.session_path.relative_to(self.root).as_posix(),
        }

    def read_pointer(self) -> dict[str, Any]:
        path = self.session_path
        if not path.is_file():
            return {"found": False, "valid": False, "stale": False, "pointer": None}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return {
                "found": True,
                "valid": False,
                "stale": True,
                "pointer": None,
                "error": str(exc),
            }
        if not isinstance(data, dict):
            return {
                "found": True,
                "valid": False,
                "stale": True,
                "pointer": None,
                "error": "session pointer is not an object",
            }
        spec = str(data.get("spec") or "")
        state_path = self._find_spec_dir_optional(spec) / "state.json" if spec else None
        valid = bool(spec and state_path and state_path.is_file())
        return {
            "found": True,
            "valid": valid,
            "stale": not valid,
            "pointer": data,
        }

    def bind_session(self, spec: str) -> dict[str, Any]:
        status = self.status(spec)
        state = status.get("state", {})
        pointer = {
            "session_key": self.session_key,
            "project": self.project_id,
            "spec": spec,
            "work_item": state.get("work_item"),
            "title": state.get("title"),
            "state": state.get("state"),
            "branch": self._git_value("rev-parse", "--abbrev-ref", "HEAD"),
            "worktree": self._git_value("rev-parse", "--show-toplevel"),
            "updated_at": self._now(),
        }
        self.session_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.session_path.with_suffix(f".{os.getpid()}.tmp")
        temporary.write_text(
            json.dumps(pointer, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, self.session_path)
        return pointer

    def clear_session(self) -> None:
        self.session_path.unlink(missing_ok=True)

    def current(self) -> dict[str, Any]:
        pointer = self.read_pointer()
        payload: dict[str, Any] = {
            "session": self.session_info(),
            "pointer": pointer,
        }
        if pointer.get("valid") and pointer.get("pointer"):
            spec = str(pointer["pointer"].get("spec"))
            payload["status"] = self.status(spec)
            payload["next"] = self._agent_next(spec)
            payload["human_checkpoint"] = self._human_checkpoint(spec)
        return payload

    def list_specs(self) -> list[dict[str, Any]]:
        config = self.config
        root = self.root / config.get("spec_root", "docs/specs")
        if not root.is_dir():
            return []
        items: list[dict[str, Any]] = []
        for directory in sorted(root.iterdir()):
            state_path = directory / "state.json"
            if not directory.is_dir() or not state_path.is_file():
                continue
            try:
                state = json.loads(state_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            item: dict[str, Any] = {
                "spec": state.get("spec_id", directory.name),
                "title": state.get("title", ""),
                "state": state.get("state", "UNKNOWN"),
                "work_item": state.get("work_item"),
                "workflow": state.get("workflow"),
                "spec_dir": directory.relative_to(self.root).as_posix(),
            }
            try:
                action = self.next(str(item["spec"]))
                item["action"] = action.get("action")
                item["task"] = action.get("task")
            except SddCommandError as exc:
                item["error"] = str(exc)
            items.append(item)
        return items

    def board(self) -> dict[str, Any]:
        """Return a Spec Kitty-style read-only board for specs and tasks."""
        payload = self._json(self._run(["board", "--json"]))
        pointer = self.read_pointer()
        current_spec = (
            str(pointer["pointer"].get("spec"))
            if pointer.get("valid") and pointer.get("pointer")
            else None
        )
        for item in payload.get("specs", []):
            item["current"] = bool(current_spec and item.get("spec") == current_spec)
        payload["current_spec"] = current_spec
        payload["session"] = self.session_info()
        return payload

    def inbox(self, stale_days: int | None = None) -> dict[str, Any]:
        """Return the read-only list of work waiting for a human."""
        args = ["inbox", "--json"]
        if stale_days is not None:
            args.extend(["--stale-days", str(stale_days)])
        return self._json(self._run(args))

    def metrics(self, since: str | None = None) -> dict[str, Any]:
        """Return read-only lead-time, rework and intervention metrics."""
        args = ["metrics", "--json"]
        if since:
            args.extend(["--since", since])
        return self._json(self._run(args))

    def events(self, spec: str | None = None) -> dict[str, Any]:
        """Return the append-only audit stream for one Spec."""
        resolved = spec or self._resolve_current_spec()
        return self._json(
            self._run(["events", "--spec", resolved, "--json"])
        )

    def session(
        self,
        spec: str | None = None,
        max_chars: int = 12000,
    ) -> dict[str, Any]:
        """Resume the session-bound work item, or select the only active spec."""
        specs = self.list_specs()
        pointer = self.read_pointer()
        if spec:
            return self._session_payload(spec, specs, max_chars, bind=True)
        if pointer.get("valid") and pointer.get("pointer"):
            bound_spec = str(pointer["pointer"].get("spec"))
            if any(str(item["spec"]) == bound_spec for item in specs):
                return self._session_payload(
                    bound_spec,
                    specs,
                    max_chars,
                    bind=True,
                    pointer=pointer,
                )
        branch_spec = self._branch_spec()
        if branch_spec and any(str(item["spec"]) == branch_spec for item in specs):
            return self._session_payload(
                branch_spec,
                specs,
                max_chars,
                bind=True,
                pointer=pointer if pointer.get("found") else None,
            )
        pending_pr = [
            item
            for item in specs
            if item.get("action") == "open_pr"
        ]
        if len(pending_pr) == 1:
            return self._session_payload(
                str(pending_pr[0]["spec"]),
                specs,
                max_chars,
                bind=True,
                pointer=pointer if pointer.get("found") else None,
            )
        if len(specs) == 1:
            return self._session_payload(
                str(specs[0]["spec"]),
                specs,
                max_chars,
                bind=True,
                pointer=pointer if pointer.get("found") else None,
            )
        if not specs:
            return {
                "project": self.project_id,
                "specs": [],
                "action": "create_spec",
                "start_with": "sdd start-work",
                "guidance": (
                    "No active spec. Ask for the work item once, then run "
                    "`sdd start-work --work-item ...`. Do not ask for an SDD stage."
                ),
                "session": self.session_info(),
                "pointer": pointer,
                "loop_contract": self._loop_contract(),
                "autopilot": self.AUTOPILOT_CONTRACT,
            }
        return {
            "project": self.project_id,
            "spec": None,
            "action": "select_spec",
            "specs": specs,
            "guidance": (
                "Multiple specs exist and this session has no valid pointer. "
                "If the developer supplied a work item, call `sdd start-work`; "
                "otherwise ask once which spec to resume."
            ),
            "session": self.session_info(),
            "pointer": pointer,
            "loop_contract": self._loop_contract(),
            "autopilot": self.AUTOPILOT_CONTRACT,
        }

    def _session_payload(
        self,
        spec: str,
        specs: list[dict[str, Any]],
        max_chars: int,
        bind: bool,
        pointer: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        status = self.status(spec)
        next_action = self._agent_next(spec)
        if bind:
            pointer = {"found": True, "valid": True, "stale": False, "pointer": self.bind_session(spec)}
        return {
            "project": self.project_id,
            "spec": spec,
            "state": status.get("state", {}).get("state"),
            "status": status,
            "next": next_action,
            "context": self.context(spec, max_chars),
            "specs": specs,
            "session": self.session_info(),
            "pointer": pointer,
            "loop_contract": self._loop_contract(),
            "autopilot": self.AUTOPILOT_CONTRACT,
            "human_checkpoint": self._human_checkpoint(spec),
        }

    def start_work(
        self,
        work_item: str,
        issue_url: str | None = None,
        title: str | None = None,
        description: str | None = None,
        domain: str = "REQ",
        risk: str = "low",
        risk_labels: Iterable[str] = (),
        product_type: str = "传统产品",
        workflow: str | None = None,
    ) -> dict[str, Any]:
        """Start or resume a requirement from a work item in one call."""
        existing = next(
            (
                item
                for item in self.list_specs()
                if str(item.get("work_item") or "") == work_item
            ),
            None,
        )
        if existing:
            spec_id = str(existing["spec"])
            work_order = self.session(spec_id)
            return {
                "resumed": True,
                "spec_id": spec_id,
                "work_order": work_order,
                "driver_prompt": "sdd/prompts/autopilot.md",
                "autopilot": self.AUTOPILOT_CONTRACT,
                "session": self.session_info(),
                "human_checkpoint": self._human_checkpoint(spec_id),
            }

        reserved = self.reserve_spec_id(domain)
        resolved_title = (title or "").strip()
        if not resolved_title and description:
            resolved_title = description.strip().splitlines()[0][:80]
        resolved_title = resolved_title or work_item
        created = self.create_spec(
            title=resolved_title,
            spec_id=str(reserved["spec_id"]),
            work_item=work_item,
            issue_url=issue_url,
            risk=risk,
            risk_labels=risk_labels,
            product_type=product_type,
            workflow=workflow,
        )
        spec_id = str(created["spec_id"])
        spec_dir = self._spec_dir_from_status(spec_id)
        context = [
            "# 需求上下文",
            "",
            f"- Work item: `{work_item}`",
        ]
        if issue_url:
            context.append(f"- Issue: {issue_url}")
        context.extend(
            [
                "",
                "## 原始需求",
                "",
                description.strip()
                if description
                else "（未提供，需 Agent 从工作项系统或 issue 读取）",
                "",
                "## 调研事实",
                "",
                "- [ ] Agent 补充：相关服务、调用链、数据、契约和历史决策",
                "",
            ]
        )
        (spec_dir / "context.md").write_text("\n".join(context), encoding="utf-8")
        (spec_dir / "unknowns.md").write_text(
            "# 未决问题\n\n"
            "- [ ] 需要 Agent 调研后补充；只在无法从代码/文档判断时向人提一个问题\n",
            encoding="utf-8",
        )

        work_order = self.session(spec_id)
        return {
            "resumed": False,
            "spec_id": spec_id,
            "work_order": work_order,
            "driver_prompt": "sdd/prompts/autopilot.md",
            "autopilot": self.AUTOPILOT_CONTRACT,
            "session": self.session_info(),
            "human_checkpoint": self._human_checkpoint(spec_id),
            "research_checklist": [
                "Read the issue/work item: scope, actors, constraints, examples.",
                "Run `sdd context` for service cards, contracts, ADRs and glossary.",
                "Inspect relevant code paths and existing tests.",
                "Record unknowns in context.md/unknowns.md before asking one blocking question.",
                "Draft spec.md, then run `sdd submit`. Stop for human approval.",
            ],
        }

    def submit_artifact(
        self,
        spec: str,
        artifact: str,
        content: str,
        run_commands: bool = True,
    ) -> dict[str, Any]:
        """Write an artifact, validate it, and advance deterministic stages."""
        allowed = {
            "spec.md",
            "design.md",
            "tasks.md",
            "verification.md",
            "context.md",
            "unknowns.md",
        }
        if artifact not in allowed:
            raise ValueError(
                "artifact must be one of: " + ", ".join(sorted(allowed))
            )
        if not content.strip():
            raise ValueError("content must not be empty")

        spec_dir = self._spec_dir_from_status(spec)
        if artifact in {"context.md", "unknowns.md"}:
            path = (spec_dir / artifact).resolve()
            if self.root.resolve() not in path.parents:
                raise ValueError("artifact path escapes the project root")
            path.write_text(content, encoding="utf-8")
            self.bind_session(spec)
            return {
                "ok": True,
                "artifact": artifact,
                "non_advancing": True,
                "state": self.status(spec).get("state", {}).get("state"),
                "next": self._agent_next(spec),
                "session": self.session_info(),
            }

        next_action = self._agent_next(spec)
        expected = {
            "write_spec": "spec.md",
            "write_design": "design.md",
            "write_tasks": "tasks.md",
            "run_verification": "verification.md",
        }.get(str(next_action.get("action")))
        if artifact != expected:
            return {
                "ok": False,
                "artifact": artifact,
                "errors": [
                    f"current action is {next_action.get('action')}; "
                    f"expected artifact is {expected or '(none)'}"
                ],
                "next": next_action,
                "session": self.session_info(),
            }

        path = (spec_dir / artifact).resolve()
        if self.root.resolve() not in path.parents:
            raise ValueError("artifact path escapes the project root")
        path.write_text(content, encoding="utf-8")
        if artifact == "spec.md":
            self.index(spec)

        verification = None
        if artifact == "verification.md" and run_commands:
            try:
                verification = self.verify(spec)
            except SddCommandError as exc:
                return {
                    "ok": False,
                    "artifact": artifact,
                    "errors": [str(exc)],
                    "verification": exc.stdout.strip(),
                    "next": self._agent_next(spec),
                    "session": self.session_info(),
                }

        stage = {
            "spec.md": "spec",
            "design.md": "design",
            "tasks.md": "tasks",
            "verification.md": "verify",
        }[artifact]
        checked = self.check(spec, stage)
        if not checked.get("ok"):
            return {
                "ok": False,
                "artifact": artifact,
                "stage": stage,
                "errors": checked.get("errors", []),
                "next": self._agent_next(spec),
                "session": self.session_info(),
            }

        if artifact == "spec.md":
            self.bind_session(spec)
            return {
                "ok": True,
                "artifact": artifact,
                "state": "DRAFT",
                "awaiting_human_approval": True,
                "message": (
                    "spec 已通过检查。现在停在人类审批点；不要继续写 design，"
                    "也不要调用 approve。"
                ),
                "human_checkpoint": self._human_checkpoint(spec),
                "next": self._agent_next(spec),
                "session": self.session_info(),
            }

        try:
            completed = self.complete(
                spec,
                evidence=f"{artifact} submitted via CLI and checked",
            )
            if artifact == "tasks.md" and completed.get("next", {}).get(
                "action"
            ) == "start_implementation":
                completed = self.complete(
                    spec,
                    evidence="implementation started automatically by CLI",
                )
        except SddCommandError as exc:
            checkpoint = self._manual_gate_checkpoint(spec)
            if checkpoint:
                self.bind_session(spec)
                return {
                    "ok": True,
                    "artifact": artifact,
                    "stage": stage,
                    "awaiting_human_approval": True,
                    "human_checkpoint": checkpoint,
                    "next": self._agent_next(spec),
                    "session": self.session_info(),
                }
            return {
                "ok": False,
                "artifact": artifact,
                "stage": stage,
                "errors": [str(exc)],
                "verification": (verification or {}).get("stdout"),
                "next": self._agent_next(spec),
                "session": self.session_info(),
            }
        self.bind_session(spec)
        return {
            "ok": True,
            "artifact": artifact,
            "stage": stage,
            "completed": True,
            "verification": verification,
            "next": completed.get("next"),
            "human_checkpoint": self._human_checkpoint(spec),
            "session": self.session_info(),
        }

    def submit_task(
        self,
        spec: str,
        task: str,
        evidence: str,
        commit: str | None = None,
    ) -> dict[str, Any]:
        """Start the current task if needed, then complete it with evidence."""
        next_action = self._agent_next(spec)
        if next_action.get("action") != "implement_task":
            return {
                "ok": False,
                "errors": [
                    f"current action is {next_action.get('action')}; expected implement_task"
                ],
                "next": next_action,
                "session": self.session_info(),
            }
        if next_action.get("task") != task:
            return {
                "ok": False,
                "errors": [
                    f"current task is {next_action.get('task')}; cannot complete {task}"
                ],
                "next": next_action,
                "session": self.session_info(),
            }
        self.start(spec, task)
        try:
            self.complete(
                spec,
                evidence,
                task=task,
                commit=commit,
            )
        except SddCommandError as exc:
            return {
                "ok": False,
                "task": task,
                "errors": [str(exc)],
                "next": self._agent_next(spec),
                "session": self.session_info(),
            }
        self.bind_session(spec)
        payload = {
            "ok": True,
            "task": task,
            "completed": True,
            "next": self._agent_next(spec),
            "human_checkpoint": self._human_checkpoint(spec),
            "session": self.session_info(),
        }
        if payload["next"].get("action") == "finish_implementation":
            checkpoint = self._manual_gate_checkpoint(spec)
            if checkpoint:
                payload["awaiting_human_approval"] = True
                payload["human_checkpoint"] = checkpoint
        return payload

    def status(self, spec: str | None = None) -> dict[str, Any]:
        if spec is None:
            try:
                spec = self._resolve_current_spec()
            except ValueError:
                pass
        args = ["status"]
        if spec:
            args.extend(["--spec", spec])
        args.append("--json")
        return self._json(self._run(args))

    def next(self, spec: str | None = None) -> dict[str, Any]:
        if spec is None:
            try:
                spec = self._resolve_current_spec()
            except ValueError:
                pass
        args = ["next"]
        if spec:
            args.extend(["--spec", spec])
        args.append("--json")
        return self._json(self._run(args))

    def check(
        self,
        spec: str | None = None,
        stage: str = "auto",
        check_git: bool = False,
        all_specs: bool = False,
    ) -> dict[str, Any]:
        args = ["check"]
        if all_specs:
            args.append("--all")
            if spec:
                raise ValueError("--all cannot be combined with --spec")
        elif spec:
            args.extend(["--spec", spec])
        args.extend(["--stage", stage, "--json"])
        if check_git:
            args.append("--check-git")
        result = self._run(args, accept_exit=(0, 1))
        payload = self._json(result)
        payload["exit_code"] = result.returncode
        return payload

    def index(self, spec: str) -> dict[str, Any]:
        result = self._run(["index", "--spec", spec, "--json"])
        return self._json(result)

    def create_spec(
        self,
        title: str,
        spec_id: str | None = None,
        domain: str | None = None,
        work_item: str | None = None,
        issue_url: str | None = None,
        risk: str = "low",
        risk_labels: Iterable[str] = (),
        product_type: str = "传统产品",
        workflow: str | None = None,
    ) -> dict[str, Any]:
        args = ["new"]
        if spec_id:
            args.append(spec_id)
        elif domain:
            args.extend(["--domain", domain])
        else:
            raise ValueError("spec_id or domain is required")
        args.extend(["--title", title])
        if work_item:
            args.extend(["--work-item", work_item])
        if issue_url:
            args.extend(["--issue-url", issue_url])
        if risk:
            args.extend(["--risk", risk])
        for label in risk_labels:
            args.extend(["--risk-label", label])
        if product_type:
            args.extend(["--product-type", product_type])
        if workflow:
            args.extend(["--workflow", workflow])
        result = self._run(args)
        created = self._created_spec_id(result.stdout) or spec_id
        payload: dict[str, Any] = {
            "project": self.project_id,
            "spec_id": created,
            "stdout": result.stdout.strip(),
        }
        if created:
            payload["status"] = self.status(created)
        return payload

    def reserve_spec_id(self, domain: str) -> dict[str, Any]:
        normalized = domain.strip().upper()
        if not re.fullmatch(r"[A-Z][A-Z0-9]*", normalized):
            raise ValueError("domain must look like ORDER, PAYMENT, USER")
        config = self.config
        specs_root = self.root / config.get("spec_root", "docs/specs")
        existing = 0
        if specs_root.is_dir():
            pattern = re.compile(rf"SPEC-{re.escape(normalized)}-(\d{{3}})$")
            for item in specs_root.iterdir():
                match = pattern.fullmatch(item.name) if item.is_dir() else None
                if match:
                    existing = max(existing, int(match.group(1)))

        state_path = self.allocation_root / ".sdd-allocations.json"
        with self._allocation_lock(state_path.with_suffix(".lock")):
            try:
                data = json.loads(state_path.read_text(encoding="utf-8"))
            except (FileNotFoundError, json.JSONDecodeError):
                data = {}
            current = int(data.get(normalized, 0))
            next_number = max(current, existing) + 1
            if next_number > 999:
                raise ValueError(f"SPEC-{normalized}-NNN is exhausted (999)")
            data[normalized] = next_number
            temporary = state_path.with_suffix(f".{os.getpid()}.tmp")
            temporary.write_text(
                json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            os.replace(temporary, state_path)
        return {
            "project": self.project_id,
            "domain": normalized,
            "spec_id": f"SPEC-{normalized}-{next_number:03d}",
            "counter": next_number,
        }

    def start(self, spec: str, task: str) -> dict[str, Any]:
        result = self._run(["start", "--spec", spec, "--task", task])
        return {"project": self.project_id, "spec": spec, "stdout": result.stdout.strip()}

    def complete(
        self,
        spec: str,
        evidence: str,
        task: str | None = None,
        commit: str | None = None,
        human: bool = False,
        approver: str | None = None,
    ) -> dict[str, Any]:
        args = ["complete", "--spec", spec, "--evidence", evidence]
        if task:
            args.extend(["--task", task])
        if commit:
            args.extend(["--commit", commit])
        if human:
            args.append("--human")
        if approver:
            args.extend(["--approver", approver])
        result = self._run(args)
        return {
            "project": self.project_id,
            "spec": spec,
            "stdout": result.stdout.strip(),
            "next": self._agent_next(spec),
        }

    def verify(
        self,
        spec: str,
        commands: Iterable[str] = (),
    ) -> dict[str, Any]:
        args = ["verify", "--spec", spec]
        for command in commands:
            args.extend(["--command", command])
        result = self._run(args)
        return {
            "project": self.project_id,
            "spec": spec,
            "stdout": result.stdout.strip(),
        }

    def report(self, spec: str) -> dict[str, Any]:
        result = self._run(["report", "--spec", spec])
        body = self.read_artifact(spec, "PR_BODY.md")
        return {
            "project": self.project_id,
            "spec": spec,
            "stdout": result.stdout.strip(),
            "body": body,
            "next": self._agent_next(spec),
            "instruction": (
                "Use PR_BODY.md for the human delivery confirmation. "
                "Do not open the PR until the state is MERGED."
            ),
        }

    def record_pr(self, spec: str, url: str | None = None) -> dict[str, Any]:
        args = ["pr", "--spec", spec]
        if url:
            args.extend(["--url", url])
        result = self._run(args)
        return {
            "project": self.project_id,
            "spec": spec,
            "stdout": result.stdout.strip(),
            "next": self._agent_next(spec),
        }

    def block(self, spec: str, reason: str) -> dict[str, Any]:
        result = self._run(["block", "--spec", spec, "--reason", reason])
        return {"project": self.project_id, "spec": spec, "stdout": result.stdout.strip()}

    def approve(
        self, spec: str | None, evidence: str, approver: str | None = None
    ) -> dict[str, Any]:
        args = ["approve"]
        if spec:
            args.extend(["--spec", spec])
        args.extend(["--human", "--evidence", evidence])
        if approver:
            args.extend(["--approver", approver])
        result = self._run(args)
        resolved = spec or self._resolve_current_spec()
        self.bind_session(resolved)
        return {
            "ok": True,
            "spec": resolved,
            "stdout": result.stdout.strip(),
            "next": self._agent_next(resolved),
            "session": self.session_info(),
        }

    def merge(
        self, spec: str | None, evidence: str, approver: str | None = None
    ) -> dict[str, Any]:
        args = ["merge"]
        if spec:
            args.extend(["--spec", spec])
        args.extend(["--human", "--evidence", evidence])
        if approver:
            args.extend(["--approver", approver])
        result = self._run(args)
        resolved = spec or self._resolve_current_spec()
        self.bind_session(resolved)
        return {
            "ok": True,
            "spec": resolved,
            "stdout": result.stdout.strip(),
            "next": self._agent_next(resolved),
            "session": self.session_info(),
        }

    def unblock(
        self, spec: str | None, evidence: str, approver: str | None = None
    ) -> dict[str, Any]:
        args = ["unblock"]
        if spec:
            args.extend(["--spec", spec])
        args.extend(["--human", "--evidence", evidence])
        if approver:
            args.extend(["--approver", approver])
        result = self._run(args)
        resolved = spec or self._resolve_current_spec()
        self.bind_session(resolved)
        return {
            "ok": True,
            "spec": resolved,
            "stdout": result.stdout.strip(),
            "next": self._agent_next(resolved),
            "session": self.session_info(),
        }

    def rewind(
        self,
        spec: str,
        target: str,
        reason: str,
        approver: str | None = None,
        force: bool = False,
        reopen_task: str | None = None,
        reset_tasks: bool = False,
    ) -> dict[str, Any]:
        """Human-only rewind to an earlier stage; delegates to sdd.py."""
        args = [
            "rewind",
            "--spec",
            spec,
            "--to",
            target,
            "--reason",
            reason,
            "--human",
            "--json",
        ]
        if approver:
            args.extend(["--approver", approver])
        if force:
            args.append("--force")
        if reopen_task:
            args.extend(["--reopen-task", reopen_task])
        if reset_tasks:
            args.append("--reset-tasks")
        result = self._run(args)
        payload = self._json(result)
        payload["project"] = self.project_id
        payload["session"] = self.session_info()
        return payload

    def read_artifact(self, spec: str, artifact: str) -> str:
        if artifact not in self.ARTIFACTS:
            allowed = ", ".join(sorted(self.ARTIFACTS))
            raise ValueError(f"artifact must be one of: {allowed}")
        status = self.status(spec)
        spec_dir = status.get("next", {}).get("spec_dir") or status.get("state", {}).get(
            "spec_dir"
        )
        if not spec_dir:
            spec_dir = self._find_spec_dir(spec)
        directory = (self.root / spec_dir).resolve()
        if self.root.resolve() not in directory.parents:
            raise ValueError("artifact path escapes the project root")
        path = directory / artifact
        if not path.is_file():
            raise FileNotFoundError(f"artifact not found: {path.relative_to(self.root)}")
        return path.read_text(encoding="utf-8")

    def context(self, spec: str | None = None, max_chars: int = 40000) -> dict[str, Any]:
        files: list[dict[str, Any]] = []
        candidates: list[Path] = []
        context_root = self.root / "sdd" / "context"
        if context_root.is_dir():
            candidates.extend(
                path
                for path in sorted(context_root.rglob("*"))
                if path.is_file() and path.suffix.lower() in {".md", ".json", ".yaml", ".yml"}
            )
        if spec:
            spec_dir = self._spec_dir_from_status(spec)
            for name in ("context.md", "unknowns.md"):
                path = spec_dir / name
                if path.is_file():
                    candidates.append(path)
        remaining = max_chars
        for path in candidates:
            if remaining <= 0:
                break
            text = path.read_text(encoding="utf-8")
            clipped = text[:remaining]
            files.append(
                {
                    "path": path.relative_to(self.root).as_posix(),
                    "content": clipped,
                    "truncated": len(clipped) < len(text),
                }
            )
            remaining -= len(clipped)
        return {
            "project": self.project_id,
            "spec": spec,
            "files": files,
            "note": (
                "No context files found. Add sdd/context/services/*.md, "
                "sdd/context/adr/*.md, sdd/context/contracts/*, or "
                "docs/specs/<id>/context.md."
                if not files
                else ""
            ),
        }

    def health(self) -> dict[str, Any]:
        return {
            "ok": True,
            "version": __version__,
            "mode": "local",
            "workspace_root": str(self.root),
            "project": self.project_id,
            "session": self.session_info(),
        }

    def _resolve_current_spec(self) -> str:
        pointer = self.read_pointer()
        if pointer.get("valid") and pointer.get("pointer"):
            return str(pointer["pointer"]["spec"])
        specs = self.list_specs()
        active = [item for item in specs if item.get("state") != "MERGED"]
        if len(active) == 1:
            return str(active[0]["spec"])
        raise ValueError("cannot resolve current spec; pass --spec")

    def _agent_next(self, spec: str) -> dict[str, Any]:
        action = dict(self.next(spec))
        action["submit_with"] = self.SUBMIT_TOOL.get(str(action.get("action")))
        return action

    def _branch_spec(self) -> str | None:
        branch = self._git_value("symbolic-ref", "--short", "HEAD") or self._git_value(
            "rev-parse", "--abbrev-ref", "HEAD"
        )
        if not branch or branch == "HEAD":
            return None
        match = re.search(r"SPEC-[A-Z][A-Z0-9]*-[0-9]{3}", branch.upper())
        return match.group(0) if match else None

    def _human_checkpoint(self, spec: str) -> dict[str, Any]:
        state = self.status(spec).get("state", {}).get("state")
        spec_dir = self._spec_dir_from_status(spec).relative_to(self.root)
        if state == "DRAFT":
            return {
                "required": True,
                "type": "spec_approval",
                "artifact": f"{spec_dir.as_posix()}/spec.md",
                "command": (
                    f"python -m sdd approve --spec {spec} --human "
                    "--evidence \"需求已确认\""
                ),
                "message": "人类确认需求范围后执行 approve；Agent 不得继续下一阶段。",
            }
        if state == "PR_READY":
            return {
                "required": True,
                "type": "delivery_confirmation",
                "artifact": f"{spec_dir.as_posix()}/PR_BODY.md",
                "command": (
                    f"python -m sdd merge --spec {spec} --human "
                    "--evidence \"交付已确认\""
                ),
                "message": (
                    "人类确认交付后执行 merge；确认前 Agent 不得创建 PR。"
                ),
            }
        return {
            "required": False,
            "type": None,
            "message": "当前没有需要人类介入的 SDD 检查点。",
        }

    def _manual_gate_checkpoint(self, spec: str) -> dict[str, Any] | None:
        inbox = self.inbox()
        for item in inbox.get("items", []):
            if item.get("spec") == spec and item.get("action") == "manual_gate":
                return {
                    "required": True,
                    "type": "manual_gate",
                    "gate": item.get("gate"),
                    "artifact": item.get("artifact"),
                    "command": item.get("command"),
                    "message": (
                        "当前阶段的自动检查已通过，但 Gate 要求人工确认；"
                        "Agent 必须停止，等人执行命令。"
                    ),
                }
        return None

    def _loop_contract(self) -> str:
        return (
            "This is a CLI-first autopilot session. A developer gives one work "
            "item; the agent follows next.action and calls next.submit_with after "
            "producing the requested artifact. Do not ask the developer what "
            "stage the work is in. The CLI re-validates and returns the next "
            "action. A task must be submitted with `sdd submit-task`. Never edit "
            "state.json. approve, merge, unblock and rewind are human-only."
        )

    def _run(
        self,
        args: list[str],
        accept_exit: tuple[int, ...] = (0,),
    ) -> CommandResult:
        script = self.root / "sdd" / "scripts" / "sdd.py"
        command = [sys.executable, str(script), "--root", str(self.root), *args]
        env = os.environ.copy()
        env.setdefault("PYTHONIOENCODING", "utf-8")
        env["SDD_SESSION_KEY"] = self.session_key
        env["SDD_SESSION_SOURCE"] = self.session_source
        env["SDD_SOURCE"] = self.source
        env.setdefault("SDD_ACTOR", "agent")
        result = subprocess.run(
            command,
            cwd=self.root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )
        rendered = " ".join(["sdd", *args])
        if result.returncode not in accept_exit:
            raise SddCommandError(
                rendered,
                result.returncode,
                result.stdout,
                result.stderr,
            )
        return CommandResult(
            command=rendered,
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
        )

    @staticmethod
    def _json(result: CommandResult) -> dict[str, Any]:
        text = result.stdout.strip()
        if not text:
            raise SddCommandError(result.command, result.returncode, "", result.stderr)
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise SddCommandError(
                result.command,
                result.returncode,
                result.stdout,
                result.stderr,
            ) from exc
        if not isinstance(payload, dict):
            raise SddCommandError(result.command, result.returncode, result.stdout)
        return payload

    @staticmethod
    def _created_spec_id(stdout: str) -> str | None:
        match = re.search(r"(?:SPEC-[A-Z][A-Z0-9]*-[0-9]{3})", stdout)
        return match.group(0) if match else None

    def _spec_dir_from_status(self, spec: str) -> Path:
        status = self.status(spec)
        spec_dir = status.get("next", {}).get("spec_dir")
        if not spec_dir:
            spec_dir = self._find_spec_dir(spec)
        path = (self.root / spec_dir).resolve()
        if self.root.resolve() not in path.parents:
            raise ValueError("spec path escapes the project root")
        return path

    def _find_spec_dir(self, spec: str) -> str:
        path = self._find_spec_dir_optional(spec)
        if not path.is_dir():
            raise ValueError(f"cannot resolve spec directory for {spec}")
        return path.relative_to(self.root).as_posix()

    def _find_spec_dir_optional(self, spec: str) -> Path:
        config = self.config
        root = self.root / config.get("spec_root", "docs/specs")
        matches = [path for path in root.glob(spec) if path.is_dir()] if spec else []
        if len(matches) == 1:
            return matches[0]
        return self.root / config.get("spec_root", "docs/specs") / spec

    def _git_value(self, *args: str) -> str | None:
        try:
            result = subprocess.run(
                ["git", *args],
                cwd=self.root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except OSError:
            return None
        return result.stdout.strip() if result.returncode == 0 else None

    @staticmethod
    def _now() -> str:
        from datetime import datetime

        return datetime.now().astimezone().isoformat(timespec="seconds")

    @staticmethod
    @contextmanager
    def _allocation_lock(path: Path) -> Iterator[None]:
        path.parent.mkdir(parents=True, exist_ok=True)
        deadline = time.monotonic() + 10
        handle: int | None = None
        while handle is None:
            try:
                handle = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                try:
                    if time.time() - path.stat().st_mtime > 30:
                        path.unlink()
                        continue
                except FileNotFoundError:
                    continue
                if time.monotonic() > deadline:
                    raise TimeoutError(f"timed out waiting for allocation lock: {path}")
                time.sleep(0.05)
        try:
            yield
        finally:
            os.close(handle)
            path.unlink(missing_ok=True)


PROTECTED_FILES = (
    "sdd/VERSION",
    "sdd/__init__.py",
    "sdd/__main__.py",
    "sdd/agents.py",
    "sdd/cli.py",
    "sdd/core.py",
    "sdd/agent-block.md",
    "sdd/agent-contract.md",
)

PROTECTED_DIRS = (
    "sdd/templates",
    "sdd/workflows",
    "sdd/prompts",
    "sdd/ci",
    "sdd/mcp",
    "sdd/scripts",
)


def protected_files(root: str | Path) -> list[Path]:
    base = Path(root).expanduser().resolve()
    files: set[Path] = set()
    for relative in PROTECTED_FILES:
        path = base / relative
        if path.is_file():
            files.add(path)
    for relative in PROTECTED_DIRS:
        path = base / relative
        if not path.is_dir():
            continue
        for item in path.rglob("*"):
            if not item.is_file():
                continue
            if "__pycache__" in item.parts or item.suffix == ".pyc":
                continue
            files.add(item)
    return sorted(files)


def write_manifest(root: str | Path) -> dict[str, Any]:
    base = Path(root).expanduser().resolve()
    version = (base / "sdd" / "VERSION").read_text(encoding="utf-8").strip()
    files = {
        path.relative_to(base).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in protected_files(base)
    }
    payload = {"kind": "manifest", "version": version, "files": files}
    path = base / "sdd" / "manifest.json"
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return payload


def verify_core(root: str | Path) -> list[str]:
    base = Path(root).expanduser().resolve()
    manifest_path = base / "sdd" / "manifest.json"
    if not manifest_path.is_file():
        return ["缺少 sdd/manifest.json；运行 `python -m sdd manifest --write`"]
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"无法读取 sdd/manifest.json：{exc}"]
    expected = payload.get("files")
    if not isinstance(expected, dict):
        return ["sdd/manifest.json 缺少 files 对象"]
    errors: list[str] = []
    for relative, digest in sorted(expected.items()):
        path = base / relative
        if not path.is_file():
            errors.append(f"受保护文件缺失：{relative}")
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != digest:
            errors.append(f"受保护文件被修改：{relative}")
    version_path = base / "sdd" / "VERSION"
    if not version_path.is_file():
        errors.append("缺少 sdd/VERSION")
    elif str(payload.get("version")) != version_path.read_text(encoding="utf-8").strip():
        errors.append("sdd/manifest.json 与 sdd/VERSION 版本不一致")
    return errors
