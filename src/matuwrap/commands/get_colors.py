"""Matugen cached colors json command."""
from pathlib import Path

from matuwrap.wrp_native import get_cached_colors
from matuwrap.core.theme import console, print_header, print_kv, print_error, fmt
from matuwrap.core.colors import get_colors

COMMAND = {
    "description": "Get cached wallpaper color",
}

WALLPAPER_PATH = Path.home() / ".current.wall"

def _run(*args: str) -> int:
    response_hex = get_cached_colors(str(WALLPAPER_PATH))
    
    if response_hex is not None:
        for k, val in sorted(response_hex.items()):
            print_kv(f"{k:<25}", fmt(val))
        return 0
    
    print_error(f"{type(response_hex) = }")
    print_error(f"{response_hex = }")
    return 1

def primary() -> tuple[str, str, str] | None:
    response_hex = (get_cached_colors(str(WALLPAPER_PATH))).get("primary", "")
    if response_hex is not None:
        
        r, g, b = (int(hex_color[i : i + 2], 16) / 255.0 for i in (0, 2, 4))
        return (f'{r}', f'{g}', f'{b}')  # '#81d5ca' from your output

def run(*args: str) -> int:
    color = primary()
    if color:
        hex_color = hex_color.lstrip("#")
        r, g, b = (int(hex_color[i : i + 2], 16) / 255.0 for i in (0, 2, 4))
        print(color)
        return 0
    return 1