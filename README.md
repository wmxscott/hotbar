# hotbar

[![CI](https://github.com/wmxscott/hotbar/actions/workflows/ci.yml/badge.svg)](https://github.com/wmxscott/hotbar/actions/workflows/ci.yml)

A keyboard toolbar for tmux, for the tools you reach for while long work runs: lazygit, gh dash, a pull request review. `prefix t` turns the status bar, after your `status-left`, into a row of keycaps, and a letter opens that tool in a popup, in the folder of the pane you were in. When the tool exits, the popup closes and you're back at your work.

```
normal      [main] 0:zsh* 1:logs-                                         "laptop" 12:04 19-Nov-26
prefix t    [main] ↯ tools   g  ● lazygit   d  ● gh dash   n  ● nvim   b  ● btop    / search  esc
                   └ mauve   └ keycap: the letter on the tool's colour, its icon in it, its name muted
```

`[main]` is tmux's default `status-left`. The toolbar draws its label and icons from a [Nerd Font](https://www.nerdfonts.com): the sketch above stands in `↯` and `●` for them, and leaves out the colours.

- **It's instant.** The toolbar is a tmux format, built when hotbar loads, so no process starts on `prefix t`.
- **Your status bar is left alone.** Outside the toolbar, it draws exactly as it did without hotbar. In it, your `status-left` stays on the left, drawn as tmux draws it, and the toolbar takes the place of the window list and `status-right`.
- **Tools can depend on the pane you're in.** A tool can be given values from that pane, and be hidden when the pane lacks one. See [Values from the pane](#values-from-the-pane).

## Requirements

- **tmux 3.8 or later.**
- **[fzf](https://github.com/junegunn/fzf) 0.59 or later**, for [search](#search). Everything else works without it.
- **A [Nerd Font](https://www.nerdfonts.com)** in your terminal, for the toolbar's label and the icons in the example config. Any character works as a tool's icon.
- **Python 3.11 or later**, when installing from source.
- **macOS or Linux.**

## Install

### Homebrew

```sh
brew install wmxscott/tap/hotbar
```

Homebrew installs tmux and fzf too.

### From source

```sh
uv tool install git+https://github.com/wmxscott/hotbar
# or: pipx install git+https://github.com/wmxscott/hotbar
```

### A config

Start from the example, then check it:

```sh
mkdir -p ~/.config/hotbar
curl -fsSL https://raw.githubusercontent.com/wmxscott/hotbar/main/examples/config.toml \
  -o ~/.config/hotbar/config.toml
hotbar check
```

## tmux setup

Add this line to your tmux config:

```tmux
run-shell "hotbar init"
```

Then reload the config, with `tmux source-file` or your own reload key, and press `prefix t`.

- **`hotbar init`** reads the config, binds `prefix t` to the toolbar, and wraps `status-format[0]`, the first status line, so it draws your `status-left` and the toolbar while it's up, and your own bar otherwise. Running it again replaces everything it set, so reloads are safe.
- **Put it after anything that sets `status-format`.** A later `set -g status-format[0]` replaces the wrap until `hotbar init` runs again. Setting `status-left` and `status-right`, as most themes do, is fine anywhere.
- **The toolbar draws `status-left` as tmux's default status line does,** with `status-left-style` and `status-left-length`, and puts its label where the window list would start, after `status-left`'s own trailing spaces. A `status-left` that lights up for the prefix with `#{client_prefix}` stays lit in the toolbar, since tmux sets it in every key table but the root one.
- **After editing the config,** run `hotbar init` again for the toolbar and its letters to change: reload your tmux config, for example with a `prefix R` bound to `source-file`, or run `hotbar init` in any pane.
- **A mistake in the config changes nothing.** tmux shows one message naming the first problem and its line, and the toolbar from the last good config stays. See [Checking the config](#checking-the-config).

### Another key

`prefix t` is tmux's clock by default, and hotbar takes it over. To use another key:

```tmux
run-shell "hotbar init --key T"
```

- **`--key`** takes any tmux key name, such as `T` or `F2`, and no tool may use it. Pass the same `--key` to `hotbar check`.
- **Moving the toolbar** unbinds the key it was on, so `t` stays unbound until tmux restarts.

## Using it

### Keys

| Key | Does |
|---|---|
| `prefix t` | Open the toolbar |
| A tool's letter | Open that tool, and close the toolbar |
| `/` | [Search](#search) the tools |
| Esc, or `t` | Close the toolbar |
| Any other key | Close the toolbar. The key goes no further, so it never reaches the pane |
| `prefix t` again | Open it again: tmux reads the prefix before the toolbar sees it, so the toolbar stays up |

With [another key](#another-key), that key takes `t`'s place.

### A tool's popup

- **It opens in the middle of the terminal,** with the status line at the top or the bottom.
- **The border** is rounded, in the tool's colour, and the title is its icon and name.
- **It starts in the folder** of the pane you were in.
- **It closes when the tool exits.** Nothing is kept running.
- **Its size** is the tool's `width` and `height`, 80% of the terminal each by default.
- **A command that isn't found** on tmux's `PATH` shows `hotbar: can't start <command>: not found` in a tmux message, and the popup closes straight away. Tools run in tmux's environment, so a tool outside tmux's `PATH` needs its full path.

### Search

`/` opens a small popup in the middle of the terminal, titled `↯ tools` with a muted border, that lists the tools as the toolbar draws them:

- **Typing** filters by title.
- **`j` / `k`** move while nothing's typed. After that, they type, and the arrow keys move.
- **Enter** opens the highlighted tool, just as its letter would.
- **Esc** closes the search without opening anything.

Tools hidden from the toolbar by `requires` are left out. The popup fits the tools, unless [`[search]`](#top-level) sets its size, and is never larger than the terminal. Without fzf 0.59 or later, `/` says so in a tmux message.

## Configuration

The config is `~/.config/hotbar/config.toml`, or `$XDG_CONFIG_HOME/hotbar/config.toml` when that's set. `--config PATH` reads another file. [`examples/config.toml`](examples/config.toml) is a place to start.

```toml
theme = "auto"

[search]
width = 40

[[tools]]
id = "lazygit"
key = "g"
title = "lazygit"
command = ["lazygit"]
icon = ""
color = "green"
width = "95%"
height = "95%"
```

### Top level

| Setting | Default | |
|---|---|---|
| `theme` | `"auto"` | `"auto"`, `"dark"` or `"light"`. See [Colours](#colours) |
| `[search]` `width`, `height` | fits the tools | The search popup's size, in the same form as a tool's `width` and `height`. A size in cells is cut to the terminal's |

### `[[tools]]`

One table per tool, on the toolbar in this order.

| Setting | Default | |
|---|---|---|
| `id` | *(required)* | Letters, digits, `-` and `_`. Unique |
| `key` | *(required)* | The letter that opens it: one character, unique, not `/`, not a control character, and not the toolbar's own key |
| `title` | *(required)* | The name on the toolbar, in the search and in the popup's title |
| `command` | *(required)* | What to run, as a list, like `["gh", "dash"]`. It runs without a shell: for pipes, `&&` or variables, use `["sh", "-c", "…"]` |
| `icon` | `"•"` | Shown before the title. Usually a Nerd Font glyph, written as an escape like `""`, but any text works |
| `color` | `"blue"` | The colour of the keycap, the icon and the popup's border: a [Catppuccin colour name](#colour-names) |
| `width` | `"80%"` | The popup's width, in terminal cells (`120`) or a percentage of the terminal (`"95%"`) |
| `height` | `"80%"` | The popup's height, the same way |
| `env` | `{}` | Environment variables for the tool, each a tmux format, like `{ PANE = "#{pane_id}" }`. Names are letters, digits and `_`. See [Values from the pane](#values-from-the-pane) |
| `requires` | *(none)* | A tmux format. While it expands empty, the tool has no keycap and isn't in the search, and its letter only closes the toolbar |

Any other setting is a mistake, and [`hotbar check`](#checking-the-config) says where.

### Values from the pane

`env` values and `requires` are tmux formats, expanded against the pane you opened the toolbar from: `#{pane_id}`, `#{session_name}`, `#{pane_current_command}`, a pane option such as `#{@name}`, or anything else in tmux's FORMATS.

- **`env`** is expanded when the tool opens, and reaches it through `display-popup -e`. A value that expands empty sets the variable empty. A `#` is tmux's, so write `##` for a literal one.
- **`requires`** is checked each time the toolbar is drawn, so a keycap comes and goes as you move between panes, with no reload.
- **Only empty hides a tool.** A comparison such as `#{==:…}` expands to `0` when it's false, which isn't empty, so wrap it: `#{?#{==:#{pane_current_command},nvim},1,}`.

For example, take a tool that lists the pull requests one coding agent opened, given that agent's session id in `$SESSION_ID`. tmux doesn't know the id, so something has to put it on the agent's pane, such as the agent's start and end hooks:

```sh
tmux set-option -p -t "$TMUX_PANE" @agent-session-id "$id"   # when the agent starts
tmux set-option -p -u -t "$TMUX_PANE" @agent-session-id      # when it ends
```

Then the tool reads it from the pane you're in:

```toml
[[tools]]
id = "prs"
key = "p"
title = "prs"
command = ["pr-list"]
icon = ""
color = "mauve"
env = { SESSION_ID = "#{@agent-session-id}" }
requires = "#{@agent-session-id}"
```

- **In the agent's pane,** the toolbar has a `p` keycap, and `p` opens `pr-list` with `SESSION_ID` set to that agent's id.
- **In any other pane,** `#{@agent-session-id}` expands empty: there's no `p` keycap, the search leaves `prs` out, and `p` only closes the toolbar.

### Colour names

`rosewater`, `flamingo`, `pink`, `mauve`, `red`, `maroon`, `peach`, `yellow`, `green`, `teal`, `sky`, `sapphire`, `blue` and `lavender`: Catppuccin's accents, each drawn from the palette for the terminal's mode. See [Colours](#colours).

## Checking the config

```sh
hotbar check
```

```
ok
  g  lazygit
  d  gh dash
  n  nvim
  b  btop
```

With mistakes, it prints each one as `path:line: message`, in line order, and exits 1:

```
/home/me/.config/hotbar/config.toml:1: theme must be "auto", "dark" or "light"
/home/me/.config/hotbar/config.toml:11: tools 'lazygit' and 'tig' both use key 'g'
/home/me/.config/hotbar/config.toml:13: tool 'tig': command must be a non-empty list of strings, like ["lazygit"]
```

A problem with no line, such as a missing file, is `path: message`. `hotbar check` doesn't expand `requires`, so it lists every tool.

`hotbar init` shows only the first problem, in a tmux message, with the home folder as `~`:

```
hotbar: ~/.config/hotbar/config.toml:1: theme must be "auto", "dark" or "light" (1 of 3 problems; hotbar check lists them)
```

## Colours

The colours are Catppuccin Latte when the terminal is light, and Macchiato when it's dark. The label is mauve, and the names and hints are muted (overlay1).

- **`theme = "auto"`** follows each terminal's mode as tmux 3.8 reports it, in `#{client_theme}`, for terminals that tell it. The toolbar, the popups' borders and the search follow it without a reload, and two clients can differ.
- **Until a terminal reports a mode,** hotbar uses the one it detects: theme-monitor's trigger file (`$XDG_DATA_HOME/theme-monitor/theme-change.trigger`), else macOS's appearance setting, else light. The toolbar and the borders use what `hotbar init` detected, and the search detects it as it opens.
- **`theme = "dark"` or `"light"`** fixes it.

## Commands

| Command | |
|---|---|
| `hotbar init [--config PATH] [--key KEY]` | Put the toolbar on `prefix KEY` (by default `t`), and wrap the status line. Run it from tmux.conf. Outside tmux, it exits 1 |
| `hotbar check [--config PATH] [--key KEY]` | Print `ok` and each tool's key and title, or each problem with its line and exit 1. `--key` is the toolbar's key, which no tool may use |
| `hotbar search --pane PANE --client CLIENT [--config PATH]` | The search, which `/` runs in its popup. It's not meant to be run by hand |
| `hotbar --version` | Print the version |

## Coming from herdr-launchpad

hotbar replaces [herdr-launchpad](https://github.com/wmxscott/herdr-launchpad) for tmux. The config stays TOML, and most of it moves over by hand; there's no converter.

| herdr-launchpad | hotbar |
|---|---|
| `~/.config/herdr/plugins/config/launchpad/config.toml` | `~/.config/hotbar/config.toml` |
| `[[entries]]` | `[[tools]]` |
| `[picker]` `width`, `height` | `[search]` `width`, `height` |
| `slot = 1` … `9`, and a Herdr key bound to each slot | `key = "g"`: the letter after `prefix t`, which every tool needs |
| `key`, a label shown in the picker | Gone: `key` is the letter itself |
| `title`, defaulting to the `id` | `title`, required |
| `command = "…"`, a string run with `sh -c` | A list only: `["sh", "-c", "…"]` |
| `color` or `colour`: a name or `"#rrggbb"` | `color` only, and a [name](#colour-names) only |
| `env`, plain strings | `env`, tmux formats. Values without a `#` carry over as they are |
| `session_env = "NAME"` | `env = { NAME = "#{@option}" }`, from a pane option something sets. See [Values from the pane](#values-from-the-pane) |
| `requires_session = true` | `requires = "#{@option}"` |
| `HERDR_ACTIVE_PANE_ID`, `HERDR_ACTIVE_PANE_CWD` and the like | Ask for what the tool needs in `env`, like `{ PANE = "#{pane_id}" }`. It starts in the pane's folder |
| `theme` | `theme`. With nothing to go on, `auto` is light, where launchpad's was dark |
| The Herdr bindings for `launchpad.open` and `launchpad.slot-<n>` | The one `tmux.conf` line, `run-shell "hotbar init"` |
| Read each time the picker opens | Read by `hotbar init`: run it again after editing |

A tool, before and after:

```toml
# herdr-launchpad
[[entries]]
id = "lazygit"
command = ["lazygit"]
icon = ""
color = "green"
slot = 1

# hotbar
[[tools]]
id = "lazygit"
key = "g"
title = "lazygit"
command = ["lazygit"]
icon = ""
color = "green"
```

A string command becomes a list through `sh -c`, so `'brew upgrade; read -r _'` becomes `["sh", "-c", "brew upgrade; read -r _"]`.

## Known limits

- **Dozens of tools.** `hotbar init` sends all its bindings to tmux as one command, and tmux limits a command's length. With `theme = "auto"`, which draws both palettes, 19 short tools fit and 20 don't; a fixed theme fits a few more, and long titles or `env` fewer. Past the limit, `init` shows `hotbar: command too long` and changes nothing.
- **A popup sized in cells larger than the terminal doesn't open.** tmux opens no popup larger than the terminal, and a tool's `width` and `height` aren't cut to fit. Use percentages.
- **No persistent tools, yet.** Every tool quits when its popup closes, and starts afresh next time. Keeping tools running between opens is planned.

## Development

```sh
uv sync
uv run pytest
uv run ruff check && uv run ruff format --check
```

The tests that need tmux start their own throwaway servers (`tmux -L <name> -f /dev/null`), with a client attached through a pty, so they never touch yours. They're skipped without tmux 3.8, and the search's without fzf 0.59.

## License

[MIT](LICENSE)
