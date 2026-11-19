"""hotbar init: a key table on prefix t whose letters open tools in popups and whose / searches
them, and a status line that draws the toolbar while it's on."""

from __future__ import annotations

import dataclasses
import os
import re
import subprocess
import sys
import unicodedata
from collections.abc import Callable, Iterable, Sequence
from pathlib import Path

from hotbar import config, theme
from hotbar.config import Config, Problem, Size, Tool
from hotbar.theme import Mode

TABLE = "hotbar"
OPEN = ("switch-client", "-T", TABLE)
LEAVE = ("switch-client", "-T", "root")
WRAP = "#{?#{==:#{client_key_table},hotbar},#{E:@hotbar-toolbar},#{E:@hotbar-status-format}}"
BOLT = "\uf0e7"
MUTED = "overlay1"
PICK = "@hotbar-pick"
# The popup's border, fzf's pointer and scrollbar, and a cell for an icon drawn wide; then the
# border, and fzf's prompt and the line under it.
SEARCH_CHROME = (6, 4)
SEARCH_MIN_WIDTH = 24
LITERAL_RE = re.compile(r"(#+)(\[?)|[,}%]")
ESCAPES = {",": "#,", "}": "#}", "%": "#{a:37}"}
HASHES_RE = re.compile(r"(#+)(\[?)")
QUOTES = str.maketrans({"\\": "\\\\", '"': '\\"', "$": "\\$", "~": "\\~", "\n": "\\n", "\r": "\\r"})
LAUNCH = (
    'c=$1; shift; command -v "$1" >/dev/null 2>&1 && exec "$@"; '
    'tmux display-message -c "$c" -l "hotbar: can\'t start $1: not found"'
)

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


def quoted(text: str) -> str:
    """`text` as one argument in tmux's command language."""
    return '"' + text.translate(QUOTES) + '"'


def unexpanded(text: str) -> str:
    """`text` as a format that one expansion turns back into it. A run of # before [ is left
    alone by the expander, so it stays as it is."""
    return HASHES_RE.sub(lambda match: match[0] if match[2] else match[1] * 2, text)


def toolbar(cfg: Config, mode: Mode) -> str:
    """The toolbar in `mode`. For "auto" it follows the theme the client reports, and `mode`, the
    detected one, is for a client that hasn't."""
    return _themed(cfg.theme == "auto", mode, lambda mode: _row(cfg.tools, mode))


def _themed(auto: bool, mode: Mode, render: Callable[[Mode], str]) -> str:
    if not auto:
        return render(mode)
    other: Mode = "light" if mode == "dark" else "dark"
    return f"#{{?#{{==:#{{client_theme}},{other}}},{render(other)},{render(mode)}}}"


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


def opener(tool: Tool, mode: Mode, auto: bool) -> str:
    """What a tool's letter runs: leave the mode, then, if its `requires` expands to something in
    the pane, expand its `env` there and open its popup."""
    run = " ; ".join(
        (
            *(f"set-option -p -F {_env(name)} {quoted(value)}" for name, value in tool.env),
            f"run-shell -C {quoted(popup(tool, mode, auto))}",
        )
    )
    if tool.requires:
        run = f"if-shell -F {quoted(f'#{{!=:{tool.requires},}}')} {{ {run} }}"
    return f"{' '.join(LEAVE)} ; {run}"


def popup(tool: Tool, mode: Mode, auto: bool) -> str:
    """The popup, as a format for run-shell -C to expand against the pane and run. display-popup
    expands neither its -e values nor its -S style, so run-shell fills in the border colour for
    the client's theme, and each `env` value quoted by q/a, which quotes only a variable, so
    opener first expands it into a pane option.

    tmux runs a command of more than one argument without a shell, so `command` reaches /bin/sh
    as written, which runs it, or says in a tmux message that it isn't on PATH. Either way the
    popup closes when it exits."""
    unset = "".join(f"set-option -p -u {_env(name)} ; " for name, _ in tool.env)
    return unset + " ".join(
        (
            _frame(tool.color, f"{tool.icon} {tool.title}", mode, auto),
            f"-w {_argument(str(tool.width))} -h {_argument(str(tool.height))}",
            f"-d {_argument('#{pane_current_path}')}",
            *(f"-e {name}=#{{q/a:{_env(name)}}}" for name, _ in tool.env),
            f"/bin/sh -c {_argument(LAUNCH)} hotbar #{{q/a:client_name}}",
            *map(_argument, tool.command),
        )
    )


def searcher(cfg: Config, mode: Mode, path: Path | None = None) -> str:
    """What / runs: leave the mode, then search the tools in a popup. tmux runs the rest of a
    binding only once its popup closes, so the search leaves the chosen tool's opener on the pane,
    and this binding runs it after: on the pane and client a letter would use, and with the
    search's popup gone, since tmux shows one popup at a time."""
    width, height = search_size(cfg)
    argv = (*command(), "search", *(("--config", str(path)) if path else ()))
    find = " ".join(
        (
            _frame(MUTED, f"{BOLT} tools", mode, cfg.theme == "auto"),
            f"-w {_within(width, 'client_width')} -h {_within(height, 'client_height')}",
            *map(_argument, argv),
            "--pane #{pane_id} --client #{q/a:client_name}",
        )
    )
    run = f"run-shell -C {quoted(f'set-option -p -u {PICK} ; #{{{PICK}}}')}"
    return " ; ".join(
        (
            " ".join(LEAVE),
            f"set-option -p -u {PICK}",
            f"run-shell -C {quoted(find)}",
            f"if-shell -F {quoted(f'#{{{PICK}}}')} {{ {run} }}",
        )
    )


def search_size(cfg: Config) -> tuple[Size, Size]:
    """[search]'s size, else one that fits each tool's row, as the search draws it, and fzf."""
    rows = (_cells(f" {tool.key}  {tool.icon} {tool.title}") for tool in cfg.tools)
    width = max(SEARCH_MIN_WIDTH, max(rows, default=0) + SEARCH_CHROME[0])
    return cfg.search.width or width, cfg.search.height or len(cfg.tools) + SEARCH_CHROME[1]


def _within(size: Size, limit: str) -> str:
    """`size` as a format that run-shell -C cuts to the client's `limit`, since tmux opens no
    popup larger than its client."""
    if isinstance(size, str):
        return _argument(size)
    return f"#{{?#{{e|>:{size},#{{{limit}}}}},#{{{limit}}},{size}}}"


def _cells(text: str) -> int:
    return sum(
        0 if unicodedata.combining(c) else 2 if unicodedata.east_asian_width(c) in ("W", "F") else 1
        for c in text
    )


def command() -> tuple[str, ...]:
    """hotbar, for tmux to run later: the script that's running, whose path an upgrade keeps, else
    this Python's module."""
    script = os.path.abspath(sys.argv[0])
    if os.path.basename(script) == "hotbar" and os.access(script, os.X_OK):
        return (script,)
    return (sys.executable, "-m", "hotbar")


def _frame(colour: str, title: str, mode: Mode, auto: bool) -> str:
    border = _themed(auto, mode, lambda mode: unexpanded(theme.colour(colour, mode)))
    return f'display-popup -E -b rounded -S "fg={border}" -T {_argument(literal(title))}'


def _argument(text: str) -> str:
    return unexpanded(quoted(text))


def _env(name: str) -> str:
    return f"@hotbar-env-{name}"


def install(
    cfg: Config,
    key: str,
    mode: Mode,
    current: str,
    saved: str | None,
    stale: str | None = None,
    path: Path | None = None,
) -> list[Command]:
    """The commands that put the toolbar on `key`, given the status-format there now, the one
    an earlier run saved, the earlier run's key if it was another, and the config for / to
    search."""
    original = saved if current == WRAP and saved is not None else current
    leave = ["Escape", key, "Any"]
    auto = cfg.theme == "auto"
    return [
        ("bind-key", "-N", "Open the hotbar", "-T", "prefix", key, *OPEN),
        *([("unbind-key", "-T", "prefix", stale)] if stale else []),
        # unbind -a on a table that doesn't exist ends the command list, silently.
        ("bind-key", "-T", TABLE, "Any", *LEAVE),
        ("unbind-key", "-a", "-T", TABLE),
        *(("bind-key", "-T", TABLE, tool.key, opener(tool, mode, auto)) for tool in cfg.tools),
        ("bind-key", "-T", TABLE, "/", searcher(cfg, mode, path)),
        *(("bind-key", "-T", TABLE, letter, *LEAVE) for letter in leave),
        ("set-option", "-s", "@hotbar-status-format", original),
        ("set-option", "-s", "@hotbar-toolbar", toolbar(cfg, mode)),
        ("set-option", "-s", "@hotbar-key", key),
        ("set-option", "-g", "status-format[0]", WRAP),
    ]


def message(problems: Sequence[Problem]) -> str:
    first = problems[0]
    text = f"hotbar: {dataclasses.replace(first, path=_tilde(first.path))}"
    if len(problems) > 1:
        text += f" (1 of {len(problems)} problems; hotbar check lists them)"
    return text


def _tilde(path: Path) -> Path:
    """`path` with the home folder as ~, so a message tmux cuts to fit keeps its end."""
    try:
        return Path("~", path.relative_to(Path.home()))
    except ValueError:
        return path


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
    path = (path or config.config_path()).absolute()
    result = _tmux(*install(cfg, key, theme.resolve(cfg.theme), current, saved, stale, path))
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
