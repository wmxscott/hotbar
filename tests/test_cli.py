"""The command-line contract, through the installed console script."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from hotbar import __version__

SCRIPT = os.path.join(os.path.dirname(sys.executable), "hotbar")
COMMANDS = [(SCRIPT,), (sys.executable, "-m", "hotbar")]
EXAMPLE = Path(__file__).resolve().parent.parent / "examples" / "config.toml"

LAZYGIT = """\
[[tools]]
id = "lazygit"
key = "g"
title = "lazygit"
command = ["lazygit"]
"""


def run(*args: str, command: tuple[str, ...] = (SCRIPT,), env: dict[str, str] | None = None):
    return subprocess.run(
        [*command, *args],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
    )


@pytest.mark.parametrize("command", COMMANDS)
@pytest.mark.parametrize("flag", ["--version", "-V"])
def test_version(command, flag):
    result = run(flag, command=command)
    assert (result.returncode, result.stdout, result.stderr) == (0, f"hotbar {__version__}\n", "")


@pytest.mark.parametrize("command", COMMANDS)
@pytest.mark.parametrize("flag", ["--help", "-h"])
def test_help(command, flag):
    result = run(flag, command=command)
    assert (result.returncode, result.stderr) == (0, "")
    assert result.stdout.startswith("usage: hotbar")
    assert "--version" in result.stdout


def test_no_arguments_prints_the_help():
    result = run()
    assert (result.returncode, result.stderr) == (0, "")
    assert result.stdout == run("--help").stdout


def test_an_unknown_argument_is_a_usage_error():
    result = run("--bogus")
    assert (result.returncode, result.stdout) == (2, "")
    assert result.stderr.startswith("usage: hotbar")


def test_help_lists_check():
    assert "check" in run("--help").stdout
    result = run("check", "--help")
    assert (result.returncode, result.stderr) == (0, "")
    assert "--config PATH" in result.stdout


def test_check_lists_the_example_tools():
    result = run("check", "--config", str(EXAMPLE))
    assert (result.returncode, result.stderr) == (0, "")
    assert result.stdout == "ok\n  g  lazygit\n  d  gh dash\n  n  nvim\n  b  btop\n"


def test_check_reads_the_config_under_xdg_config_home(tmp_path):
    (tmp_path / "hotbar").mkdir()
    (tmp_path / "hotbar" / "config.toml").write_text(LAZYGIT, encoding="utf-8")
    result = run("check", env={**os.environ, "XDG_CONFIG_HOME": str(tmp_path)})
    assert (result.returncode, result.stdout, result.stderr) == (0, "ok\n  g  lazygit\n", "")


def test_check_reports_a_duplicate_key_with_its_line(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text(LAZYGIT + LAZYGIT.replace("lazygit", "tig"), encoding="utf-8")
    result = run("check", "--config", str(path))
    assert (result.returncode, result.stdout) == (1, "")
    assert result.stderr == f"{path}:8: tools 'lazygit' and 'tig' both use key 'g'\n"


def test_check_reports_every_problem(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text('theme = "blue"\n' + LAZYGIT + "slot = 1\n", encoding="utf-8")
    result = run("check", "--config", str(path))
    assert (result.returncode, result.stdout) == (1, "")
    assert result.stderr == (
        f'{path}:1: theme must be "auto", "dark" or "light"\n'
        f"{path}:7: tool 'lazygit': unknown setting 'slot'\n"
    )


def test_check_without_a_config(tmp_path):
    path = tmp_path / "missing.toml"
    result = run("check", "--config", str(path))
    assert (result.returncode, result.stdout, result.stderr) == (
        1,
        "",
        f"{path}: no config file yet\n",
    )


CLASH = "is the toolbar's own key; choose another, or pass hotbar another --key"


def test_help_lists_init():
    assert "init" in run("--help").stdout
    result = run("init", "--help")
    assert (result.returncode, result.stderr) == (0, "")
    assert "--config PATH" in result.stdout
    assert "--key KEY" in result.stdout


def test_check_reports_a_tool_on_the_toolbar_key(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text(LAZYGIT.replace('"g"', '"t"'), encoding="utf-8")
    result = run("check", "--config", str(path))
    assert (result.returncode, result.stdout) == (1, "")
    assert result.stderr == f"{path}:3: tool 'lazygit': key 't' {CLASH}\n"


def test_check_takes_the_toolbar_key(tmp_path):
    result = run("check", "--config", str(EXAMPLE), "--key", "g")
    assert (result.returncode, result.stdout) == (1, "")
    assert result.stderr == f"{EXAMPLE}:13: tool 'lazygit': key 'g' {CLASH}\n"
    assert run("check", "--config", str(EXAMPLE), "--key", "t").returncode == 0


def test_init_outside_tmux_says_how_to_run_it(tmp_path):
    env = {name: value for name, value in os.environ.items() if name != "TMUX"}
    result = run("init", "--config", str(EXAMPLE), env=env)
    assert (result.returncode, result.stdout) == (1, "")
    assert (
        result.stderr == 'hotbar init runs inside tmux, from tmux.conf: run-shell "hotbar init"\n'
    )


def test_help_lists_search():
    assert "search" in run("--help").stdout
    result = run("search", "--help")
    assert (result.returncode, result.stderr) == (0, "")
    for option in ("--config PATH", "--pane PANE", "--client CLIENT"):
        assert option in result.stdout


def test_search_needs_the_pane_and_the_client():
    result = run("search")
    assert (result.returncode, result.stdout) == (2, "")
    assert "--pane" in result.stderr
