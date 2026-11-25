#!/usr/bin/env python3
"""Install and select a supported icon theme for the current Juarchy user."""
import argparse
import configparser
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('theme', choices=('kora', 'mkos-big-sur'))
    args = parser.parse_args()
    theme_name, repository, subdirectory = {
        'kora': ('kora', 'https://github.com/bikass/kora.git', 'kora'),
        'mkos-big-sur': ('Mkos-Big-Sur', 'https://github.com/zayronxio/Mkos-Big-Sur.git', ''),
    }[args.theme]
    home = Path.home()
    config = Path(os.environ.get('XDG_CONFIG_HOME', home / '.config'))
    data = Path(os.environ.get('XDG_DATA_HOME', home / '.local/share'))
    state = Path(os.environ.get('XDG_STATE_HOME', home / '.local/state'))
    backup = state / 'jubal-desktop/icon-backups' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    target = data / 'icons' / theme_name
    # Complete and verify the download before touching any existing settings.
    with tempfile.TemporaryDirectory(prefix='juarchy-icons-') as temporary:
        source = Path(temporary) / 'source'
        subprocess.run(['git', 'clone', '--depth', '1', repository, str(source)], check=True)
        icons = source / subdirectory
        if not (icons / 'index.theme').is_file():
            raise RuntimeError('The download does not contain an icon theme')
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() or target.is_symlink():
            backup.mkdir(parents=True, exist_ok=True)
            shutil.move(str(target), str(backup / theme_name))
        try:
            shutil.copytree(icons, target, symlinks=True, ignore=shutil.ignore_patterns('.git'))
        except Exception:
            if target.exists():
                shutil.rmtree(target)
            if (backup / theme_name).exists():
                shutil.move(str(backup / theme_name), str(target))
            raise
    if shutil.which('gtk-update-icon-cache'):
        subprocess.run(['gtk-update-icon-cache', '-f', '-t', str(target)], check=False)
    cli = config / 'caelestia/cli.json'
    preferences = json.loads(cli.read_text()) if cli.exists() else {}
    theme = preferences.setdefault('theme', {})
    for key in ('iconTheme', 'iconThemeDark', 'iconThemeLight'):
        theme[key] = theme_name
    for relative in ('caelestia/cli.json', 'gtk-3.0/settings.ini', 'gtk-4.0/settings.ini'):
        existing = config / relative
        if existing.exists():
            saved = backup / relative
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(existing, saved)
    cli.parent.mkdir(parents=True, exist_ok=True)
    cli.write_text(json.dumps(preferences, indent=2) + '\n')
    for version in ('3.0', '4.0'):
        path = config / f'gtk-{version}/settings.ini'
        settings = configparser.ConfigParser(interpolation=None)
        settings.read(path)
        if not settings.has_section('Settings'):
            settings.add_section('Settings')
        settings['Settings']['gtk-icon-theme-name'] = theme_name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('w') as stream:
            settings.write(stream, space_around_delimiters=False)
    subprocess.run(['gsettings', 'set', 'org.gnome.desktop.interface', 'icon-theme', theme_name], check=True)
    print(theme_name + ' installed and selected. Wallpaper colour changes will retain these icons.')
    print('Previous settings saved in:', backup)
    print('Restart the file manager: nautilus --quit; nautilus')


if __name__ == '__main__':
    main()
