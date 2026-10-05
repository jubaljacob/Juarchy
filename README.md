# Juarchy

A personal Hyprland desktop based on Caelestia, starting from the customized
build captured on **5 October 2026**. The first baseline is tagged
`baseline-2026-10-05`; subsequent changes build on that version.

GitHub repository: [jubaljacob/Juarchy](https://github.com/jubaljacob/Juarchy).
The local checkout is currently `~/Projects/jubal-desktop`.

The baseline includes the current bar and audio controls, grouped launcher,
combined Arch/AUR package browser with recommendations, settings pages,
weather map, display brightness controls, and Gruvbox soft dark palette.
The shell's QML components are copied into this repository, including the
components that previously linked to system files. Upstream C++ plugin and
supporting source are also included under `shell/`.

The desktop shell now has its own QuickShell configuration, `juarchy`, and
uses `juarchy-shell` for startup and controls. Its initial appearance is
unchanged. Caelestia's native plugins, CLI theme tools, settings directory,
state and caches remain compatibility dependencies in this first migration.
This stage does not introduce new privacy defaults or remove features.

## Switch the current desktop

From an unlocked Hyprland desktop terminal, run:

```sh
python ~/Projects/jubal-desktop/scripts/activate.py
```

The switch backs up the existing files, installs an independent shell copy
at `~/.config/quickshell/juarchy`, and routes startup, menu, lock, region
screenshots, brightness and the audio repair helper to it. It preserves
the computer's current Hyprland settings and personal additions. It checks
session access before modifying files, waits for the original shell to stop,
checks the new shell's IPC controls, and restores the previous files and
shell if activation fails. The original Caelestia shell directory is retained.
Run this from the desktop terminal because sandboxed agents may be unable
to access the compositor and shell sockets.

After activation:

```sh
~/.local/bin/juarchy-shell status
~/.local/bin/juarchy-shell restart
~/.local/bin/juarchy-shell version
```

To undo the switch, restoring the files captured immediately before activation:

```sh
python ~/Projects/jubal-desktop/scripts/activate.py --rollback
```

Rollback replaces those files with their backed-up versions and saves the
current versions in a separate recovery backup. Keep the checkout and backups
until you have finished checking the new shell on the desktop.

## Supported systems

This is an **Arch Linux / Hyprland** baseline. It has been captured on
Hyprland 0.56.2 with its Lua configuration, Caelestia Shell 2.5.0,
Caelestia CLI 1.1.3, and the Quickshell build recorded in `BASELINE.json`.
Older Hyprland releases using only `hyprland.conf` need a configuration port.
Other Linux distributions need their own package manifests and runtime testing.
This is a desktop configuration, not an operating-system image.

## Install on another computer

Clone your private repository with your authenticated GitHub account:

```sh
gh repo clone jubaljacob/Juarchy
cd Juarchy
```

From the checkout, inspect the required packages:

```sh
python scripts/dependencies.py
python scripts/dependencies.py --check
```

The first command prints installation commands without running them. The
manifests prefer official repositories, with AUR dependencies for the current
Caelestia runtime. `packages/baseline-versions.txt` records versions from the
original machine; it does not pin packages or guarantee future ABI compatibility.
The existing `caelestia-shell` package supplies the compiled native plugin and
supporting tools. Our own QML runs separately under the `juarchy` configuration;
the original `caelestia` configuration is preserved.

Preview and install as your desktop user, without sudo:

```sh
python scripts/install.py
python scripts/install.py --apply
```

The installer backs up every destination it replaces. It installs copies,
does not install packages or restart services, and leaves unrelated files
alone. Log out and back in to activate the installed configuration. It uses
the conventional `~/.config` and `~/.local` layout; a custom `XDG_CONFIG_HOME`
is not supported by this installer yet.

On a computer needing the original Intel/NVIDIA laptop workarounds, preview
the optional profile first:

```sh
python scripts/install.py --profile intel-nvidia
python scripts/install.py --profile intel-nvidia --apply
```

See [portability and known issues](docs/PORTABILITY.md) before enabling it.

## Make it your own

- `shell/`: shell QML, components, native plugin source, and upstream assets.
- `home/.config/caelestia/shell.json`: bar layout and shell preferences.
- `home/.config/hypr/hyprland.lua`: shared compositor settings and shortcuts.
- `home/.config/jubal-launcher/menu.json`: shared menu entries.
- `home/.local/bin/` and `home/.local/lib/`: custom helpers and package guidance.
- `profiles/`: optional hardware settings.
- `local/home/`: ignored personal overrides, copied over shared files at install.

Edit `~/.config/hypr/machine.lua` for a particular computer's monitors,
keyboard, or other compositor settings. The installer creates it once and
preserves it on later installs. Brightness state and monitor names are not
copied from the original machine.

Shared development happens in the checkout. Preview and rerun the installer
to apply changes; editing live configuration does not automatically update
the repository. Run validation before committing:

```sh
python scripts/validate.py
git add .
git commit -m "Describe the change"
git push
```

## Restore an installation

The installer prints its backup directory after applying changes. Preview
and restore that backup with:

```sh
python scripts/install.py --restore ~/.local/state/jubal-desktop/backups/TIMESTAMP
python scripts/install.py --restore ~/.local/state/jubal-desktop/backups/TIMESTAMP --apply
```

A restore makes another backup of the current files before replacing them.
Keep backups outside this repository.

## Publish the private repository

GitHub authentication belongs to your account and is never stored here:

```sh
sudo pacman -S --needed github-cli
gh auth login
python scripts/publish.py
```

The publishing script uses the existing **jubaljacob/Juarchy** repository,
checks its private visibility and your push access, configures a GitHub
noreply author address for future commits, and pushes `main` and the baseline
tag. It merges any GitHub initialization commits before pushing; if those
files conflict, resolve and commit the merge, then rerun the script. It does
not force-push or change an origin that points elsewhere. The first local
baseline commit uses a local-only author identity.

## Credits and license

Derived from [Caelestia Shell](https://github.com/caelestia-dots/shell)
2.5.0, under **GPL-3.0-only**. See [LICENSE](LICENSE) and
[upstream attribution](UPSTREAM.md). Existing assets and vendored components
retain their original notices and licenses. Caelestia native module names,
global shortcut IDs and layer namespaces remain intact for runtime compatibility.
QuickShell instance selection uses Juarchy's own `juarchy` configuration name.
