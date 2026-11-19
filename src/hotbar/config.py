"""The config file: where it lives, the tools it lists, and what's wrong with it."""

from __future__ import annotations

import os
import re
import tomllib
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from hotbar.theme import ACCENTS

THEMES = ("auto", "dark", "light")
REQUIRED = ("id", "key", "title", "command")
ID_RE = re.compile(r"[A-Za-z0-9_-]+")
ENV_NAME_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
PERCENT_RE = re.compile(r"(\d{1,3})%")
HEADER_RE = re.compile(r"\s*(\[\[?)\s*([^\]]+?)\s*\]")
SETTING_RE = re.compile(r"\s*([\w.\-\"' ]+?)\s*=")
SYNTAX_RE = re.compile(r"(.*) \(at (?:line (\d+), column \d+|end of document)\)", re.DOTALL)

Size = int | str


@dataclass(frozen=True)
class Tool:
    id: str
    key: str
    title: str
    command: tuple[str, ...]
    icon: str = "•"
    color: str = "blue"
    width: Size = "80%"
    height: Size = "80%"
    env: tuple[tuple[str, str], ...] = ()
    requires: str | None = None


@dataclass(frozen=True)
class Search:
    width: Size | None = None
    height: Size | None = None


@dataclass(frozen=True)
class Config:
    theme: str = "auto"
    search: Search = field(default_factory=Search)
    tools: tuple[Tool, ...] = ()


@dataclass(frozen=True)
class Problem:
    path: Path
    line: int | None
    message: str

    def __str__(self) -> str:
        where = f"{self.path}:{self.line}" if self.line else str(self.path)
        return f"{where}: {self.message}"


class ConfigError(Exception):
    def __init__(self, problems: list[Problem]) -> None:
        super().__init__("\n".join(map(str, problems)))
        self.problems = tuple(problems)


def config_path() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME", "")
    base = Path(xdg) if os.path.isabs(xdg) else Path.home() / ".config"
    return base / "hotbar" / "config.toml"


def load(path: Path | None = None) -> Config:
    path = path or config_path()
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise ConfigError([Problem(path, None, "no config file yet")]) from None
    except OSError as err:
        raise ConfigError([Problem(path, None, f"can't read it: {err.strerror}")]) from None
    except UnicodeDecodeError:
        raise ConfigError([Problem(path, None, "isn't UTF-8 text")]) from None
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as err:
        raise ConfigError([_syntax_problem(path, text, err)]) from None
    report = _Report(path, text)
    config = _config(data, report)
    if report.problems:
        raise ConfigError(sorted(report.problems, key=lambda problem: problem.line or 0))
    return config


def _syntax_problem(path: Path, text: str, err: tomllib.TOMLDecodeError) -> Problem:
    match = SYNTAX_RE.fullmatch(str(err))
    if not match:
        return Problem(path, None, str(err))
    message, line = match.groups()
    number = int(line) if line else len(text.splitlines()) or 1
    return Problem(path, number, message[:1].lower() + message[1:])


class _Report:
    """Collects problems, each at the line where the setting it's about is written."""

    def __init__(self, path: Path, text: str) -> None:
        self.path = path
        self.lines = _lines(text)
        self.problems: list[Problem] = []

    def __call__(self, where: tuple[str | int, ...], message: str) -> None:
        while where and where not in self.lines:
            where = where[:-1]
        self.problems.append(Problem(self.path, self.lines.get(where), message))


def _lines(text: str) -> dict[tuple[str | int, ...], int]:
    """The line each table and setting is first written on, by its path in the parsed data, so
    the third tool's key is ("tools", 2, "key"). tomllib keeps no positions."""
    found: dict[tuple[str | int, ...], int] = {}
    table: tuple[str | int, ...] = ()
    tools = -1
    for number, line in enumerate(text.splitlines(), 1):
        if header := HEADER_RE.match(line):
            keys = _keys(header[2])
            if header[1] == "[[" and keys == ("tools",):
                tools += 1
                table = ("tools", tools)
                found.setdefault(("tools",), number)
            elif keys[0] == "tools" and len(keys) > 1:
                table = ("tools", tools, *keys[1:])
            else:
                table = keys
            found.setdefault(table, number)
        elif setting := SETTING_RE.match(line):
            keys = _keys(setting[1])
            for end in range(1, len(keys) + 1):
                found.setdefault((*table, *keys[:end]), number)
    return found


def _keys(dotted: str) -> tuple[str, ...]:
    return tuple(part.strip().strip("\"'") for part in dotted.split("."))


def _config(data: dict, report: _Report) -> Config:
    for name in data:
        if name not in ("theme", "search", "tools"):
            report((name,), f"unknown setting {name!r}")
    theme = data.get("theme", "auto")
    if theme not in THEMES:
        report(("theme",), 'theme must be "auto", "dark" or "light"')
    return Config(
        theme=theme,
        search=_search(data.get("search", {}), report),
        tools=_tools(data.get("tools", []), report),
    )


def _search(raw: object, report: _Report) -> Search:
    if not isinstance(raw, dict):
        report(("search",), "[search] must be a table")
        return Search()
    return Search(**_fields(raw, SEARCH_FIELDS, ("search",), "[search]", report))


def _tools(raw: object, report: _Report) -> tuple[Tool, ...]:
    if not isinstance(raw, list):
        report(("tools",), "tools must be an array of tables, written [[tools]]")
        return ()
    tools: list[Tool] = []
    names: list[str] = []
    ids: set[str] = set()
    keys: dict[str, int] = {}
    for index, item in enumerate(raw):
        where = ("tools", index)
        tool_id = item.get("id") if isinstance(item, dict) else None
        valid = isinstance(tool_id, str) and ID_RE.fullmatch(tool_id)
        names.append(repr(tool_id) if valid else str(index + 1))
        if not isinstance(item, dict):
            report(where, f"tool {names[index]} must be a table")
            continue
        label = f"tool {names[index]}"
        fields = _fields(item, TOOL_FIELDS, where, label, report)
        for name in REQUIRED:
            if name not in item:
                report(where, f"{label}: {name} is required")
        if "id" in fields:
            if fields["id"] in ids:
                report((*where, "id"), f"two tools have id {fields['id']!r}")
            ids.add(fields["id"])
        if "key" in fields:
            first = keys.setdefault(fields["key"], index)
            if first != index:
                both = f"{names[first]} and {names[index]}"
                report((*where, "key"), f"tools {both} both use key {fields['key']!r}")
        if all(name in fields for name in REQUIRED):
            tools.append(Tool(**fields))
    return tuple(tools)


def _fields(
    raw: dict,
    validators: dict[str, Callable[[object], object]],
    where: tuple[str | int, ...],
    label: str,
    report: _Report,
) -> dict:
    fields = {}
    for name, value in raw.items():
        validate = validators.get(name)
        if validate is None:
            report((*where, name), f"{label}: unknown setting {name!r}")
            continue
        try:
            fields[name] = validate(value)
        except ValueError as err:
            report((*where, name), f"{label}: {name} {err}")
    return fields


def _id(value: object) -> str:
    if isinstance(value, str) and ID_RE.fullmatch(value):
        return value
    raise ValueError("must use only letters, digits, - and _")


def _key(value: object) -> str:
    if (
        isinstance(value, str)
        and len(value) == 1
        and value != "/"
        and unicodedata.category(value) != "Cc"
    ):
        return value
    raise ValueError("must be one character, not / and not a control character")


def _text(value: object) -> str:
    if isinstance(value, str) and value.strip():
        return value
    raise ValueError("must be a non-empty string")


def _command(value: object) -> tuple[str, ...]:
    if (
        isinstance(value, list)
        and value
        and all(isinstance(arg, str) for arg in value)
        and value[0].strip()
    ):
        return tuple(value)
    raise ValueError('must be a non-empty list of strings, like ["lazygit"]')


def _color(value: object) -> str:
    if isinstance(value, str) and value in ACCENTS:
        return value
    raise ValueError(f"must be a Catppuccin colour: {', '.join(ACCENTS)}")


def _size(value: object) -> Size:
    if isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= 65535:
        return value
    match = PERCENT_RE.fullmatch(value) if isinstance(value, str) else None
    if match and 1 <= int(match[1]) <= 100:
        return value
    raise ValueError('must be a number of cells or a percentage, like "80%"')


def _env(value: object) -> tuple[tuple[str, str], ...]:
    if isinstance(value, dict) and all(
        ENV_NAME_RE.fullmatch(name) and isinstance(text, str) for name, text in value.items()
    ):
        return tuple(value.items())
    raise ValueError('must be a table of strings, like { NAME = "#{pane_id}" }')


SEARCH_FIELDS = {"width": _size, "height": _size}
TOOL_FIELDS = {
    "id": _id,
    "key": _key,
    "title": _text,
    "command": _command,
    "icon": _text,
    "color": _color,
    "width": _size,
    "height": _size,
    "env": _env,
    "requires": _text,
}
