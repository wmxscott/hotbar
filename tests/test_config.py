"""Loading the config, and what it reports about a bad one."""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from hotbar import config
from hotbar.config import Config, ConfigError, Search, Tool
from hotbar.theme import ACCENTS

EXAMPLE = Path(__file__).resolve().parent.parent / "examples" / "config.toml"

LAZYGIT = """\
[[tools]]
id = "lazygit"
key = "g"
title = "lazygit"
command = ["lazygit"]
"""

GH_DASH = """\
[[tools]]
id = "gh-dash"
key = "d"
title = "gh dash"
command = ["gh", "dash"]
"""

SIZE = 'must be a number of cells or a percentage, like "80%"'
ENV = 'must be a table of strings, like { NAME = "#{pane_id}" }'
KEY = "must be one character, not / and not a control character"
COMMAND = 'must be a non-empty list of strings, like ["lazygit"]'
COLOR = "must be a Catppuccin colour: " + ", ".join(ACCENTS)


def write(tmp_path: Path, text: str | bytes) -> Path:
    path = tmp_path / "config.toml"
    if isinstance(text, bytes):
        path.write_bytes(text)
    else:
        path.write_text(text, encoding="utf-8")
    return path


def problems(tmp_path: Path, text: str) -> list[str]:
    path = write(tmp_path, text)
    with pytest.raises(ConfigError) as err:
        config.load(path)
    assert all(problem.path == path for problem in err.value.problems)
    return [f"{problem.line}: {problem.message}" for problem in err.value.problems]


def test_the_example_loads():
    loaded = config.load(EXAMPLE)
    assert loaded.theme == "auto"
    assert [(tool.key, tool.title) for tool in loaded.tools] == [
        ("g", "lazygit"),
        ("d", "gh dash"),
        ("n", "nvim"),
        ("b", "btop"),
    ]
    assert all(tool.icon != "•" and tool.color in ACCENTS for tool in loaded.tools)


def test_defaults(tmp_path):
    loaded = config.load(write(tmp_path, LAZYGIT))
    assert loaded == Config(
        theme="auto",
        search=Search(width=None, height=None),
        tools=(Tool(id="lazygit", key="g", title="lazygit", command=("lazygit",)),),
    )
    tool = loaded.tools[0]
    assert (tool.icon, tool.color, tool.width, tool.height) == ("•", "blue", "80%", "80%")
    assert (tool.env, tool.requires) == ((), None)


def test_every_setting(tmp_path):
    text = """\
theme = "light"

[search]
width = 40
height = "50%"

[[tools]]
id = "review"
key = "R"
title = "review"
command = ["review", "--mine"]
icon = "\\ue726"
color = "mauve"
width = 120
height = "60%"
env = { SESSION = "#{@session}", PANE = "#{pane_id}" }
requires = "#{@session}"
"""
    assert config.load(write(tmp_path, text)) == Config(
        theme="light",
        search=Search(width=40, height="50%"),
        tools=(
            Tool(
                id="review",
                key="R",
                title="review",
                command=("review", "--mine"),
                icon="",
                color="mauve",
                width=120,
                height="60%",
                env=(("SESSION", "#{@session}"), ("PANE", "#{pane_id}")),
                requires="#{@session}",
            ),
        ),
    )


def test_tools_keep_their_order(tmp_path):
    loaded = config.load(write(tmp_path, GH_DASH + LAZYGIT))
    assert [tool.id for tool in loaded.tools] == ["gh-dash", "lazygit"]


def test_an_empty_file_has_no_tools(tmp_path):
    assert config.load(write(tmp_path, "")) == Config()


def test_env_in_its_own_table(tmp_path):
    loaded = config.load(write(tmp_path, LAZYGIT + '[tools.env]\nA = "1"\nB = "#{pane_id}"\n'))
    assert loaded.tools[0].env == (("A", "1"), ("B", "#{pane_id}"))


def test_the_objects_are_frozen(tmp_path):
    loaded = config.load(write(tmp_path, LAZYGIT))
    with pytest.raises(dataclasses.FrozenInstanceError):
        loaded.tools[0].key = "x"
    with pytest.raises(dataclasses.FrozenInstanceError):
        loaded.search.width = 3
    assert hash(loaded) == hash(config.load(write(tmp_path, LAZYGIT)))


def test_the_path_follows_xdg(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    assert config.config_path() == tmp_path / "xdg" / "hotbar" / "config.toml"


@pytest.mark.parametrize("xdg", [None, "", "relative/dir"])
def test_the_path_falls_back_to_home(monkeypatch, tmp_path, xdg):
    monkeypatch.setenv("HOME", str(tmp_path))
    if xdg is None:
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    else:
        monkeypatch.setenv("XDG_CONFIG_HOME", xdg)
    assert config.config_path() == tmp_path / ".config" / "hotbar" / "config.toml"


def test_load_reads_the_default_path(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    (tmp_path / "hotbar").mkdir()
    (tmp_path / "hotbar" / "config.toml").write_text(LAZYGIT, encoding="utf-8")
    assert [tool.id for tool in config.load().tools] == ["lazygit"]


def test_a_missing_file(tmp_path):
    path = tmp_path / "config.toml"
    with pytest.raises(ConfigError) as err:
        config.load(path)
    assert str(err.value) == f"{path}: no config file yet"
    assert err.value.problems[0].line is None


def test_an_unreadable_file(tmp_path):
    with pytest.raises(ConfigError) as err:
        config.load(tmp_path)
    assert str(err.value).startswith(f"{tmp_path}: can't read it: ")


def test_a_file_that_is_not_utf8(tmp_path):
    path = write(tmp_path, b'theme = "\xff"\n')
    with pytest.raises(ConfigError) as err:
        config.load(path)
    assert str(err.value) == f"{path}: isn't UTF-8 text"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ('theme = "auto"\n\n[[tools]]\nid = \n', "4: invalid value"),
        ("[[tools]\n", "1: expected ']]' at the end of an array declaration"),
        ('theme = "auto"\ntitle = "x', "2: unterminated string"),
    ],
)
def test_toml_syntax_errors_name_the_line(tmp_path, text, expected):
    assert problems(tmp_path, text) == [expected]


def test_every_problem_is_reported_in_line_order(tmp_path):
    text = LAZYGIT.replace('key = "g"', 'key = "gg"') + 'color = "chartreuse"\n'
    text = 'theme = "blue"\n' + text + GH_DASH.replace('title = "gh dash"\n', "")
    assert problems(tmp_path, text) == [
        '1: theme must be "auto", "dark" or "light"',
        f"4: tool 'lazygit': key {KEY}",
        f"7: tool 'lazygit': color {COLOR}",
        "8: tool 'gh-dash': title is required",
    ]


def test_the_error_message_lists_every_problem(tmp_path):
    path = write(tmp_path, 'theme = "blue"\nsearch = 3\n')
    with pytest.raises(ConfigError) as err:
        config.load(path)
    assert str(err.value) == (
        f'{path}:1: theme must be "auto", "dark" or "light"\n{path}:2: [search] must be a table'
    )


def without(line: str) -> str:
    return LAZYGIT.replace(line + "\n", "")


def replace(line: str, new: str) -> str:
    return LAZYGIT.replace(line, new)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ('colour_scheme = "dark"\n' + LAZYGIT, "1: unknown setting 'colour_scheme'"),
        ('theme = "blue"\n' + LAZYGIT, '1: theme must be "auto", "dark" or "light"'),
        ("theme = 1\n", '1: theme must be "auto", "dark" or "light"'),
        ("search = 3\n" + LAZYGIT, "1: [search] must be a table"),
        (LAZYGIT + "[search]\ndepth = 3\n", "7: [search]: unknown setting 'depth'"),
        (LAZYGIT + "[search]\nwidth = 0\n", f"7: [search]: width {SIZE}"),
        (LAZYGIT + '[search]\nheight = "120%"\n', f"7: [search]: height {SIZE}"),
        ('[tools]\nid = "x"\n', "1: tools must be an array of tables, written [[tools]]"),
        ("tools = [1]\n", "1: tool 1 must be a table"),
        (without('id = "lazygit"'), "1: tool 1: id is required"),
        (
            replace('"lazygit"\nkey', '"has.dot"\nkey'),
            "2: tool 1: id must use only letters, digits, - and _",
        ),
        (LAZYGIT + "slot = 1\n", "6: tool 'lazygit': unknown setting 'slot'"),
        (LAZYGIT + 'colour = "red"\n', "6: tool 'lazygit': unknown setting 'colour'"),
        (without('key = "g"'), "1: tool 'lazygit': key is required"),
        (replace('key = "g"', 'key = "gg"'), f"3: tool 'lazygit': key {KEY}"),
        (replace('key = "g"', 'key = ""'), f"3: tool 'lazygit': key {KEY}"),
        (replace('key = "g"', 'key = "/"'), f"3: tool 'lazygit': key {KEY}"),
        (replace('key = "g"', 'key = "\\t"'), f"3: tool 'lazygit': key {KEY}"),
        (replace('key = "g"', 'key = "\\u001b"'), f"3: tool 'lazygit': key {KEY}"),
        (replace('key = "g"', "key = 1"), f"3: tool 'lazygit': key {KEY}"),
        (without('title = "lazygit"'), "1: tool 'lazygit': title is required"),
        (
            replace('title = "lazygit"', 'title = " "'),
            "4: tool 'lazygit': title must be a non-empty string",
        ),
        (without('command = ["lazygit"]'), "1: tool 'lazygit': command is required"),
        (replace('["lazygit"]', '"lazygit"'), f"5: tool 'lazygit': command {COMMAND}"),
        (replace('["lazygit"]', "[]"), f"5: tool 'lazygit': command {COMMAND}"),
        (replace('["lazygit"]', '["lazygit", 3]'), f"5: tool 'lazygit': command {COMMAND}"),
        (replace('["lazygit"]', '[""]'), f"5: tool 'lazygit': command {COMMAND}"),
        (LAZYGIT + 'icon = ""\n', "6: tool 'lazygit': icon must be a non-empty string"),
        (LAZYGIT + 'color = "chartreuse"\n', f"6: tool 'lazygit': color {COLOR}"),
        (LAZYGIT + 'color = "#a1b2c3"\n', f"6: tool 'lazygit': color {COLOR}"),
        (LAZYGIT + 'color = "base"\n', f"6: tool 'lazygit': color {COLOR}"),
        (LAZYGIT + 'width = "80"\n', f"6: tool 'lazygit': width {SIZE}"),
        (LAZYGIT + 'width = "0%"\n', f"6: tool 'lazygit': width {SIZE}"),
        (LAZYGIT + "width = 0\n", f"6: tool 'lazygit': width {SIZE}"),
        (LAZYGIT + "width = 65536\n", f"6: tool 'lazygit': width {SIZE}"),
        (LAZYGIT + 'height = "101%"\n', f"6: tool 'lazygit': height {SIZE}"),
        (LAZYGIT + "height = true\n", f"6: tool 'lazygit': height {SIZE}"),
        (LAZYGIT + 'env = "A=1"\n', f"6: tool 'lazygit': env {ENV}"),
        (LAZYGIT + "env = { A = 1 }\n", f"6: tool 'lazygit': env {ENV}"),
        (LAZYGIT + 'env = { "1A" = "x" }\n', f"6: tool 'lazygit': env {ENV}"),
        (LAZYGIT + '\n[tools.env]\nGOOD = "x"\nBAD = 1\n', f"7: tool 'lazygit': env {ENV}"),
        (LAZYGIT + 'requires = ""\n', "6: tool 'lazygit': requires must be a non-empty string"),
        (LAZYGIT + "requires = true\n", "6: tool 'lazygit': requires must be a non-empty string"),
        (LAZYGIT + replace('key = "g"', 'key = "z"'), "7: two tools have id 'lazygit'"),
        (
            LAZYGIT + GH_DASH.replace('key = "d"', 'key = "g"'),
            "8: tools 'lazygit' and 'gh-dash' both use key 'g'",
        ),
    ],
)
def test_rejects(tmp_path, text, expected):
    assert problems(tmp_path, text) == [expected]
