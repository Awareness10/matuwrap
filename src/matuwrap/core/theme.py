"""Centralized Rich theme and styled output helpers with matugen colors."""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.theme import Theme

from matuwrap.core.colors import get_colors

# Load colors from wallpaper (cached at import time)
_colors = get_colors()


def _build_theme() -> Theme:
    """Build Rich theme from matugen colors."""
    return Theme(
        {
            "title": f"bold {_colors.primary}",
            "label": f"{_colors.outline}",
            "value": f"{_colors.on_surface}",
            "success": f"bold {_colors.secondary}",
            "warning": f"bold {_colors.tertiary}",
            "error": f"bold {_colors.error}",
            "muted": f"{_colors.outline_variant}",
            "accent": f"{_colors.tertiary}",
            "info": f"{_colors.primary}",
            "surface": f"{_colors.surface_container}",
            # Data type colors
            "str": f"{_colors.on_surface}",
            "num": f"{_colors.tertiary}",
            "bool_on": f"bold {_colors.secondary}",
            "bool_off": f"{_colors.outline_variant}",
            "unit": f"{_colors.outline}",
        }
    )


THEME = _build_theme()
console = Console(theme=THEME)


def print_header(text: str | None) -> None:
    """Print a styled header."""
    if text is not None:
        console.print(f"\n[title]{text}[/title]")


def print_kv(label: str, value: str, label_width: int = 14) -> None:
    """Print a key-value pair with aligned label."""
    console.print(f"  [label]{label:<{label_width}}[/label] [value]{value}[/value]")


def fmt(value: str | int | float | bool, unit: str = "") -> str:
    """Format a value with type-appropriate styling.

    - Strings: str style
    - Numbers: num style (with optional unit in unit style)
    - Bools: bool_on/bool_off style, displayed as ON/OFF
    """
    if isinstance(value, bool):
        if value:
            return "[bool_on]ON[/bool_on]"
        return "[bool_off]OFF[/bool_off]"

    if isinstance(value, (int, float)):
        if unit:
            return f"[num]{value}[/num][unit]{unit}[/unit]"
        return f"[num]{value}[/num]"

    # String - check for on/off/true/false
    lower = str(value).lower()
    if lower in ("on", "true", "yes", "enabled"):
        return f"[bool_on]{value.upper()}[/bool_on]"
    if lower in ("off", "false", "no", "disabled"):
        return f"[bool_off]{value.upper()}[/bool_off]"

    return f"[str]{value}[/str]"


def print_success(text: str) -> None:
    """Print a success message."""
    console.print(f"[success]✓[/success] {text}")


def print_error(text: str) -> None:
    """Print an error message."""
    console.print(f"[error]✗[/error] {text}")


def print_warning(text: str) -> None:
    """Print a warning message."""
    console.print(f"[warning]![/warning] {text}")


def print_info(text: str) -> None:
    """Print an info message."""
    console.print(f"[info]∟[/info] {text}")


def create_table(*columns: str, title: str | None = None) -> Table:
    """Create a styled table with consistent formatting."""
    table = Table(
        title=title,
        title_style="title",
        header_style="label",
        border_style="muted",
        show_header=True,
        show_edge=True,
        pad_edge=True,
    )
    for col in columns:
        table.add_column(col)
    return table


def print_panel(content: str, title: str | None = None) -> None:
    """Print content in a styled panel."""
    console.print(
        Panel(
            content,
            title=title,
            title_align="left",
            border_style="muted",
            padding=(0, 1),
        )
    )


def fix_emoji_width(text: str) -> str:
    """Fix emoji width for table alignment.

    Strips variation selector-16 (U+FE0F) which causes width miscalculation
    in some terminals. Emoji will render as text style instead of color.
    """
    return text.replace("\uFE0F", "")
