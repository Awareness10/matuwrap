"""Color cache must follow the wallpaper symlink's target, not just its mtime."""

import os
import shutil
import struct
import tempfile
import unittest
import zlib
from pathlib import Path


def _solid_png(path: Path, rgb: tuple[int, int, int], size: int = 16) -> None:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    row = b"\x00" + bytes(rgb) * size
    ihdr = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(row * size)) + chunk(b"IEND", b"")
    )


@unittest.skipIf(shutil.which("matugen") is None, "matugen not installed")
class TestColorCacheKey(unittest.TestCase):
    # Isolate the cache and matugen's config: a real (non-dry-run) matugen run
    # would otherwise apply the user's templates and set their wallpaper
    ISOLATED_ENV = ("XDG_CACHE_HOME", "XDG_CONFIG_HOME", "HOME")

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self._old_env = {k: os.environ.get(k) for k in self.ISOLATED_ENV}
        for key in self.ISOLATED_ENV:
            os.environ[key] = str(self.tmp / key.lower())

    def tearDown(self):
        for key, value in self._old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        shutil.rmtree(self.tmp)

    def test_repointed_symlink_with_same_mtime_invalidates_cache(self):
        """Regression: two wallpapers copied in the same second share an mtime,
        so switching between them kept serving the first one's colors."""
        from matuwrap.wrp_native import get_cached_colors

        red, blue = self.tmp / "red.png", self.tmp / "blue.png"
        _solid_png(red, (200, 30, 30))
        _solid_png(blue, (30, 60, 200))
        for img in (red, blue):
            os.utime(img, ns=(1_770_748_105_000_000_000, 1_770_748_105_000_000_000))

        wall = self.tmp / ".current.wall"
        wall.symlink_to(red)
        red_colors = get_cached_colors(str(wall))

        wall.unlink()
        wall.symlink_to(blue)
        blue_colors = get_cached_colors(str(wall))

        self.assertTrue(red_colors and blue_colors)
        self.assertNotEqual(red_colors["primary"], blue_colors["primary"])


if __name__ == "__main__":
    unittest.main()
