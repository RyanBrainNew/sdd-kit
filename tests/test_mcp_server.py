import asyncio
import json
import shutil
import tempfile
import unittest
from pathlib import Path

try:
    from mcp.client.client import Client

    from sdd.mcp.registry import Registry
    from sdd.mcp.server import create_server
    from sdd.mcp.service import SddService
except ImportError:
    Client = None
    create_server = None
    Registry = None
    SddService = None


KIT_ROOT = Path(__file__).resolve().parents[1]


@unittest.skipIf(Client is None, "mcp SDK not installed")
class SddMcpServerTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        shutil.copytree(KIT_ROOT / "sdd", self.root / "sdd")
        (self.root / "docs").mkdir()
        self.registry_path = self.root / "sdd-mcp.json"
        self.registry_path.write_text(
            json.dumps(
                {
                    "workspace_root": str(self.root),
                    "projects": {"demo": {"path": "."}},
                }
            ),
            encoding="utf-8",
        )
        self.service = SddService(Registry.load(self.registry_path))
        self.server = create_server(self.service)

    def tearDown(self):
        self.temp.cleanup()

    def test_tools_and_health(self):
        async def run():
            async with Client(self.server) as client:
                tools = await client.list_tools()
                result = await client.call_tool("sdd_health", {})
                return [tool.name for tool in tools.tools], result

        names, result = asyncio.run(run())
        self.assertIn("sdd_session", names)
        self.assertIn("sdd_start_work", names)
        self.assertIn("sdd_submit_artifact", names)
        self.assertIn("sdd_submit_task", names)
        self.assertIn("sdd_list_specs", names)
        self.assertIn("sdd_board", names)
        self.assertIn("sdd_pr", names)
        self.assertIn("sdd_next", names)
        self.assertIn("sdd_context", names)
        self.assertIn("sdd_reserve_spec_id", names)
        self.assertNotIn("sdd_approve", names)
        self.assertNotIn("sdd_merge", names)
        self.assertFalse(getattr(result, "is_error", getattr(result, "isError", False)))

    def test_local_root_mode_health(self):
        server = create_server(SddService(Registry.single(self.root)))

        async def run():
            async with Client(server) as client:
                return await client.call_tool("sdd_health", {})

        result = asyncio.run(run())
        payload = getattr(result, "structured_content", None)
        self.assertIsNotNone(payload)
        self.assertEqual(payload["mode"], "local")
        self.assertEqual(payload["projects"], 1)


if __name__ == "__main__":
    unittest.main()
