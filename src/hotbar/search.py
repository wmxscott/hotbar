"""hotbar search: the tools in fzf, in the popup that / opens. Enter leaves the chosen tool's opener
on the pane, and the / binding runs it once the popup has closed."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from hotbar import config, theme, toolbar
from hotbar.config import Tool
from hotbar.theme import Mode

MIN_FZF = (0, 59)
LOOK = ("--layout=reverse", "--height=100%", "--border=none", "--margin=0", "--padding=0")
ARGS = (
    "--ansi",
    *LOOK,
    "--no-info",
    "--prompt=> ",
    # A row is the tool's id, then its keycap and icon, then its title, which alone is searched.
    # fzf 0.59 applies --nth after --with-nth, so a hidden id can't be searched.
    "--delimiter=\t",
    "--with-nth=2..",
    "--nth=2..",
    "--tabstop=1",
    "--with-shell=sh -c",
    *(
        arg
        for key, move in (("j", "down"), ("k", "up"))
        for arg in (
            "--bind",
            f'{key}:transform:[ -n "$FZF_QUERY" ] && echo "put({key})" || echo {move}',
        )
    ),
)


def search(path: Path | None, pane: str, client: str) -> int:
    problem = fzf_problem()
    if problem:
        return _say(client, problem)
    try:
        cfg = config.load(path)
    except config.ConfigError as err:
        return _say(client, toolbar.message(err.problems))
    probe = "#{client_theme}\t" + "".join(
        f"#{{!=:{tool.requires},}}" if tool.requires else "1" for tool in cfg.tools
    )
    found = toolbar._tmux(("display-message", "-p", "-c", client, "-t", pane, probe))
    if found.returncode:
        return _say(client, f"hotbar: {found.stderr.strip()}")
    reported, _, shown = found.stdout.removesuffix("\n").partition("\t")
    mode = resolve(cfg.theme, reported)
    tools = {tool.id: tool for tool, flag in zip(cfg.tools, shown, strict=False) if flag == "1"}
    result = subprocess.run(
        ["fzf", *ARGS],
        input="".join(f"{row(tool, mode)}\n" for tool in tools.values()),
        stdout=subprocess.PIPE,
        encoding="utf-8",
        check=False,
    )
    if result.returncode in (1, 130):
        return 0
    if result.returncode:
        return _say(client, f"hotbar: fzf exited with status {result.returncode}")
    tool = tools[result.stdout.partition("\t")[0]]
    opener = toolbar.opener(tool, mode, cfg.theme == "auto")
    toolbar._tmux(("set-option", "-p", "-t", pane, toolbar.PICK, opener))
    return 0


def resolve(setting: str, reported: str) -> Mode:
    """The config's theme, or for auto, the one the client reports, else the detected one."""
    if setting == "auto" and reported in ("light", "dark"):
        return reported
    return theme.resolve(setting)


def row(tool: Tool, mode: Mode) -> str:
    """A tool's line for fzf, drawn as its keycap on the toolbar."""
    colour, base, muted = (
        _rgb(theme.colour(name, mode)) for name in (tool.color, "base", toolbar.MUTED)
    )
    icon, title = (" ".join(text.splitlines()) for text in (tool.icon, tool.title))
    return (
        f"{tool.id}\t\x1b[1;38;2;{base};48;2;{colour}m {tool.key} \x1b[0m "
        f"\x1b[38;2;{colour}m{icon}\x1b[0m\t\x1b[38;2;{muted}m{title}\x1b[0m"
    )


def _rgb(hex_colour: str) -> str:
    return ";".join(str(int(hex_colour[i : i + 2], 16)) for i in (1, 3, 5))


def fzf_problem() -> str | None:
    try:
        out = subprocess.run(
            ["fzf", "--version"],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        out = ""
    words = out.split()
    found = words[0] if words else "none"
    numbers = [int(part) for part in found.split(".")[:2] if part.isdecimal()]
    if len(numbers) == 2 and tuple(numbers) >= MIN_FZF:
        return None
    return f"hotbar: search needs fzf {'.'.join(map(str, MIN_FZF))} or newer; found {found}"


def _say(client: str, text: str) -> int:
    print(text, file=sys.stderr)
    toolbar._tmux(("display-message", "-c", client, "-l", text))
    return 1
