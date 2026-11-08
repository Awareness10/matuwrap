"""Freshness check of the bash integration script written by `wrp install`."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from matuwrap.commands.install import BASH_INTEGRATION

# Only the cache helpers; the rest of the script runs wrp and fastfetch
HELPERS = BASH_INTEGRATION.split("# On shell startup")[0]

# The fastfetch section: FF_DEFS is just the functions, FASTFETCH adds the
# startup `ff` call
FASTFETCH = BASH_INTEGRATION[BASH_INTEGRATION.index("# --- Fastfetch"):]
FF_DEFS = FASTFETCH.split("# Run fastfetch on shell startup")[0]

COLOR = "#abcdef"
ARCH_ARGS = [
    "--color", COLOR,
    "--logo", "arch",
    "--logo-color-1", COLOR,
    "--logo-color-2", COLOR,
]


def _text_args(path: str) -> list[str]:
    return [
        "--color", COLOR,
        "--logo", path,
        "--logo-type", "file",
        "--logo-color-1", COLOR,
        "--logo-padding-top", "1",
    ]


def _image_args(path: str, width: str = "30", height: str = "20") -> list[str]:
    return [
        "--color", COLOR,
        "--logo", path,
        "--logo-type", "kitty-direct",
        "--logo-width", width,
        "--logo-height", height,
    ]


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


class TestFastfetch(unittest.TestCase):
    """Run the fastfetch section with a stub `fastfetch` that records its args."""

    HINT = "set MW_FF_IMAGE"

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.home = Path(self._tmp.name)
        self.bin = self.home / "bin"
        self.bin.mkdir()
        self.args_file = self.home / "fastfetch-args"
        stub = self.bin / "fastfetch"
        stub.write_text(f'#!/bin/sh\nprintf "%s\\n" "$@" > "{self.args_file}"\n')
        stub.chmod(0o755)
        self.logo = self.home / "logo.txt"
        self.logo.write_text("logo")
        self.image = self.home / "logo.png"
        self.image.write_bytes(b"png")
        self.state = self.home / ".local" / "state" / "matuwrap" / "ff-logo"
        self.stderr = ""
        self.stdout = ""

    def tearDown(self):
        self._tmp.cleanup()

    def _run(
        self,
        command: str = "ff",
        script: str | None = None,
        with_fastfetch: bool = True,
        **env_vars: str,
    ) -> list[str] | None:
        """Run `command` after the ff definitions; return fastfetch's args."""
        path = f"{self.bin}:/usr/bin:/bin" if with_fastfetch else "/nonexistent"
        env = {"HOME": str(self.home), "PATH": path, "AW_COLOR": COLOR, "TERM": "xterm-256color"}
        env.update(env_vars)
        if script is None:
            script = FF_DEFS + "\n" + command
        result = subprocess.run(
            ["/bin/bash", "-c", script], env=env, capture_output=True, text=True
        )
        self.stdout, self.stderr = result.stdout, result.stderr
        # Without fastfetch the trailing `command -v fastfetch && ff` exits 1
        if with_fastfetch:
            self.assertEqual(result.returncode, 0, result.stderr)
        if not self.args_file.exists():
            return None
        return self.args_file.read_text().splitlines()

    def _kitty(self, command: str = "ff image", **env_vars: str) -> list[str] | None:
        env = {"TERM": "xterm-kitty", "MW_FF_IMAGE": str(self.image)}
        env.update(env_vars)
        return self._run(command, **env)

    # --- Startup ---------------------------------------------------------

    def test_startup_runs_ff(self):
        self.assertEqual(self._run(script=FASTFETCH), ARCH_ARGS)
        self.assertEqual(self.stderr, "")

    def test_startup_uses_saved_image_mode_quietly(self):
        self.state.parent.mkdir(parents=True)
        self.state.write_text("image\n")
        self.assertEqual(self._run(script=FASTFETCH, TERM="xterm-kitty"), ARCH_ARGS)
        self.assertEqual(self.stderr, "")

    def test_startup_skipped_without_fastfetch(self):
        self.assertIsNone(self._run(script=FASTFETCH, with_fastfetch=False))
        self.assertEqual(self.stderr, "")

    # --- Text mode -------------------------------------------------------

    def test_text_arch_logo_when_unset(self):
        self.assertEqual(self._run(), ARCH_ARGS)

    def test_text_arch_logo_when_empty(self):
        self.assertEqual(self._run(MW_FF_LOGO=""), ARCH_ARGS)

    def test_text_logo_when_set(self):
        self.assertEqual(self._run(MW_FF_LOGO=str(self.logo)), _text_args(str(self.logo)))

    def test_text_logo_path_with_spaces(self):
        logo = self.home / "my logo.txt"
        logo.write_text("logo")
        self.assertEqual(self._run(MW_FF_LOGO=str(logo)), _text_args(str(logo)))

    def test_text_arch_logo_when_file_missing(self):
        self.assertEqual(self._run(MW_FF_LOGO=str(self.home / "missing.txt")), ARCH_ARGS)

    def test_text_literal_tilde_is_expanded(self):
        self.assertEqual(self._run(MW_FF_LOGO="~/logo.txt"), _text_args(str(self.logo)))

    def test_text_literal_tilde_missing_file(self):
        self.assertEqual(self._run(MW_FF_LOGO="~/missing.txt"), ARCH_ARGS)

    def test_text_and_ascii_args(self):
        for arg in ("text", "ascii"):
            with self.subTest(arg=arg):
                self.assertEqual(
                    self._kitty(f"ff {arg}", MW_FF_LOGO=str(self.logo)),
                    _text_args(str(self.logo)),
                )

    def test_unknown_arg(self):
        result = subprocess.run(
            ["/bin/bash", "-c", FF_DEFS + "\nff bogus"],
            env={"HOME": str(self.home), "PATH": f"{self.bin}:/usr/bin:/bin"},
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("usage: ff", result.stderr)
        self.assertFalse(self.args_file.exists())

    # --- Image mode ------------------------------------------------------

    def test_image_in_kitty(self):
        self.assertEqual(self._kitty(), _image_args(str(self.image)))
        self.assertEqual(self.stderr, "")

    def test_image_custom_size(self):
        self.assertEqual(
            self._kitty(MW_FF_IMAGE_WIDTH="40", MW_FF_IMAGE_HEIGHT="18"),
            _image_args(str(self.image), "40", "18"),
        )

    def test_image_literal_tilde_is_expanded(self):
        self.assertEqual(self._kitty(MW_FF_IMAGE="~/logo.png"), _image_args(str(self.image)))

    def test_image_in_supported_terminals(self):
        for term in ({"TERM": "xterm-ghostty"},
                     {"TERM": "xterm-256color", "TERM_PROGRAM": "WezTerm"}):
            with self.subTest(**term):
                self.assertEqual(self._kitty(**term), _image_args(str(self.image)))

    def test_image_falls_back_over_ssh(self):
        for var in ("SSH_TTY", "SSH_CONNECTION"):
            with self.subTest(var=var):
                args = self._kitty(MW_FF_LOGO=str(self.logo), **{var: "x"})
                self.assertEqual(args, _text_args(str(self.logo)))
                self.assertEqual(self.stderr, "")

    def test_image_falls_back_in_other_terminal(self):
        for term in ("xterm-256color", "tmux-256color", "linux"):
            with self.subTest(term=term):
                self.assertEqual(self._kitty(TERM=term), ARCH_ARGS)
                self.assertEqual(self.stderr, "")

    def test_image_without_mw_ff_image_hints(self):
        self.assertEqual(self._kitty(MW_FF_IMAGE=""), ARCH_ARGS)
        self.assertIn(self.HINT, self.stderr)

    def test_image_missing_file_hints(self):
        args = self._kitty(MW_FF_IMAGE="~/missing.png", MW_FF_LOGO=str(self.logo))
        self.assertEqual(args, _text_args(str(self.logo)))
        self.assertIn(self.HINT, self.stderr)

    # --- Saved mode and ff-toggle -----------------------------------------

    def test_saved_image_mode(self):
        self.state.parent.mkdir(parents=True)
        self.state.write_text("image\n")
        self.assertEqual(self._kitty("ff"), _image_args(str(self.image)))

    def test_saved_legacy_ascii_mode(self):
        self.state.parent.mkdir(parents=True)
        self.state.write_text("ascii\n")
        self.assertEqual(self._kitty("ff", MW_FF_LOGO=str(self.logo)), _text_args(str(self.logo)))

    def test_toggle_creates_state_and_flips(self):
        self.assertEqual(self._kitty("ff-toggle"), _image_args(str(self.image)))
        self.assertEqual(self.state.read_text(), "image\n")
        self.assertIn("ff logo: image", self.stdout)

        self.assertEqual(self._kitty("ff-toggle"), ARCH_ARGS)
        self.assertEqual(self.state.read_text(), "text\n")
        self.assertIn("ff logo: text", self.stdout)

        self.assertEqual(self._kitty("ff-toggle"), _image_args(str(self.image)))
        self.assertEqual(self.state.read_text(), "image\n")

    def test_toggle_from_legacy_ascii(self):
        self.state.parent.mkdir(parents=True)
        self.state.write_text("ascii\n")
        self.assertEqual(self._kitty("ff-toggle"), _image_args(str(self.image)))
        self.assertEqual(self.state.read_text(), "image\n")

    def test_toggle_respects_xdg_state_home(self):
        state_home = self.home / "state"
        self._kitty("ff-toggle", XDG_STATE_HOME=str(state_home))
        self.assertEqual((state_home / "matuwrap" / "ff-logo").read_text(), "image\n")
        self.assertFalse(self.state.exists())

    def test_toggle_to_image_without_mw_ff_image_hints(self):
        self.assertEqual(self._kitty("ff-toggle", MW_FF_IMAGE=""), ARCH_ARGS)
        self.assertEqual(self.state.read_text(), "image\n")
        self.assertIn(self.HINT, self.stderr)

    def test_no_personal_paths(self):
        for personal in ("akatsuki", "Pictures/kitty"):
            self.assertNotIn(personal, BASH_INTEGRATION)


if __name__ == "__main__":
    unittest.main()


# The PS1 section (git-prompt and venv helpers aren't needed to build it)
PROMPT = BASH_INTEGRATION[BASH_INTEGRATION.index("# --- PS1"):BASH_INTEGRATION.index("# --- Fastfetch")]
WRP_PS1 = r"\[\033[38;2;1;2;3m\]\u"


class TestPrompt(unittest.TestCase):
    """The colored prompt is set in every terminal that shows 24-bit color."""

    def _ps1(self, **env) -> str:
        result = subprocess.run(
            # PS1 set in the script: bash drops it from a non-interactive shell's environment
            ["bash", "--norc", "-c", "PS1=default\n" + PROMPT + '\nprintf "%s" "$PS1"'],
            env={"PATH": os.environ["PATH"], "WRP_PS1": WRP_PS1, **env},
            capture_output=True, text=True, check=True,
        )
        return result.stdout

    def test_colored_in_color_terminals(self):
        for env in ({"TERM": "xterm-256color"}, {"TERM": "xterm-kitty"},
                    {"TERM": "foot"}, {"TERM": "foot-extra"}, {"TERM": "alacritty"},
                    {"TERM": "xterm-ghostty"}, {"TERM": "unknown", "COLORTERM": "truecolor"}):
            with self.subTest(**env):
                self.assertIn(WRP_PS1, self._ps1(**env))

    def test_window_title_in_graphical_terminals(self):
        for term in ("xterm-256color", "foot", "alacritty"):
            with self.subTest(term=term):
                self.assertTrue(self._ps1(TERM=term).startswith(r"\[\e]0;"))

    def test_default_prompt_in_plain_terminals(self):
        for term in ("linux", "dumb"):
            with self.subTest(term=term):
                self.assertEqual(self._ps1(TERM=term), "default")
