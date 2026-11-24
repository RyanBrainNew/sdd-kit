import ast
import json
import unittest
from pathlib import Path


KIT_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = KIT_ROOT / "deploy" / "runner" / "CONTRACT.md"

PHASES = (
    "## 1. 准备隔离工作区",
    "## 2. 启动或恢复工作项",
    "## 3. 读取 next",
    "## 4. 运行 Agent",
    "## 5. 提交阶段产物与任务证据",
    "## 6. 处理人工检查点",
    "## 7. 归档运行证据",
)

PUBLIC_COMMANDS = {
    "start-work",
    "resume",
    "submit",
    "submit-task",
    "complete",
    "events",
}

HUMAN_ACTIONS = ("approve", "reapprove", "merge", "unblock", "rewind", "waive")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def split_sections(text: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current = ""
    body: list[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            if current:
                sections[current] = "\n".join(body)
            current = line.strip()
            body = []
            continue
        body.append(line)
    if current:
        sections[current] = "\n".join(body)
    return sections


class ContractDocumentTests(unittest.TestCase):
    def setUp(self):
        if not CONTRACT_PATH.is_file():
            self.fail(f"缺少契约文件：{CONTRACT_PATH}")
        self.text = read_text(CONTRACT_PATH)
        self.sections = split_sections(self.text)

    def test_contract_has_required_phases(self):
        # [AC-001-1]
        for heading in PHASES:
            self.assertIn(heading, self.sections)

    def test_contract_maps_each_phase_to_cli(self):
        # [AC-001-2]
        for heading in PHASES:
            body = self.sections[heading]
            for field in ("命令", "输入", "输出", "失败"):
                self.assertIn(field, body, msg=f"{heading} 缺少 {field}")
            self.assertIn("python -m sdd ", body, msg=f"{heading} 缺少 CLI 命令")

    def test_examples_use_public_cli_only(self):
        # [AC-001-3]
        for command in PUBLIC_COMMANDS:
            self.assertIn(f"python -m sdd {command}", self.text)
        self.assertNotIn("sdd/scripts", self.text)
        self.assertNotIn("import sdd", self.text)

    def test_contract_covers_result_states(self):
        # [AC-002-1]
        section = self.sections["## 8. 返回类型与退出语义"]
        for token in ("成功", "ok=false", "decision_required", "awaiting_human_approval"):
            self.assertIn(token, section)
        self.assertIn("退出", section)

    def test_contract_forbids_human_actions(self):
        # [AC-002-2]
        section = self.sections["## 9. Runner 职责与禁止动作"]
        for action in HUMAN_ACTIONS:
            self.assertIn(action, section)
        self.assertIn("不得调用", section)
        self.assertIn("human_checkpoint", section)

    def test_contract_assigns_runtime_to_runner(self):
        # [AC-002-3]
        section = self.sections["## 9. Runner 职责与禁止动作"]
        for token in ("Docker", "沙箱", "日志", "资源"):
            self.assertIn(token, section)
        self.assertIn("不属于", section)


class EntryPointTests(unittest.TestCase):
    def test_readme_links_runner_contract(self):
        # [AC-003-1]
        for name in ("README.md", "sdd/README.md"):
            text = read_text(KIT_ROOT / name)
            self.assertIn("deploy/runner/CONTRACT.md", text, msg=name)


class ReleaseBoundaryTests(unittest.TestCase):
    def test_mcp_exposes_no_human_actions(self):
        # [AC-003-2]
        source = read_text(KIT_ROOT / "sdd" / "mcp" / "server.py")
        tree = ast.parse(source)
        names = {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        for action in HUMAN_ACTIONS:
            self.assertNotIn(f"sdd_{action}", names)
        manifest = json.loads(read_text(KIT_ROOT / "sdd" / "manifest.json"))
        self.assertIn("sdd/mcp/server.py", manifest["files"])


if __name__ == "__main__":
    unittest.main()
