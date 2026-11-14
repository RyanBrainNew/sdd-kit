import tempfile
import unittest
from pathlib import Path

from sdd.agents import (
    BEGIN_MARKER,
    END_MARKER,
    sync_agents,
    verify_agents,
)


KIT_ROOT = Path(__file__).resolve().parents[1]


class AgentsBlockTest(unittest.TestCase):
    def make_target(self, temp: str) -> Path:
        target = Path(temp)
        (target / "sdd").mkdir()
        source = KIT_ROOT / "sdd" / "agent-block.md"
        (target / "sdd" / "agent-block.md").write_text(
            source.read_text(encoding="utf-8"), encoding="utf-8"
        )
        return target

    def test_creates_agents_with_managed_block(self):
        with tempfile.TemporaryDirectory() as temp:
            target = self.make_target(temp)
            result = sync_agents(target)
            self.assertTrue(result["created"])
            self.assertTrue(result["changed"])
            text = (target / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn(BEGIN_MARKER, text)
            self.assertIn(END_MARKER, text)
            self.assertEqual(verify_agents(target), [])

    def test_preserves_existing_rules_and_replaces_only_block(self):
        with tempfile.TemporaryDirectory() as temp:
            target = self.make_target(temp)
            existing = (
                "# Project rules\n\n"
                "Use pnpm and never edit generated files.\n\n"
                f"{BEGIN_MARKER}\nold block\n{END_MARKER}\n\n"
                "## Tail\n\nKeep this tail.\n"
            )
            (target / "AGENTS.md").write_text(existing, encoding="utf-8")
            result = sync_agents(target)
            self.assertTrue(result["changed"])
            text = (target / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("# Project rules", text)
            self.assertIn("Use pnpm", text)
            self.assertIn("## Tail", text)
            self.assertIn("Keep this tail.", text)
            self.assertNotIn("old block", text)
            self.assertEqual(text.count(BEGIN_MARKER), 1)
            self.assertEqual(verify_agents(target), [])

    def test_sync_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temp:
            target = self.make_target(temp)
            (target / "AGENTS.md").write_text("# Existing\n", encoding="utf-8")
            sync_agents(target)
            first = (target / "AGENTS.md").read_text(encoding="utf-8")
            result = sync_agents(target)
            self.assertFalse(result["changed"])
            self.assertEqual((target / "AGENTS.md").read_text(encoding="utf-8"), first)

    def test_verify_detects_missing_or_tampered_block(self):
        with tempfile.TemporaryDirectory() as temp:
            target = self.make_target(temp)
            (target / "AGENTS.md").write_text("# no block\n", encoding="utf-8")
            self.assertTrue(verify_agents(target))
            sync_agents(target)
            text = (target / "AGENTS.md").read_text(encoding="utf-8")
            (target / "AGENTS.md").write_text(
                text.replace("python -m sdd resume --json", "python -m sdd status"),
                encoding="utf-8",
            )
            self.assertTrue(verify_agents(target))


if __name__ == "__main__":
    unittest.main()
