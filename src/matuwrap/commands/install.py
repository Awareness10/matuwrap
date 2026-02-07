"""Install matuwrap shell integration."""

import re
from datetime import datetime
from pathlib import Path
import shutil

from matuwrap.core.theme import console, print_error, print_success, print_warning

COMMAND = {
    "description": "Install shell integration",
    "subcommands": [
        ("bash", "", "Install bash PS1 + fastfetch integration"),
    ],
}

SCRIPT_DIR = Path.home() / ".config" / "matuwrap" / "scripts"
SCRIPT_PATH = SCRIPT_DIR / "matuwrap"
BASHRC = Path.home() / ".bashrc"
SOURCE_LINE = f"source {SCRIPT_PATH}"

BASH_INTEGRATION = r"""# matuwrap shell integration
# Source this from .bashrc:  source ~/.config/matuwrap/scripts/matuwrap

# --- Matugen color loading ------------------------------------------------

reload-colors() {
    export WRP_PS1="$(wrp get_colors ps1 2>/dev/null)"
    export AW_COLOR="$(wrp get_colors 2>/dev/null)"
}

command -v wrp >/dev/null 2>&1 && reload-colors

# --- Git prompt -----------------------------------------------------------

if [ -f /usr/share/git/completion/git-prompt.sh ]; then
    source /usr/share/git/completion/git-prompt.sh
elif [ -f ~/.git-prompt.sh ]; then
    source ~/.git-prompt.sh
fi

export GIT_PS1_SHOWDIRTYSTATE=1
export GIT_PS1_SHOWSTASHSTATE=1
export GIT_PS1_SHOWUNTRACKEDFILES=1
export GIT_PS1_SHOWUPSTREAM="auto"

# --- Venv prompt ----------------------------------------------------------

export VIRTUAL_ENV_DISABLE_PROMPT=1

__matuwrap_venv() {
    [ -n "$VIRTUAL_ENV" ] && echo "(${VIRTUAL_ENV_PROMPT:-.venv}) "
}

# --- PS1 ------------------------------------------------------------------

case "$TERM" in
    xterm-color|*-256color|xterm-kitty)
        _MW_RED='\[\033[31m\]'
        _MW_BOLD='\[\033[1m\]'
        _MW_NC='\[\033[0m\]'

        if [ -n "$SSH_CLIENT" ] || [ -n "$SSH_TTY" ]; then
            _MW_HOST="${_MW_BOLD}\[\033[38;5;214m\]\u@\h:\w${_MW_NC}"
        else
            _MW_HOST="${_MW_BOLD}${WRP_PS1}${_MW_NC}"
        fi

        PS1="\$(__matuwrap_venv)${_MW_HOST}${_MW_RED}\$(__git_ps1 \" (%s)\")${_MW_NC}\n\$ "

        # Terminal title
        case "$TERM" in
            xterm*|rxvt*) PS1="\[\e]0;\u@\h: \w\a\]$PS1" ;;
        esac
        ;;
esac

# --- Fastfetch override ---------------------------------------------------

ff() {
    fastfetch \
        --color "$AW_COLOR" \
        --logo arch \
        --logo-color-1 "$AW_COLOR" \
        --logo-color-2 "$AW_COLOR"
}
"""


def _backup(path: Path) -> Path | None:
    """Backup an existing file with a timestamp suffix. Returns backup path.

    Only the most recent backup is kept; older ones are removed.
    """
    if not path.exists():
        return None

    # Remove previous backups for this file
    for old in sorted(path.parent.glob(f"{path.name}.*.bak")):
        old.unlink()

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = path.with_name(f"{path.name}.{stamp}.bak")
    shutil.copy2(path, backup)
    return backup


# Patterns for lines that the matuwrap shell script now handles.
_PROMPT_RE = re.compile("|".join([
    r"git-prompt\.sh",
    r"GIT_PS1_",
    r"VIRTUAL_ENV_DISABLE_PROMPT",
    r"__venv_prompt",
    r"reload-colors",
    r"WRP_PS1",
    r'"?\$color_prompt"?',
    r"unset color_prompt",
    r"PS1=",
    r"\\e\]0;",
]))

# Lines that close a block but aren't content (fi, esac, ;;, }, blank).
_STRUCTURAL = frozenset({"", "fi", "esac", ";;", "}"})


def _find_prompt_region(lines: list[str]) -> tuple[int, int] | None:
    """Return (start, end) indices of the prompt-setup region to replace."""
    hits = [i for i, l in enumerate(lines) if _PROMPT_RE.search(l)]
    if not hits:
        return None
    start, end = hits[0], hits[-1]

    # Expand backwards over leading comments / blanks
    while start > 0 and (
        lines[start - 1].strip() == "" or lines[start - 1].strip().startswith("#")
    ):
        start -= 1

    # Expand forwards over structural closing lines (fi, esac, ;;) and blanks
    while end + 1 < len(lines) and lines[end + 1].strip() in _STRUCTURAL:
        end += 1

    return start, end


def _find_insert_point(lines: list[str]) -> int:
    """Fallback insertion point when no prompt region is detected."""
    # After the TERM / color_prompt case block
    for i, line in enumerate(lines):
        if "color_prompt=yes" in line:
            for j in range(i, len(lines)):
                if lines[j].strip() == "esac":
                    return j + 1

    # After non-interactive guard
    for i, line in enumerate(lines):
        if "*) return" in line:
            for j in range(i, len(lines)):
                if lines[j].strip() == "esac":
                    return j + 1

    return len(lines)


def _patch_bashrc() -> bool:
    """Insert source line into .bashrc, replacing the old prompt setup region."""
    if not BASHRC.exists():
        return False

    text = BASHRC.read_text()
    has_source = SOURCE_LINE in text
    has_old = bool(_PROMPT_RE.search(text))

    # Already sourced and no stale prompt lines → nothing to do
    if has_source and not has_old:
        return False

    backup = _backup(BASHRC)
    if backup:
        print_warning(f"Backed up  {backup}")

    lines = text.splitlines()

    # Strip any existing matuwrap source / comment lines (will re-add in position)
    lines = [
        l for l in lines
        if SOURCE_LINE not in l and l.strip() != "# matuwrap shell integration"
    ]

    source_block = ["", "# matuwrap shell integration", SOURCE_LINE, ""]

    region = _find_prompt_region(lines)
    if region:
        start, end = region
        lines[start : end + 1] = source_block
        console.print(
            f"[muted]Replaced prompt region (lines {start + 1}–{end + 1})[/muted]"
        )
    else:
        pos = _find_insert_point(lines)
        lines[pos:pos] = source_block

    BASHRC.write_text("\n".join(lines) + "\n")
    print_success(f"Patched    {BASHRC}")
    return True


def _install_bash() -> int:
    """Write shell integration script and patch .bashrc."""
    SCRIPT_DIR.mkdir(parents=True, exist_ok=True)

    backup = _backup(SCRIPT_PATH)
    if backup:
        print_warning(f"Backed up  {backup}")

    SCRIPT_PATH.write_text(BASH_INTEGRATION.lstrip("\n"))
    SCRIPT_PATH.chmod(0o644)
    print_success(f"Installed  {SCRIPT_PATH}")

    if not _patch_bashrc():
        console.print(f"[muted].bashrc already sources matuwrap[/muted]")

    console.print()
    console.print("[muted]Reload:  source ~/.bashrc[/muted]")
    return 0


def run(*args: str) -> int:
    if not args or args[0] == "bash":
        return _install_bash()

    print_error(f"Unknown target: {args[0]}")
    return 1
