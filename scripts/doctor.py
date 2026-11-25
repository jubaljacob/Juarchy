#!/usr/bin/env python3
"""Read-only checks before installing Juarchy on an Arch Linux desktop."""
import os
from pathlib import Path
import re
import shutil
import subprocess

from dependencies import packages


def version_tuple(value):
    match = re.match(r'(?:\d+:)?(\d+)\.(\d+)\.(\d+)', value)
    return tuple(map(int, match.groups())) if match else None


def assess(installed, which=shutil.which, home=None, environ=None, uid=None):
    home = home or Path.home()
    environ = os.environ if environ is None else environ
    uid = os.geteuid() if uid is None else uid
    errors, warnings = [], []
    if uid == 0:
        errors.append('Run as your desktop user, without sudo.')
    for variable, directory in (('XDG_CONFIG_HOME', '.config'), ('XDG_DATA_HOME', '.local/share'),
                                ('XDG_STATE_HOME', '.local/state')):
        if environ.get(variable) and Path(environ[variable]) != home / directory:
            errors.append(variable + ' must be unset or ' + str(home / directory))
    required = set(packages('arch') + packages('aur'))
    # The stable package can also provide qs; runtime compatibility is separate.
    if which('qs'):
        required.discard('quickshell-git')
    missing = sorted(required - installed.keys())
    if missing:
        errors.append('Missing packages: ' + ', '.join(missing) + '. See python scripts/dependencies.py')
    for command in ('Hyprland', 'hyprctl', 'qs', 'caelestia', 'grim', 'slurp',
                    'wl-copy', 'wpctl', 'hyprsunset', 'gpu-screen-recorder'):
        if not which(command):
            errors.append('Missing executable: ' + command)
    hyprland = version_tuple(installed.get('hyprland', ''))
    if hyprland is None or hyprland < (0, 56, 2):
        errors.append('This Lua configuration requires Hyprland 0.56.2 or newer.')
    for package, baseline in (('hyprland', (0, 56, 2)), ('caelestia-shell', (2, 5, 0)),
                              ('caelestia-cli', (1, 1, 3))):
        if package in installed and version_tuple(installed[package]) != baseline:
            warnings.append(package + ' ' + installed[package] + ' differs from the tested baseline '
                            + '.'.join(map(str, baseline)) + '; check shell startup.')
    if not environ.get('HYPRLAND_INSTANCE_SIGNATURE'):
        warnings.append('No Hyprland session detected. Check graphics and shell startup after login.')
    return errors, warnings


def main():
    if not shutil.which('pacman'):
        raise SystemExit('Juarchy requires Arch Linux (or an Arch-based system) with pacman.')
    result = subprocess.run(['pacman', '-Q'], text=True, capture_output=True, check=True, timeout=20)
    installed = dict(line.split(maxsplit=1) for line in result.stdout.splitlines())
    errors, warnings = assess(installed)
    for message in errors:
        print('FAIL: ' + message)
    for message in warnings:
        print('NOTE: ' + message)
    for unit in ('NetworkManager.service', 'bluetooth.service', 'power-profiles-daemon.service'):
        result = subprocess.run(['systemctl', 'is-active', '--quiet', unit],
                                capture_output=True, text=True, check=False, timeout=10)
        if result.stderr.strip():
            print('NOTE: Could not inspect ' + unit + ': ' + result.stderr.strip().splitlines()[0])
        elif result.returncode:
            print('NOTE: ' + unit + ' is not active. See docs/INSTALL.md for service setup.')
    if errors:
        raise SystemExit(1)
    print('Prerequisites passed. Native plugin ABI, graphics, suspend and unlocking still need a desktop test.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, subprocess.SubprocessError) as error:
        raise SystemExit('Checks could not finish: ' + str(error))
