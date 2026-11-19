# Plan: hotbar 1.0.0

| | |
|---|---|
| **Status** | draft · next: H1 |
| **Updated** | 2026-11-19 |
| **Tracker** | — |
| **Related** | [design, approved 2026-11-19](../superpowers/specs/2026-11-19-hotbar-design.md); [herdr-launchpad](https://github.com/wmxscott/herdr-launchpad), the Herdr plugin it replaces; switchboard's [cards plan](https://github.com/wmxscott/switchboard/blob/main/docs/plans/toqdop-sidebar-cards.md), which Stack S waits on |

## Goal

hotbar gives tmux a keyboard toolbar for the tools you reach for while long work runs. `prefix t` turns the status bar into a row of keycaps, and a letter opens that tool in a popup in the current pane's folder. It replaces herdr-launchpad in the user's move from Herdr to tmux, and anyone can install it from the tap.

**Falsifiable:** after this plan, in the user's tmux:
- `prefix t` shows `tools` and a keycap per configured tool, at once, and Esc brings the normal bar back unchanged;
- `prefix t` then `g` opens lazygit in a green-bordered popup in the pane's repo, and quitting lazygit closes it;
- in a pane with a Claude agent, `prefix t` then `p` opens `prs` scoped to that agent, and in a pane without one, there's no `p` keycap.

### Done when

- [ ] hotbar 1.0.0 is released through `wmxscott/homebrew-tap`, CI green on macOS and Linux, and installed here.
- [ ] `wmxscott/hotbar` requires its CI checks (`gh-harden` re-run with the job names).
- [ ] The README covers install, the config reference, the keys, and a "coming from herdr-launchpad" mapping.
- [ ] switchboard records each Claude agent's session id on its pane, released through the tap.
- [ ] In the user's tmux, after the rollout:
  - the toolbar shows their 7 tools;
  - each letter opens its tool;
  - `/` finds a tool by typing;
  - `p` is scoped to the agent below, and missing without one;
  - the normal status bar, switchboard's segment included, is unchanged outside toolbar mode.

## Settled: do not re-derive

- **S1 The design is approved** (2026-11-19). The spec linked above records the user's decisions and the builder check. This plan is the live artifact, and it carries every decision it needs.
- **S2 Toolbar mode (user):**
  - **`prefix t`** turns the status bar into the toolbar.
  - **On the left:** a plain label, `` (nf-fa-bolt, U+F0E7) then `tools` in lower case, mauve and bold, with no background.
  - **Then a keycap per tool:** the letter, bold, on a block of the tool's colour; then the icon in that colour; then the name in a muted colour. Tools are separated by two spaces.
  - **On the right, muted:** `/ search  esc`.
  - **A letter** opens that tool.
  - **Esc, or `prefix t` again,** leaves without opening anything. The user accepted this when it was offered as a guess.
  - **`/`** opens a fuzzy search over the tools, also an accepted guess.

  **Rejected:**
  - the fuzzy popup picker as the main way in (today's launchpad);
  - boxed "chips" and icons-only styles;
  - an upper-case `TOOLS`.
- **S3 A tool's popup (user):** a rounded border in the tool's colour, titled with its icon and name. It starts in the folder of the pane you were in, and closes when the tool exits.
- **S4 Persistent tools are deferred (user: "low priority").** Every tool quits when its popup closes. The finding for when this is revisited is in the spec's Non-goals: a separate tmux server silently disables tmux-continuum's autosave, and hidden sessions need switchboard and dotfiles changes.
- **S5 `prs` stays scoped to the pane's agent (user).** That needs two things:
  - switchboard records the agent's session id on its pane (Stack S);
  - hotbar's `env` and `requires` are tmux formats, expanded against the pane you came from.

  In a pane without an agent, `prs` has no keycap.
- **S6 The config:**
  - TOML at `$XDG_CONFIG_HOME/hotbar/config.toml` (default `~/.config/hotbar/config.toml`), with `theme` at the top level and `[[tools]]` tables, as in [The config schema](#the-config-schema);
  - `key` replaces launchpad's `slot`;
  - `env` and `requires` replace `session_env` and `requires_session`;
  - no migration command (my call): the README maps the fields, and the user's config is converted by hand in R2.
- **S7 The toolbar is instant and leaves the normal bar alone** (anti-goals):
  - no process starts on `prefix t`;
  - outside toolbar mode, the status bar renders exactly as without hotbar;
  - nothing can leave a client stuck in the key table.
- **S8 Colours follow light and dark,** with the full Catppuccin palette: Latte when light, Macchiato when dark. tmux 3.8's own theme colours cover only ten names, so hotbar resolves the config's names itself.
- **S9 The repo:**
  - **`wmxscott/hotbar`:** public, created 2026-11-19, bootstrapped with the user's `gh-harden`. CODEOWNERS is the first commit (`e2eaff1`), and the rulesets require PRs and code-owner approval, with admin bypass.
  - **Rulesets to finish:** `gh-harden` is re-run with the CI job names once H1's CI exists.
  - **Commits:** plain signed git with a noreply address, like switchboard.
  - **Layout:** a `.bare` worktree layout under `~/Developer/wmxscott/hotbar`.
  - MIT licence, and no personal data.
- **S10 Facts about tmux and the user's config** (checked 2026-11-19):
  - tmux 3.8's default `status-format[0]` draws `status-left`, the window list and `status-right`. The user's config sets those three and never sets `status-format`. So wrapping `status-format[0]` preserves their bar.
  - The user's `status-left` already switches on `#{client_key_table}` (its `RESIZE` indicator), so drawing from the key table is proven in their setup.
  - `prefix t` is tmux's default clock, which the user doesn't use.
  - `display-popup` takes `-b rounded`, `-S`, `-T`, `-d` and `-e`.
- **S11 Reuse launchpad by copying.** `herdr-launchpad/lib/launchpad.py` (about 900 lines) has config loading, validation with located error messages, the Catppuccin palette and theme detection. hotbar copies what fits, under the same author and the same MIT licence. It doesn't depend on herdr-launchpad, which keeps working for Herdr.
- **S12 One stack for hotbar.**
  - **Rejected:** a separate "config" stack beside "toolbar". The toolbar is generated from the config schema, so they share it; a split would be a dependency, not a peer.
  - Stack S (switchboard) and Stack R (rollout) live in other repos, and are listed here so the plan is whole.
- **S13 Tests never touch the user's tmux server.** Real checks use `tmux -L <name> -f /dev/null`, and run hotbar from the checkout by full path.

## The config schema

### Top level

| Setting | Default | |
|---|---|---|
| `theme` | `"auto"` | `"auto"`, `"dark"` or `"light"`; see [Colours](#colours) |
| `[search]` `width`, `height` | fits the tools | the search popup's size |

### `[[tools]]`, in toolbar order

| Setting | Required | |
|---|---|---|
| `id` | yes | letters, digits, `-` and `_`; unique |
| `key` | yes | one character; unique; not `/`; not a control key |
| `title` | yes | the name on the keycap and the popup title |
| `command` | yes | an argv list |
| `icon` | no | any character |
| `color` | no | a Catppuccin colour name (`rosewater` … `lavender`) |
| `width`, `height` | no | cells, or a percentage (`"95%"`) |
| `env` | no | `{ NAME = "<tmux format>" }`, expanded against the pane you came from |
| `requires` | no | a tmux format; when it expands empty, the keycap hides and the key does nothing |

### Errors

- A missing or invalid file is reported with the file and the line, as launchpad does, by `hotbar check` and by `hotbar init`.
- On a bad config, `init` installs no toolbar and shows one tmux message naming the problem. The rest of tmux is untouched.

## Toolbar mode

### Loading

- **One line in `tmux.conf`:** `run-shell "hotbar init"`. Re-running it (`prefix R`) leaves exactly one copy of everything: no double-wrapped `status-format`, no stale letters in the key table.
- **It binds `prefix t`** to switch the client to the key table `hotbar`.
- **In that table:**
  - each tool's letter opens it, and returns the client to the root table;
  - `/` opens the search;
  - Escape and `t` return to the root table;
  - any other key returns to the root table and does nothing.

### Drawing

- **One lead:** wrap `status-format[0]` once, so the status line is `#{?#{==:#{client_key_table},hotbar},<toolbar>,<the format that was there>}`. The toolbar is a static format generated from the config at `init`, so no process runs on `prefix t`.
- **A keycap per tool:** `#[bg=<colour>,fg=<base>,bold] <key> #[default] #[fg=<colour>]<icon> #[fg=<muted>]<title>`, two spaces apart, after the label. Each is wrapped in `#{?<requires>,…,}` when the tool has `requires`.
- **On the right,** muted: `/ search  esc`.
- The builder picks the exact mechanism, as long as S7 holds, and checks it against the user's real `tmux.conf` and `theme.conf` loaded into a throwaway server.

## Popups

- A letter runs `display-popup -E -b rounded -S fg=<colour> -T "<icon> <title>" -w <width> -h <height> -d "#{pane_current_path}"`, with `-e NAME=<expanded env>` per `env` entry, then the tool's command.
- The formats in `env` and `requires` are expanded against the pane the toolbar was opened from.
- The popup closes when the command exits. A command that fails to start shows a tmux message and returns, never a blank popup that stays open.

## Values from the pane

### switchboard (Stack S)

- switchboard writes the agent's session id to a pane option, `@switchboard-session-id`, from the hook payload's `session_id`, for Claude at least, and for Codex and Pi if their payloads carry one.
- It's cleared with switchboard's other options when the agent ends, and stays in its hook's fast path with no new imports.

### hotbar

- The user's `prs` becomes `env = { PR_TRACKER_SESSION_ID = "#{@switchboard-session-id}" }` with `requires = "#{@switchboard-session-id}"`.
- Before Stack S lands, `requires` expands empty, so `prs` simply has no keycap.

## Search

- `/` opens a small popup running fzf over the tools: each tool's keycap, icon and name. Typing filters, `j`/`k` (outside typing) or the arrows move, Enter opens the tool as its letter would, and Esc closes.
- The look matches switchboard's picker, copied rather than imported.
- fzf 0.59 or later, matching switchboard's floor.

## Colours

- Config colour names resolve to Catppuccin Latte or Macchiato hex values, in the same palette as launchpad.
- `theme = "auto"` follows the terminal's light and dark mode without a reload. With `"dark"` or `"light"`, it's fixed.
- How `auto` follows changes is the builder's call. Options include tmux 3.8's mode detection, theme-monitor's trigger file as switchboard's `theme.py` reads it, or two pre-generated formats picked by a tmux condition.

## Stacks and phases

### Stack H: hotbar

- **Base:** `main`
- **Owns:** `src/hotbar/**`, `tests/**`, `examples/**`, `pyproject.toml`, `uv.lock`, `README.md`, `LICENSE`,
  `.github/workflows/**`, `contrib/hotbar.rb`, `docs/plans/tor8q8-hotbar.md`
- **Independent of:** S (before S lands, `prs` has no keycap), R
- **Depends on:** —

| Phase | Lands | Depends on |
|---|---|---|
| H1 | the package, the CLI skeleton, CI, the licence, the formula draft | — |
| H2 | the config: loading, validation, the palette, `hotbar check` | H1 |
| H3 | `hotbar init`: the key table and the toolbar drawn on `prefix t` | H2 |
| H4 | the letters open their tools in popups, with `env` and `requires` | H3 |
| H5 | `/` search | H4 |
| H6 | README and 1.0.0 | H5 |

- [ ] H1: package, CLI, CI
- [ ] H2: the config
- [ ] H3: the toolbar
- [ ] H4: opening tools
- [ ] H5: search
- [ ] H6: README and 1.0.0

**H1: package, CLI, CI.**
- A uv project with the `src/hotbar` package, for Python 3.11 or later. `hotbar --version` and `hotbar --help`.
- Ruff config matching switchboard's.
- CI: a test matrix on `macos-15` and `ubuntu-latest` × Python 3.11 and 3.14 (lint, tests, a smoke test), plus a gitleaks `secrets` job, as in switchboard's `ci.yml`.
- MIT `LICENSE`, a README stub, and `contrib/hotbar.rb` (a virtualenv formula like `contrib/switchboard.rb`, with a zeroed sha256).
- After it merges, the orchestrator re-runs `gh-harden wmxscott/hotbar` with the CI job names (S9).
- Cites S9 and S11.

*Shippable when:* CI is green; `uv run hotbar --version` prints the version.
*Split seam:* CI after the package.

**H2: the config.**
- Loading from S6's path, the schema in [The config schema](#the-config-schema), and the located errors.
- The palette, and theme detection for `auto`.
- `hotbar check`: prints "ok" and the tools, or the problems, and exits 1 on problems.
- `examples/config.toml` with a handful of common tools: lazygit, gh dash, nvim.
- Copied from launchpad where it fits (S11).
- Cites S6, S8 and S11.

*Shippable when:* tests and lint pass; `hotbar check` on the example config prints its tools; a config with a duplicate `key` reports the line.
*Split seam:* the palette and theme after loading and validation.

**H3: the toolbar.**
- `hotbar init`, as in [Loading](#loading) and [Drawing](#drawing), with idempotent re-runs.
- The bad-config path from [Errors](#errors).
- Letters are bound to leave the mode only; opening tools is H4.
- Cites S2, S7, S8 and S10.

*Shippable when:* tests and lint pass. On a throwaway server loaded with the user's real `tmux.conf` and `theme.conf` (with its plugins line removed):
- `prefix t` (`send-keys -K` from an attached pty client) switches the status line to the toolbar, as captured;
- Esc restores it byte for byte;
- `init` run twice leaves one wrap.
*Split seam:* the key table and its bindings first, then the `status-format` wrap.

**H4: opening tools.**
- The letters run the popup in [Popups](#popups), with `env` expanded and `requires` honoured.
- The failure path.
- Cites S3 and S5.

*Shippable when:* tests and lint pass. On a throwaway server:
- a letter opens a popup with the configured border colour and title, in the pane's folder;
- a tool's exit closes it;
- a tool with `requires = "#{@x}"` has no keycap until the pane option `@x` is set, and then its `env` gets the value.
*Split seam:* `env`/`requires` after the plain popup.

**H5: search.**
- [Search](#search).
- Cites S2.

*Shippable when:* tests and lint pass; on a throwaway server, `prefix t` then `/`, typing part of a title, and Enter opens that tool.
*Split seam:* none needed.

**H6: README and 1.0.0.**
- **The README:**
  - what hotbar is, with a text rendering of the toolbar;
  - install through the tap;
  - the `tmux.conf` line, and choosing a key other than `t`;
  - the config reference;
  - colours;
  - a "coming from herdr-launchpad" field mapping;
  - the requirements: tmux 3.8, Python 3.11, fzf 0.59 and a Nerd Font.
- `__version__` 1.0.0, and the formula url.
- After it merges: tag `v1.0.0`, then the tap formula and `brew install`.

*Shippable when:* tests and lint pass; the README's commands and fields match the code.
*Split seam:* none needed.

### Stack S: switchboard records the agent's session id

- **Base:** `main`
- **Owns:** `src/switchboard/**`
- **Independent of:** H, R (before S lands, `prs` has no keycap; after it lands, hotbar needs no change)
- **Depends on:** —

This stack is in `wmxscott/switchboard`, and `Owns` is relative to that repo. Its files are also owned by switchboard's cards plan (Stack A), so S1 starts only after that stack has landed (see [Blocked on](#blocked-on)).

| Phase | Lands | Depends on |
|---|---|---|
| S1 | `@switchboard-session-id` on the agent's pane, and a switchboard release | — |

- [ ] S1: the agent's session id

**S1: the agent's session id.**
- As in [switchboard (Stack S)](#switchboard-stack-s).
- Tests for Claude, and for Codex and Pi when their payloads carry an id.
- A README line in switchboard's options list.
- Released through the tap as a patch release after 1.4.0.

*Shippable when:* switchboard's tests and lint pass; on a throwaway server, a `SessionStart` payload piped to `switchboard hook SessionStart` sets the option, and `SessionEnd` clears it.
*Split seam:* none needed.

### Stack R: rollout

- **Base:** `main`
- **Owns:** `stow/tmux/**`, `stow/brew/**`
- **Independent of:** —
- **Depends on:** H, S

R1 is in `wmxscott/dotfiles`, which commits through `git app` and `gh app-auth exec`. R2 is in the private dotfiles repo, through a PR to `main`, then merged into the `wmxscott` leaf branch.

| Phase | Lands | Depends on |
|---|---|---|
| R1 | dotfiles: the Brewfile entry and the `tmux.conf` line | H6 |
| R2 | private: the user's hotbar config | R1, S1 |

- [ ] R1: dotfiles
- [ ] R2: the user's config

**R1: dotfiles.**
- `hotbar` in `stow/brew/.Brewfile`.
- `run-shell "command -v hotbar >/dev/null && hotbar init; exit 0"` in `tmux.conf`.
- Restow with `dotf`.

*Shippable when:* after `brew install`, `prefix R` in the user's tmux shows the toolbar on `prefix t`. The user does the reload.
*Split seam:* none needed.

**R2: the user's config.**
- `~/.config/hotbar/config.toml` in the private package, converted from their launchpad config, as listed at the end of the spec:
  - 7 tools;
  - `projects` dropped;
  - `wkt` runs `wkt --tmux`;
  - `prs` gets `env` and `requires`.
- The letters are confirmed with the user before the PR.

*Shippable when:* `hotbar check` passes on it, and the user's toolbar shows the 7 tools.
*Split seam:* none needed.

## Forest from the trees

### Challenge

There's no advisor tool in this session, so here is the strongest case against the sequence, argued myself.

- **The case:**
  - H3 lands a toolbar whose letters do nothing, a visible feature that doesn't work.
  - H1 and H2 land nothing a user can see.
  - Three PRs could pass without anyone opening a tool, and a wrong call in H3's drawing (the `status-format` wrap) would surface only once H4 makes the toolbar worth using daily.
- **What it surfaced:**
  1. There's no release before H6, so a do-nothing toolbar never reaches a user. H3 stays separate because it carries the riskiest call, rewriting the status line. Isolating it means its review is about one thing: the normal bar must stay intact.
  2. H3's *Shippable when* tests against the user's real `tmux.conf` and `theme.conf`, not a bare config. That catches the drawing risk at H3, not at rollout.
  3. Stack S is independent of H on purpose. If the cards plan runs long, hotbar still ships, with `prs` hidden until S lands.
- **Considered and rejected:** merging H4 and H5. Search is optional to the Goal's core (letters), and keeping it separate means a slip there can't delay the letters.

### Drift test

1. **If every phase after this one were cancelled, would the user's tmux be at least as good as before?** In particular: is the normal status bar unchanged, and is no key left doing something surprising?
2. **Does this PR serve "a letter away from a tool, in a popup, from a toolbar on `prefix t`", or is it building something the Goal doesn't ask for,** such as persistence, a launcher for projects, or mouse support?

## Not doing

- **Persistent tools:** deferred by the user (S4).
- **A config migration command:** rejected (S6).
- **Herdr support:** out of scope; herdr-launchpad keeps it.
- **The `projects` tool:** dropped while the herdr-projects port is on hold.
- **The mouse:** out of scope.

## Blocked on

- **Stack S (S1) waits for switchboard's cards plan, Stack A,** to land (switchboard 1.4.0), because both change `src/switchboard/**`. Owner: this session's orchestrator. It blocks S1, and through it R2.

## Log

- 2026-11-19: repo created and bootstrapped with `gh-harden` (CODEOWNERS `e2eaff1`); plan written from the approved design.
- 2026-11-19: H1 landed as #2; gh-harden re-run to require the five CI checks.
