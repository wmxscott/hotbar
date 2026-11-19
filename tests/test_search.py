"""The search's rows, its fzf options and its fzf check, without tmux."""

from __future__ import annotations

import dataclasses
import os
import subprocess

import pytest

from hotbar import search, theme
from hotbar.config import Tool

LAZYGIT = Tool(
    id="lazygit", key="g", title="lazygit", command=("lazygit",), icon="", color="green"
)
GH_DASH = Tool(id="gh-dash", key="d", title="gh dash", command=("gh", "dash"), color="blue")
NVIM = Tool(id="editor", key="x", title="nvim", command=("nvim",), color="teal")


def test_a_row_is_the_tools_id_then_its_keycap_icon_and_name_as_the_toolbar_draws_them():
    assert search.row(LAZYGIT, "dark") == (
        "lazygit\t\x1b[1;38;2;36;39;58;48;2;166;218;149m g \x1b[0m "
        "\x1b[38;2;166;218;149m\x1b[0m\t\x1b[38;2;128;135;162mlazygit\x1b[0m"
    )


def test_a_light_row():
    assert search.row(LAZYGIT, "light") == (
        "lazygit\t\x1b[1;38;2;239;241;245;48;2;64;160;43m g \x1b[0m "
        "\x1b[38;2;64;160;43m\x1b[0m\t\x1b[38;2;140;143;161mlazygit\x1b[0m"
    )


def test_a_row_is_one_line():
    tool = dataclasses.replace(LAZYGIT, icon="a\nb", title="one\ntwo\n")
    assert "\n" not in search.row(tool, "dark")
    assert "a b" in search.row(tool, "dark")
    assert "one two" in search.row(tool, "dark")


def fzf_filter(query: str, *tools: Tool) -> list[str]:
    result = subprocess.run(
        ["fzf", *search.ARGS, f"--filter={query}"],
        input="".join(search.row(tool, "dark") + "\n" for tool in tools),
        capture_output=True,
        text=True,
        timeout=10,
        env={name: value for name, value in os.environ.items() if not name.startswith("FZF_")},
    )
    return [line.partition("\t")[0] for line in result.stdout.splitlines()]


needs_fzf = pytest.mark.skipif(search.fzf_problem() is not None, reason="needs fzf 0.59 or later")


@needs_fzf
@pytest.mark.parametrize(
    ("query", "found"),
    [("dash", ["gh-dash"]), ("lzgt", ["lazygit"]), ("x", []), ("editor", []), ("gh-", [])],
)
def test_typing_searches_the_titles(query, found):
    assert fzf_filter(query, LAZYGIT, GH_DASH, NVIM) == found


def test_fzf_is_drawn_as_switchboards_picker_with_j_and_k_until_typing():
    assert search.ARGS[:9] == (
        "--ansi",
        "--layout=reverse",
        "--height=100%",
        "--border=none",
        "--margin=0",
        "--padding=0",
        "--no-info",
        "--prompt=> ",
        "--delimiter=\t",
    )
    assert "--with-shell=sh -c" in search.ARGS
    assert 'j:transform:[ -n "$FZF_QUERY" ] && echo "put(j)" || echo down' in search.ARGS
    assert 'k:transform:[ -n "$FZF_QUERY" ] && echo "put(k)" || echo up' in search.ARGS


def fake_fzf(monkeypatch, tmp_path, version: str | None) -> None:
    if version is not None:
        script = tmp_path / "fzf"
        script.write_text(f"#!/bin/sh\necho '{version}'\n", encoding="utf-8")
        script.chmod(0o755)
    monkeypatch.setenv("PATH", str(tmp_path))


@pytest.mark.parametrize("version", ["0.59.0 (bbe1721)", "0.75.0 (Homebrew)", "0.100.1", "1.0"])
def test_fzf_0_59_or_newer_will_do(monkeypatch, tmp_path, version):
    fake_fzf(monkeypatch, tmp_path, version)
    assert search.fzf_problem() is None


@pytest.mark.parametrize(
    ("version", "found"), [("0.58.1 (abc)", "0.58.1"), ("0.9.0", "0.9.0"), ("", "none")]
)
def test_an_older_fzf_is_a_problem(monkeypatch, tmp_path, version, found):
    fake_fzf(monkeypatch, tmp_path, version)
    assert search.fzf_problem() == f"hotbar: search needs fzf 0.59 or newer; found {found}"


def test_no_fzf_is_a_problem(monkeypatch, tmp_path):
    fake_fzf(monkeypatch, tmp_path, None)
    assert search.fzf_problem() == "hotbar: search needs fzf 0.59 or newer; found none"


@pytest.mark.parametrize(
    ("setting", "reported", "mode"),
    [("auto", "light", "light"), ("auto", "dark", "dark"), ("dark", "light", "dark")],
)
def test_the_colours_follow_the_config_then_the_client(setting, reported, mode):
    assert search.resolve(setting, reported) == mode


def test_the_colours_are_detected_when_the_client_reports_none(monkeypatch):
    monkeypatch.setattr(theme, "detect", lambda: "light")
    assert search.resolve("auto", "") == "light"
