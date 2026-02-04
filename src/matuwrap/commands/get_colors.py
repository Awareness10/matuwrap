"""Matugen cached colors json command."""
from pathlib import Path

from matuwrap.wrp_native import get_cached_colors
#from matuwrap.core.theme import console, print_header, print_kv, print_error, fmt

COMMAND = {
    "description": "Get cached wallpaper color",
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

def run(*args: str) -> int:
    color = primary()
    if color:
        print(color)
        return 0
    return 1