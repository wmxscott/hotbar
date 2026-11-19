"""Catppuccin's colours: Latte when the terminal is light, Macchiato when it's dark."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Literal

Mode = Literal["light", "dark"]
ACCENTS = (
    *("rosewater", "flamingo", "pink", "mauve", "red", "maroon", "peach", "yellow"),
    *("green", "teal", "sky", "sapphire", "blue", "lavender"),
)

LATTE = {
    "rosewater": "#dc8a78",
    "flamingo": "#dd7878",
    "pink": "#ea76cb",
    "mauve": "#8839ef",
    "red": "#d20f39",
    "maroon": "#e64553",
    "peach": "#fe640b",
    "yellow": "#df8e1d",
    "green": "#40a02b",
    "teal": "#179299",
    "sky": "#04a5e5",
    "sapphire": "#209fb5",
    "blue": "#1e66f5",
    "lavender": "#7287fd",
    "text": "#4c4f69",
    "subtext1": "#5c5f77",
    "subtext0": "#6c6f85",
    "overlay2": "#7c7f93",
    "overlay1": "#8c8fa1",
    "overlay0": "#9ca0b0",
    "surface2": "#acb0be",
    "surface1": "#bcc0cc",
    "surface0": "#ccd0da",
    "base": "#eff1f5",
    "mantle": "#e6e9ef",
    "crust": "#dce0e8",
}
MACCHIATO = {
    "rosewater": "#f4dbd6",
    "flamingo": "#f0c6c6",
    "pink": "#f5bde6",
    "mauve": "#c6a0f6",
    "red": "#ed8796",
    "maroon": "#ee99a0",
    "peach": "#f5a97f",
    "yellow": "#eed49f",
    "green": "#a6da95",
    "teal": "#8bd5ca",
    "sky": "#91d7e3",
    "sapphire": "#7dc4e4",
    "blue": "#8aadf4",
    "lavender": "#b7bdf8",
    "text": "#cad3f5",
    "subtext1": "#b8c0e0",
    "subtext0": "#a5adcb",
    "overlay2": "#939ab7",
    "overlay1": "#8087a2",
    "overlay0": "#6e738d",
    "surface2": "#5b6078",
    "surface1": "#494d64",
    "surface0": "#363a4f",
    "base": "#24273a",
    "mantle": "#1e2030",
    "crust": "#181926",
}
PALETTES: dict[Mode, dict[str, str]] = {"light": LATTE, "dark": MACCHIATO}
TRIGGER = ("theme-monitor", "theme-change.trigger")


def colour(name: str, mode: Mode) -> str:
    """The hex value of a palette name, such as a tool's `color`, in `mode`."""
    return PALETTES[mode][name]


def resolve(theme: str) -> Mode:
    """The mode for a config's `theme`: as set, or detected for `auto`."""
    if theme in ("light", "dark"):
        return theme
    return detect()


def detect() -> Mode:
    """theme-monitor's trigger file, else macOS's appearance, else light, as switchboard does."""
    data = os.environ.get("XDG_DATA_HOME", "")
    base = Path(data) if os.path.isabs(data) else Path.home() / ".local" / "share"
    try:
        found = base.joinpath(*TRIGGER).read_text(encoding="utf-8").strip().lower()
    except (OSError, UnicodeDecodeError):
        found = ""
    if found in ("light", "dark"):
        return found
    if sys.platform != "darwin":
        return "light"
    try:
        result = subprocess.run(
            ["defaults", "read", "-g", "AppleInterfaceStyle"],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return "light"
    return "dark" if result.stdout.strip() == "Dark" else "light"
