from __future__ import annotations

import argparse
import os
import sys
from typing import Any

from . import __version__
from .registry import Registry, RegistryError
from .service import SddService

try:
    from mcp.server.mcpserver import MCPServer
except ImportError:  # pragma: no cover - compatibility with MCP SDK 1.x
    from mcp.server.fastmcp import FastMCP as MCPServer  # type: ignore


def create_server(service: SddService) -> Any:
    mode = service.registry.mode
    server = MCPServer(
        name="sdd-control-plane",
        version=__version__,
        instructions=(
            f"SDD autopilot control plane in {mode} mode. The repository CLI "
            "(`python -m sdd`) is the source of truth; MCP is an optional adapter. "
            "The developer supplies one work item, not an SDD stage. For new work "
            "call sdd_start_work once; for resume call sdd_session. Then follow "
            "next.action: research and produce the requested artifact, and submit "
            "it with next.submit_with (sdd_submit_artifact). Submit each "
            "implementation task with sdd_submit_task. The server re-validates the "
            "current state and returns the next action, so never ask the developer "
            "to choose a stage. Stop only at the returned human_checkpoint (spec "
            "approval or PR merge). In shared registry mode, writes apply to "
            "server-side worktrees only; a remote server cannot modify a "
            "developer's local clone. Agents must not edit state.json. approve, "
            "merge and unblock are deliberately not exposed as MCP tools."
        ),
    )

    @server.tool()
    def sdd_health() -> dict[str, Any]:
        """Return server version, registry path and project count."""
        return service.health()

    @server.tool()
    def sdd_list_projects() -> list[dict[str, Any]]:
        """List projects registered on this shared server."""
        return service.list_projects()

    @server.tool()
    def sdd_list_specs(project: str) -> list[dict[str, Any]]:
        """List specs with their current state and next action."""
        return service.list_specs(project)

    @server.tool()
    def sdd_board(project: str) -> dict[str, Any]:
        """Show a read-only board of specs, task statuses and next actions."""
        return service.board(project)

    @server.tool()
    def sdd_events(
        project: str,
        spec: str | None = None,
    ) -> dict[str, Any]:
        """Read the append-only state and human-checkpoint audit stream."""
        return service.events(project, spec)

    @server.tool()
    def sdd_session(
        project: str,
        spec: str | None = None,
        max_chars: int = 12000,
    ) -> dict[str, Any]:
        """One-call entrypoint: current state, next action, context and loop contract."""
        return service.session(project, spec, max_chars)

    @server.tool()
    def sdd_start_work(
        project: str,
        work_item: str,
        issue_url: str | None = None,
        title: str | None = None,
        description: str | None = None,
        domain: str = "REQ",
        risk: str = "low",
        risk_labels: list[str] | None = None,
        product_type: str = "传统产品",
    ) -> dict[str, Any]:
        """Start or resume a requirement from one work item; returns a work order."""
        return service.start_work(
            project,
            work_item=work_item,
            issue_url=issue_url,
            title=title,
            description=description,
            domain=domain,
            risk=risk,
            risk_labels=risk_labels or [],
            product_type=product_type,
        )

    @server.tool()
    def sdd_submit_artifact(
        project: str,
        spec: str,
        artifact: str,
        content: str,
        run_commands: bool = True,
    ) -> dict[str, Any]:
        """Submit the current artifact; the server validates and auto-advances."""
        return service.submit_artifact(
            project, spec, artifact, content, run_commands=run_commands
        )

    @server.tool()
    def sdd_submit_task(
        project: str,
        spec: str,
        task: str,
        evidence: str,
        commit: str | None = None,
    ) -> dict[str, Any]:
        """Complete the current task with evidence, auto-starting it if needed."""
        return service.submit_task(project, spec, task, evidence, commit)

    @server.tool()
    def sdd_status(
        project: str,
        spec: str | None = None,
    ) -> dict[str, Any]:
        """Read the current SDD state and next action for a project."""
        return service.status(project, spec)

    @server.tool()
    def sdd_next(
        project: str,
        spec: str | None = None,
    ) -> dict[str, Any]:
        """Return the exact next action the coding agent should execute."""
        return service.next(project, spec)

    @server.tool()
    def sdd_check(
        project: str,
        spec: str | None = None,
        stage: str = "auto",
        check_git: bool = False,
    ) -> dict[str, Any]:
        """Validate SDD artifacts and return structured errors."""
        return service.check(project, spec, stage, check_git)

    @server.tool()
    def sdd_create_spec(
        project: str,
        title: str,
        spec_id: str | None = None,
        domain: str | None = None,
        work_item: str | None = None,
        issue_url: str | None = None,
        risk: str = "low",
        risk_labels: list[str] | None = None,
        product_type: str = "传统产品",
    ) -> dict[str, Any]:
        """Create a new SDD spec in a registered project."""
        return service.create_spec(
            project,
            title=title,
            spec_id=spec_id,
            domain=domain,
            work_item=work_item,
            issue_url=issue_url,
            risk=risk,
            risk_labels=risk_labels or [],
            product_type=product_type,
        )

    @server.tool()
    def sdd_reserve_spec_id(
        project: str,
        domain: str,
    ) -> dict[str, Any]:
        """Atomically reserve the next SPEC-<domain>-NNN id across branches."""
        return service.reserve_spec_id(project, domain)

    @server.tool()
    def sdd_start(
        project: str,
        spec: str,
        task: str,
    ) -> dict[str, Any]:
        """Mark a task as In Progress before editing code."""
        return service.start(project, spec, task)

    @server.tool()
    def sdd_complete(
        project: str,
        spec: str,
        evidence: str,
        task: str | None = None,
        commit: str | None = None,
    ) -> dict[str, Any]:
        """Complete the current stage or task and advance the state machine."""
        return service.complete(project, spec, evidence, task, commit)

    @server.tool()
    def sdd_verify(
        project: str,
        spec: str,
        commands: list[str] | None = None,
    ) -> dict[str, Any]:
        """Run configured project tests and record command evidence."""
        return service.verify(project, spec, commands or [])

    @server.tool()
    def sdd_report(
        project: str,
        spec: str,
    ) -> dict[str, Any]:
        """Generate PR_BODY.md and return its contents."""
        return service.report(project, spec)

    @server.tool()
    def sdd_pr(
        project: str,
        spec: str,
        url: str | None = None,
    ) -> dict[str, Any]:
        """Record a PR URL after opening the PR; only valid in PR_READY/MERGED."""
        return service.record_pr(project, spec, url)

    @server.tool()
    def sdd_block(
        project: str,
        spec: str,
        reason: str,
    ) -> dict[str, Any]:
        """Stop work and record a blocking question with evidence."""
        return service.block(project, spec, reason)

    @server.tool()
    def sdd_read_artifact(
        project: str,
        spec: str,
        artifact: str,
    ) -> str:
        """Read an allowed SDD artifact (spec, design, tasks, verification, PR body)."""
        return service.read_artifact(project, spec, artifact)

    @server.tool()
    def sdd_context(
        project: str,
        spec: str | None = None,
        max_chars: int = 40000,
    ) -> dict[str, Any]:
        """Read service cards, contracts, ADRs and spec context for planning."""
        return service.context(project, spec, max_chars)

    return server


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sdd-mcp",
        description="Shared MCP control plane for registered SDD projects",
    )
    parser.add_argument(
        "--registry",
        default=None,
        help="path to sdd-mcp.json (or set SDD_MCP_REGISTRY)",
    )
    parser.add_argument(
        "--root",
        default=None,
        help="local repository root; enables local-clone mode (stdio by default)",
    )
    parser.add_argument(
        "--project-id",
        default=None,
        help="project id exposed in local-clone mode; default: sdd/config.json project",
    )
    parser.add_argument(
        "--transport",
        default=None,
        choices=["stdio", "sse", "streamable-http"],
    )
    parser.add_argument("--host", default=os.environ.get("SDD_MCP_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("SDD_MCP_PORT", "8765")))
    parser.add_argument(
        "--path",
        default=os.environ.get("SDD_MCP_PATH", "/mcp"),
        help="streamable HTTP path",
    )
    parser.add_argument("--version", action="version", version=__version__)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.root and args.registry:
        print("[sdd-mcp] use either --root or --registry, not both", file=sys.stderr)
        return 2
    try:
        registry = (
            Registry.single(args.root, args.project_id)
            if args.root
            else Registry.load(args.registry or os.environ.get("SDD_MCP_REGISTRY"))
        )
        service = SddService(registry)
    except (RegistryError, OSError, ValueError) as exc:
        print(f"[sdd-mcp] {exc}", file=sys.stderr)
        return 2

    server = create_server(service)
    transport = (
        args.transport
        or os.environ.get("SDD_MCP_TRANSPORT")
        or ("stdio" if args.root else "streamable-http")
    )
    if transport == "stdio":
        server.run("stdio")
    elif transport == "sse":
        server.run("sse", host=args.host, port=args.port)
    else:
        server.run(
            "streamable-http",
            host=args.host,
            port=args.port,
            streamable_http_path=args.path,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
