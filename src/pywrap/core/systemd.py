"""Systemd user service management."""

import subprocess
from dataclasses import dataclass


@dataclass
class ServiceStatus:
    """Status information for a systemd service."""

    name: str
    active: bool
    enabled: bool
    status: str  # "active", "inactive", "failed", etc.
    description: str | None = None


def _run_systemctl(*args: str) -> subprocess.CompletedProcess:
    """Run systemctl --user command."""
    return subprocess.run(
        ["systemctl", "--user", *args],
        capture_output=True,
        text=True,
    )


def get_status(name: str) -> ServiceStatus:
    """Get status of a user service."""
    is_active = _run_systemctl("is-active", name)
    is_enabled = _run_systemctl("is-enabled", name)

    status_text = is_active.stdout.strip()
    active = status_text == "active"
    enabled = is_enabled.stdout.strip() == "enabled"

    # Get description
    desc_result = _run_systemctl("show", name, "--property=Description")
    desc_line = desc_result.stdout.strip()
    description = desc_line.split("=", 1)[1] if "=" in desc_line else None

    return ServiceStatus(
        name=name,
        active=active,
        enabled=enabled,
        status=status_text,
        description=description,
    )


def start(name: str) -> bool:
    """Start a user service. Returns True on success."""
    result = _run_systemctl("start", name)
    return result.returncode == 0


def stop(name: str) -> bool:
    """Stop a user service. Returns True on success."""
    result = _run_systemctl("stop", name)
    return result.returncode == 0


def restart(name: str) -> bool:
    """Restart a user service. Returns True on success."""
    result = _run_systemctl("restart", name)
    return result.returncode == 0


def get_logs(name: str, lines: int = 50) -> str:
    """Get recent logs for a user service."""
    result = subprocess.run(
        ["journalctl", "--user", "-u", name, "-n", str(lines), "--no-pager"],
        capture_output=True,
        text=True,
    )
    return result.stdout
