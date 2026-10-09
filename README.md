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
Privacy preferences are stored separately in `~/.config/juarchy/privacy.json`.
Weather waits for a chosen location, remote music artwork and visualisers start
disabled, and notification history stays in memory by default. Existing artwork
from local files and playback controls remain available.

In Settings, choose a weather location under **Language & region**, enable media
options under **Services**, and set notification retention under
**Services → Notifications**. Session-only history clears at logout or shell
restart and erases older saved notification content and cached notification
images. Longer retention offers 1, 7 or 30 days; an erase action clears history
and its images immediately. Notification messages are hidden on the lock screen.
Saved history and privacy preferences are separate from theme and monitor settings.

The dashboard notch is completely hidden at rest. Hovering over its top-centre
taskbar area reveals it to half the taskbar height; clicking its centre dash
opens the full dashboard.
The notch shares the dashboard's translucent, blurred material and smoothly
joins the top edge and the open dashboard.
Moving outside the notch and dashboard retracts it. Click the centre dash again,
click outside, or press Escape to close it. The notch is approximately 8 cm
wide using the display's reported physical density and scaling. Existing
dashboard shortcuts still work. Its Settings hover option controls the notch
preview rather than opening the full dashboard.
The icon to the right of the dash toggles Do not disturb. The icon to its left
starts fullscreen screen recording without audio; click its red stop icon to
stop and save the recording. These quick controls work independently of the
dashboard.
The sun/moon icon beside DND toggles Night light, using Hyprsunset at 4500 K for
warmer screen colours. Turning it off restores normal colours and leaves
brightness alone. Hyprsunset starts on the first enable action, and the icon
reads its actual state, including changes made outside the shell.
Normal colours show a sun; the enabled blue-light filter shows a moon. Enabled
toggles have a soft coloured highlight, with smooth icon and colour transitions.
Use `juarchy-night-light enable --temperature 4000`, `disable`, or `status`
from a terminal. The notch toggle uses 4500 K when enabling.
The microphone icon toggles mute for the current default input and shows a
crossed-out microphone when muted. The coffee-cup icon toggles Keep awake,
preventing automatic screen blanking and sleep. The screenshot icon
beside recording hides the notch and closes the dashboard, then lets you select
a region to save and copy to the clipboard. Escape cancels the selection.

The bottom-right utilities panel is disabled. Its corner hover and shortcut
cannot open it, and it no longer appears below the notification sidebar.
Quick actions remain in the notch, while connectivity, audio, devices and
power controls remain in the taskbar. Notifications and status toasts still work.

Application tray icons stay hidden behind a chevron at the left edge of the
top-right controls, followed by the date and time, active window, status icons
and power button. Click it to reveal the icons, then click it again or move away to
collapse them. Clicking an icon keeps its usual application action; hovering
an expanded icon still shows its tray menu.

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

For a friend starting with Windows, follow the full
[Windows dual-boot → Arch → Juarchy installation guide](docs/INSTALL.md).
It covers private repository access or a shareable archive, dependencies,
services, laptop checks, updates and recovery. Juarchy installs the desktop
after Arch and Hyprland are working; it does not partition disks or install Arch.

Clone the private repository with an authenticated GitHub account that has access:

```sh
gh repo clone jubaljacob/Juarchy
cd Juarchy
```

From the checkout, inspect the required packages:

```sh
python scripts/dependencies.py
python scripts/dependencies.py --check
python scripts/doctor.py
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
python scripts/install.py --shared-only
python scripts/install.py --shared-only --apply
```

The installer backs up every destination it replaces. It installs copies,
does not install packages or restart services, and leaves unrelated files
alone. Log out and back in to activate the installed configuration. It uses
the conventional `~/.config` and `~/.local` layout; a custom `XDG_CONFIG_HOME`
is not supported by this installer yet. `--shared-only` ignores any personal
`local/home` overrides; omit it when deliberately applying your own overrides.
Existing machine settings and privacy choices are always preserved.

On a computer needing the original Intel/NVIDIA laptop workarounds, preview
the optional profile first:

```sh
python scripts/install.py --profile intel-nvidia
python scripts/install.py --profile intel-nvidia --apply
```

See [portability and known issues](docs/PORTABILITY.md) before enabling it.

## Make it your own

### Screenshots

Press **Print Screen** and drag to select a region. **Escape** cancels.
The screenshot is saved under `~/Pictures/Screenshots` and copied to the
clipboard. **Shift + Print Screen** captures all displays. The desktop
menu's screenshot entries use the same tool. Region selection uses `slurp`
and capture uses `grim`, independently of the desktop shell.

Run `juarchy-screenshot` (or `juarchy-screenshot --full`) from a terminal.
Set `JUARCHY_SCREENSHOT_DIR` to override the save directory. Otherwise the
tool uses the configured XDG Pictures directory plus `Screenshots`.

### Wallpaper themes

Open **Wallpaper & style** in desktop settings. **Use wallpaper colours**
generates the desktop palette from the current wallpaper and updates it when
you choose another image. **Match wallpaper brightness** lets new wallpapers
choose light/dark mode and colour intensity; disable it to keep your chosen
mode. Choose a fixed palette in **Colours** to stop automatic colour extraction.

Enter a theme name and click **Save** to remember the current wallpaper,
palette, mode, colour variant, and brightness matching preference together.
Use **Apply** beside a saved theme to restore it. Preset names are unique;
remove an old preset before saving a replacement with the same name.
Presets live in `~/.config/juarchy/themes.json` (or your XDG configuration
directory) and are personal settings, outside the checkout. Wallpapers are
referenced by their original paths, so keep those images in place. Applying
a missing image reports an error without changing the desktop.

The same presets can be managed with `juarchy-theme list`,
`juarchy-theme save "Forest"`, `juarchy-theme apply "Forest"`, and
`juarchy-theme delete "Forest"`. Use `--no-smart` when saving from the
terminal to record that brightness matching should be disabled. The settings
UI restores this preference for future wallpaper selections; the command-line
apply action restores the recorded wallpaper, mode and palette.

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

## Spotlight search

**Super + Space** opens one contextual search field for apps, settings, filenames,
calculations, broad unit conversions, web searches and cached currency rates.
**Super + Alt + Space** opens the grouped desktop menu. See
[Spotlight usage and privacy](docs/spotlight.md) for examples and search roots.
