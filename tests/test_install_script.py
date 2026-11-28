import unittest
from pathlib import Path


KIT_ROOT = Path(__file__).resolve().parents[1]


class InstallScriptTest(unittest.TestCase):
    def test_irm_installer_supports_release_and_local_source(self):
        text = (KIT_ROOT / "install.ps1").read_text(encoding="utf-8")
        for expected in (
            "[CmdletBinding()]",
            "[string]$Repo",
            "[string]$Ref = \"latest\"",
            "[string]$SourcePath",
            "[switch]$NoPath",
            "[switch]$Force",
            "sdd/scripts/sdd.py",
            "releases/latest/download/sdd-kit.zip",
            "archive/refs/heads/main.zip",
            "SetEnvironmentVariable(\"Path\"",
            "Refusing to install to a drive root",
            "must not contain each other",
            "sdd init",
        ):
            self.assertIn(expected, text)

    def test_windows_command_shim_uses_kit_pythonpath(self):
        text = (KIT_ROOT / "bin" / "sdd.cmd").read_text(encoding="utf-8")
        self.assertIn("PYTHONPATH", text)
        self.assertIn("python -m sdd", text)
        self.assertIn("py -3 -m sdd", text)
        ps1 = (KIT_ROOT / "bin" / "sdd.ps1").read_text(encoding="utf-8")
        self.assertIn("py -3 -m sdd", ps1)

    def test_release_workflow_publishes_installer_and_bundle(self):
        text = (KIT_ROOT / ".github" / "workflows" / "release.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("tags:", text)
        self.assertIn("git archive", text)
        self.assertIn("dist/sdd-kit.zip", text)
        self.assertIn("dist/install.ps1", text)
        self.assertIn("gh release create", text)

    def test_readme_documents_one_line_install(self):
        text = (KIT_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("irm ", text)
        self.assertIn("install.ps1", text)


if __name__ == "__main__":
    unittest.main()
