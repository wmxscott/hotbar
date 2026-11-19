"""The toolbar's format and the tmux commands that install it, without tmux."""

from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

import pytest

from hotbar import toolbar
from hotbar.config import Config, Problem, Search, Tool
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


@pytest.mark.parametrize(
    ("text", "quoted"),
    [
        ("lazygit", '"lazygit"'),
        ("a b;", '"a b;"'),
        ("it's", '"it\'s"'),
        ('say "hi"', '"say \\"hi\\""'),
        ("$HOME ~/x", '"\\$HOME \\~/x"'),
        ("back\\slash", '"back\\\\slash"'),
        ("one\ntwo\r", '"one\\ntwo\\r"'),
        ("#{pane_id} {}", '"#{pane_id} {}"'),
        ("", '""'),
    ],
)
def test_quoted_text_is_one_tmux_argument(text, quoted):
    assert toolbar.quoted(text) == quoted


@pytest.mark.parametrize(
    ("text", "escaped"),
    [
        ("lazygit", "lazygit"),
        ("a#b", "a##b"),
        ("#{pane_id}", "##{pane_id}"),
        ("###S", "######S"),
        ("#[fg=red]", "#[fg=red]"),
        ("##[", "##["),
        ("a,b} 50%", "a,b} 50%"),
    ],
)
def test_unexpanded_text(text, escaped):
    assert toolbar.unexpanded(text) == escaped


LAUNCH = toolbar.unexpanded(toolbar.quoted(toolbar.LAUNCH))


def test_a_popup_in_the_tools_colour_with_its_title_and_size_in_the_panes_folder():
    assert toolbar.popup(LAZYGIT, "dark", auto=False) == (
        'display-popup -E -b rounded -S "fg=##a6da95" -T "\ue702 lazygit" -w "80%" -h "80%" '
        f'-d "##{{pane_current_path}}" /bin/sh -c {LAUNCH} hotbar #{{q/a:client_name}} "lazygit"'
    )


def test_a_light_popup():
    assert '-S "fg=##40a02b"' in toolbar.popup(LAZYGIT, "light", auto=False)


def test_an_auto_popup_follows_the_client_theme_and_falls_back_to_the_detected_one():
    border = '-S "fg=#{?#{==:#{client_theme},light},##40a02b,##a6da95}"'
    assert border in toolbar.popup(LAZYGIT, "dark", auto=True)


def test_a_popup_has_the_configured_size():
    tool = dataclasses.replace(LAZYGIT, width=120, height="95%")
    assert ' -w "120" -h "95%" ' in toolbar.popup(tool, "dark", auto=False)


def test_a_popup_title_and_command_reach_tmux_as_written():
    tool = dataclasses.replace(
        LAZYGIT, icon="#", title='it\'s "a" 5% ;$X', command=("sh", "-c", "echo $HOME; #x")
    )
    popup = toolbar.popup(tool, "dark", auto=False)
    assert ' -T "######## it\'s \\"a\\" 5##{a:37} ;\\$X" ' in popup
    assert popup.endswith(' "sh" "-c" "echo \\$HOME; ##x"')


def test_env_is_expanded_into_a_pane_option_and_passed_quoted():
    tool = dataclasses.replace(LAZYGIT, env=(("SID", "#{@session}"), ("AT", "#{pane_id}")))
    popup = toolbar.popup(tool, "dark", auto=False)
    assert popup.startswith(
        "set-option -p -u @hotbar-env-SID ; set-option -p -u @hotbar-env-AT ; display-popup "
    )
    assert " -e SID=#{q/a:@hotbar-env-SID} -e AT=#{q/a:@hotbar-env-AT} /bin/sh " in popup
    assert toolbar.opener(tool, "dark", auto=False) == (
        'switch-client -T root ; set-option -p -F @hotbar-env-SID "#{@session}" ; '
        f'set-option -p -F @hotbar-env-AT "#{{pane_id}}" ; run-shell -C {toolbar.quoted(popup)}'
    )


def test_a_letter_leaves_the_mode_and_opens_its_tool():
    popup = toolbar.popup(LAZYGIT, "dark", auto=False)
    assert toolbar.opener(LAZYGIT, "dark", auto=False) == (
        f"switch-client -T root ; run-shell -C {toolbar.quoted(popup)}"
    )


def test_requires_opens_the_tool_only_when_it_expands_to_something():
    popup = toolbar.popup(PRS, "dark", auto=False)
    assert toolbar.opener(PRS, "dark", auto=False) == (
        'switch-client -T root ; if-shell -F "#{!=:#{@session},}" '
        f"{{ run-shell -C {toolbar.quoted(popup)} }}"
    )


def bindings(key: str, cfg: Config, path: Path | None = None) -> list[tuple[str, ...]]:
    return [
        ("bind-key", "-N", "Open the hotbar", "-T", "prefix", key, "switch-client", "-T", "hotbar"),
        ("bind-key", "-T", "hotbar", "Any", "switch-client", "-T", "root"),
        ("unbind-key", "-a", "-T", "hotbar"),
        *(
            ("bind-key", "-T", "hotbar", tool.key, toolbar.opener(tool, "dark", auto=False))
            for tool in cfg.tools
        ),
        ("bind-key", "-T", "hotbar", "/", toolbar.searcher(cfg, "dark", path)),
        *(
            ("bind-key", "-T", "hotbar", letter, "switch-client", "-T", "root")
            for letter in ("Escape", key, "Any")
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
    assert commands == bindings("t", cfg) + options(DEFAULT, cfg)


def test_install_binds_letters_that_follow_the_client_theme_for_auto():
    cfg = Config(theme="auto", tools=(LAZYGIT,))
    commands = toolbar.install(cfg, "t", "dark", current=DEFAULT, saved=None)
    assert ("bind-key", "-T", "hotbar", "g", toolbar.opener(LAZYGIT, "dark", auto=True)) in commands


def test_install_again_wraps_the_saved_original_not_the_wrap():
    cfg = Config(theme="dark", tools=(PRS,))
    commands = toolbar.install(cfg, "t", "dark", current=WRAP, saved=DEFAULT)
    assert commands == bindings("t", cfg) + options(DEFAULT, cfg)


def test_install_after_the_status_line_changed_keeps_the_new_one():
    cfg = Config(theme="dark", tools=(LAZYGIT,))
    commands = toolbar.install(cfg, "t", "dark", current="#S", saved=DEFAULT)
    assert commands == bindings("t", cfg) + options("#S", cfg)


def test_install_with_another_key_unbinds_the_old_one():
    cfg = Config(theme="dark", tools=(LAZYGIT,))
    commands = toolbar.install(cfg, "T", "dark", current=WRAP, saved=DEFAULT, stale="t")
    expected = bindings("T", cfg)
    expected.insert(1, ("unbind-key", "-T", "prefix", "t"))
    assert commands == expected + options(DEFAULT, cfg, key="T")


def test_install_binds_slash_to_search_the_config_it_loaded():
    cfg = Config(theme="dark", tools=(LAZYGIT,))
    path = Path("/c.toml")
    commands = toolbar.install(cfg, "t", "dark", current=DEFAULT, saved=None, path=path)
    assert commands == bindings("t", cfg, path) + options(DEFAULT, cfg)


SEARCH = (
    'display-popup -E -b rounded -S "fg=##8087a2" -T "\uf0e7 tools" '
    "-w #{?#{e|>:24,#{client_width}},#{client_width},24} "
    "-h #{?#{e|>:6,#{client_height}},#{client_height},6} "
    '"/bin/hotbar" "search" "--config" "/c.toml" --pane #{pane_id} --client #{q/a:client_name}'
)


def test_slash_searches_in_a_popup_then_runs_what_the_search_left_on_the_pane(monkeypatch):
    monkeypatch.setattr(toolbar, "command", lambda: ("/bin/hotbar",))
    cfg = Config(theme="dark", tools=(LAZYGIT, PRS))
    assert toolbar.searcher(cfg, "dark", Path("/c.toml")) == (
        "switch-client -T root ; set-option -p -u @hotbar-pick ; "
        f"run-shell -C {toolbar.quoted(SEARCH)} ; "
        'if-shell -F "#{@hotbar-pick}" '
        '{ run-shell -C "set-option -p -u @hotbar-pick ; #{@hotbar-pick}" }'
    )


def test_a_search_without_a_path_finds_the_config_itself(monkeypatch):
    monkeypatch.setattr(toolbar, "command", lambda: ("/bin/hotbar",))
    search = toolbar.searcher(Config(theme="dark", tools=(LAZYGIT, PRS)), "dark")
    assert toolbar.quoted(SEARCH.replace(' "--config" "/c.toml"', "")) in search


def test_an_auto_search_border_follows_the_client_theme():
    search = toolbar.searcher(Config(theme="auto", tools=(LAZYGIT,)), "dark")
    assert ' -S \\"fg=#{?#{==:#{client_theme},light},##8c8fa1,##8087a2}\\" ' in search


@pytest.mark.parametrize(
    ("tools", "size"),
    [
        ((), (24, 4)),
        ((LAZYGIT, PRS), (24, 6)),
        ((dataclasses.replace(LAZYGIT, title="a much longer title, to fit"),), (39, 5)),
        ((dataclasses.replace(LAZYGIT, title="ツール" * 6),), (48, 5)),
    ],
)
def test_the_search_fits_the_tools(tools, size):
    assert toolbar.search_size(Config(tools=tools)) == size


def test_the_search_takes_its_size_from_the_config():
    cfg = Config(search=Search(width=50, height="40%"), tools=(LAZYGIT,))
    assert toolbar.search_size(cfg) == (50, "40%")
    assert toolbar.search_size(Config(search=Search(height=9), tools=(LAZYGIT,))) == (24, 9)
    search = toolbar.searcher(cfg, "dark")
    assert ' -w #{?#{e|>:50,#{client_width}},#{client_width},50} -h \\"40%\\" ' in search


def test_tmux_runs_the_script_that_ran(monkeypatch, tmp_path):
    script = tmp_path / "bin" / "hotbar"
    script.parent.mkdir()
    script.write_text("#!/bin/sh\n", encoding="utf-8")
    script.chmod(0o755)
    monkeypatch.setattr(sys, "argv", [str(script), "init"])
    assert toolbar.command() == (str(script),)


@pytest.mark.parametrize("argv0", ["/x/hotbar/__main__.py", "-c", "/nowhere/hotbar"])
def test_tmux_runs_this_python_when_no_script_ran(monkeypatch, argv0):
    monkeypatch.setattr(sys, "argv", [argv0, "init"])
    assert toolbar.command() == (sys.executable, "-m", "hotbar")


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


def test_the_message_writes_the_home_folder_as_a_tilde(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    path = tmp_path / ".config" / "hotbar" / "config.toml"
    assert toolbar.message([Problem(path, None, "no config file yet")]) == (
        "hotbar: ~/.config/hotbar/config.toml: no config file yet"
    )
