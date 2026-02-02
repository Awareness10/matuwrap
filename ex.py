from pathlib import Path
from matuwrap.wrp_native import get_cached_colors

WALLPAPER_PATH = Path.home() / ".current.wall"
cached_colors = get_cached_colors(str(WALLPAPER_PATH))
if cached_colors is not None:
    print(type(cached_colors))
    print(cached_colors)
    print()
    print(cached_colors.get("primary"))