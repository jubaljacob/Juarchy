#!/usr/bin/env python3
"""Switch the current desktop to Juarchy, with preflight checks and automatic rollback."""
import argparse
import fcntl
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

import install

ROOT = Path(__file__).resolve().parents[1]
SHELL = '.config/quickshell/juarchy'
FILES = ('.config/hypr/hyprland.lua', '.local/bin/jubal-launcher',
         '.local/bin/monitor-brightness', '.config/jubal-launcher/menu.json')


def run(*command):
    return subprocess.run(command, capture_output=True, text=True, check=True, timeout=20).stdout.strip()


def instances(config):
    output = run('qs', '-c', config, 'list', '-j')
    return [] if output.startswith('No running instances') else json.loads(output)


def stop(config):
    for instance in instances(config):
        run('qs', '-c', config, 'kill', '--pid', str(instance['pid']))
    deadline = time.monotonic() + 8
    while instances(config):
        if time.monotonic() >= deadline:
            raise RuntimeError(config + ' did not stop; refusing to start a second shell')
        time.sleep(0.1)


def start(config):
    run('qs', '-c', config, '-n', '-d')
    deadline = time.monotonic() + 15
    while True:
        try:
            locked = run('qs', '-c', config, 'ipc', 'call', 'lock', 'isLocked')
            if config == 'juarchy':
                if run('qs', '-c', config, 'ipc', 'call', 'juarchy', 'ready') != 'true':
                    raise RuntimeError('Juarchy is not ready')
                targets = run('qs', '-c', config, 'ipc', 'show')
                if not all(target in targets for target in ('jubalMenu', 'brightness', 'nexus', 'picker')):
                    raise RuntimeError('Required desktop controls are missing')
            if locked not in ('true', 'false'):
                raise RuntimeError('Invalid lock status')
            return
        except (RuntimeError, subprocess.SubprocessError):
            if time.monotonic() >= deadline:
                raise
            time.sleep(0.2)


def transform(name, text):
    if name.endswith('hyprland.lua'):
        for old, new in (('caelestia shell lock lock', '~/.local/bin/juarchy-shell lock lock'),
                         ('caelestia shell nexus open', '~/.local/bin/juarchy-shell nexus open'),
                         ('caelestia shell -d', '~/.local/bin/juarchy-shell start')):
            if old not in text:
                raise ValueError('Expected startup or shortcut missing: ' + old)
            text = text.replace(old, new)
        return text.replace('agent and Caelestia', 'agent and Juarchy')
    if name.endswith('jubal-launcher'):
        if '"qs", "-c", "caelestia"' not in text:
            raise ValueError('Expected native launcher routing missing')
        return text.replace('"qs", "-c", "caelestia"', '"qs", "-c", "juarchy"').replace(
            "Restart Caelestia with 'caelestia shell -r -d'", "Restart Juarchy with 'juarchy-shell restart'")
    if name.endswith('monitor-brightness'):
        if '"-c", "caelestia"' not in text:
            raise ValueError('Expected brightness routing missing')
        text = text.replace('"-c", "caelestia"', '"-c", "juarchy"')
        beginning = text.index('    try:\n        response = run(*command).strip()')
        end = text.index('    if not response.startswith', beginning)
        return (text[:beginning] + '    response = run(*command).strip()\n' + text[end:]).replace(
            'Caelestia did not accept', 'Juarchy did not accept')
    if name.endswith('menu.json'):
        menu = json.loads(text)
        def visit(node):
            for item in node['items']:
                if 'items' in item:
                    visit(item)
                command = item.get('command', [])
                if command[:2] == ['caelestia', 'shell']:
                    item['command'] = ['~/.local/bin/juarchy-shell', *command[2:]]
                elif command == ['caelestia', 'screenshot', '-r']:
                    item['command'] = ['qs', '-c', 'juarchy', 'ipc', 'call', 'picker', 'open']
                elif item['label'] == 'Caelestia version':
                    item['label'] = 'Juarchy shell version'
                    item['command'] = ['~/.local/bin/juarchy-shell', 'version']
        visit(menu)
        return json.dumps(menu, indent=2) + '\n'
    raise ValueError('Unexpected file: ' + name)


def restore(backup, home):
    manifest = json.loads((backup / 'manifest.json').read_text())
    if manifest['home'] != str(home) or (backup / 'FAILED').exists():
        raise ValueError('Backup is not a completed installation for this home')
    entries = {item['path']: backup / 'home' / item['path'] if item['previous'] else None
               for item in manifest['entries']}
    return install.apply(entries, home, shell=False)


def activate(home):
    old = instances('caelestia')
    if instances('juarchy'):
        raise RuntimeError('Juarchy is already running; use juarchy-shell restart after making edits')
    # Check the compositor and shell sockets BEFORE changing files or stopping anything.
    if not run('hyprctl', 'version'):
        raise RuntimeError('Cannot access the Hyprland session. Run this from a desktop terminal.')
    if old:
        locked = run('qs', '-c', 'caelestia', 'ipc', 'call', 'lock', 'isLocked')
        if locked != 'false':
            raise RuntimeError('Unlock the desktop before switching shells')
    with tempfile.TemporaryDirectory(prefix='juarchy-activate-') as directory:
        entries = {SHELL: ROOT / 'shell', '.local/bin/juarchy-shell': ROOT / 'home/.local/bin/juarchy-shell'}
        for name in FILES:
            source = install.safe_target(home, name)
            target = Path(directory) / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            target.write_text(transform(name, source.read_text()))
            entries[name] = target
        # Retain this computer's monitors, helpers, theme, histories and preferences.
        audio = home / '.local/bin/apply-audio-fix'
        if audio.exists():
            target = Path(directory) / 'apply-audio-fix'
            shutil.copy2(audio, target)
            target.write_text(audio.read_text().replace('["caelestia", "shell", "--restart"]',
                                                       '[str(Path.home() / ".local/bin/juarchy-shell"), "restart"]'))
            if 'from pathlib import Path' not in target.read_text():
                target.write_text(target.read_text().replace('import argparse\n',
                                                            'import argparse\nfrom pathlib import Path\n', 1))
            entries['.local/bin/apply-audio-fix'] = target
        backup = install.apply(entries, home)
    print('Backup: ' + str(backup), flush=True)
    try:
        if old:
            stop('caelestia')
        start('juarchy')
        run('hyprctl', 'reload')
        errors = run('hyprctl', 'configerrors')
        if errors and errors.lower() != 'ok':
            raise RuntimeError('Hyprland configuration errors: ' + errors)
    except BaseException:
        # Do not start the old shell if Juarchy cannot be stopped safely.
        stop('juarchy')
        recovery = restore(backup, home)
        if old:
            start('caelestia')
        run('hyprctl', 'reload')
        print('Activation failed; original configuration restored. Recovery backup: ' + str(recovery), file=sys.stderr)
        raise
    marker = home / '.local/state/juarchy/activation.json'
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(json.dumps({'backup': str(backup)}, indent=2) + '\n')
    print('Juarchy is active. Startup, launcher, lock, screenshots and brightness use the Juarchy shell.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rollback', action='store_true', help='restore the configuration from the last successful switch')
    args = parser.parse_args()
    home = Path.home()
    lockfile = home / '.local/state/juarchy/switch.lock'
    lockfile.parent.mkdir(parents=True, exist_ok=True)
    with lockfile.open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if not args.rollback:
            activate(home)
            return
        marker = home / '.local/state/juarchy/activation.json'
        backup = Path(json.loads(marker.read_text())['backup'])
        if run('qs', '-c', 'juarchy', 'ipc', 'call', 'lock', 'isLocked') != 'false':
            raise RuntimeError('Unlock Juarchy before rollback')
        stop('juarchy')
        recovery = restore(backup, home)
        start('caelestia')
        run('hyprctl', 'reload')
        marker.unlink()
        print('Original desktop restored. Juarchy files backed up to ' + str(recovery))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        detail = getattr(error, 'stderr', None) or str(error)
        print('Juarchy switch failed: ' + detail.strip(), file=sys.stderr)
        print('Run this command from an unlocked Hyprland desktop terminal.', file=sys.stderr)
        sys.exit(1)
