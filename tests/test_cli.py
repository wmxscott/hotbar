"""The command-line contract, through the installed console script."""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

from hotbar import __version__

SCRIPT = os.path.join(os.path.dirname(sys.executable), "hotbar")
COMMANDS = [(SCRIPT,), (sys.executable, "-m", "hotbar")]


def run(*args: str, command: tuple[str, ...] = (SCRIPT,)):
    return subprocess.run(
        [*command, *args],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=30,
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
