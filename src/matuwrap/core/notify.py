"""System notification wrapper using notify-send."""

import subprocess


def notify(
    title: str,
    message: str,
    icon: str | None = None,
    urgency: str = "normal",
    timeout: int = 2000,
    app_name: str = "matuwrap",
) -> None:
    """Send a desktop notification via notify-send.

    Args:
        title: Notification title
        message: Notification body
        icon: Path to icon file (optional)
        urgency: low, normal, or critical
        timeout: Display time in milliseconds
        app_name: Application name for notification
    """
    cmd = [
        "notify-send",
        "-t",
        str(timeout),
        "-u",
        urgency,
        "-a",
        app_name,
    ]

    if icon:
        cmd.extend(["-i", icon])

    cmd.extend([title, message])

    subprocess.run(cmd, check=False, capture_output=True)
