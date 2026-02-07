"""Matugen cached colors json command."""
from pathlib import Path

from matuwrap.wrp_native import get_cached_colors
#from matuwrap.core.theme import console, print_header, print_kv, print_error, fmt

COMMAND = {
    "description": "Get cached wallpaper color",
    "subcommands": [
        ("ps1", "", "Output bash PS1 fragment with matugen colors"),
    ],
}

WALLPAPER_PATH = Path.home() / ".current.wall"

def primary():
    colors = get_cached_colors(str(WALLPAPER_PATH))
    if not colors:
        return None

    hex_color = colors.get("primary")
    if not hex_color:
        return None

    return hex_color

def hex_to_ansi(hex_color: str) -> str:
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return f"\033[38;2;{r};{g};{b}m"

def _hex_to_ps1(hex_color: str) -> str:
    """Convert hex color to bash PS1 color escape (literal, for bash to interpret)."""
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return f"\\[\\033[38;2;{r};{g};{b}m\\]"

def ps1() -> str:
    """Output bash PS1 fragment: colored user@host:workdir."""
    colors = get_cached_colors(str(WALLPAPER_PATH))
    reset = "\\[\\033[0m\\]"

    if not colors:
        return "\\u@\\h:\\w"

    parts = []
    primary = colors.get("primary")
    if primary:
        parts.append(f"{_hex_to_ps1(primary)}\\u{reset}@{_hex_to_ps1(primary)}\\h{reset}")
    else:
        parts.append("\\u@\\h")

    parts.append(":")

    tertiary = colors.get("tertiary")
    if tertiary:
        parts.append(f"{_hex_to_ps1(tertiary)}\\w{reset}")
    else:
        parts.append("\\w")

    return "".join(parts)

def run(*args: str) -> int:
    if args and args[0] == "ps1":
        print(ps1())
        return 0
    color = primary()
    if color:
        print(color)
        return 0
    return 1