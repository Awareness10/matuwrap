"""Freshness check of the bash integration script written by `wrp install`."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from matuwrap.commands.install import BASH_INTEGRATION

# Only the cache helpers; the rest of the script runs wrp and fastfetch
HELPERS = BASH_INTEGRATION.split("# On shell startup")[0]


class TestCacheFreshness(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.home = Path(self._tmp.name)
        self.cache = self.home / ".cache" / "matuwrap" / "ps1"
        self.aw_colors = self.home / ".config" / "aw-shell" / "config" / "colors.json"
        self.cache.parent.mkdir(parents=True)
        (self.home / "wall.png").write_bytes(b"")
        (self.home / ".current.wall").symlink_to(self.home / "wall.png")
        self.cache.write_text("ps1")
        self._stamp(self.home / ".current.wall", 100)
        self._stamp(self.cache, 200)

    def tearDown(self):
        self._tmp.cleanup()

    def _stamp(self, path: Path, mtime: int) -> None:
        os.utime(path, (mtime, mtime), follow_symlinks=False)

    def _fresh(self) -> bool:
        env = {"HOME": str(self.home), "PATH": os.environ["PATH"]}
        result = subprocess.run(["bash", "-c", HELPERS + "\n_mw_cache_fresh"], env=env)
        return result.returncode == 0

    def test_fresh_without_aw_shell(self):
        self.assertTrue(self._fresh())

    def test_stale_after_wallpaper_change(self):
        self._stamp(self.home / ".current.wall", 300)
        self.assertFalse(self._fresh())

    def test_stale_after_aw_shell_palette_change(self):
        self.aw_colors.parent.mkdir(parents=True)
        self.aw_colors.write_text("{}")
        self._stamp(self.aw_colors, 300)
        self.assertFalse(self._fresh())

    def test_fresh_when_aw_shell_palette_is_older(self):
        self.aw_colors.parent.mkdir(parents=True)
        self.aw_colors.write_text("{}")
        self._stamp(self.aw_colors, 150)
        self.assertTrue(self._fresh())


if __name__ == "__main__":
    unittest.main()
