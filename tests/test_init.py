"""hotbar init against a real, throwaway tmux server, with a client attached through a pty."""

from __future__ import annotations

import fcntl
import json
import os
import pty
import re
import shlex
import struct
import subprocess
import sys
import termios
import threading
import time
import uuid
from collections.abc import Callable
from pathlib import Path

import pytest

from hotbar.toolbar import WRAP

SCRIPT = os.path.join(os.path.dirname(sys.executable), "hotbar")
THEME_REPORTS = {"dark": b"\x1b[?997;1n", "light": b"\x1b[?997;2n"}
LEAVES = "switch-client -T root"
OPENS = "switch-client -T root, then a popup"
FOREGROUND_RE = re.compile(rb"\x1b\[38;2;(\d+);(\d+);(\d+)m")
AWKWARD = [
    *("a b", "it's", 'say "hi"', "#{pane_id}", "a;", ";", "$HOME", "~/x", "back\\slash"),
    *("one\ntwo", "%H", "#[fg=red]", "##", "#S", "{a}", "", "é ✓"),
]

TOOLS = """\
theme = "dark"

[[tools]]
id = "lazygit"
key = "g"
title = "lazygit"
command = ["lazygit"]

[[tools]]
id = "gh-dash"
key = "d"
title = "gh dash"
command = ["gh", "dash"]

[[tools]]
id = "prs"
key = "p"
title = "prs"
command = ["prs"]
requires = "#{@x}"
"""


def tmux_version() -> tuple[int, int]:
    try:
        result = subprocess.run(["tmux", "-V"], capture_output=True, text=True, timeout=10)
    except OSError:
        return (0, 0)
    found = re.search(r"(\d+)\.(\d+)", result.stdout)
    return (int(found[1]), int(found[2])) if found else (0, 0)


pytestmark = pytest.mark.skipif(tmux_version() < (3, 8), reason="needs tmux 3.8 or later")


def wait_for(found: Callable[[], object], timeout: float = 5) -> object:
    deadline = time.monotonic() + timeout
    while not (value := found()):
        assert time.monotonic() < deadline, "timed out"
        time.sleep(0.02)
    return value


class Server:
    def __init__(self, tmp_path: Path) -> None:
        self.name = f"hotbar-test-{uuid.uuid4().hex[:12]}"
        self.env = {name: value for name, value in os.environ.items() if name != "TMUX"}
        self.config = tmp_path / "config.toml"
        self("-f", os.devnull, "new-session", "-d", "-s", "main", "-x", "250", "-y", "10", "cat")
        self.socket = Path(self("display-message", "-p", "#{socket_path}").strip())
        self("set-option", "-as", "terminal-features", ",xterm-256color:RGB")

    def run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["tmux", "-L", self.name, *args],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=10,
            env=self.env,
        )

    def __call__(self, *args: str) -> str:
        result = self.run(*args)
        assert result.returncode == 0, result.stderr
        return result.stdout

    def option(self, *args: str) -> str:
        return self("show-options", "-v", *args).removesuffix("\n")

    def keys(self, table: str) -> dict[str, str]:
        result = self.run("list-keys", "-T", table, "-F", "#{key_string}\t#{key_command}")
        return dict(line.split("\t") for line in result.stdout.splitlines())

    def table(self) -> dict[str, str]:
        """The hotbar table, with a binding that leaves the mode and opens a popup as OPENS."""
        opens = re.compile(rf"{LEAVES} \\; .*display-popup")
        return {
            key: OPENS if opens.match(command) else command
            for key, command in self.keys("hotbar").items()
        }

    def pane(self) -> str:
        return self("capture-pane", "-p", "-t", "main").rstrip()

    def init(self, text: str, *args: str) -> subprocess.CompletedProcess[str]:
        self.config.write_text(text, encoding="utf-8")
        pid = self("display-message", "-p", "#{pid}").strip()
        return subprocess.run(
            [SCRIPT, "init", "--config", str(self.config), *args],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=30,
            env={**self.env, "TMUX": f"{self.socket},{pid},0"},
        )


class Client:
    """A terminal attached to the server, which answers tmux's question about its theme."""

    def __init__(self, server: Server, theme: str = "dark") -> None:
        self.server = server
        self.theme = theme
        self.output = bytearray()
        self.fd, tty = pty.openpty()
        fcntl.ioctl(tty, termios.TIOCSWINSZ, struct.pack("HHHH", 10, 250, 0, 0))
        self.process = subprocess.Popen(
            ["tmux", "-L", server.name, "attach"],
            stdin=tty,
            stdout=tty,
            stderr=tty,
            env={**server.env, "TERM": "xterm-256color"},
            start_new_session=True,
        )
        os.close(tty)
        threading.Thread(target=self._read, daemon=True).start()
        self.name = wait_for(lambda: server("list-clients", "-F", "#{client_name}").strip())

    def _read(self) -> None:
        while True:
            try:
                data = os.read(self.fd, 65536)
            except OSError:
                return
            if not data:
                return
            self.output += data
            if b"\x1b[?996n" in data:
                os.write(self.fd, THEME_REPORTS[self.theme])

    def report(self, theme: str) -> None:
        self.theme = theme
        os.write(self.fd, THEME_REPORTS[theme])
        wait_for(lambda: self.format("#{client_theme}") == theme)

    def format(self, text: str) -> str:
        return self.server("display-message", "-p", "-c", self.name, text).removesuffix("\n")

    def status(self) -> str:
        return self.format("#{E:status-format[0]}")

    def press(self, *keys: str) -> None:
        self.server("send-keys", "-K", "-c", self.name, *keys)

    def type(self, text: str) -> None:
        """Types into the terminal. send-keys -K waits for what the key runs, and a popup runs
        until it closes."""
        os.write(self.fd, text.encode())

    def table(self) -> str:
        return self.format("#{client_key_table}")

    def enters(self, table: str) -> bool:
        return bool(wait_for(lambda: self.table() == table))

    def reaches_the_pane(self) -> bool:
        """Types X until one more shows in the pane, which it can't while a popup has the keys."""
        before = self.server.pane().count("X")

        def typed() -> bool:
            self.press("X")
            return self.server.pane().count("X") > before

        return bool(wait_for(typed))

    def border(self, title: str) -> str:
        """The colour of the popup border drawn before `title`."""
        drawn = wait_for(lambda: self.output.find(f"╭─{title}".encode()) + 1)
        *_, colour = FOREGROUND_RE.finditer(self.output, 0, drawn)
        return "#" + "".join(f"{int(part):02x}" for part in colour.groups())

    def close(self) -> None:
        self.process.kill()
        self.process.wait()
        os.close(self.fd)


@pytest.fixture
def server(tmp_path):
    server = Server(tmp_path)
    yield server
    server.run("kill-server")
    server.socket.unlink(missing_ok=True)


@pytest.fixture
def client(server):
    client = Client(server)
    yield client
    client.close()


def ok(result: subprocess.CompletedProcess[str]) -> None:
    assert (result.returncode, result.stdout, result.stderr) == (0, "", "")


def leave(*letters: str, key: str = "t") -> dict[str, str]:
    """The hotbar table for tools on `letters`, each opening a popup, and every other key
    leaving the mode."""
    return {**dict.fromkeys(letters, OPENS), **dict.fromkeys(("/", "Escape", key, "Any"), LEAVES)}


def test_init_binds_the_table_and_wraps_the_status_line(server):
    original = server.option("-g", "status-format[0]")
    ok(server.init(TOOLS))
    assert server.table() == leave("g", "d", "p")
    assert server.keys("prefix")["t"] == "switch-client -T hotbar"
    assert server.option("-g", "status-format[0]") == WRAP
    assert server.option("-s", "@hotbar-status-format") == original


def test_init_from_run_shell_says_nothing(server):
    server.config.write_text(TOOLS, encoding="utf-8")
    command = f"{shlex.quote(SCRIPT)} init --config {shlex.quote(str(server.config))}"
    assert server("run-shell", command) == ""
    assert server.option("-g", "status-format[0]") == WRAP


def test_init_twice_leaves_one_wrap_and_only_the_current_letters(server):
    original = server.option("-g", "status-format[0]")
    ok(server.init(TOOLS))
    ok(server.init(TOOLS.replace('key = "d"', 'key = "n"')))
    assert server.table() == leave("g", "n", "p")
    assert server.option("-g", "status-format[0]") == WRAP
    assert server.option("-s", "@hotbar-status-format") == original


def test_another_key_moves_the_binding(server):
    ok(server.init(TOOLS))
    ok(server.init(TOOLS, "--key", "T"))
    assert "t" not in server.keys("prefix")
    assert server.keys("prefix")["T"] == "switch-client -T hotbar"
    assert server.table() == leave("g", "d", "p", key="T")


def test_another_key_leaves_a_binding_that_is_not_hotbar_s(server):
    ok(server.init(TOOLS))
    server("bind-key", "-T", "prefix", "t", "clock-mode")
    ok(server.init(TOOLS, "--key", "T"))
    assert server.keys("prefix")["t"] == "clock-mode"


@pytest.mark.parametrize(
    ("text", "args"),
    [
        ('theme = "blue"\n', ()),
        (TOOLS.replace('key = "g"', 'key = "t"'), ()),
        (TOOLS, ("--key", "NotAKey")),
    ],
)
def test_a_bad_config_installs_nothing(server, text, args):
    before = (server.keys("prefix"), server.option("-g", "status-format[0]"))
    ok(server.init(text, *args))
    assert server.run("list-keys", "-T", "hotbar").returncode == 1
    assert (server.keys("prefix"), server.option("-g", "status-format[0]")) == before
    assert server("show-options", "-sq", "@hotbar-toolbar") == ""


def test_a_bad_config_keeps_the_last_good_toolbar(server):
    ok(server.init(TOOLS))
    ok(server.init('theme = "blue"\n'))
    assert server.table() == leave("g", "d", "p")
    assert server.option("-g", "status-format[0]") == WRAP


def test_a_bad_config_shows_one_message(server, client):
    ok(server.init('theme = "blue"\nsearch = 3\n'))
    message = (
        f'hotbar: {server.config}:1: theme must be "auto", "dark" or "light" '
        "(1 of 2 problems; hotbar check lists them)"
    )
    wait_for(lambda: message.encode() in client.output)


def test_the_toolbar_is_drawn_only_in_the_mode(server, client):
    before = client.status()
    ok(server.init(TOOLS))
    assert client.status() == before
    client.press("C-b", "t")
    assert client.enters("hotbar")
    drawn = client.status()
    for text in ("\uf0e7 tools#[default]", " g ", "lazygit", " d ", "gh dash", "/ search  esc "):
        assert text in drawn
    assert "#[fg=#c6a0f6,bold]" in drawn
    client.press("Escape")
    assert client.enters("root")
    assert client.status() == before


@pytest.mark.parametrize("key", ["/", "t", "z", "Enter"])
def test_every_key_leaves_the_mode_and_reaches_no_pane(server, client, key):
    ok(server.init(TOOLS))
    client.press("C-b", "t")
    assert client.enters("hotbar")
    client.press(key)
    assert client.enters("root")
    server("send-keys", "-t", "main", "X")
    assert wait_for(lambda: server("capture-pane", "-p").rstrip()) == "X"


def test_requires_shows_the_keycap_once_the_pane_has_the_value(server, client):
    ok(server.init(TOOLS))
    client.press("C-b", "t")
    assert client.enters("hotbar")
    assert "prs" not in client.status()
    server("set-option", "-p", "@x", "1")
    assert "prs" in client.status()


def test_auto_follows_the_client_theme_without_a_reload(server, client):
    ok(server.init(TOOLS.replace('theme = "dark"', 'theme = "auto"')))
    client.press("C-b", "t")
    assert client.enters("hotbar")
    client.report("light")
    assert "#[fg=#8839ef,bold]" in client.status()
    client.report("dark")
    assert "#[fg=#c6a0f6,bold]" in client.status()


def tool(key: str, command: list[str], **fields: object) -> str:
    fields = {"id": f"tool-{ord(key)}", "key": key, "title": key, "command": command, **fields}
    return "[[tools]]\n" + "".join(f"{name} = {toml(value)}\n" for name, value in fields.items())


def toml(value: object) -> str:
    if isinstance(value, dict):
        return "{ " + ", ".join(f"{name} = {toml(item)}" for name, item in value.items()) + " }"
    return json.dumps(value, ensure_ascii=False)


def open_tool(client: Client, letter: str) -> None:
    client.press("C-b", "t")
    assert client.enters("hotbar")
    client.type(letter)
    assert client.enters("root")


@pytest.mark.parametrize(("theme", "colour"), [("dark", "#a6da95"), ("light", "#40a02b")])
def test_a_letter_opens_its_tool_in_a_popup_in_the_panes_folder(
    server, client, tmp_path, theme, colour
):
    folder = tmp_path / "a folder"
    folder.mkdir()
    server("respawn-pane", "-k", "-t", "main", "-c", str(folder), "cat")
    out = tmp_path / "out"
    hold = 'pwd > "$1"; read line'
    fields = {"title": "lazy git", "icon": "", "color": "green"}
    ok(server.init('theme = "auto"\n' + tool("g", ["sh", "-c", hold, "sh", str(out)], **fields)))
    client.report(theme)
    open_tool(client, "g")
    assert Path(wait_for(lambda: out.exists() and out.read_text().strip())) == folder.resolve()
    assert client.border(" lazy git") == colour
    client.press("Enter")
    assert client.reaches_the_pane()


def test_the_tool_exiting_closes_its_popup(server, client, tmp_path):
    out = tmp_path / "out"
    echo = 'echo ready > "$1"; read line; echo "$line" >> "$1"'
    ok(server.init(tool("g", ["sh", "-c", echo, "sh", str(out)])))
    open_tool(client, "g")
    wait_for(out.exists)
    client.press("h", "i", "Enter")
    assert wait_for(lambda: out.read_text() == "ready\nhi\n")
    assert client.reaches_the_pane()
    assert "hi" not in server.pane()


def test_a_tool_opens_only_once_the_pane_has_what_it_requires_and_gets_it(server, client, tmp_path):
    out = tmp_path / "out"
    show = 'printf %s "$FOO" > "$1"'
    command = ["sh", "-c", show, "sh", str(out)]
    ok(server.init(tool("p", command, requires="#{@x}", env={"FOO": "#{@x}"})))
    open_tool(client, "p")
    assert client.reaches_the_pane()
    assert not out.exists()
    server("set-option", "-p", "-t", "main", "@x", "hello")
    open_tool(client, "p")
    assert wait_for(lambda: out.exists() and out.read_text()) == "hello"
    assert "@hotbar-env" not in server("show-options", "-p", "-t", "main")


def test_titles_commands_and_env_reach_the_tool_as_written(server, client, tmp_path):
    out = tmp_path / "out"
    title = 'it\'s "q" #1 ;$HOME %H a,b} #[x]'
    write = 'o=$1; shift; printf "[%s]\\n" "$@" "$FOO" "$EMPTY" > "$o.new"; mv "$o.new" "$o"'
    command = ["sh", "-c", f"{write}; read line", "sh", str(out), *AWKWARD]
    env = {"FOO": "pre-#{@x}", "EMPTY": "#{@nothing}"}
    ok(server.init(tool("g", command, title=title, icon="#", env=env)))
    value = 'it\'s "q" $H ;x #{pane_id} \\ ~'
    server("set-option", "-p", "-t", "main", "@x", value)
    open_tool(client, "g")
    lines = (*AWKWARD, f"pre-{value}", "")
    assert wait_for(lambda: out.exists() and out.read_text()) == "".join(f"[{a}]\n" for a in lines)
    wait_for(lambda: f"╭─# {title}".encode() in client.output)
    client.press("Enter")
    assert client.reaches_the_pane()


def test_a_command_that_is_not_on_path_says_so_and_leaves_no_popup(server, client):
    ok(server.init(tool("g", ["hotbar-test-missing", "--flag"])))
    open_tool(client, "g")
    wait_for(lambda: b"hotbar: can't start hotbar-test-missing: not found" in client.output)
    assert client.reaches_the_pane()
