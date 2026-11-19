"""The toolbar's format and the tmux commands that install it, without tmux."""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from hotbar import toolbar
from hotbar.config import Config, Problem, Tool
from hotbar.toolbar import WRAP

LAZYGIT = Tool(
    id="lazygit", key="g", title="lazygit", command=("lazygit",), icon="\ue702", color="green"
)
PRS = Tool(
    id="prs",
    key="p",
    title="prs",
    command=("prs",),
    icon="\ue726",
    color="mauve",
    requires="#{@session}",
)
DEFAULT = "#[align=left]#{T:status-left}#[align=right]#{T:status-right}"

DARK_LABEL = " #[fg=#c6a0f6#,bold]\uf0e7 tools#[default]"
DARK_LAZYGIT = (
    "  #[bg=#a6da95#,fg=#24273a#,bold] g #[default] #[fg=#a6da95]\ue702 #[fg=#8087a2]lazygit"
)
DARK_PRS = "  #[bg=#c6a0f6#,fg=#24273a#,bold] p #[default] #[fg=#c6a0f6]\ue726 #[fg=#8087a2]prs"
DARK_RIGHT = "#[default]#[align=right]#[fg=#8087a2]/ search  esc "
LIGHT_LABEL = " #[fg=#8839ef#,bold]\uf0e7 tools#[default]"
LIGHT_LAZYGIT = (
    "  #[bg=#40a02b#,fg=#eff1f5#,bold] g #[default] #[fg=#40a02b]\ue702 #[fg=#8c8fa1]lazygit"
)
LIGHT_RIGHT = "#[default]#[align=right]#[fg=#8c8fa1]/ search  esc "
DARK = DARK_LABEL + DARK_LAZYGIT + DARK_RIGHT
LIGHT = LIGHT_LABEL + LIGHT_LAZYGIT + LIGHT_RIGHT


@pytest.mark.parametrize(
    ("text", "escaped"),
    [
        ("lazygit", "lazygit"),
        ("a#b", "a####b"),
        ("##", "########"),
        ("#[fg=red]", "##[fg=red]"),
        ("##[", "####["),
        ("a,b", "a#,b"),
        ("{a}", "{a#}"),
        ("#{pane_id}", "####{pane_id#}"),
        ("50%", "50#{a:37}"),
        ("%H", "#{a:37}H"),
    ],
)
def test_literal_text(text, escaped):
    assert toolbar.literal(text) == escaped


def test_a_dark_toolbar():
    assert toolbar.toolbar(Config(theme="dark", tools=(LAZYGIT,)), "dark") == DARK


def test_a_light_toolbar():
    assert toolbar.toolbar(Config(theme="light", tools=(LAZYGIT,)), "light") == LIGHT


def test_no_tools_leaves_the_label_and_the_hints():
    assert toolbar.toolbar(Config(theme="dark"), "dark") == DARK_LABEL + DARK_RIGHT


def test_tools_are_in_order_two_spaces_apart():
    cfg = Config(theme="dark", tools=(LAZYGIT, dataclasses.replace(PRS, requires=None)))
    assert toolbar.toolbar(cfg, "dark") == DARK_LABEL + DARK_LAZYGIT + DARK_PRS + DARK_RIGHT


def test_requires_hides_the_keycap_when_it_expands_empty():
    cfg = Config(theme="dark", tools=(LAZYGIT, PRS))
    assert toolbar.toolbar(cfg, "dark") == (
        DARK_LABEL + DARK_LAZYGIT + "#{?#{!=:#{@session},}," + DARK_PRS + ",}" + DARK_RIGHT
    )


def test_auto_follows_the_client_theme_and_falls_back_to_the_detected_one():
    cfg = Config(theme="auto", tools=(LAZYGIT,))
    assert toolbar.toolbar(cfg, "dark") == f"#{{?#{{==:#{{client_theme}},light}},{LIGHT},{DARK}}}"
    assert toolbar.toolbar(cfg, "light") == f"#{{?#{{==:#{{client_theme}},dark}},{DARK},{LIGHT}}}"


def test_titles_icons_and_keys_are_drawn_as_written():
    tool = Tool(id="x", key="#", title="a,b} 5%", command=("x",), icon="#", color="green")
    assert toolbar.toolbar(Config(theme="dark", tools=(tool,)), "dark") == (
        DARK_LABEL
        + "  #[bg=#a6da95#,fg=#24273a#,bold] #### #[default] #[fg=#a6da95]#### "
        + "#[fg=#8087a2]a#,b#} 5#{a:37}"
        + DARK_RIGHT
    )


def bindings(key: str, *letters: str) -> list[tuple[str, ...]]:
    return [
        ("bind-key", "-N", "Open the hotbar", "-T", "prefix", key, "switch-client", "-T", "hotbar"),
        ("bind-key", "-T", "hotbar", "Any", "switch-client", "-T", "root"),
        ("unbind-key", "-a", "-T", "hotbar"),
        *(
            ("bind-key", "-T", "hotbar", letter, "switch-client", "-T", "root")
            for letter in (*letters, "/", "Escape", key, "Any")
        ),
    ]


def options(original: str, cfg: Config, key: str = "t") -> list[tuple[str, ...]]:
    return [
        ("set-option", "-s", "@hotbar-status-format", original),
        ("set-option", "-s", "@hotbar-toolbar", toolbar.toolbar(cfg, "dark")),
        ("set-option", "-s", "@hotbar-key", key),
        ("set-option", "-g", "status-format[0]", WRAP),
    ]


def test_the_wrap_draws_the_toolbar_only_in_the_hotbar_table():
    assert WRAP == (
        "#{?#{==:#{client_key_table},hotbar},#{E:@hotbar-toolbar},#{E:@hotbar-status-format}}"
    )


def test_install_binds_the_table_and_wraps_the_status_line():
    cfg = Config(theme="dark", tools=(LAZYGIT, PRS))
    commands = toolbar.install(cfg, "t", "dark", current=DEFAULT, saved=None)
    assert commands == bindings("t", "g", "p") + options(DEFAULT, cfg)


def test_install_again_wraps_the_saved_original_not_the_wrap():
    cfg = Config(theme="dark", tools=(PRS,))
    commands = toolbar.install(cfg, "t", "dark", current=WRAP, saved=DEFAULT)
    assert commands == bindings("t", "p") + options(DEFAULT, cfg)


def test_install_after_the_status_line_changed_keeps_the_new_one():
    cfg = Config(theme="dark", tools=(LAZYGIT,))
    commands = toolbar.install(cfg, "t", "dark", current="#S", saved=DEFAULT)
    assert commands == bindings("t", "g") + options("#S", cfg)


def test_install_with_another_key_unbinds_the_old_one():
    cfg = Config(theme="dark", tools=(LAZYGIT,))
    commands = toolbar.install(cfg, "T", "dark", current=WRAP, saved=DEFAULT, stale="t")
    expected = bindings("T", "g")
    expected.insert(1, ("unbind-key", "-T", "prefix", "t"))
    assert commands == expected + options(DEFAULT, cfg, key="T")


def test_the_message_names_the_first_problem():
    path = Path("/c.toml")
    assert (
        toolbar.message([Problem(path, 3, "theme is wrong")]) == "hotbar: /c.toml:3: theme is wrong"
    )


def test_the_message_counts_the_problems():
    path = Path("/c.toml")
    problems = [Problem(path, 3, "theme is wrong"), Problem(path, 9, "x"), Problem(path, 12, "y")]
    assert toolbar.message(problems) == (
        "hotbar: /c.toml:3: theme is wrong (1 of 3 problems; hotbar check lists them)"
    )
