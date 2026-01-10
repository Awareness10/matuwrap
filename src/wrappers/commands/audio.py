"""Audio sink toggle command."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from wrappers.core.notify import notify
from wrappers.core.theme import console, print_header, print_success, print_error, fmt

# Try native implementation
try:
    from wrappers.wrp_native import get_audio_sinks, set_default_sink, AudioSink
    _USE_NATIVE = True
except ImportError:
    _USE_NATIVE = False
    get_audio_sinks = None  # type: ignore[assignment]
    set_default_sink = None  # type: ignore[assignment]

if TYPE_CHECKING:
    from wrappers.wrp_native import AudioSink

COMMAND = {
    "description": "Toggle audio between HDMI/Headset",
    "subcommands": [
        ("show", "", "Show current audio sinks"),
    ],
}


def _find_sink(sinks: list[AudioSink], pattern: str) -> AudioSink | None:
    """Find sink matching pattern."""
    for sink in sinks:
        if re.search(pattern, sink.name, re.IGNORECASE):
            return sink
    return None


def _toggle(
    hdmi_pattern: str = r"HDMI|AD103",
    headset_pattern: str = r"HyperX|Headset",
) -> int:
    """Toggle between HDMI and headset audio sinks."""
    if not _USE_NATIVE or get_audio_sinks is None or set_default_sink is None:
        print_error("Native module not available")
        return 1

    sinks = get_audio_sinks()
    hdmi = _find_sink(sinks, hdmi_pattern)
    headset = _find_sink(sinks, headset_pattern)

    if not hdmi or not headset:
        missing = []
        if not hdmi:
            missing.append("HDMI")
        if not headset:
            missing.append("Headset")
        print_error(f"Failed to detect: {fmt(', '.join(missing))}")
        notify("Audio", "Failed to detect audio devices", urgency="critical")
        return 1

    # Determine which is current default and switch to other
    if headset.is_default:
        if set_default_sink(hdmi.id):
            print_success(f"Switched to {fmt('HDMI')} [muted](TV)[/muted]")
            notify("Audio", "Switched to HDMI (TV)")
        else:
            print_error("Failed to switch to HDMI")
            return 1
    else:
        if set_default_sink(headset.id):
            print_success(f"Switched to {fmt('Headset')}")
            notify("Audio", "Switched to Headset")
        else:
            print_error("Failed to switch to Headset")
            return 1

    return 0


def _show() -> int:
    """Show current audio sink status."""
    if not _USE_NATIVE or get_audio_sinks is None:
        print_error("Native module not available")
        return 1

    sinks = get_audio_sinks()
    print_header("Audio Sinks")

    for sink in sinks:
        if sink.is_default:
            indicator = "[bool_on]●[/bool_on]"
            id_fmt = f"[bool_on]{sink.id}[/bool_on]"
        else:
            indicator = "[muted]○[/muted]"
            id_fmt = fmt(sink.id)

        vol_str = f" [muted]vol:[/muted] {fmt(sink.volume)}" if sink.volume is not None else ""
        console.print(f"  {indicator} {id_fmt}[muted].[/muted] {fmt(sink.name)}{vol_str}")

    console.print()
    return 0


def run(*args: str) -> int:
    """Dispatch audio subcommands."""
    if args and args[0] == "show":
        return _show()
    return _toggle()
