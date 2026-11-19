"""Command-line interface."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from hotbar import __version__


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="hotbar",
        description="A keyboard toolbar for tmux, opening the tools you reach for in popups.",
    )
    parser.add_argument("-V", "--version", action="version", version=f"%(prog)s {__version__}")
    parser.parse_args(argv)
    parser.print_help()
    return 0
