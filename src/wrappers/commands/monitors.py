"""Monitor information command."""

from wrappers.core import hyprland
from wrappers.core.hyprland import TRANSFORMS, swap_if_rotated
from wrappers.core.theme import console, print_header, print_kv, print_error, fmt

COMMAND = {
    "description": "Show monitor information",
}


def run(*args: str) -> int:
    """Display information about all connected monitors."""
    try:
        monitors = hyprland.get_monitors()
    except hyprland.HyprlandError as e:
        print_error(f"Failed to get monitors: {e}")
        return 1

    if not monitors:
        print_error("No monitors found")
        return 1

    for monitor in monitors:
        name = monitor.get("name", "unknown")
        monitor_id = monitor.get("id", "?")
        make = monitor.get("make", "")
        model = monitor.get("model", "")
        width = monitor.get("width", 0)
        height = monitor.get("height", 0)
        refresh = round(monitor.get("refreshRate", 0))
        x = monitor.get("x", 0)
        y = monitor.get("y", 0)
        scale = monitor.get("scale", 1)
        workspace = monitor.get("activeWorkspace", {}).get("name", "?")
        dpms = "on" if monitor.get("dpmsStatus", True) else "off"
        transform = monitor.get("transform", 0)

        # Swap dimensions for 90° or 270° rotation
        width, height = swap_if_rotated(width, height, transform)
        transform_label = TRANSFORMS.get(transform)

        print_header(f"{name} [muted](ID {fmt(monitor_id)})[/muted]")
        print_kv("Model", fmt(f"{make} {model}".strip() or "unknown"))

        # Resolution with optional transform label
        res_str = f"{fmt(width)}[unit]x[/unit]{fmt(height)} [unit]@[/unit] {fmt(refresh, 'Hz')}"
        if transform_label:
            res_str += f" [muted]({transform_label})[/muted]"
        print_kv("Resolution", res_str)

        print_kv("Position", f"{fmt(x)}[unit],[/unit]{fmt(y)}")
        print_kv("Scale", fmt(scale))
        print_kv("Workspace", fmt(workspace))
        print_kv("DPMS", fmt(dpms))

    console.print()
    return 0
