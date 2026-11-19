"""Command-line interface."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from hotbar import __version__, config


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
    check.add_argument(
        "--config",
        type=Path,
        metavar="PATH",
        help="the config file (default: $XDG_CONFIG_HOME/hotbar/config.toml)",
    )
    args = parser.parse_args(argv)
    if args.command == "check":
        return _check(args.config)
    parser.print_help()
    return 0


def _check(path: Path | None) -> int:
    try:
        loaded = config.load(path)
    except config.ConfigError as err:
        for problem in err.problems:
            print(problem, file=sys.stderr)
        return 1
    print("ok")
    for tool in loaded.tools:
        print(f"  {tool.key}  {tool.title}")
    return 0
