"""Philips Hue Bridge control."""

from __future__ import annotations

import os
import requests
from pathlib import Path
from typing import Any
from dotenv import load_dotenv

from matuwrap.core.colors import get_colors
from matuwrap.core.notify import notify
from matuwrap.core.theme import (
    console,
    print_header,
    print_success,
    print_error,
    print_warning,
    create_table,
    fix_emoji_width,
    fmt,
)

load_dotenv()
HUE_BRIDGE_IP = os.environ.get("HUE_BRIDGE_IP")
HUE_USERNAME = os.environ.get("HUE_USERNAME")
HUE_LOGO = Path(__file__).resolve().parents[1] / 'assets' / 'img' / 'hue_logo_.png'

COMMAND = {
    "description": "Control Philips Hue lights",
    "args": "<subcommand> [args]",
    "subcommands": [
        ("list", "", "List all lights and their status"),
        ("on", "<id>", "Turn light on"),
        ("off", "<id>", "Turn light off"),
        ("brightness", "<id> <0-254>", "Set brightness level"),
        ("color", "<id> <hue> [sat]", "Set color (hue: 0-65535, sat: 0-254)"),
        ("temp", "<id> <153-500>", "Set color temperature (153=warm, 500=cool)"),
        ("theme", "<id> [color]", "Set light to matugen theme color (default: primary)"),
    ],
}



class HueController:
    """Philips Hue Bridge API controller."""

    def __init__(self, bridge_ip: str, username: str) -> None:
        self.bridge_ip = bridge_ip
        self.username = username
        self.base_url = f"http://{bridge_ip}/api/{username}"

    def get_lights(self) -> dict[str, Any]:
        """Get all lights."""
        resp = requests.get(f"{self.base_url}/lights", timeout=10)
        resp.raise_for_status()
        return resp.json()

    def set_light_state(self, light_id: int, **kwargs: Any) -> list[dict[str, Any]]:
        """Set light state (on, bri, hue, sat, ct, etc.)."""
        url = f"{self.base_url}/lights/{light_id}/state"
        resp = requests.put(url, json=kwargs, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def turn_on(self, light_id: int) -> list[dict[str, Any]]:
        return self.set_light_state(light_id, on=True)

    def turn_off(self, light_id: int) -> list[dict[str, Any]]:
        return self.set_light_state(light_id, on=False)

    def set_brightness(self, light_id: int, brightness: int) -> list[dict[str, Any]]:
        """brightness: 0-254"""
        return self.set_light_state(light_id, on=True, bri=brightness)

    def set_color(self, light_id: int, hue: int, saturation: int = 254) -> list[dict[str, Any]]:
        """hue: 0-65535, saturation: 0-254"""
        return self.set_light_state(light_id, on=True, hue=hue, sat=saturation)

    def set_temperature(self, light_id: int, ct: int) -> list[dict[str, Any]]:
        """ct: 153-500 (warm to cool)"""
        return self.set_light_state(light_id, on=True, ct=ct)


def _check_config() -> bool:
    """Check if Hue configuration is available."""
    if not HUE_BRIDGE_IP or not HUE_USERNAME:
        print_error("Hue bridge not configured")
        console.print(
            f"  [muted]Set environment variables:[/muted]\n"
            f"    {fmt('HUE_BRIDGE_IP')} [muted]- Bridge IP address[/muted]\n"
            f"    {fmt('HUE_USERNAME')} [muted]- Bridge username/token[/muted]"
        )
        return False
    return True


def _list_lights(hue: HueController) -> int:
    """List all lights and their status."""
    try:
        lights = hue.get_lights()
    except requests.exceptions.RequestException as e:
        print_error(f"Failed to connect to bridge: {e}")
        return 1

    print_header("Hue Lights")

    table = create_table("ID", "Name", "State", "Brightness")
    for light_id, light in sorted(lights.items(), key=lambda x: int(x[0])):
        state = light.get("state", {})
        is_on = state.get("on", False)
        bri = state.get("bri", 0)

        if is_on:
            state_str = "[bool_on]ON[/bool_on]"
            bri_pct = round(bri / 254 * 100)
            bri_str = f"{fmt(bri_pct)}[muted]%[/muted]"
        else:
            state_str = "[muted]OFF[/muted]"
            bri_str = "[muted]-[/muted]"

        table.add_row(fmt(light_id), fix_emoji_width(light["name"]), state_str, bri_str)

    console.print(table)
    return 0


def _turn_on(hue: HueController, light_id: int) -> int:
    """Turn a light on."""
    try:
        hue.turn_on(light_id)
        print_success(f"Light {fmt(light_id)} turned on")
        notify("Hue", f"Light {light_id} on", str(HUE_LOGO))
        return 0
    except requests.exceptions.RequestException as e:
        print_error(f"Failed to turn on light {light_id}: {e}")
        return 1


def _turn_off(hue: HueController, light_id: int) -> int:
    """Turn a light off."""
    try:
        hue.turn_off(light_id)
        print_success(f"Light {fmt(light_id)} turned off")
        notify("Hue", f"Light {light_id} off", str(HUE_LOGO))
        return 0
    except requests.exceptions.RequestException as e:
        print_error(f"Failed to turn off light {light_id}: {e}")
        return 1


def _set_brightness(hue: HueController, light_id: int, value: int) -> int:
    """Set light brightness."""
    if not 0 <= value <= 100:
        print_error(f"Brightness must be 0-100 (%), got {fmt(value)}")
        return 1

    try:
        pct = value
        value = int(value / 100 * 254)
        hue.set_brightness(light_id, value)
        pct = round(value / 254 * 100)
        print_success(f"Light {fmt(light_id)} brightness set to {fmt(pct)}%")
        return 0
    except requests.exceptions.RequestException as e:
        print_error(f"Failed to set brightness: {e}")
        return 1


def _set_color(hue: HueController, light_id: int, hue_val: int, sat: int = 254) -> int:
    """Set light color."""
    if not 0 <= hue_val <= 65535:
        print_error(f"Hue must be 0-65535, got {fmt(hue_val)}")
        return 1
    if not 0 <= sat <= 254:
        print_error(f"Saturation must be 0-254, got {fmt(sat)}")
        return 1
    try:
        hue.set_color(light_id, hue_val, sat)
        print_success(f"Light {fmt(light_id)} color set [muted](hue={hue_val}, sat={sat})[/muted]")
        return 0
    except requests.exceptions.RequestException as e:
        print_error(f"Failed to set color: {e}")
        return 1


def _set_temperature(hue: HueController, light_id: int, ct: int) -> int:
    """Set light color temperature."""
    if not 153 <= ct <= 500:
        print_error(f"Temperature must be 153-500, got {fmt(ct)}")
        return 1
    try:
        hue.set_temperature(light_id, ct)
        temp_desc = "warm" if ct < 250 else "neutral" if ct < 400 else "cool"
        print_success(f"Light {fmt(light_id)} temperature set to {fmt(ct)} [muted]({temp_desc})[/muted]")
        return 0
    except requests.exceptions.RequestException as e:
        print_error(f"Failed to set temperature: {e}")
        return 1


def _hex_to_hue(hex_color: str) -> tuple[int, int]:
    """Convert hex color to Hue's hue/saturation values.

    Returns (hue: 0-65535, sat: 0-254).
    """
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i : i + 2], 16) / 255.0 for i in (0, 2, 4))

    max_c = max(r, g, b)
    min_c = min(r, g, b)
    diff = max_c - min_c

    # Hue calculation
    if diff == 0:
        h = 0.0
    elif max_c == r:
        h = ((g - b) / diff) % 6
    elif max_c == g:
        h = (b - r) / diff + 2
    else:
        h = (r - g) / diff + 4
    h = h / 6.0  # Normalize to 0-1

    # Saturation calculation
    s = 0.0 if max_c == 0 else diff / max_c

    # Convert to Hue ranges
    hue_val = int(h * 65535)
    sat_val = int(s * 254)

    return hue_val, sat_val


# Available theme colors
THEME_COLORS = (
    "primary",
    "secondary",
    "tertiary",
    "primary_container",
    "secondary_container",
)


def _set_theme(hue: HueController, light_id: int, color_name: str = "primary") -> int:
    """Set light to matugen theme color."""
    colors = get_colors()

    if color_name not in THEME_COLORS:
        print_error(f"Unknown theme color: {fmt(color_name)}")
        console.print(f"  [muted]Available:[/muted] {', '.join(THEME_COLORS)}")
        return 1

    hex_color = getattr(colors, color_name)
    hue_val, sat_val = _hex_to_hue(hex_color)

    try:
        hue.set_color(light_id, hue_val, sat_val)
        print_success(
            f"Light {fmt(light_id)} set to {fmt(color_name)} "
            f"[muted]({hex_color})[/muted]"
        )
        notify("Hue", f"Light {light_id} --> {color_name}", str(HUE_LOGO))
        return 0
    except requests.exceptions.RequestException as e:
        print_error(f"Failed to set theme color: {e}")
        return 1


def _parse_int(value: str, name: str) -> int | None:
    """Parse integer argument with error handling."""
    try:
        return int(value)
    except ValueError:
        print_error(f"Invalid {name}: {fmt(value)} [muted](must be integer)[/muted]")
        return None


def _usage() -> int:
    """Show usage information."""
    print_warning("Usage: wrp hue <subcommand> [args]")
    console.print(f"  [muted]Run[/muted] {fmt('wrp help hue')} [muted]for details[/muted]")
    return 1


def run(*args: str) -> int:
    """Dispatch hue subcommands."""
    if not _check_config():
        return 1

    hue = HueController(HUE_BRIDGE_IP, HUE_USERNAME)  # type: ignore[arg-type]

    if not args:
        return _list_lights(hue)

    cmd = args[0]

    if cmd == "list":
        return _list_lights(hue)

    elif cmd == "on":
        if len(args) < 2:
            print_error("Missing light ID")
            return 1
        light_id = _parse_int(args[1], "light ID")
        if light_id is None:
            return 1
        return _turn_on(hue, light_id)

    elif cmd == "off":
        if len(args) < 2:
            print_error("Missing light ID")
            return 1
        light_id = _parse_int(args[1], "light ID")
        if light_id is None:
            return 1
        return _turn_off(hue, light_id)

    elif cmd == "brightness":
        if len(args) < 3:
            print_error("Usage: wrp hue brightness <id> <percent>")
            return 1
        light_id = _parse_int(args[1], "light ID")
        value = _parse_int(args[2], "brightness")
        if light_id is None or value is None:
            return 1
        return _set_brightness(hue, light_id, value)

    elif cmd == "color":
        if len(args) < 3:
            print_error("Usage: wrp hue color <id> <hue> [sat]")
            return 1
        light_id = _parse_int(args[1], "light ID")
        sat = 254
        if not args[2].__contains__("#"):
            hue_val = _parse_int(args[2], "hue")
            if len(args) >= 4:
                sat_val = _parse_int(args[3], "saturation")
                if sat_val is None:
                    return 1
                sat = sat_val
        else:
            hex_hue = _hex_to_hue(args[2])
            hue_val = _parse_int(str(hex_hue[0]), "hue")
            sat_val = _parse_int(str(hex_hue[1]), "saturation")
            if sat_val is not None:
                sat = sat_val
        if light_id is None or hue_val is None:
            return 1
        return _set_color(hue, light_id, hue_val, sat)

    elif cmd == "temp":
        if len(args) < 3:
            print_error("Usage: wrp hue temp <id> <153-500>")
            return 1
        light_id = _parse_int(args[1], "light ID")
        ct = _parse_int(args[2], "temperature")
        if light_id is None or ct is None:
            return 1
        return _set_temperature(hue, light_id, ct)

    elif cmd == "theme":
        if len(args) < 2:
            print_error("Usage: wrp hue theme <id> [color]")
            console.print(f"  [muted]Colors:[/muted] {', '.join(THEME_COLORS)}")
            return 1
        light_id = _parse_int(args[1], "light ID")
        if light_id is None:
            return 1
        color_name = args[2] if len(args) >= 3 else "primary"
        return _set_theme(hue, light_id, color_name)

    else:
        print_error(f"Unknown subcommand: {fmt(cmd)}")
        return _usage()
