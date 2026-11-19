# hotbar

[![CI](https://github.com/wmxscott/hotbar/actions/workflows/ci.yml/badge.svg)](https://github.com/wmxscott/hotbar/actions/workflows/ci.yml)

A keyboard toolbar for tmux, for the tools you reach for while long work runs: lazygit, gh dash, a pull request review. `prefix t` turns the status bar into a row of keycaps, and a letter opens that tool in a popup, in the folder of the pane you were in. When the tool exits, the popup closes and you're back at your work.

**Not released yet.** So far, `hotbar check` reads the config, `~/.config/hotbar/config.toml`, and lists its tools or reports each problem with its line. [`examples/config.toml`](examples/config.toml) is a place to start.

## License

[MIT](LICENSE)
