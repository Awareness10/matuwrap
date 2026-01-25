#!/usr/bin/env python3
"""Performance tests for native vs subprocess implementations.

Run with: pytest tests/test_performance.py -v
Or standalone: python tests/test_performance.py
"""

import json
import os
import subprocess
import time
import unittest
from pathlib import Path
from typing import Callable
from unittest import skipIf

# Check environment conditions
def _check_hyprland() -> bool:
    """Check if running in a Hyprland session with socket available."""
    his = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE")
    if not his:
        return False
    xdg = os.environ.get("XDG_RUNTIME_DIR", "")
    paths = [
        f"{xdg}/hypr/{his}/.socket.sock",
        f"/tmp/hypr/{his}/.socket.sock",
    ]
    return any(os.path.exists(p) for p in paths)


IN_HYPRLAND = _check_hyprland()
WALLPAPER_PATH = Path.home() / ".current.wall"
HAS_WALLPAPER = WALLPAPER_PATH.exists()


def benchmark(func: Callable, iterations: int = 50, warmup: int = 5) -> float:
    """Run benchmark and return average time in milliseconds."""
    for _ in range(warmup):
        func()

    start = time.perf_counter()
    for _ in range(iterations):
        func()
    elapsed = time.perf_counter() - start

    return (elapsed / iterations) * 1000


class PerformanceResult:
    """Container for performance comparison results."""

    def __init__(self, name: str, native_ms: float, baseline_ms: float):
        self.name = name
        self.native_ms = native_ms
        self.baseline_ms = baseline_ms
        self.speedup = baseline_ms / native_ms if native_ms > 0 else 0

    def __str__(self) -> str:
        return (
            f"{self.name:35} "
            f"native: {self.native_ms:8.3f}ms  "
            f"baseline: {self.baseline_ms:8.3f}ms  "
            f"speedup: {self.speedup:>7.1f}x"
        )


class TestColorCachePerformance(unittest.TestCase):
    """Performance tests for matugen color caching."""

    @skipIf(not HAS_WALLPAPER, f"Wallpaper not found at {WALLPAPER_PATH}")
    def test_cached_colors_faster_than_cold(self):
        """Cached color loading should be much faster than cold start."""
        from matuwrap.wrp_native import get_cached_colors, invalidate_color_cache

        wallpaper = str(WALLPAPER_PATH)

        # Measure cold start (single run - it's slow)
        invalidate_color_cache()
        start = time.perf_counter()
        get_cached_colors(wallpaper)
        cold_ms = (time.perf_counter() - start) * 1000

        # Measure cached access
        cached_ms = benchmark(lambda: get_cached_colors(wallpaper))

        speedup = cold_ms / cached_ms

        # Cache should be at least 100x faster than running matugen
        self.assertGreater(speedup, 100, "Cache should be at least 100x faster")

    @skipIf(not HAS_WALLPAPER, f"Wallpaper not found at {WALLPAPER_PATH}")
    def test_cache_invalidation_performance(self):
        """Cache invalidation should be very fast."""
        from matuwrap.wrp_native import invalidate_color_cache

        invalidation_ms = benchmark(invalidate_color_cache, iterations=100)

        # Invalidation should be under 1ms
        self.assertLess(invalidation_ms, 1.0, "Cache invalidation should be under 1ms")


class TestAudioSinkPerformance(unittest.TestCase):
    """Performance tests for PipeWire audio sink enumeration."""

    def test_native_sinks_vs_subprocess(self):
        """Native sink enumeration should be faster than subprocess."""
        from matuwrap.wrp_native import get_audio_sinks

        def native_sinks():
            return get_audio_sinks()

        def subprocess_sinks():
            result = subprocess.run(["wpctl", "status"], capture_output=True, text=True)
            return result.stdout

        native_ms = benchmark(native_sinks)
        baseline_ms = benchmark(subprocess_sinks)

        # Native should be faster (or at least comparable)
        # Note: both use subprocess internally, but native has optimized parsing
        self.assertLess(native_ms, baseline_ms * 2, "Native should not be more than 2x slower")

    def test_audio_sink_parsing_consistency(self):
        """Audio sink parsing should return consistent results."""
        from matuwrap.wrp_native import get_audio_sinks

        results = [len(get_audio_sinks()) for _ in range(10)]
        self.assertEqual(len(set(results)), 1, "Sink count should be consistent")


class TestHyprlandIPCPerformance(unittest.TestCase):
    """Performance tests for Hyprland IPC."""

    @skipIf(not IN_HYPRLAND, "Not in Hyprland session")
    def test_native_socket_vs_subprocess(self):
        """Native socket IPC should be faster than subprocess hyprctl."""
        from matuwrap.wrp_native import hyprctl_json

        def native_monitors():
            return json.loads(hyprctl_json("monitors"))

        def subprocess_monitors():
            result = subprocess.run(
                ["hyprctl", "-j", "monitors"], capture_output=True, text=True
            )
            return json.loads(result.stdout)

        native_ms = benchmark(native_monitors)
        baseline_ms = benchmark(subprocess_monitors)

        result = PerformanceResult("hyprctl -j monitors", native_ms, baseline_ms)

        # Native socket should be at least 5x faster
        self.assertGreater(result.speedup, 5, "Native socket should be at least 5x faster")

    @skipIf(not IN_HYPRLAND, "Not in Hyprland session")
    def test_native_multiple_commands(self):
        """Multiple rapid IPC calls should maintain performance."""
        from matuwrap.wrp_native import hyprctl_json

        commands = ["monitors", "workspaces", "clients", "activewindow"]

        def run_all_commands():
            for cmd in commands:
                hyprctl_json(cmd)

        ms = benchmark(run_all_commands, iterations=20)
        per_command = ms / len(commands)
        # Each command should average under 5ms
        self.assertLess(per_command, 5, "Each command should average under 5ms")

    @skipIf(not IN_HYPRLAND, "Not in Hyprland session")
    def test_json_parsing_overhead(self):
        """JSON parsing overhead should be minimal."""
        from matuwrap.wrp_native import hyprctl, hyprctl_json

        def raw_command():
            return hyprctl("monitors")

        def json_command():
            return hyprctl_json("monitors")

        raw_ms = benchmark(raw_command)
        json_ms = benchmark(json_command)

        overhead = json_ms - raw_ms

        # JSON overhead should be under 1ms
        self.assertLess(abs(overhead), 1.0, "JSON overhead should be under 1ms")


class TestSystemInfoPerformance(unittest.TestCase):
    """Performance tests for system information queries."""

    def test_memory_info_performance(self):
        """Memory info should be fast."""
        from matuwrap.wrp_native import memory_info

        ms = benchmark(memory_info, iterations=100)

        # Memory info should be under 20ms (sysinfo crate refreshes system state)
        self.assertLess(ms, 20, "Memory info should be under 20ms")

    def test_cpu_usage_performance(self):
        """CPU usage has inherent delay but should be reasonable."""
        from matuwrap.wrp_native import cpu_usage

        # CPU usage requires a 100ms sleep internally for sampling
        start = time.perf_counter()
        cpu_usage()
        ms = (time.perf_counter() - start) * 1000

        # Should be around 100-150ms due to internal sampling delay
        self.assertGreater(ms, 90, "CPU usage should include sampling delay")
        self.assertLess(ms, 200, "CPU usage should not exceed 200ms")


class TestCommandDiscoveryPerformance(unittest.TestCase):
    """Performance tests for CLI command discovery."""

    def test_command_import_performance(self):
        """Command module imports should be fast."""
        import importlib
        import pkgutil

        from matuwrap import commands

        def discover_commands():
            """Mimics the CLI's command discovery."""
            discovered = {}
            for module_info in pkgutil.iter_modules(commands.__path__):
                if module_info.name.startswith("_"):
                    continue
                module = importlib.import_module(f"matuwrap.commands.{module_info.name}")
                if hasattr(module, "COMMAND"):
                    discovered[module_info.name] = module.COMMAND
            return discovered

        # First discovery (modules may be cached from other tests)
        start = time.perf_counter()
        discover_commands()
        first_ms = (time.perf_counter() - start) * 1000

        # Discovery should be under 100ms
        self.assertLess(first_ms, 100, "Command discovery should be under 100ms")

    def test_cli_help_performance(self):
        """CLI help generation should be fast."""

        def run_help():
            result = subprocess.run(
                [".venv/bin/wrp", "--help"],
                capture_output=True,
                cwd=Path(__file__).parent.parent,
            )
            return result.stdout

        ms = benchmark(run_help, iterations=10)

        # Help should be under 200ms
        self.assertLess(ms, 200, "CLI help should be under 200ms")


class TestThemePerformance(unittest.TestCase):
    """Performance tests for theme/colors module."""

    def test_theme_initialization(self):
        """Theme initialization should be fast."""
        import sys

        # Clear theme module to test fresh import
        modules_to_clear = [k for k in sys.modules if "theme" in k.lower()]
        for mod in modules_to_clear:
            if mod in sys.modules:
                del sys.modules[mod]

        start = time.perf_counter()
        from matuwrap.core.theme import THEME, console  # noqa: F401
        cold_ms = (time.perf_counter() - start) * 1000


        # Theme init should be under 50ms
        self.assertLess(cold_ms, 50, "Theme initialization should be under 50ms")

    def test_fmt_function_performance(self):
        """fmt() function should be fast for various types."""
        from matuwrap.core.theme import fmt

        test_values = [
            True, False, 42, 3.14, "hello", "enabled", "disabled",
            "on", "off", 0, -5, 999999, 0.000001,
        ]

        def format_all():
            for v in test_values:
                fmt(v)

        ms = benchmark(format_all, iterations=1000)
        per_call = ms / len(test_values)


        # Each fmt call should be under 0.1ms
        self.assertLess(per_call, 0.1, "fmt() should be under 0.1ms per call")

    def test_create_table_performance(self):
        """Table creation should be fast."""
        from matuwrap.core.theme import create_table

        def create_tables():
            for _ in range(10):
                table = create_table("Name", "Value", "Status", title="Test")  # noqa: F841

        ms = benchmark(create_tables, iterations=100)
        per_table = ms / 10

        # Each table creation should be under 1ms
        self.assertLess(per_table, 1, "Table creation should be under 1ms")


class TestEndToEndPerformance(unittest.TestCase):
    """End-to-end performance tests for full commands."""

    def test_audio_show_command(self):
        """Full 'wrp audio show' command performance."""
        cwd = Path(__file__).parent.parent

        def run_audio_show():
            subprocess.run(
                [".venv/bin/wrp", "audio", "show"],
                capture_output=True,
                cwd=cwd,
            )

        ms = benchmark(run_audio_show, iterations=10)

        # Full command should be under 500ms
        self.assertLess(ms, 500, "Full audio show command should be under 500ms")

    @skipIf(not IN_HYPRLAND, "Not in Hyprland session")
    def test_monitors_show_command(self):
        """Full 'wrp monitors show' command performance."""
        cwd = Path(__file__).parent.parent

        def run_monitors_show():
            subprocess.run(
                [".venv/bin/wrp", "monitors", "show"],
                capture_output=True,
                cwd=cwd,
            )

        ms = benchmark(run_monitors_show, iterations=10)

        # Full command should be under 500ms
        self.assertLess(ms, 500, "Full monitors show command should be under 500ms")


class TestRunCommandPerformance(unittest.TestCase):
    """Performance tests for the run_command native function."""

    def test_run_command_vs_subprocess(self):
        """Native run_command should have minimal overhead."""
        from matuwrap.wrp_native import run_command

        def native_echo():
            return run_command("echo", ["hello"])

        def subprocess_echo():
            result = subprocess.run(["echo", "hello"], capture_output=True, text=True)
            return result.stdout

        native_ms = benchmark(native_echo)
        baseline_ms = benchmark(subprocess_echo)

        # Native should be comparable to subprocess (within 2x)
        self.assertLess(native_ms, baseline_ms * 2, "Native should be within 2x of subprocess")


def print_summary():
    """Print a summary header."""
    print("=" * 90)
    print("Performance Tests: Native vs Baseline Implementations")
    print("=" * 90)


if __name__ == "__main__":
    print_summary()
    unittest.main(verbosity=2)
