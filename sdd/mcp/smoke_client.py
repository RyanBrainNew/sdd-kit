from __future__ import annotations

import argparse
import asyncio
import json

from mcp.client.client import Client


async def main(url: str) -> None:
    async with Client(url) as client:
        tools = await client.list_tools()
        print("tools:", ", ".join(tool.name for tool in tools.tools))
        health = await client.call_tool("sdd_health", {})
        payload = getattr(health, "structured_content", None) or health.model_dump()
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("url", nargs="?", default="http://127.0.0.1:8765/mcp")
    args = parser.parse_args()
    asyncio.run(main(args.url))
