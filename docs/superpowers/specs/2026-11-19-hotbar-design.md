# hotbar: design

**Status:** approved by the user on 2026-11-19. The builder check is done (2026-11-19), and its questions are answered here.

## Why

The user is moving from Herdr to tmux. In Herdr they use their own plugin, `herdr-launchpad` (`wmxscott/herdr-launchpad`, Python and fzf, about 900 lines). It opens their most-used terminal tools in popups.

In their words, it's for the intermittent tasks they do while long-running work goes on (lazygit, gh dash, PR review) before going back to the work. It was designed to replace the toolbars of traditional IDEs. Today you open the launchpad, type a couple of keys to fuzzy-search, press Enter, use the tool in a popup, then dismiss it.

The user wants it redesigned for tmux, not ported line for line. They chose a **toolbar mode on the status bar**, keyboard only, with icons and colours used "in an elegant way".

hotbar is a new public repository, `wmxscott/hotbar`, and a command, `hotbar`. herdr-launchpad stays as it is while the user still runs Herdr. A later project, a public "LazyVim for tmux" distro, will bundle hotbar.

## Goals (the user's decisions)

- **`prefix t` turns the status bar into the toolbar.** It shows, from the left:
  - a plain label, the icon `` (nf-fa-bolt) then `tools` in lower case, in mauve, bold, with no background;
  - then each tool as a **keycap**: its letter, bold, on a block of the tool's colour, then the tool's icon in that colour, then its name in a muted text colour;
  - and on the right, muted, `/ search  esc`.
- **A tool's letter opens it in a popup.** The popup has a rounded border in the tool's colour, and a title of its icon and name. The tool starts in the folder of the pane you were in, and the popup closes when the tool exits.
- **Tools that need the agent in the pane underneath (user):** `prs` shows only the pull requests of the coding agent in the pane you came from, as it does under Herdr today. In a pane with no agent, a tool like that is hidden from the toolbar. See [Values from the pane](#values-from-the-pane).
- **Letters are the user's to assign**, along with the icon, colour and size, in the config.
- **The look** is the user's pick from mockups: "A, keycaps", with the plain label from "B". The mockup is reproduced below.

```
normal:    ● widget/fix-login   1 claude  2 zsh                              ▲ gadget/main
prefix t:   tools   g  lazygit   r  tuicr   d  gh dash   p  prs   n  nvim   / search  esc
            └ mauve  └ keycap: letter on the tool's colour, icon in its colour, name muted
```

These were offered as guesses and the user didn't object:
- **Esc, or `prefix t` again,** leaves toolbar mode without opening anything, and the normal bar comes back.
- **`/`** opens a fuzzy search over the tools in a small popup, in the look of switchboard's picker. Enter opens the highlighted tool.
- **The config stays TOML, like launchpad's,** so the user's current config moves over with a letter added to each tool.

## Non-goals

- Herdr support. herdr-launchpad keeps that.
- A project list or launcher. The herdr-projects port was dropped (user, 2026-11-20): with sessions restored across restarts, opening a repo that has none is rare, and `wkt --tmux` from its folder covers it.
- The mouse. Nothing needs it.
- A config migration command. The README shows the mapping, and the user's own config is converted by hand in the rollout (my call).
- **Persistent tools: deferred (user, 2026-11-19, "low priority").** Every tool quits when its popup closes. For when it's revisited, the design question is already known:
  - **A separate tmux server** (`tmux -L hotbar`) for kept-alive tools silently disables tmux-continuum's autosave. Continuum v3.1.0 (`continuum.tmux`, `another_tmux_server_running`) counts the processes whose command starts with `tmux`, excluding the current server, against the current server's clients. It only wires its save call into `status-right` when they match. The user's `theme.conf` resets `status-right` on every `prefix R`, so a kept-alive tool at reload time means autosave stops until the next clean reload or restart.
  - Hiding the server from that count (by launching under another name) is fragile, because tmux renames its server process on Linux.
  - **Hidden sessions on the user's own server** avoid the count, since their popup clients are the server's own clients. They need switchboard to skip `_`-prefixed sessions, the dotfiles `choose-tree` key to filter them, and hotbar to tidy leftovers at startup.

## Anti-goals: failures even if it works

- **A slow toolbar.** `prefix t` must redraw the bar at once, as tmux's own mode indicators do (the user's bar already shows `RESIZE` from a key table). No process starts on `prefix t`.
- **A broken normal bar.** Outside toolbar mode, the status bar looks exactly as it does without hotbar. That includes switchboard's `#{E:@attention}` segment and the user's own `status-left`/`status-right`.
- **Being stuck in toolbar mode,** for example when a key isn't bound or a tool fails to start.
- **A config mistake that silently does nothing.** As in launchpad, mistakes are reported with where they are.

## The config

- **Where:** `~/.config/hotbar/config.toml` (XDG; `$XDG_CONFIG_HOME/hotbar/config.toml`). It's read at load and on `hotbar reload`.
- **Top level:** `theme = "auto" | "dark" | "light"`, as in launchpad, plus anything the builder needs for the search popup's size.
- **One `[[tools]]` table per tool, in toolbar order:**

| Setting | Required | Meaning |
|---|---|---|
| `id` | yes | Letters, digits, `-` and `_`. Unique |
| `key` | yes | One character, unique, not `/` and not Escape |
| `title` | yes | The name on the toolbar and the popup |
| `command` | yes | argv list, as launchpad |
| `icon` | no | Any character; a Nerd Font glyph in the examples |
| `color` | no | A Catppuccin colour name (`green`, `peach`, `blue`, `mauve`, `teal`, `yellow`, `sapphire`, `lavender`, …), as launchpad |
| `width`, `height` | no | As launchpad: cells or a percentage |
| `env` | no | Environment variables for the tool, each a tmux format expanded against the pane you came from. See [Values from the pane](#values-from-the-pane) |
| `requires` | no | A tmux format, expanded against the pane you came from. When it's empty, the tool is hidden from the toolbar and its key does nothing |

- launchpad's other fields (`slot`, the picker sizes) go. `key` replaces `slot`. `env` and `requires` replace launchpad's `session_env` and `requires_session`.
- Field names are the builder's call, as long as `prs` can be expressed.
- Validation and error messages reuse launchpad's code where it fits.

## Colours

- Colours follow light and dark mode, like the rest of the setup: Catppuccin Latte when light, Macchiato when dark.
- tmux 3.8's own theme colours cover only ten names, so hotbar needs the full Catppuccin palette for the config's names.
- Following the terminal's mode without a reload is required. The mechanism is the builder's call. switchboard's `theme.py` detects the mode (`SWITCHBOARD_THEME`, theme-monitor's trigger file, then macOS `defaults`), and tmux 3.8 has `theme detect`.

## How it fits into tmux

### Loading

- **One line in `tmux.conf`,** for example `run-shell "hotbar init"`. It binds `prefix t`, builds the key table and the toolbar from the config, and wires whatever hooks are needed.
- **`t` is free** in the user's config: tmux's default `t` is the clock, which the user doesn't use.
- The README documents choosing another key.

### Toolbar mode

- `prefix t` switches the client to a key table (`hotbar`) that holds one binding per tool letter, plus `/`, Escape and `prefix t`.
- Any other key leaves the mode without doing anything.
- After a letter, `/` or Escape, the client is back in the root table.
- The status bar shows the toolbar while the client's key table is `hotbar`, and the normal bar otherwise.
- **One lead:** wrap the existing `status-format[0]` in `#{?#{==:#{client_key_table},hotbar},<toolbar>,<the existing format>}` at load. That keeps whatever the user has, and draws with no process on `prefix t`.

### Popups

- `display-popup -E` with `-b rounded`, `-S fg=<colour>`, `-T "<icon> <title>"`, the configured size, and `-d #{pane_current_path}`.

### Values from the pane

- **Today:** under Herdr, launchpad asked Herdr for the agent session in the focused pane, and gave `prs` that id as `PR_TRACKER_SESSION_ID`. Without one, `prs` was unavailable.
- **In tmux:** nothing records an agent's session id yet. switchboard's hooks receive it in every payload (`session_id`), so switchboard records it on the agent's pane, in a pane option such as `@switchboard-session-id`, and clears it with the rest of its options when the agent ends.
  - That's a small switchboard change, landing in its own release after 1.4.0 (the cards), whose stack owns those files.
  - At least Claude must record it, since that's what `prs` (pr-tracker) tracks. Codex and Pi follow if their payloads carry an id.
- **hotbar's side:**
  - a tool's `env` values and its `requires` are tmux formats, expanded against the pane the toolbar was opened from;
  - `env` reaches the tool through `display-popup -e`;
  - `requires` hides the keycap when it's empty. The toolbar is drawn by tmux, so this is a format conditional, with no process started.
- **The user's `prs` becomes:** `env = { PR_TRACKER_SESSION_ID = "#{@switchboard-session-id}" }`, `requires = "#{@switchboard-session-id}"`.

### Search

- `/` opens a small popup with fzf: each tool's icon, name and letter, in switchboard's picker look (j/k, Enter, Esc, typing to search).
- **fzf version:** switchboard's floor is 0.59, and the same floor or lower is fine for this simple list.

## Constraints

- tmux 3.8 or later, Python 3.11 or later, and fzf (for search only).
- macOS and Linux, with CI on both, like switchboard.
- **A new public repository,** `wmxscott/hotbar`, bootstrapped with the user's `gh-harden` (dotfiles `stow/gh/.local/bin/gh-harden`). The empty repo gets its CODEOWNERS first commit and rulesets, all work lands through PRs, and `gh-harden` is re-run with the CI job names once CI exists.
- **MIT licence,** and no personal data in the repo.
- **Shipped through `wmxscott/homebrew-tap`** with a `contrib/hotbar.rb` draft, like switchboard.
- **switchboard:** one small change outside this repo, recording the agent's session id on its pane (see [Values from the pane](#values-from-the-pane)). It lands after switchboard 1.4.0.
- **Rollout, after the first release:**
  - dotfiles gains the `tmux.conf` line and a Brewfile entry;
  - the private package gains the converted config, as in [The user's tools](#the-users-tools-for-the-rollout-and-the-examples);
  - herdr-launchpad and its Herdr config are untouched.
- Built as a stacked plan, with PRs of at most 400 production lines. Tests never touch the user's tmux server; they use `tmux -L <name> -f /dev/null`.

## Left to the builder

- How the toolbar is drawn: the status-format wrap, or another approach that keeps the normal bar intact and draws instantly.
- How colours follow light and dark mode.
- How `hotbar init` reloads cleanly when run twice (`prefix R`).
- How much of launchpad's code is reused.

## The user's tools, for the rollout and the examples

From their launchpad config:
- lazygit (green, U+E702), tuicr (peach, U+F4D2), gh dash (blue, U+F09B), pull requests (mauve, U+E726, scoped to the pane's agent);
- nvim (teal, U+E7C5), update dotfiles (yellow, U+F2C1), wkt (U+E725).

Two of launchpad's tools change (my calls, from the builder check):
- **`projects` is dropped,** because it runs Herdr's projects plugin, which won't be ported.
- **`wkt` runs `wkt --tmux`** instead of `wkt --herdr`. It duplicates `prefix W`, which is harmless.

The letters in the mockup were my guesses: `g` lazygit, `r` tuicr, `d` gh dash, `p` prs, `n` nvim, `u` dotfiles, `w` wkt. The user confirms them at rollout.
