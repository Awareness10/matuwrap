"""CLI entry point for wrappers."""

import argparse
import importlib
import pkgutil
import sys

from wrappers import commands
from wrappers.core.theme import console, print_error


def _discover_commands() -> dict[str, dict]:
    """Discover all commands from the commands package."""
    discovered = {}
    for module_info in pkgutil.iter_modules(commands.__path__):
        if module_info.name.startswith("_"):
            continue
        module = importlib.import_module(f"wrappers.commands.{module_info.name}")
        if hasattr(module, "COMMAND"):
            discovered[module_info.name] = module.COMMAND
    return discovered


def _print_help(cmds: dict[str, dict]) -> None:
    """Print modern styled help."""
    console.print("[title]wrp[/title] [muted]─[/muted] Hyprland system utilities\n")
    console.print("[label]Usage:[/label]  wrp [value]<command>[/value] [muted][args][/muted]\n")
    console.print("[label]Commands:[/label]")

    col_width = 18
    for name, meta in cmds.items():
        args = meta.get("args", "")
        cmd_text = f"{name} {args}".strip()
        padding = " " * max(1, col_width - len(cmd_text))
        arg_part = f" [muted]{args}[/muted]" if args else ""
        console.print(f"  [value]{name}[/value]{arg_part}{padding}{meta['description']}")

        if meta.get("subcommands"):
            subs = [s[0] for s in meta["subcommands"]]
            console.print(f"{' ' * (col_width + 2)}[muted]└ {', '.join(subs)}[/muted]")

    console.print("\n[label]Options:[/label]")
    console.print("  [value]-h[/value], [value]--help[/value]      Show this help message")


class _StyledParser(argparse.ArgumentParser):
    """ArgumentParser with styled output."""

    def __init__(self, cmds: dict[str, dict], *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._cmds = cmds

    def error(self, message: str) -> None:
        print_error(message)
        console.print("Run [value]wrp --help[/value] for usage")
        sys.exit(1)

    def print_help(self, file=None) -> None:  # noqa: ARG002
        _print_help(self._cmds)


def main() -> int:
    """Main entry point."""
    cmds = _discover_commands()

    parser = _StyledParser(cmds, prog="wrp", add_help=False)
    parser.add_argument("-h", "--help", action="store_true")
    parser.add_argument("command", nargs="?", choices=list(cmds.keys()))
    parser.add_argument("args", nargs="*")

    args = parser.parse_args()

    if args.help or not args.command:
        parser.print_help()
        return 0

    module = importlib.import_module(f"wrappers.commands.{args.command}")
    return module.run(*args.args)


if __name__ == "__main__":
    sys.exit(main())
