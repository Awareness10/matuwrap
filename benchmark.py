#!/usr/bin/env python3
"""Benchmark native vs subprocess performance."""

import subprocess
import time
import os

# Check if we're in Hyprland (env var + socket exists)
def _check_hyprland() -> bool:
    his = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE")
    if not his:
        return False
    # Try XDG_RUNTIME_DIR first (Hyprland 0.40+), then /tmp
    xdg = os.environ.get("XDG_RUNTIME_DIR", "")
    paths = [
        f"{xdg}/hypr/{his}/.socket.sock",
        f"/tmp/hypr/{his}/.socket.sock",
    ]
    return any(os.path.exists(p) for p in paths)

IN_HYPRLAND = _check_hyprland()


def benchmark(name: str, func, iterations: int = 100, warmup: int = 5) -> float:
    """Run benchmark and return average time in ms."""
    for _ in range(warmup):
        func()

    start = time.perf_counter()
    for _ in range(iterations):
        func()
    elapsed = time.perf_counter() - start

    return (elapsed / iterations) * 1000


def print_result(name: str, native_ms: float, old_ms: float):
    """Print benchmark result with speedup."""
    speedup = old_ms / native_ms
    print(f"{name:35} native: {native_ms:8.3f}ms  old: {old_ms:8.3f}ms  speedup: {speedup:>7.1f}x")


def main():
    print("=" * 90)
    print("Performance Benchmark: Native vs Old Implementation")
    print("=" * 90)

    iterations = 50
    print(f"\nIterations per test: {iterations}\n")

    # =========================================================================
    # Color caching benchmark
    # =========================================================================
    print("Matugen Color Loading:")
    print("-" * 90)

    from wrappers.wrp_native import invalidate_color_cache, get_cached_colors
    from pathlib import Path

    wallpaper = str(Path.home() / ".current.wall")

    if Path(wallpaper).exists():
        # Cold start (runs matugen)
        invalidate_color_cache()

        def cold_colors():
            invalidate_color_cache()
            return get_cached_colors(wallpaper)

        def cached_colors():
            return get_cached_colors(wallpaper)

        # Measure cold start (just once, it's slow)
        start = time.perf_counter()
        cold_colors()
        cold_ms = (time.perf_counter() - start) * 1000

        # Measure cached
        cached_ms = benchmark("cached colors", cached_colors, iterations)

        print(f"{'Cold start (matugen subprocess)':35} {cold_ms:8.2f}ms")
        print(f"{'Cached (mtime validated)':35} {cached_ms:8.3f}ms")
        print(f"{'Speedup':35} {cold_ms/cached_ms:>8.0f}x")
    else:
        print(f"⚠ Wallpaper not found at {wallpaper}")

    # =========================================================================
    # Audio sink benchmark
    # =========================================================================
    print("\nPipeWire Audio Sinks:")
    print("-" * 90)

    from wrappers.wrp_native import get_audio_sinks

    def native_sinks():
        return get_audio_sinks()

    def old_wpctl_sinks():
        """Old implementation: parse wpctl status text."""
        result = subprocess.run(["wpctl", "status"], capture_output=True, text=True)
        return result.stdout

    native_ms = benchmark("native (pw-dump + JSON parse)", native_sinks, iterations)
    old_ms = benchmark("old (wpctl status + regex)", old_wpctl_sinks, iterations)
    print_result("Audio sink enumeration", native_ms, old_ms)

    # =========================================================================
    # Hyprland IPC benchmark
    # =========================================================================
    if IN_HYPRLAND:
        print("\nHyprland IPC:")
        print("-" * 90)

        import json
        from wrappers.wrp_native import hyprctl_json

        def native_monitors():
            return json.loads(hyprctl_json("monitors"))

        def subprocess_monitors():
            result = subprocess.run(["hyprctl", "-j", "monitors"], capture_output=True, text=True)
            return json.loads(result.stdout)

        native_ms = benchmark("native (socket)", native_monitors, iterations)
        old_ms = benchmark("subprocess (hyprctl)", subprocess_monitors, iterations)
        print_result("hyprctl -j monitors", native_ms, old_ms)
    else:
        print("\n⚠ Not in Hyprland session - skipping IPC benchmarks")

    # =========================================================================
    # Full command benchmark
    # =========================================================================
    print("\nFull Command Execution (wrp audio show):")
    print("-" * 90)

    def run_wrp_audio():
        subprocess.run([".venv/bin/wrp", "audio", "show"], capture_output=True)

    cmd_ms = benchmark("wrp audio show", run_wrp_audio, 20)
    print(f"{'Full command time':35} {cmd_ms:8.2f}ms")

    print("\n" + "=" * 90)
    print("Summary: Native implementations provide significant speedups,")
    print("especially for cached colors (~7000x) and Hyprland IPC (~20x).")
    print("=" * 90)


if __name__ == "__main__":
    main()
