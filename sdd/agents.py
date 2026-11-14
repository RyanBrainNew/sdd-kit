from __future__ import annotations

import re
from pathlib import Path


BEGIN_MARKER = "<!-- SDD:MANAGED:START -->"
END_MARKER = "<!-- SDD:MANAGED:END -->"


def agent_block(root: str | Path) -> str:
    path = Path(root).expanduser().resolve() / "sdd" / "agent-block.md"
    if not path.is_file():
        raise FileNotFoundError(f"missing SDD agent block: {path}")
    return path.read_text(encoding="utf-8").strip()


def _normalize(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n").strip()


def extract_managed_block(text: str) -> str:
    normalized = _normalize(text)
    pattern = re.compile(
        re.escape(BEGIN_MARKER) + r".*?" + re.escape(END_MARKER),
        re.DOTALL,
    )
    match = pattern.search(normalized)
    return match.group(0).strip() if match else ""


def merge_managed_block(existing: str, block: str) -> str:
    """Replace only the managed block; preserve every line outside it."""
    existing = _normalize(existing)
    block = _normalize(block)
    pattern = re.compile(
        re.escape(BEGIN_MARKER) + r".*?" + re.escape(END_MARKER),
        re.DOTALL,
    )
    if pattern.search(existing):
        return pattern.sub(block, existing, count=1).strip() + "\n"
    if not existing:
        return block + "\n"
    return existing.rstrip() + "\n\n" + block + "\n"


def sync_agents(root: str | Path) -> dict[str, object]:
    base = Path(root).expanduser().resolve()
    block = agent_block(base)
    path = base / "AGENTS.md"
    existing = path.read_text(encoding="utf-8") if path.is_file() else ""
    merged = merge_managed_block(existing, block)
    changed = merged != existing
    if changed:
        path.write_text(merged, encoding="utf-8", newline="\n")
    return {
        "ok": True,
        "path": path.relative_to(base).as_posix(),
        "changed": changed,
        "created": not bool(existing),
    }


def verify_agents(root: str | Path) -> list[str]:
    base = Path(root).expanduser().resolve()
    path = base / "AGENTS.md"
    if not path.is_file():
        return ["缺少 AGENTS.md"]
    expected = agent_block(base)
    actual = extract_managed_block(path.read_text(encoding="utf-8"))
    if not actual:
        return ["AGENTS.md 缺少 SDD 托管块"]
    if _normalize(actual) != _normalize(expected):
        return ["AGENTS.md 的 SDD 托管块与 sdd/agent-block.md 不一致"]
    return []
