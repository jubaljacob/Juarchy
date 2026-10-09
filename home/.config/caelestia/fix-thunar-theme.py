#!/usr/bin/env python3
"""Keep Thunar's foreground colors readable after Caelestia regenerates GTK CSS."""

import os
import configparser
import json
from pathlib import Path
import subprocess


CONFIG = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
MARKER = "/* Thunar readable foregrounds */"
COLORS = """
/* Thunar readable foregrounds */
.thunar.background,
.thunar .titlebar,
.thunar .sidebar,
.thunar .view,
.thunar .view cell,
.thunar .sidebar .view,
.thunar .frame.standard-view .view,
.thunar label,
.thunar button,
.thunar entry,
.thunar menubar,
.thunar menu,
.thunar popover {
    color: @window_fg_color;
}

.thunar button,
.thunar entry {
    background-color: @card_bg_color;
    background-image: none;
}

.thunar menu,
.thunar popover {
    background-color: @popover_bg_color;
}

.thunar entry {
    caret-color: @window_fg_color;
}

.thunar .view:selected,
.thunar .view:selected:backdrop,
.thunar .view cell:selected,
.thunar .sidebar .view:selected,
.thunar .frame.standard-view .view:selected,
.thunar .frame.standard-view .view *:selected,
.thunar button:checked,
.thunar button:checked label,
.thunar button.toggle:checked,
.thunar button.toggle:checked label,
.thunar header.top tabs .reorderable-page:checked label,
.thunar menuitem:hover,
.thunar menuitem:hover label {
    color: @accent_color;
}

.thunar entry selection {
    background-color: @accent_bg_color;
    color: @accent_fg_color;
}

.thunar :disabled,
.thunar :disabled label,
.thunar :disabled image {
    color: alpha(@window_fg_color, 0.55);
}
"""


def update(path: Path, transform) -> None:
    if path.is_file():
        original = path.read_text()
        changed = transform(original)
        if changed != original:
            path.write_text(changed)


def sync_settings(config: Path, mode: str) -> tuple[str, str]:
    """Keep the GTK base theme and icons consistent with the current palette."""
    theme = 'adw-gtk3-dark' if mode == 'dark' else 'adw-gtk3'
    try:
        preferences = json.loads((config / 'caelestia/cli.json').read_text()).get('theme', {})
    except (OSError, ValueError):
        preferences = {}
    icons = preferences.get('iconTheme' + mode.capitalize()) or preferences.get('iconTheme') or 'Papirus-' + mode.capitalize()
    for version in ('3.0', '4.0'):
        path = config / f'gtk-{version}/settings.ini'
        settings = configparser.ConfigParser(interpolation=None)
        settings.read(path)
        if not settings.has_section('Settings'):
            settings.add_section('Settings')
        settings['Settings']['gtk-theme-name'] = theme
        settings['Settings']['gtk-icon-theme-name'] = icons
        settings['Settings']['gtk-application-prefer-dark-theme'] = str(mode == 'dark').lower()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('w') as output:
            settings.write(output, space_around_delimiters=False)
    return theme, icons


def main() -> None:
    mode = os.environ.get('SCHEME_MODE')
    if mode not in ('dark', 'light'):
        state = Path(os.environ.get('XDG_STATE_HOME', Path.home() / '.local/state'))
        try:
            mode = json.loads((state / 'caelestia/scheme.json').read_text()).get('mode')
        except (OSError, ValueError):
            mode = 'dark'
    mode = 'light' if mode == 'light' else 'dark'
    theme, icons = sync_settings(CONFIG, mode)
    # Desktop portal settings must agree with the GTK settings files.
    for key, value in (('gtk-theme', theme), ('icon-theme', icons), ('color-scheme', 'prefer-' + mode)):
        try:
            subprocess.run(['gsettings', 'set', 'org.gnome.desktop.interface', key, value],
                           capture_output=True, timeout=5, check=False)
        except (OSError, subprocess.TimeoutExpired):
            pass
    for version in ("3.0", "4.0"):
        directory = CONFIG / f"gtk-{version}"
        update(
            directory / "gtk.css",
            lambda css: css.replace(
                "@define-color theme_selected_fg_color @primary;",
                "@define-color theme_selected_fg_color @accent_color;",
            ),
        )
        update(
            directory / "thunar.css",
            lambda css: css.split(MARKER, 1)[0].rstrip() + "\n" + COLORS,
        )


if __name__ == "__main__":
    main()
