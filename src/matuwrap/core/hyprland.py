"""Hyprland IPC wrapper using native socket communication."""

from collections.abc import Callable
from typing import Any
import json
import subprocess
import logging

logger = logging.getLogger(__name__)

_native_hyprctl: Callable[[str], str] | None = None
_native_hyprctl_json: Callable[[str], str] | None = None
_USE_NATIVE = False

try:
    from matuwrap.wrp_native import hyprctl as _native_hyprctl, hyprctl_json as _native_hyprctl_json
    _USE_NATIVE = True
except ImportError:
    logger.warning("Native module unavailable, using subprocess fallback (slower)")

class HyprlandError(Exception):
    """Raised when hyprctl command fails."""


# Monitor transform values from Hyprland
# https://wiki.hyprland.org/Configuring/Monitors/#rotating
TRANSFORMS: dict[int, str | None] = {
    0: None,            # Normal (no rotation)
    1: "90°",           # 90 degrees
    2: "180°",          # 180 degrees
    3: "270°",          # 270 degrees
    4: "flipped",       # Flipped
    5: "flipped 90°",   # Flipped + 90
    6: "flipped 180°",  # Flipped + 180
    7: "flipped 270°",  # Flipped + 270
}


def is_rotated(transform: int) -> bool:
    """Check if transform represents a 90° or 270° rotation.

    These rotations swap width and height dimensions.
    """
    return transform in (1, 3, 5, 7)


def swap_if_rotated(width: int, height: int, transform: int) -> tuple[int, int]:
    """Swap width and height if transform is a 90°/270° rotation.

    Args:
        width: Original width.
        height: Original height.
        transform: Hyprland transform value (0-7).

    Returns:
        Tuple of (width, height), swapped if rotated.
    """
    if is_rotated(transform):
        return height, width
    return width, height


def _run_hyprctl(*args: str) -> str:
    """Run hyprctl with arguments and return output."""
    if _USE_NATIVE and _native_hyprctl is not None:
        command = " ".join(args)
        return _native_hyprctl(command)
    
    # Fallback: use subprocess
    result = subprocess.run(
        ["hyprctl", *args],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise HyprlandError(result.stderr.strip() or "hyprctl command failed")
    return result.stdout


def _query_json(*args: str) -> Any:
    """Run hyprctl with -j flag and parse JSON output."""
    if _USE_NATIVE and _native_hyprctl_json is not None:
        command = " ".join(args)
        try:
            return json.loads(_native_hyprctl_json(command))
        except json.JSONDecodeError as e:
            raise HyprlandError(f"Invalid JSON from hyprctl: {e}")

    # Fallback: use subprocess
    output = _run_hyprctl("-j", *args)
    try:
        return json.loads(output)
    except json.JSONDecodeError as e:
        raise HyprlandError(f"Invalid JSON from hyprctl: {e}")


def get_monitors() -> list[dict]:
    """Get list of all monitors with their properties."""
    return _query_json("monitors")


def get_active_workspace() -> dict:
    """Get the currently active workspace."""
    return _query_json("activeworkspace")


def get_clients() -> list[dict]:
    """Get list of all windows/clients."""
    return _query_json("clients")


def get_active_window() -> dict:
    """Get the currently focused window."""
    return _query_json("activewindow")


def dispatch(command: str, *args: str) -> None:
    """Execute a Hyprland dispatcher command."""
    _run_hyprctl("dispatch", command, *args)
