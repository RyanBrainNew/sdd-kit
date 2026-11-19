import re
import subprocess
import unittest
from pathlib import Path
from urllib.parse import urlparse


KIT_ROOT = Path(__file__).resolve().parents[1]
SITE = KIT_ROOT / "site"


def read_site(name: str) -> str:
    return (SITE / name).read_text(encoding="utf-8")


class SiteStructureTests(unittest.TestCase):
    def setUp(self):
        self.html = read_site("index.html")

    def test_hero_contract(self):
        """[AC-001-1] 首屏必须给出定位、版本和两个动作。"""
        self.assertIn('lang="zh-CN"', self.html)
        heading = re.search(r"<h1[^>]*>(.*?)</h1>", self.html, re.S)
        self.assertIsNotNone(heading)
        text = re.sub(r"<[^>]+>", "", heading.group(1)).strip()
        self.assertEqual(text, "把 SDD 装进仓库")
        self.assertIn('href="#quickstart"', self.html)
        self.assertIn("https://github.com/RyanBrainNew/sdd-kit", self.html)
        self.assertIn("0.6.1", self.html)

    def test_required_sections(self):
        """[AC-001-2] 六个内容区必须有稳定锚点。"""
        for anchor in (
            "why",
            "flow",
            "architecture",
            "quickstart",
            "commands",
            "fit",
            "faq",
        ):
            self.assertIn(f'id="{anchor}"', self.html)
        self.assertGreaterEqual(self.html.count("<section"), 6)

    def test_relative_assets(self):
        """[AC-001-3][AC-005-2] 资源必须相对路径且真实存在。"""
        references = re.findall(r'(?:src|href)="([^"]+)"', self.html)
        checked = 0
        for reference in references:
            parsed = urlparse(reference)
            if parsed.scheme or reference.startswith(("#", "mailto:", "data:")):
                continue
            self.assertFalse(
                reference.startswith("/"),
                f"绝对路径在 Pages 子路径下会失效：{reference}",
            )
            target = (SITE / reference.split("#", 1)[0].split("?", 1)[0]).resolve()
            self.assertTrue(target.exists(), f"资源不存在：{reference}")
            checked += 1
        self.assertGreaterEqual(checked, 3)

    def test_accessibility_hooks(self):
        """[AC-002-3] 跳转链接、地标和菜单语义必须存在。"""
        self.assertIn('class="skip-link"', self.html)
        self.assertIn('href="#main"', self.html)
        self.assertIn('id="main"', self.html)
        self.assertIn('aria-expanded="false"', self.html)
        self.assertIn('aria-controls="nav-links"', self.html)
        self.assertIn("<main", self.html)
        self.assertIn("<footer", self.html)

    def test_metadata(self):
        self.assertIn("<title>SDD Kit", self.html)
        self.assertRegex(self.html, r'<meta name="description" content="[^"]+"')
        self.assertIn('name="viewport"', self.html)

    def test_no_internal_artifacts(self):
        """站点是公开门面，不能携带内部工件信息。"""
        for forbidden in (
            "docs/specs/SPEC-",
            "SPEC-DEVTOOLS",
            "example.invalid",
            ".sdd/runtime",
            "codex",
        ):
            self.assertNotIn(forbidden, self.html)


class SiteStyleTests(unittest.TestCase):
    def setUp(self):
        self.css = read_site("styles.css")

    def test_design_tokens(self):
        self.assertIn(":root {", self.css)
        self.assertIn("--accent:", self.css)
        self.assertIn("var(--accent)", self.css)
        _, rest = self.css.split(":root {", 1)
        rest = rest.split("}", 1)[1]
        self.assertNotRegex(
            rest,
            r"#[0-9a-fA-F]{3,8}\b",
            "设计令牌之外的硬编码颜色必须收回 :root",
        )

    def test_mobile_rules(self):
        """[AC-001-3] 窄屏不能出现横向滚动。"""
        self.assertIn("overflow-x: clip", self.css)
        self.assertIn("@media (max-width: 720px)", self.css)
        self.assertNotIn("100vw", self.css)

    def test_reduced_motion(self):
        """[AC-002-4] 必须尊重系统减少动态效果设置。"""
        self.assertIn("@media (prefers-reduced-motion: reduce)", self.css)
        reduced = self.css.split("@media (prefers-reduced-motion: reduce)", 1)[1]
        self.assertIn("animation: none", reduced)
        self.assertIn("transition: none", reduced)

    def test_no_forbidden_css(self):
        self.assertNotIn("transition: all", self.css)
        self.assertNotIn("@import", self.css)
        self.assertNotRegex(self.css, r"url\(\s*[\"']?https?://")


class SiteInteractionTests(unittest.TestCase):
    def setUp(self):
        self.js = read_site("app.js")
        self.html = read_site("index.html")
        self.css = read_site("styles.css")

    def test_clipboard_feedback(self):
        """[AC-002-1] 复制必须有成功与失败反馈，并在 2 秒恢复。"""
        self.assertIn("navigator.clipboard", self.js)
        self.assertIn("execCommand", self.js)
        self.assertIn("已复制", self.js)
        self.assertIn("复制失败", self.js)
        self.assertIn("setTimeout", self.js)
        self.assertIn("2000", self.js)

    def test_no_js_content(self):
        """[AC-002-2] 正文与命令必须在 HTML 中，复制按钮默认隐藏。"""
        self.assertIn("python -m sdd resume --json", self.html)
        self.assertIn("<pre><code>", self.html)
        self.assertIn(".copy {", self.css)
        copy_block = self.css.split(".copy {", 1)[1].split("}", 1)[0]
        self.assertIn("display: none", copy_block)
        self.assertIn('classList.add("js")', self.js)

    def test_aria_hooks(self):
        """[AC-002-3] 菜单、当前区块与动效降级必须可被辅助技术感知。"""
        self.assertIn('setAttribute("aria-expanded"', self.js)
        self.assertIn("Escape", self.js)
        self.assertIn("aria-current", self.js)
        self.assertIn("prefers-reduced-motion", self.js)


class PagesWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.workflow = (KIT_ROOT / ".github" / "workflows" / "pages.yml").read_text(
            encoding="utf-8"
        )
        self.html = read_site("index.html")

    def test_uploads_site_only(self):
        """[AC-005-1] 只允许把 site/ 作为 Pages 制品。"""
        self.assertIn("actions/upload-pages-artifact@", self.workflow)
        self.assertIn("path: ./site", self.workflow)
        self.assertNotIn("path: ./docs", self.workflow)

    def test_permissions(self):
        self.assertIn("contents: read", self.workflow)
        self.assertIn("pages: write", self.workflow)
        self.assertIn("id-token: write", self.workflow)
        self.assertIn("actions/deploy-pages@", self.workflow)
        self.assertIn("name: github-pages", self.workflow)

    def test_triggers(self):
        self.assertIn("workflow_dispatch", self.workflow)
        self.assertIn("branches: [main]", self.workflow)
        self.assertIn("needs: build", self.workflow)

    def test_relative_site_assets(self):
        """[AC-005-2] 子路径部署下不能出现根路径资源。"""
        for reference in re.findall(r'(?:src|href)="([^"]+)"', self.html):
            if reference.startswith(("http://", "https://", "#", "mailto:")):
                continue
            self.assertFalse(reference.startswith("/"), reference)


class ReadmeTests(unittest.TestCase):
    def setUp(self):
        self.text = (KIT_ROOT / "README.md").read_text(encoding="utf-8")
        self.lines = self.text.splitlines()
        self.head = "\n".join(self.lines[:40])

    def test_header(self):
        """[AC-003-1] 前 40 行必须有名称、定位、徽章和两个入口。"""
        for expected in (
            "SDD Kit",
            "把 SDD 装进仓库",
            "img.shields.io",
            "actions/workflows/tests.yml",
            "0.6.1",
            "3.11",
            "docs/GUIDE.md",
        ):
            self.assertIn(expected, self.head)
        self.assertGreaterEqual(self.head.count("img.shields.io"), 3)

    def test_quickstart(self):
        """[AC-003-2] 接入、恢复、验证三条路径必须在同一节。"""
        for expected in (
            "python bootstrap.py",
            "python -m sdd resume --json",
            "python -m sdd verify-core",
            "python -m unittest discover -s tests -v",
        ):
            self.assertIn(expected, self.text)

    def test_doc_nav(self):
        """[AC-003-3] 深文档入口必须齐全。"""
        for expected in (
            "docs/GUIDE.md",
            "ARCHITECTURE.md",
            "ADOPTION.md",
            "sdd/agent-contract.md",
            "sdd/README.md",
            "sdd/mcp/README.md",
            "deploy/README.md",
        ):
            self.assertIn(expected, self.text)

    def test_license_section(self):
        """[AC-003-4] 未声明许可证时必须如实说明且不放许可证徽章。"""
        self.assertIn("许可证", self.text)
        self.assertIn("未声明", self.text)
        self.assertNotIn("MIT License", self.text)
        self.assertNotIn("Apache-2.0", self.text)
        self.assertNotIn("license-MIT", self.text)

    def test_readme_is_a_front_page(self):
        self.assertLess(len(self.lines), 260)


class GuideTests(unittest.TestCase):
    def setUp(self):
        self.guide = (KIT_ROOT / "docs" / "GUIDE.md").read_text(encoding="utf-8")

    def test_all_sections(self):
        """[AC-004-1] 原 README 的 16 个一级章节必须全部保留。"""
        for section in (
            "三条硬约束",
            "先回答几个关键问题",
            "完整链路架构图",
            "人到底要做哪几步",
            "快速接入（平台团队）",
            "一次需求的 CLI 全链路",
            "托管块与冲突规则",
            "两种开发模式",
            "多微服务与历史知识没沉淀",
            "核心保护与版本管理",
            "CI 做什么",
            "与 AIDLC / Trellis / Matt skills 的关系",
            "目录结构",
            "常见问题",
            "自测",
            "边界",
        ):
            self.assertIn(section, self.guide)
        self.assertGreaterEqual(self.guide.count("\n## "), 16)

    def test_commands_preserved(self):
        """[AC-004-2] 迁移只动标题，不改命令文本。"""
        for command in (
            "python bootstrap.py --target",
            "python -m sdd resume --json",
            "python -m sdd submit --spec",
            "python -m sdd approve --spec",
            "python -m sdd merge --spec",
            "python -m sdd check --all --stage ci --check-git",
        ):
            self.assertIn(command, self.guide)


class LinkTests(unittest.TestCase):
    def test_relative_links(self):
        """[AC-004-3] README 与 GUIDE 的相对链接必须真实存在。"""
        checked = 0
        for name in ("README.md", "docs/GUIDE.md"):
            path = KIT_ROOT / name
            text = path.read_text(encoding="utf-8")
            targets = re.findall(r"\]\(([^)\s]+)\)", text)
            targets += re.findall(r'(?:src|href)="([^"]+)"', text)
            for target in targets:
                if target.startswith(("http://", "https://", "#", "mailto:", "data:")):
                    continue
                local = target.split("#", 1)[0].split("?", 1)[0]
                if not local:
                    continue
                resolved = (path.parent / local).resolve()
                self.assertTrue(resolved.exists(), f"{name} 链接失效：{target}")
                checked += 1
        self.assertGreaterEqual(checked, 10)


class AboutTests(unittest.TestCase):
    def setUp(self):
        self.text = (KIT_ROOT / "docs" / "GITHUB-ABOUT.md").read_text(
            encoding="utf-8"
        )
        remote_url = subprocess.run(
            ["git", "-C", str(KIT_ROOT), "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        remote = re.search(r"github\.com[:/]([^/]+)/([^/\s.]+)", remote_url)
        self.assertIsNotNone(remote, "无法从 .git/config 解析 GitHub 远端")
        owner, repo = remote.group(1), remote.group(2)
        self.pages_url = f"https://{owner.lower()}.github.io/{repo}/"

    def test_about_material(self):
        """[AC-005-3] Description、Topics、Homepage 三项素材齐全。"""
        for heading in ("Description", "Topics", "Homepage"):
            self.assertIn(heading, self.text)
        self.assertIn("SDD-L2", self.text)
        for topic in (
            "spec-driven-development",
            "ai-agents",
            "developer-tools",
            "mcp",
            "agents-md",
        ):
            self.assertIn(topic, self.text)

    def test_homepage_matches_pages(self):
        """[AC-005-4] 文档中的 Homepage 必须等于该仓库的默认 Pages 地址。"""
        self.assertIn(self.pages_url, self.text)


if __name__ == "__main__":
    unittest.main()
