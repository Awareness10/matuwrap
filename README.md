# matuwrap

Hyprland system utilities with matugen-themed output and native Rust acceleration.

## Install

Requires Rust toolchain and [maturin](https://github.com/PyO3/maturin).

```bash
# Sync dependencies
uv sync

# Build and install
uv run maturin build --release
uv tool install .
```

For development:

```bash
# Sync dependencies
uv sync

# Build and run
uv run maturin develop --release   # Build + install to local .venv
uv run wrp monitors                # Run from .venv
```

## Usage

```bash
wrp
wrp -h                    # Show help

wrp monitors              # Show monitor info
wrp audio                 # Toggle HDMI/Headset
wrp audio show            # Show current sinks
wrp sunshine              # Show status
wrp sunshine start|stop   # Control service
wrp sunshine monitors     # List capture monitors
wrp sunshine monitor DP-1 # Set capture monitor
```

## Performance

Native Rust module (`wrp_native`) provides significant speedups:

| Operation | Before | After | Speedup |
|-----------|--------|-------|---------|
| Matugen colors (cached) | 345ms | 0.02ms | ~15,000x |
| Hyprland IPC | 2.1ms | 0.05ms | ~40x |

- **Color caching**: Matugen results cached to `~/.cache/matuwrap/colors.json` with wallpaper mtime validation
- **Hyprland IPC**: Direct Unix socket communication instead of spawning `hyprctl`

## Adding Commands

Create a file in `src/matuwrap/commands/`:

```python
# src/matuwrap/commands/mycommand.py
"""Short description."""

COMMAND = {
    "description": "What this command does",
    "args": "<arg>",       # optional
    "subcommands": [       # optional
        ("sub", "<arg>", "Subcommand description"),
    ],
}

def run(*args: str) -> int:
    if args and args[0] == "sub":
        return do_sub(args[1])
    return do_default()
```

Auto-discovered. Available immediately as `wrp mycommand`.

## Theme Helpers

Import from `matuwrap.core.theme`:

| Function | Purpose |
|----------|---------|
| `print_header(text)` | Section headers |
| `print_kv(label, value)` | Key-value pairs |
| `print_success/error/warning/info(text)` | Status messages |
| `fmt(value, unit="")` | Type-aware formatting |
| `create_table(*columns)` | Styled tables |
| `console` | Rich console instance |

## Architecture

```
src/matuwrap/
├── cli.py              # Entry point, command discovery
├── commands/           # Auto-discovered command modules
│   ├── audio.py        # PipeWire sink management
│   ├── monitors.py     # Hyprland monitor info
│   └── sunshine.py     # Sunshine streaming control
└── core/
    ├── colors.py       # Matugen color extraction (cached)
    ├── hyprland.py     # Hyprland IPC (native socket)
    ├── theme.py        # Rich console theming
    └── ...

rust/
├── Cargo.toml
└── src/lib.rs          # PyO3 native module
```
