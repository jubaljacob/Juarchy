# Portability and known issues

## Shared baseline

The shared configuration uses automatic monitor discovery and preserves the
original keyboard shortcuts, shell layout, and palette. The source snapshot
does not depend on symlinks to the original machine's `/etc` directory.
Caelestia's native plugin, helper tools, PAM setup, fonts, and CLI still come
from the runtime packages. Keep the runtime compatible with the captured
2.5.0 source; newer package versions may require updating this fork.

`machine.lua` belongs to each computer and survives subsequent installs.
Ignored overrides under `local/home/` can customize other files without
publishing them. These overrides replace a shared file in full, rather than
merging JSON settings.

## Optional Intel/NVIDIA profile

`profiles/intel-nvidia/home/` contains the original laptop workarounds:

- Hyprland portal shared-memory screen capture for cross-GPU compatibility.
- Libcamera CPU software ISP configuration for its Intel IPU6 camera.
- Chromium Wayland and PipeWire camera flags.
- A brightnessctl wrapper preferring Intel's connected internal panel.

These are hardware workarounds, not general defaults. The capture workaround
can cost performance. The profile replaces the Chromium flags file; place
additional browser flags in `local/home/.config/chromium-flags.conf` before
installing if you need to preserve custom flags.

The built-in camera's driver and sensor support must already be present.
On the original machine `libcamera`, `libcamera-ipa`, and `pipewire-libcamera`
were installed. Enabling the profile does not install drivers or make native
applications support libcamera.

**Unresolved at capture:** Discord desktop screen sharing can be black or
frozen, and its built-in camera access fails through direct V4L2 capture.
A separate Chromium test successfully captured windows. Its tab test had
no second tab; the bundled diagnostic now opens an animated sample tab and
includes a camera test. The test results do not establish that Discord's
encoding or remote video delivery works.

## Excluded machine and account state

The project excludes browser profiles, application sessions, credentials,
SSH keys, Wi-Fi connection profiles, notification history, application
history, caches, backups, monitor brightness state, and personal wallpaper.
The shared palette is Gruvbox soft dark; the upstream default wallpaper is
available in the bundled assets rather than copying the personal wallpaper.

Login-manager configuration, bootloader changes, GPU driver installation,
storage repair, and root snapshot policies are outside the desktop installer.
The menu's snapshot actions require an independently configured snapshot
helper. `snap-now` reports when it is missing; the desktop installer does not
create, delete, or prune system snapshots.

The menu also contains shortcuts for optional applications used in the
original build. Those applications are not installed by the desktop
prerequisite manifest. Adjust menu entries to match each computer.

## Current verification limits

Installer deployment, backups, restore behavior, portable paths, package
guidance, and source syntax are checked locally. GUI startup, hardware
capture, and rendering on another computer still need a real desktop test.
The live desktop was not switched over during repository preparation.
