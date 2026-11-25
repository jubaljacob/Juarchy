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
and its images immediately.
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
at `~/.config/quickshell/juarchy`, and routes startup, menu, region
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

## Nived's setup: ASUS ROG Zephyrus G15 (GA503RM)

This branch (`nived-setup`) also carries the full setup of Nived's laptop as
the `asus-g15` hardware profile. Use it to rebuild that machine from scratch,
or as a starting point for another ASUS ROG laptop.

| Part | Hardware | How it is handled |
|---|---|---|
| CPU / integrated GPU | AMD Ryzen 7 6800HS with Radeon 680M | `mesa`, `vulkan-radeon`, `libva`; drives the laptop panel |
| Discrete GPU | NVIDIA GeForce RTX 3060 Mobile | `nvidia-open-dkms`, `nvidia-utils`, NVIDIA suspend/resume services |
| Panel | 2560×1440, 165 Hz (`eDP-1`) | 165 Hz on the charger, 60 Hz on battery (`power-mode`) |
| ASUS controls | Power profiles, Fn keys, keyboard light, battery limit | `asusctl` / `asusd` with `/etc/asusd` from the profile |
| Audio | AMD audio coprocessor | `sof-firmware` |
| Mouse | Logitech MX Master 3S (Bluetooth) | `logiops` (thumb-button gestures) and `openlogi-bin` |

### What the profile contains

`profiles/asus-g15/`:

| File | Installed to | Purpose |
|---|---|---|
| `home/.config/hypr/machine.lua` | `~/.config/hypr/machine.lua` (first install only) | Power-mode hooks, Fn+F5 notification, touchpad scroll speed (`scroll_factor = 0.3`), natural scrolling, 4-finger swipe (`workspace_swipe_distance = 500`), sliding workspace animation, Super+Tab stepping, hyprlock key bindings, Bluetooth agent, Hyprland logging |
| `home/.local/bin/power-mode` | `~/.local/bin/` | Silent / balanced / turbo presets and the 165/60 Hz refresh switch |
| `home/.local/bin/asus-profile-sync` and `home/.config/systemd/user/asus-profile-sync.service` | `~/.local/bin/`, `~/.config/systemd/user/` | Applies the AC/battery profile at login and after resume (asusd only switches on plug/unplug) |
| `home/.local/bin/juarchy-lock` and `home/.config/hypr/hyprlock.conf` | `~/.local/bin/`, `~/.config/hypr/` | The hyprlock lock screen, coloured from the current theme |
| `home/.local/bin/juarchy-idle` and `home/.config/hypr/hypridle.conf` | `~/.local/bin/`, `~/.config/hypr/` | Lock, screen-off and sleep timings (table below) |
| `home/.config/caelestia/shell.json` | `~/.config/caelestia/shell.json` | Bar layout and shell preferences, with the shell's own idle timeouts turned off so hypridle owns them |
| `system/etc/asusd/asusd.ron` | `/etc/asusd/` | 80 % battery charge limit; Performance on AC, Quiet on battery |
| `system/etc/asusd/aura_19b6.ron` | `/etc/asusd/` | Keyboard backlight: static red, medium brightness |
| `system/etc/logid.cfg` | `/etc/` | MX Master 3S thumb button: hold and move left/right to switch workspace |
| `packages.txt`, `aur.txt` | — | Drivers and tools this laptop needs on top of the shared desktop packages |
| `setup-system.sh` | — | Installs those packages, copies the `/etc` files and enables the services |
| `extras/monitors.lua` | copy by hand | The saved two-monitor layout (laptop panel plus a 1440p monitor on `DP-9`) |

`~/.config/hypr/machine.lua` is only written when it does not exist yet, so
later installs never overwrite your tweaks there. `shell.json` from the profile
replaces the shared one in full.

Do **not** use `--profile intel-nvidia` on this laptop; that profile holds
workarounds for a different, Intel-based machine.

### Fresh install, step by step

1. **Install Arch Linux** with a working network connection, a user with
   `sudo`, and `git`, `python` and `yay`. See [docs/INSTALL.md](docs/INSTALL.md)
   for dual-booting with Windows.

2. **Get this branch:**

   ```sh
   gh repo clone jubaljacob/Juarchy
   cd Juarchy
   git switch nived-setup
   ```

3. **Install the shared desktop packages** (Hyprland, Caelestia shell,
   Quickshell, PipeWire and so on). Print the commands, run them, then check:

   ```sh
   python scripts/dependencies.py
   python scripts/dependencies.py --check
   ```

4. **Install the desktop with the ASUS profile**, as your normal user. Preview
   first, then apply:

   ```sh
   python scripts/install.py --profile asus-g15 --shared-only
   python scripts/install.py --profile asus-g15 --shared-only --apply
   ```

5. **Install the drivers, ASUS and mouse tools, and system configs.** Preview
   first, then apply (asks for your sudo password):

   ```sh
   profiles/asus-g15/setup-system.sh
   profiles/asus-g15/setup-system.sh --apply
   ```

   This installs everything in `packages.txt` and `aur.txt`, copies
   `system/etc/` into `/etc` (keeping a `.bak-<date>` copy of any file it
   changes), and enables:
   - system: `power-profiles-daemon`, `bluetooth`, `logid`,
     `nvidia-suspend`, `nvidia-resume`, `nvidia-hibernate`
   - user: `asus-profile-sync`, `hypridle`, `openlogi-agent`

6. **Start Hyprland on login.** There is no login manager; Hyprland starts
   when you log in on tty1. Add this to `~/.bash_profile`:

   ```sh
   # Start Hyprland automatically after login on tty1
   if [[ -z $WAYLAND_DISPLAY && -z $DISPLAY && ${XDG_VTNR:-0} -eq 1 ]]; then
       hypr_logs="$HOME/.local/state/hypr/logs"
       mkdir -p "$hypr_logs"
       ls -1t "$hypr_logs"/hyprland-*.log 2>/dev/null | tail -n +10 | xargs -r rm -f
       start-hyprland -- --config "$HOME/.config/hypr/hyprland.lua" \
           >>"$hypr_logs/hyprland-$(date +%F_%H-%M-%S).log" 2>&1
   fi
   ```

   This keeps the ten newest Hyprland logs in `~/.local/state/hypr/logs`.

7. **Reboot** so the NVIDIA modules load.

8. **Set up monitors.** Press **Super + Ctrl + D** (nwg-displays) and save the
   layout; it is written to `~/.config/hypr/monitors.lua`. To reuse the old
   two-monitor layout instead:

   ```sh
   cp profiles/asus-g15/extras/monitors.lua ~/.config/hypr/monitors.lua
   ```

9. **Pair the MX Master 3S.** Open Bluetooth with **Super + Ctrl + B**, pair
   the mouse, then open OpenLogi and set the **Gesture button** to **None**
   so logid can use it for workspace switching.

### Check that everything works

```sh
nvidia-smi                 # NVIDIA driver loaded, RTX 3060 listed
asusctl profile get        # Active profile: Performance (charger) / Quiet (battery)
asusctl battery info       # charge limit 80
power-mode status          # power source, profile and refresh rate
systemctl --user status asus-profile-sync hypridle openlogi-agent
python scripts/doctor.py
```

Then try **Fn + F5** (a notification shows the new mode), **Super + L** (lock
screen) and unplugging the charger (the panel drops to 60 Hz and switches to
Quiet).

### Daily use

**Power modes.** Fn + F5 cycles Silent → Balanced → Turbo in the firmware.
From a terminal:

```sh
power-mode silent | balanced | turbo   # set a profile now
power-mode auto                        # charger: turbo + 165 Hz, battery: silent + 60 Hz
power-mode refresh 120                 # set the panel refresh rate by hand
power-mode status
```

**Battery charge limit.** Set to 80 % in `/etc/asusd/asusd.ron`. Charge to 100 %
once with `asusctl battery oneshot`, or change the limit with
`asusctl battery limit 90`.

**Keyboard backlight.** `asusctl aura` changes mode and colour;
`asusctl leds set low|med|high|off` changes brightness.

**Touchpad and swipe speed.** In `~/.config/hypr/machine.lua`:
- `scroll_factor = 0.3`: two-finger scroll speed. Lower is slower; 1.0 is
  the unmodified Linux speed.
- `workspace_swipe_distance = 500`: finger travel in pixels for one
  workspace. Higher makes the 4-finger swipe slower (Hyprland default 300).

Hyprland reloads the file as soon as you save it.

**Lock, screen off and sleep** (`juarchy-idle`, driven by hypridle):

| Idle time | On the charger | On battery |
|---|---|---|
| 2 min | Sleep if already locked | Sleep if already locked |
| 5 min | — | Lock and turn the panel off |
| 7 min | — | Sleep |
| 10 min | — | Sleep, locked or not |
| 45 min | Lock | — |
| 47 min | Sleep | — |

The laptop always locks before sleeping. On the charger with an external
monitor connected, "sleep" turns only the laptop panel off: an external monitor
on the NVIDIA port can drop out on wake-up and crash Hyprland. External
monitors are never turned off by DPMS for the same reason.

**Mouse.** Hold the MX Master 3S thumb button and move left or right to switch
workspace (it sends Super + Tab and Super + Shift + Tab).

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

### Omarchy themes

Juarchy carries [Omarchy](https://github.com/basecamp/omarchy)'s 23 themes, each
with its own palette and wallpapers. Choose one in **Wallpaper & style → Omarchy
themes** and the wallpaper, the shell, GTK and Qt apps, terminals, Hyprland and
the other themed apps all follow it. Moving between a theme's backgrounds (the
**Next background** button, the thumbnails under the grid, or
**Super + Ctrl + Space**) keeps the theme's colours, as in Omarchy.
**Super + Shift + Ctrl + Space** switches to the next theme.

The themes are downloaded from Omarchy (MIT licensed) at a pinned revision
rather than stored in this repository:

```sh
python scripts/install-omarchy-themes.py           # preview
python scripts/install-omarchy-themes.py --apply   # about 75 MB in ~/.local/share/juarchy
```

From a terminal:

```sh
juarchy-theme omarchy list
juarchy-theme omarchy set tokyo-night --background 3-swirl-buck
juarchy-theme omarchy next            # or prev
juarchy-theme omarchy background next # or prev, or: set NAME_OR_IMAGE_PATH
```

Each theme's `colors.toml` becomes a complete Caelestia colour scheme: the
background, text, accent and error colours are the theme's own, the 16 terminal
colours use Omarchy's mapping unchanged, and the Material container and "on"
colours are mixed from them and checked for readable contrast. Light themes
(Catppuccin Latte, Flexoki Light, Lupine, Rosé Pine, White) switch the desktop to light mode, so
the **Dark theme** switch is disabled while an Omarchy theme is active. Choose a
scheme under **Colours**, or **Use wallpaper colours**, to leave Omarchy mode.
Picking any image while a theme is active changes the wallpaper only.

Add your own theme as `~/.config/juarchy/omarchy-themes/NAME/` with a
`colors.toml` (the format is described in Omarchy's `docs/theming.md`) and a
`backgrounds/` folder. Drop extra images for an existing theme into
`~/.config/juarchy/omarchy-backgrounds/NAME/`. Intro videos and video
backgrounds are not used.

### Agent usage

The bar shows Claude Code and Codex: each agent's mark and how much of its
busiest limit window is spent. Hover for the panel, with the plan, the
5-hour and weekly meters and their reset countdowns, any model-specific
allowance, and what this computer spent today and over seven days (tokens,
prompts, sessions, most-used model). Past 75% and 90% the figure warms and
then turns urgent. An agent that is not installed or signed in says so in the
panel. Hide the widget with `"enabled": false` for the `agents` entry in
`~/.config/caelestia/shell.json`.

Token and prompt counts are read from the agents' own session files and never
leave the computer. **Limits** come from Anthropic's usage endpoint (using the
sign-in Claude Code keeps) and from the Codex app-server, so they contact
Anthropic and OpenAI and wait for consent: turn on **Settings → Services →
Agent usage → Check Claude and Codex limits**. Sign-ins are only read, never
rewritten or stored, and never appear in the output. Failed checks keep the last
numbers marked as old; limits are re-checked about every five minutes (three
when close to the limit), and the refresh button in the panel checks at once.

```sh
python ~/.local/bin/juarchy-agent-usage            # the JSON the bar reads
python ~/.local/bin/juarchy-agent-usage --force    # check limits now
python ~/.local/bin/juarchy-agent-usage --agent claude --no-limits
```

- `shell/`: shell QML, components, native plugin source, and upstream assets.
- `home/.config/caelestia/shell.json`: bar layout and shell preferences.
- `home/.config/hypr/hyprland.lua`: shared compositor settings and shortcuts.
- `home/.config/jubal-launcher/menu.json`: shared menu entries.
- `home/.local/bin/` and `home/.local/lib/`: custom helpers and package guidance.
- `profiles/`: optional hardware settings (`asus-g15` is Nived's laptop; see above).
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
