"""hotbar init: a key table on prefix t, and a status line that draws the toolbar while it's on."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path

from hotbar import config, theme
from hotbar.config import Config, Problem, Tool
from hotbar.theme import Mode

TABLE = "hotbar"
OPEN = ("switch-client", "-T", TABLE)
LEAVE = ("switch-client", "-T", "root")
WRAP = "#{?#{==:#{client_key_table},hotbar},#{E:@hotbar-toolbar},#{E:@hotbar-status-format}}"
BOLT = "\uf0e7"
MUTED = "overlay1"
LITERAL_RE = re.compile(r"(#+)(\[?)|[,}%]")
ESCAPES = {",": "#,", "}": "#}", "%": "#{a:37}"}

Command = tuple[str, ...]


def literal(text: str) -> str:
    """`text` as a format that draws it as written, inside a conditional or not.

    The expander halves a run of #, and the status line halves it again, unless a [ follows, when
    the expander leaves it alone. tmux runs strftime at every level of nesting, so no % survives.
    """

    def escape(match: re.Match[str]) -> str:
        if match[1]:
            return "#" * len(match[1]) * (2 if match[2] else 4) + match[2]
        return ESCAPES[match[0]]

    return LITERAL_RE.sub(escape, text)


def toolbar(cfg: Config, mode: Mode) -> str:
    """The toolbar in `mode`. For "auto" it follows the theme the client reports, and `mode`, the
    detected one, is for a client that hasn't."""
    if cfg.theme != "auto":
        return _row(cfg.tools, mode)
    other: Mode = "light" if mode == "dark" else "dark"
    return (
        f"#{{?#{{==:#{{client_theme}},{other}}},{_row(cfg.tools, other)},{_row(cfg.tools, mode)}}}"
    )


def _row(tools: Iterable[Tool], mode: Mode) -> str:
    muted, base, mauve = (theme.colour(name, mode) for name in (MUTED, "base", "mauve"))
    row = f" #[fg={mauve}#,bold]{BOLT} tools#[default]"
    for tool in tools:
        colour = theme.colour(tool.color, mode)
        keycap = (
            f"  #[bg={colour}#,fg={base}#,bold] {literal(tool.key)} #[default] "
            f"#[fg={colour}]{literal(tool.icon)} #[fg={muted}]{literal(tool.title)}"
        )
        if tool.requires:
            keycap = f"#{{?#{{!=:{tool.requires},}},{keycap},}}"
        row += keycap
    return row + f"#[default]#[align=right]#[fg={muted}]/ search  esc "


def install(
    cfg: Config, key: str, mode: Mode, current: str, saved: str | None, stale: str | None = None
) -> list[Command]:
    """The commands that put the toolbar on `key`, given the status-format there now, the one
    an earlier run saved, and the earlier run's key if it was another."""
    original = saved if current == WRAP and saved is not None else current
    leave = [*(tool.key for tool in cfg.tools), "/", "Escape", key, "Any"]
    return [
        ("bind-key", "-N", "Open the hotbar", "-T", "prefix", key, *OPEN),
        *([("unbind-key", "-T", "prefix", stale)] if stale else []),
        # unbind -a on a table that doesn't exist ends the command list, silently.
        ("bind-key", "-T", TABLE, "Any", *LEAVE),
        ("unbind-key", "-a", "-T", TABLE),
        *(("bind-key", "-T", TABLE, letter, *LEAVE) for letter in leave),
        ("set-option", "-s", "@hotbar-status-format", original),
        ("set-option", "-s", "@hotbar-toolbar", toolbar(cfg, mode)),
        ("set-option", "-s", "@hotbar-key", key),
        ("set-option", "-g", "status-format[0]", WRAP),
    ]


def message(problems: Sequence[Problem]) -> str:
    text = f"hotbar: {problems[0]}"
    if len(problems) > 1:
        text += f" (1 of {len(problems)} problems; hotbar check lists them)"
    return text


def init(path: Path | None, key: str) -> int:
    if not os.environ.get("TMUX"):
        print(
            'hotbar init runs inside tmux, from tmux.conf: run-shell "hotbar init"', file=sys.stderr
        )
        return 1
    try:
        cfg = config.load(path, toolbar_key=key)
    except config.ConfigError as err:
        return _say(message(err.problems))
    current = _option("-g", "status-format[0]") or ""
    saved = _option("-s", "@hotbar-status-format")
    if current == WRAP and saved is None:
        return _say("hotbar: the status-format it wrapped is lost; run tmux set -gu status-format")
    old = _option("-s", "@hotbar-key")
    stale = old if old and old != key and _bound(old) == " ".join(OPEN) else None
    result = _tmux(*install(cfg, key, theme.resolve(cfg.theme), current, saved, stale))
    if result.returncode:
        return _say(f"hotbar: {result.stderr.strip()}")
    return 0


def _option(*args: str) -> str | None:
    output = _tmux(("show-options", "-qv", *args)).stdout
    return output.removesuffix("\n") if output else None


def _bound(key: str) -> str:
    return _tmux(("list-keys", "-T", "prefix", "-F", "#{key_command}", key)).stdout.strip()


def _say(text: str) -> int:
    _tmux(("display-message", "-l", text))
    return 0


def _tmux(*commands: Command) -> subprocess.CompletedProcess[str]:
    """Runs `commands` in one tmux call, which stops at the first that fails. tmux ends a command
    at an argument ending in ;, unless it ends in \\;."""
    argv: list[str] = []
    for command in commands:
        argv += [*(arg[:-1] + "\\;" if arg.endswith(";") else arg for arg in command), ";"]
    return subprocess.run(
        ["tmux", *argv[:-1]],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=10,
    )
