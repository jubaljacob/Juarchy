# Install Juarchy on another laptop

Juarchy installs the shared desktop on an existing **Arch Linux + Hyprland**
system. Use your own Linux username and password. It includes the dashboard
notch, Spotlight search, screenshots, night light, themes and settings; it does
not copy Jubal's accounts, passwords, Wi-Fi profiles, wallpaper, location or
monitor configuration. The default icon theme is Papirus.

## 1. Prepare Windows and install Arch

Before changing partitions, back up Windows files and save the BitLocker/device
encryption recovery key somewhere accessible from another device. Boot changes
can trigger recovery. Disable Windows Fast Startup and fully shut down Windows
before using Linux. Follow the [Arch dual-boot guide](https://wiki.archlinux.org/title/Dual_boot_with_Windows)
for firmware, encryption and partitioning details.

Shrink Windows from Windows Disk Management, leaving unallocated space for
Arch. Keep the Windows, recovery and existing EFI partitions; do not format
them. Install Arch into the space set aside for it, using the same firmware
boot mode as Windows (normally UEFI). Disk names and partition sizes are specific
to the laptop, so this repository does not automate partitioning or boot setup.
Use the [Arch installation guide](https://wiki.archlinux.org/title/Installation_guide)
and verify that **both Windows and Arch still boot** before proceeding.

On Arch, create a regular user with sudo access, configure networking, and
install Hyprland plus the graphics drivers appropriate to this laptop. Confirm
that you can enter a basic Hyprland session and open a terminal. The shared
configuration is tested with Hyprland **0.56.2** and uses Lua; see
[Hyprland configuration](https://wiki.hypr.land/configuring/core/).
Do not copy another machine's NVIDIA or monitor configuration.

## 2. Get Juarchy

The repository is private. Choose one route:

- **Archive:** ask the owner for a source archive made with `git archive`
  (instructions below). Extract it into your home directory and open a terminal
  in the extracted `Juarchy` directory. No GitHub account is needed.
- **Git:** the owner grants your GitHub account repository access; accept the
  invitation, then run the following on Arch using **your own** account:

  ```sh
  sudo pacman -Syu --needed git python github-cli
  gh auth login
  gh repo clone jubaljacob/Juarchy
  cd Juarchy
  ```

For the archive route, install Python and Git first if needed:

```sh
sudo pacman -Syu --needed python git
```

All following `python scripts/...` commands run from the Juarchy directory.

## 3. Install desktop dependencies

```sh
python scripts/dependencies.py
```

This prints an official-package command and an AUR-package command. Review and
run the official command first. It includes the default browser, editor,
terminal, file manager, Bluetooth/audio/display tools and build prerequisites.
If you do not have an AUR helper, install `yay` using its
[upstream instructions](https://github.com/Jguer/yay#installation), as your
regular user:

```sh
git clone https://aur.archlinux.org/yay.git /tmp/juarchy-yay
cd /tmp/juarchy-yay
less PKGBUILD
makepkg -si
cd -
```

Then run the printed AUR command, reviewing its build files and prompts.
Caelestia Shell supplies the native plugins and fonts; Caelestia CLI supplies
theme and recording tools. Juarchy uses its own QML configuration. The tested
versions are Caelestia Shell 2.5.0 and CLI 1.1.3, recorded in `BASELINE.json`.
Rolling package upgrades can change their APIs/ABI; the manifest is not a
version lock. Resolve build failures before installing the desktop files.

On a fresh Arch installation using NetworkManager, enable its service. If
another network manager is already configured, resolve that choice first:

```sh
sudo systemctl enable --now NetworkManager.service
```

For Bluetooth and the desktop power-profile controls:

```sh
sudo systemctl enable --now bluetooth.service power-profiles-daemon.service
```

Use only one power-profile manager; an existing TLP setup needs a deliberate
choice before enabling power-profiles-daemon. PipeWire/WirePlumber and portals
run in the user session; logging in again after package installation lets their
normal session activation take effect.

```sh
python scripts/dependencies.py --check
python scripts/doctor.py
```

Fix any `FAIL` lines first. `NOTE` lines identify inactive services, an absent
Hyprland session or versions differing from the tested baseline. These checks
do not prove that native plugins or laptop hardware work correctly.

## 4. Preview and install

Run without sudo:

```sh
python scripts/install.py --shared-only
python scripts/install.py --shared-only --apply
```

Read the preview: installation replaces the listed desktop configuration files
and backs up their previous contents. `--shared-only` excludes `local/home`
overrides even if someone handed you their working checkout. Existing
`~/.config/hypr/machine.lua` and Juarchy privacy preferences are preserved.
The installer requires the conventional `~/.config`, `~/.local/share` and
`~/.local/state` paths. It does not install packages or start services.

Record the printed backup path. Log out, then choose Hyprland at login. If
starting from a text console, use `Hyprland --config ~/.config/hypr/hyprland.lua`.
An existing session launcher explicitly pointing to another config must be
updated to use this Lua file. Use one desktop shell at a time; remove any
separate Caelestia/Waybar autostart from your own session setup. The supplied
Hyprland configuration starts Juarchy automatically.

The optional `--profile intel-nvidia` installs workarounds for the original
laptop. It is **not** required for all NVIDIA laptops; leave it off unless the
hardware needs the specific fixes in [PORTABILITY.md](PORTABILITY.md).

Optional: install the Omarchy themes (palettes and wallpapers, about 75 MB,
downloaded from Omarchy's repository) to choose them in **Wallpaper & style**:

```sh
python scripts/install-omarchy-themes.py --apply
```

## 5. Check and personalise

```sh
~/.local/bin/juarchy-shell status
hyprctl configerrors
```

- `Super + Return`: terminal; `Super + Shift + Return`: browser.
- `Super + Space`: Spotlight; `Super + Alt + Space`: grouped menu.
- Hover at the top centre, then click the dash: dashboard and quick controls.
- `Print Screen`: region screenshot; `Shift + Print Screen`: all displays.
- `Super + Shift + W`: settings, wallpaper and appearance.
- `Super + Shift + F`: file manager (Nautilus; quick-preview a file with the spacebar).
- Test speakers, microphone, Wi-Fi, Bluetooth and brightness on this laptop.
- Save your work, then test `Super + L` with **your Arch user's password**,
  followed by suspend/resume. Keep a working text-console login available
  during this first test.

Make Nautilus the program that opens folders for Spotlight, links and other apps:
`xdg-mime default org.gnome.Nautilus.desktop inode/directory`. (The installer leaves
your existing default applications alone.)

Choose your own weather location and privacy options in settings. Put your
wallpapers in `~/Pictures/Wallpapers` and select one in Wallpaper & style.
For monitor scaling and keyboard layout, edit `~/.config/hypr/machine.lua`;
this file survives updates. See [Spotlight privacy](spotlight.md) for network
lookups and file-search settings. Extra menu applications, fingerprint/face
unlock and snapshot management require their own setup.

## Update or undo

For a Git clone, run `git pull --ff-only` in the checkout. For an archive,
extract the next version into a new directory. Recheck dependencies and preview
the installation before applying it. Machine settings and privacy choices
survive, but other shared configuration files are replaced; save your own
changes or maintain them under `local/home` and omit `--shared-only` when you
deliberately want those overrides. Theme presets are stored outside the checkout.

To undo an installation, use its printed backup path (replace `TIMESTAMP`):

```sh
python scripts/install.py --restore ~/.local/state/jubal-desktop/backups/TIMESTAMP
python scripts/install.py --restore ~/.local/state/jubal-desktop/backups/TIMESTAMP --apply
```

Then log out and back in. If the graphical session fails, use `Ctrl + Alt + F3`
to log into a text console and run the restore there. Restore also saves the
current files into a new recovery backup.

## Owner: make an archive for a friend

After committing the changes, run from the repository:

```sh
git archive --format=tar.gz --prefix=Juarchy/ --output=/tmp/Juarchy.tar.gz HEAD
sha256sum /tmp/Juarchy.tar.gz
```

Share that archive and its checksum. It contains only committed source,
documentation and bundled assets, including the license. It excludes `.git`,
ignored `local/home` overrides, live account data and uncommitted changes.
The recipient can check `sha256sum Juarchy.tar.gz`, then extract with
`tar -xzf Juarchy.tar.gz` and follow this guide. An archive has no `git pull`;
repository access is the convenient route for ongoing updates.
