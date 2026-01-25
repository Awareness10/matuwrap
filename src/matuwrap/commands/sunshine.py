"""Sunshine streaming service control."""

from pathlib import Path

from matuwrap.core import hyprland, systemd
from matuwrap.core.hyprland import TRANSFORMS, swap_if_rotated
from matuwrap.core.notify import notify
from matuwrap.core.theme import (
    console,
    print_header,
    print_kv,
    print_success,
    print_error,
    print_warning,
    print_info,
    create_table,
    fmt,
)

COMMAND = {
    "description": "Control Sunshine streaming",
    "args": "<action>",
    "subcommands": [
        ("status", "", "Show service status"),
        ("start", "", "Start Sunshine"),
        ("stop", "", "Stop Sunshine"),
        ("restart", "", "Restart Sunshine"),
        ("logs", "<n>", "Show last n log lines (default: 50)"),
        ("monitors", "", "List available monitors"),
        ("monitor", "<name>", "Set capture monitor"),
    ],
}

SERVICE_NAME = "sunshine"
CONFIG_PATH = Path.home() / ".config" / "sunshine" / "sunshine.conf"


def _read_config() -> dict[str, str]:
    """Read Sunshine config file into a dict."""
    config = {}
    if CONFIG_PATH.exists():
        for line in CONFIG_PATH.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                config[key.strip()] = value.strip()
    return config


def _write_config(config: dict[str, str]) -> None:
    """Write config dict back to file."""
    lines = [f"{k} = {v}" for k, v in config.items()]
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text("\n".join(lines) + "\n")


def status() -> int:
    """Show Sunshine service status."""
    svc = systemd.get_status(SERVICE_NAME)

    print_header("Sunshine Status")

    # Service active/inactive
    if svc.active:
        status_str = f"[bool_on]● {svc.status.upper()}[/bool_on]"
    else:
        status_str = f"[bool_off]○ {svc.status.upper()}[/bool_off]"

    print_kv("Service", status_str)
    print_kv("Enabled", fmt(svc.enabled))

    if svc.description:
        print_kv("Description", fmt(svc.description))

    # Show current monitor config if available
    config = _read_config()
    if "output_name" in config:
        print_kv("Monitor", fmt(config["output_name"]))

    console.print()
    return 0


def start() -> int:
    """Start Sunshine service."""
    svc = systemd.get_status(SERVICE_NAME)

    if svc.active:
        print_warning(f"Sunshine is already {fmt('running')}")
        return 0

    if systemd.start(SERVICE_NAME):
        print_success(f"Sunshine {fmt('started')}")
        notify("Sunshine", "Streaming service started")
        return 0
    else:
        print_error("Failed to start Sunshine")
        notify("Sunshine", "Failed to start", urgency="critical")
        return 1


def stop() -> int:
    """Stop Sunshine service."""
    svc = systemd.get_status(SERVICE_NAME)

    if not svc.active:
        print_warning(f"Sunshine is not {fmt('running')}")
        return 0

    if systemd.stop(SERVICE_NAME):
        print_success(f"Sunshine {fmt('stopped')}")
        notify("Sunshine", "Streaming service stopped")
        return 0
    else:
        print_error("Failed to stop Sunshine")
        notify("Sunshine", "Failed to stop", urgency="critical")
        return 1


def restart() -> int:
    """Restart Sunshine service."""
    if systemd.restart(SERVICE_NAME):
        print_success(f"Sunshine {fmt('restarted')}")
        notify("Sunshine", "Streaming service restarted")
        return 0
    else:
        print_error("Failed to restart Sunshine")
        notify("Sunshine", "Failed to restart", urgency="critical")
        return 1


def logs(lines: int = 50) -> int:
    """Show recent Sunshine logs."""
    print_header(f"Sunshine Logs [muted](last {fmt(lines)} lines)[/muted]")
    console.print()

    log_output = systemd.get_logs(SERVICE_NAME, lines)
    if log_output.strip():
        console.print(log_output, highlight=False)
    else:
        print_info("No logs available")

    return 0


def set_monitor(output_name: str) -> int:
    """Set the monitor Sunshine captures."""
    config = _read_config()
    old_monitor = config.get("output_name", "not set")

    config["output_name"] = output_name
    _write_config(config)

    print_success(f"Monitor set: {fmt(old_monitor)} [muted]→[/muted] {fmt(output_name)}")
    print_info("Restart Sunshine for changes to take effect")
    notify("Sunshine", f"Monitor set to {output_name}")

    return 0


def list_monitors() -> int:
    """List available monitors for Sunshine capture."""
    try:
        monitors = hyprland.get_monitors()
    except hyprland.HyprlandError as e:
        print_error(f"Failed to get monitors: {e}")
        return 1

    config = _read_config()
    current = config.get("output_name", "")

    print_header("Available Monitors")
    console.print()

    table = create_table("", "Name", "Resolution", "Position")

    for m in monitors:
        name = m.get("name", "unknown")
        width = m.get("width", 0)
        height = m.get("height", 0)
        x = m.get("x", 0)
        y = m.get("y", 0)
        transform = m.get("transform", 0)

        # Swap dimensions for 90°/270° rotations
        width, height = swap_if_rotated(width, height, transform)
        transform_label = TRANSFORMS.get(transform)

        is_current = name == current
        indicator = "[bool_on]●[/bool_on]" if is_current else "[muted]○[/muted]"
        name_fmt = f"[bool_on]{name}[/bool_on]" if is_current else fmt(name)
        res_fmt = f"{fmt(width)}[unit]x[/unit]{fmt(height)}"
        if transform_label:
            res_fmt += f" [muted]({transform_label})[/muted]"
        pos_fmt = f"{fmt(x)}[unit],[/unit]{fmt(y)}"

        table.add_row(indicator, name_fmt, res_fmt, pos_fmt)

    console.print(table)
    return 0


def run(*args: str) -> int:
    """Dispatch sunshine subcommands."""
    if not args:
        return status()

    action, *rest = args
    actions = {
        "status": status,
        "start": start,
        "stop": stop,
        "restart": restart,
        "logs": lambda: logs(int(rest[0]) if rest else 50),
        "monitor": lambda: set_monitor(rest[0]) if rest else list_monitors(),
        "monitors": list_monitors,
    }

    if action not in actions:
        print_error(f"Unknown action: {fmt(action)}")
        print_info(f"Available: {', '.join(actions.keys())}")
        return 1

    return actions[action]()
