"""Type stubs for wrp_native Rust extension module."""

from typing import Final

# Command execution

def run_command(program: str, args: list[str]) -> str:
    """Run a command and return stdout as string.

    Raises:
        OSError: If command fails to execute.
        RuntimeError: If command returns non-zero exit code.
    """
    ...

# Hyprland IPC

def hyprctl(command: str) -> str:
    """Query Hyprland IPC directly via Unix socket.

    Args:
        command: Hyprland IPC command (e.g., "monitors", "dispatch workspace 1").

    Returns:
        Raw response string from Hyprland.

    Raises:
        RuntimeError: If HYPRLAND_INSTANCE_SIGNATURE not set.
        ConnectionError: If socket connection fails.
        IOError: If read/write fails.
    """
    ...

def hyprctl_json(command: str) -> str:
    """Query Hyprland IPC with JSON output.

    Args:
        command: Hyprland IPC command (e.g., "monitors", "clients").

    Returns:
        JSON string response from Hyprland.

    Raises:
        RuntimeError: If HYPRLAND_INSTANCE_SIGNATURE not set.
        ConnectionError: If socket connection fails.
        IOError: If read/write fails.
    """
    ...

# Matugen color caching

def get_cached_colors(wallpaper_path: str) -> dict[str, str] | None:
    """Get matugen colors with caching.

    Colors are cached to ~/.cache/matuwrap/colors.json and validated
    against wallpaper mtime.

    Args:
        wallpaper_path: Path to wallpaper image file.

    Returns:
        Dict of color_name -> hex_value, or None if matugen fails.
    """
    ...

def invalidate_color_cache() -> None:
    """Invalidate the color cache, forcing regeneration on next call."""
    ...

# PipeWire audio

class AudioSink:
    """Represents a PipeWire audio sink."""

    id: Final[int]
    """Sink ID."""

    name: Final[str]
    """Sink name/description."""

    description: Final[str]
    """Additional description (may be empty)."""

    volume: Final[float | None]
    """Current volume level (0.0-1.0), or None if unavailable."""

    is_default: Final[bool]
    """Whether this is the default sink."""

    def __repr__(self) -> str: ...

def get_audio_sinks() -> list[AudioSink]:
    """Get audio sinks from PipeWire via wpctl status.

    Returns:
        List of AudioSink objects.

    Raises:
        OSError: If wpctl fails to execute.
        RuntimeError: If wpctl returns error.
    """
    ...

def set_default_sink(sink_id: int) -> bool:
    """Set the default audio sink by ID.

    Args:
        sink_id: PipeWire sink ID.

    Returns:
        True if successful, False otherwise.

    Raises:
        OSError: If wpctl fails to execute.
    """
    ...

# System info

def memory_info() -> tuple[int, int, int]:
    """Get system memory info.

    Returns:
        Tuple of (total_bytes, used_bytes, available_bytes).
    """
    ...

def cpu_usage() -> float:
    """Get CPU usage as percentage.

    Note: This function blocks for ~100ms to get accurate reading.

    Returns:
        CPU usage percentage (0.0 - 100.0).
    """
    ...
