"""Dynamic color generation using matugen with native caching."""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

WALLPAPER_PATH = Path.home() / ".current.wall"

_native_get_colors: Callable[[str], dict[str, str]] | None = None
_USE_NATIVE = False

# Try native implementation
try:
    from matuwrap.wrp_native import get_cached_colors as _native_get_colors # type: ignore
    _USE_NATIVE = True
except ImportError:
    _USE_NATIVE = False
    _native_get_colors = None  # type: ignore[assignment]


@dataclass
class Colors:
    """Material You color scheme from matugen."""

    primary: str
    on_primary: str
    primary_container: str
    on_primary_container: str
    secondary: str
    on_secondary: str
    secondary_container: str
    tertiary: str
    error: str
    surface: str
    on_surface: str
    surface_container: str
    outline: str
    outline_variant: str

    @classmethod
    def default(cls) -> "Colors":
        """Fallback colors when matugen unavailable."""
        return cls(
            primary="#7aa2f7",
            on_primary="#1a1b26",
            primary_container="#3d59a1",
            on_primary_container="#c0caf5",
            secondary="#9ece6a",
            on_secondary="#1a1b26",
            secondary_container="#414868",
            tertiary="#bb9af7",
            error="#f7768e",
            surface="#1a1b26",
            on_surface="#c0caf5",
            surface_container="#24283b",
            outline="#565f89",
            outline_variant="#414868",
        )

    @classmethod
    def from_dict(cls, c: dict) -> "Colors":
        """Create Colors from a dict, using defaults for missing keys."""
        defaults = cls.default()
        return cls(
            primary=c.get("primary", defaults.primary),
            on_primary=c.get("on_primary", defaults.on_primary),
            primary_container=c.get("primary_container", defaults.primary_container),
            on_primary_container=c.get("on_primary_container", defaults.on_primary_container),
            secondary=c.get("secondary", defaults.secondary),
            on_secondary=c.get("on_secondary", defaults.on_secondary),
            secondary_container=c.get("secondary_container", defaults.secondary_container),
            tertiary=c.get("tertiary", defaults.tertiary),
            error=c.get("error", defaults.error),
            surface=c.get("surface", defaults.surface),
            on_surface=c.get("on_surface", defaults.on_surface),
            surface_container=c.get("surface_container", defaults.surface_container),
            outline=c.get("outline", defaults.outline),
            outline_variant=c.get("outline_variant", defaults.outline_variant),
        )


def get_colors(wallpaper: Path | None = None) -> Colors:
    """Get color scheme from wallpaper using matugen.

    Uses native Rust implementation with mtime-based caching.
    Falls back to default colors if matugen unavailable or fails.
    """
    path = wallpaper or WALLPAPER_PATH

    if not path.exists():
        return Colors.default()

    resolved = str(path.resolve())

    if _USE_NATIVE:
        if _native_get_colors is None:
            return Colors.default()
        colors = _native_get_colors(resolved)
        if colors is not None:
            return Colors.from_dict(colors)  # type: ignore
        return Colors.default()

    # Fallback: no native, no matugen subprocess (removed for performance)
    return Colors.default()
