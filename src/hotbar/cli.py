"""Command-line interface."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from hotbar import __version__, config, search, toolbar


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="hotbar",
        description="A keyboard toolbar for tmux, opening the tools you reach for in popups.",
    )
    parser.add_argument("-V", "--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", title="commands")
    check = commands.add_parser(
        "check",
        help="check the config and list its tools",
        description="Check the config: print ok and its tools, or each problem with its line.",
    )
    init = commands.add_parser(
        "init",
        help="put the toolbar on prefix t; run it from tmux.conf",
        description="Bind prefix KEY to the toolbar, and draw it on the status line while it's "
        'on. Run it from tmux.conf: run-shell "hotbar init". A bad config changes nothing, and '
        "tmux shows its first problem.",
    )
    find = commands.add_parser(
        "search",
        help="search the tools in fzf; the toolbar's / runs it",
        description="Search the tools in fzf, in the popup the toolbar's / opens. Enter leaves the "
        "chosen tool's tmux commands in PANE's @hotbar-pick, which / runs once the popup closes.",
    )
    find.add_argument(
        "--pane", required=True, help="the pane the toolbar was opened from, as its #{pane_id}"
    )
    find.add_argument("--client", required=True, help="the client that opened it")
    for command in (check, init, find):
        command.add_argument(
            "--config",
            type=Path,
            metavar="PATH",
            help="the config file (default: $XDG_CONFIG_HOME/hotbar/config.toml)",
        )
    for command in (check, init):
        command.add_argument(
            "--key",
            default="t",
            metavar="KEY",
            help="the key after the prefix that opens the toolbar and closes it, which no tool "
            "may use (default: t)",
        )
    args = parser.parse_args(argv)
    if args.command == "check":
        return _check(args.config, args.key)
    if args.command == "init":
        return toolbar.init(args.config, args.key)
    if args.command == "search":
        return search.search(args.config, args.pane, args.client)
    parser.print_help()
    return 0


def _check(path: Path | None, key: str) -> int:
    try:
        loaded = config.load(path, toolbar_key=key)
    except config.ConfigError as err:
        for problem in err.problems:
            print(problem, file=sys.stderr)
        return 1
    print("ok")
    for tool in loaded.tools:
        print(f"  {tool.key}  {tool.title}")
    return 0
