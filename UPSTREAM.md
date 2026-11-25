# Upstream attribution

This project contains Caelestia Shell v2.5.0, originally published at:

- https://github.com/caelestia-dots/shell
- https://github.com/caelestia-dots/shell/releases/tag/v2.5.0

The source archive was available in the original machine's AUR build cache
and its SHA-256 was verified against the cached PKGBUILD before extraction:

`6bef9feff9f9c6afeb6fdf0b9bb1cfc3cfd7dff4c2a020e8079d6720975f3b6a`

The original revision is recorded in `shell/REVISION` and `BASELINE.json`.
Current installed QML and local overrides were then copied over that source.
Changes include the grouped launcher, combined package browser, settings
pages, weather map, brightness synchronization, appearance, and portable
installation tools. Project capture date: 2026-10-05.

The original GPL license is preserved at the project root and in `shell/`.
Font and other bundled asset license files remain alongside their assets.
This project is a derivative configuration maintained separately from Caelestia.
Caelestia CLI and Quickshell remain external dependencies with their own licenses.

The original shell CMake project and native plugin source are included so
we can maintain them later. The initial installer uses the installed native
plugin package rather than replacing system libraries. The upstream build
instructions remain in `shell/UPSTREAM_README.md`; rebuilding and packaging
our own native runtime is a future migration requiring ABI checks.

Juarchy shell 0.1.0 introduces independent QuickShell instance selection and
controls while preserving the current interface. Caelestia native import names,
global shortcuts, layer namespaces and shared theme/state paths are retained
until those dependencies are replaced together. The Juarchy entry point omits
the upstream crash-report URL. Juarchy's privacy defaults remove automatic
IP-location lookup, require consent for remote music artwork and visualisers,
and use in-memory notification history unless longer retention is selected.

## Omarchy themes and agent usage

The theme palettes, preview images and wallpapers installed by
`scripts/install-omarchy-themes.py` come from https://github.com/basecamp/omarchy
(Copyright (c) David Heinemeier Hansson, MIT licence), pinned in that script and
recorded with its licence in `~/.local/share/juarchy/omarchy-themes`. They are
downloaded when installing, not stored here. Palette-to-scheme mapping, background
switching and the usage collector are Juarchy's own code; the agent usage panel
follows the design of Omarchy's `agents` plugin and the usage endpoints and
app-server calls used by its collectors. The `shell/assets/agents/claude.svg` and
`codex.svg` marks are copied from that plugin and remain the property of their owners.
