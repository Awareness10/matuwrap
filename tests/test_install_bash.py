"""`wrp install bash`: script install and .bashrc patching, in a temp HOME."""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from matuwrap.commands import install

ALREADY = ".bashrc already sources matuwrap"


class TestInstallBash(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        home = Path(self._tmp.name)
        self.script_dir = home / ".config" / "matuwrap" / "scripts"
        self.script = self.script_dir / "matuwrap"
        self.bashrc = home / ".bashrc"
        self.source_line = f"source {self.script}"

        patches = {
            "SCRIPT_DIR": self.script_dir,
            "SCRIPT_PATH": self.script,
            "BASHRC": self.bashrc,
            "SOURCE_LINE": self.source_line,
            "console": mock.MagicMock(),
            "print_success": mock.MagicMock(),
            "print_warning": mock.MagicMock(),
        }
        for name, value in patches.items():
            patcher = mock.patch.object(install, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def tearDown(self):
        self._tmp.cleanup()

    def _messages(self) -> str:
        calls = (
            install.console.print.call_args_list
            + install.print_success.call_args_list
            + install.print_warning.call_args_list
        )
        return "\n".join(str(c.args[0]) for c in calls if c.args)

    def _backups(self) -> list[Path]:
        return list(self.bashrc.parent.glob(".bashrc.*.bak"))

    def test_installs_script(self):
        self.bashrc.write_text("")
        self.assertEqual(install.run("bash"), 0)
        self.assertEqual(self.script.read_text(), install.BASH_INTEGRATION.lstrip("\n"))

    def test_missing_bashrc_is_created(self):
        self.assertEqual(install.run("bash"), 0)
        self.assertEqual(
            self.bashrc.read_text(),
            f"# matuwrap shell integration\n{self.source_line}\n",
        )
        self.assertIn(f"Created    {self.bashrc}", self._messages())
        self.assertNotIn(ALREADY, self._messages())
        self.assertEqual(self._backups(), [])

    def test_existing_without_source_line_is_patched(self):
        original = 'export PATH="$HOME/.local/bin:$PATH"\nalias ll="ls -l"\n'
        self.bashrc.write_text(original)
        self.assertEqual(install.run("bash"), 0)

        lines = self.bashrc.read_text().splitlines()
        self.assertEqual(lines.count(self.source_line), 1)
        # Sourced after the PATH export so `wrp` is found
        self.assertGreater(lines.index(self.source_line), 0)
        self.assertEqual(lines[lines.index(self.source_line) - 1], "# matuwrap shell integration")
        self.assertIn('alias ll="ls -l"', lines)
        self.assertIn(f"Patched    {self.bashrc}", self._messages())
        self.assertNotIn(ALREADY, self._messages())
        backups = self._backups()
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(), original)

    def test_existing_with_source_line_is_unchanged(self):
        original = (
            'export PATH="$HOME/.local/bin:$PATH"\n'
            f"\n# matuwrap shell integration\n{self.source_line}\n"
        )
        self.bashrc.write_text(original)
        self.assertEqual(install.run("bash"), 0)
        self.assertEqual(self.bashrc.read_text(), original)
        self.assertIn(ALREADY, self._messages())
        self.assertNotIn("Patched", self._messages())
        self.assertEqual(self._backups(), [])

    def test_existing_ending_with_source_line_no_path_is_unchanged(self):
        original = f'alias ll="ls -l"\n\n# matuwrap shell integration\n{self.source_line}\n'
        self.bashrc.write_text(original)
        install.run("bash")
        self.assertEqual(self.bashrc.read_text(), original)
        self.assertIn(ALREADY, self._messages())

    def test_source_line_before_path_export_is_moved(self):
        self.bashrc.write_text(
            f"# matuwrap shell integration\n{self.source_line}\n"
            'export PATH="$HOME/.local/bin:$PATH"\n'
        )
        install.run("bash")
        lines = self.bashrc.read_text().splitlines()
        self.assertEqual(lines.count(self.source_line), 1)
        self.assertGreater(
            lines.index(self.source_line),
            lines.index('export PATH="$HOME/.local/bin:$PATH"'),
        )
        self.assertIn(f"Patched    {self.bashrc}", self._messages())

    def test_second_run_after_create_is_unchanged(self):
        install.run("bash")
        created = self.bashrc.read_text()
        install.print_success.reset_mock()
        install.console.reset_mock()

        install.run("bash")
        self.assertEqual(self.bashrc.read_text(), created)
        self.assertIn(ALREADY, self._messages())

    def test_unknown_target(self):
        with mock.patch.object(install, "print_error") as print_error:
            self.assertEqual(install.run("zsh"), 1)
        print_error.assert_called_once()
        self.assertFalse(self.bashrc.exists())


if __name__ == "__main__":
    unittest.main()
