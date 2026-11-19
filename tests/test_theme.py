"""The palette, and which half of it a theme setting picks."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

from hotbar import theme
from hotbar.theme import ACCENTS, LATTE, MACCHIATO

NAMES = [
    *("rosewater", "flamingo", "pink", "mauve", "red", "maroon", "peach", "yellow"),
    *("green", "teal", "sky", "sapphire", "blue", "lavender"),
    *("text", "subtext1", "subtext0", "overlay2", "overlay1", "overlay0"),
    *("surface2", "surface1", "surface0", "base", "mantle", "crust"),
]


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A home with no theme-monitor file, on Linux, with nothing on PATH."""
    home = tmp_path / "home"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    monkeypatch.setenv("PATH", str(bin_dir))
    monkeypatch.setattr(sys, "platform", "linux")
    return home


def trigger(base: Path, value: str) -> None:
    path = base / "theme-monitor" / "theme-change.trigger"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def macos(monkeypatch: pytest.MonkeyPatch, home: Path, stdout: str, status: int) -> None:
    monkeypatch.setattr(sys, "platform", "darwin")
    defaults = home.parent / "bin" / "defaults"
    defaults.write_text(f"#!/bin/sh\nprintf '{stdout}'\nexit {status}\n")
    defaults.chmod(0o755)


def test_the_palettes_are_the_whole_of_catppuccin():
    assert list(LATTE) == NAMES
    assert list(MACCHIATO) == NAMES
    assert all(
        re.fullmatch(r"#[0-9a-f]{6}", value) for value in [*LATTE.values(), *MACCHIATO.values()]
    )


def test_the_accents_are_the_names_a_tool_may_use():
    assert list(ACCENTS) == NAMES[:14]


@pytest.mark.parametrize(
    ("name", "mode", "value"),
    [
        ("green", "light", "#40a02b"),
        ("green", "dark", "#a6da95"),
        ("mauve", "light", "#8839ef"),
        ("mauve", "dark", "#c6a0f6"),
        ("base", "light", "#eff1f5"),
        ("base", "dark", "#24273a"),
        ("overlay1", "light", "#8c8fa1"),
        ("overlay1", "dark", "#8087a2"),
    ],
)
def test_colour(name, mode, value):
    assert theme.colour(name, mode) == value


def test_a_set_theme_is_fixed(home):
    trigger(home / ".local/share", "dark")
    assert theme.resolve("light") == "light"
    trigger(home / ".local/share", "light")
    assert theme.resolve("dark") == "dark"


@pytest.mark.parametrize("mode", ["light", "dark"])
def test_auto_follows_theme_monitor(home, mode):
    trigger(home / ".local/share", f" {mode.upper()}\n")
    assert theme.resolve("auto") == mode


def test_theme_monitor_under_xdg_data_home(home, monkeypatch, tmp_path):
    trigger(home / ".local/share", "light")
    trigger(tmp_path / "data", "dark")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    assert theme.resolve("auto") == "dark"


def test_a_relative_xdg_data_home_is_ignored(home, monkeypatch):
    trigger(home / ".local/share", "dark")
    monkeypatch.setenv("XDG_DATA_HOME", "data")
    assert theme.resolve("auto") == "dark"


@pytest.mark.parametrize(("stdout", "status", "mode"), [("Dark\\n", 0, "dark"), ("", 1, "light")])
def test_auto_asks_macos(home, monkeypatch, stdout, status, mode):
    macos(monkeypatch, home, stdout, status)
    assert theme.resolve("auto") == mode


def test_an_unknown_trigger_falls_through_to_macos(home, monkeypatch):
    trigger(home / ".local/share", "sepia")
    macos(monkeypatch, home, "Dark\\n", 0)
    assert theme.resolve("auto") == "dark"


def test_macos_without_defaults_is_light(home, monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    assert theme.resolve("auto") == "light"


def test_elsewhere_with_nothing_to_go_on_is_light(home):
    assert theme.resolve("auto") == "light"
