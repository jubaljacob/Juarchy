#!/usr/bin/env python3
"""Preview or deploy the shared desktop, with backups and reversible restores."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
SHELL_ITEMS = ('assets', 'components', 'modules', 'services', 'utils', 'shell.qml', 'LICENSE')


def exists(path):
    return path.exists() or path.is_symlink()


def remove(path):
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    elif exists(path):
        path.unlink()


def safe_target(home, relative):
    relative = Path(relative)
    if relative.is_absolute() or '..' in relative.parts or str(relative) == '.':
        raise ValueError('Invalid destination: ' + str(relative))
    path = home / relative
    for parent in path.parents:
        if parent == home:
            break
        if parent.is_symlink():
            raise ValueError('Destination parent is a symlink: ' + str(parent))
    return path


def plan(profile=None, home=None, shared_only=False):
    entries = {}
    trees = [ROOT / 'home']
    if profile:
        trees.append(ROOT / 'profiles' / profile / 'home')
    if not shared_only:
        trees.append(ROOT / 'local/home')
    for tree in trees:
        if not tree.exists():
            continue
        for source in sorted(tree.rglob('*')):
            if '__pycache__' in source.parts or source.suffix in ('.pyc', '.pyo'):
                continue
            if source.is_symlink():
                raise ValueError('Source symlinks are not supported: ' + str(source))
            if source.is_file():
                entries[str(source.relative_to(tree))] = source
    entries['.config/quickshell/juarchy'] = ROOT / 'shell'
    # Existing machine settings and consent always win, even over local/home.
    for name, example in (('.config/juarchy/privacy.json', 'privacy.json'),
                          ('.config/hypr/machine.lua', 'machine.lua')):
        if home is not None and exists(home / name):
            entries.pop(name, None)
        elif home is not None:
            entries.setdefault(name, ROOT / 'examples' / example)
    return entries


def write_file(source, target, home):
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    # Desktop Entry Exec requires quoted, escaped arguments (not shell expansion).
    if '@HOME@' in source.read_text(errors='ignore'):
        if source.suffix != '.desktop':
            raise ValueError('Unexpected HOME template: ' + str(source))
        quoted = str(home).replace('\\', '\\\\\\\\').replace('"', '\\\\"').replace('`', '\\\\`').replace('$', '\\\\$').replace('%', '%%')
        target.write_text(source.read_text().replace('@HOME@', quoted))


def deploy(source, target, home, shell=False):
    if shell:
        target.mkdir(parents=True, exist_ok=True)
        for name in SHELL_ITEMS:
            item = source / name
            if item.is_dir():
                shutil.copytree(item, target / name, ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.pyo'))
            else:
                shutil.copy2(item, target / name)
    elif source.is_symlink():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.symlink_to(os.readlink(source))
    elif source.is_dir():
        shutil.copytree(source, target, symlinks=True)
    else:
        write_file(source, target, home)


def backup_root(home):
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    root = home / '.local/state/jubal-desktop/backups' / stamp
    safe_target(home, root.relative_to(home) / 'manifest.json')
    root.mkdir(parents=True)
    return root


def apply(entries, home, shell=True):
    # Validate every destination before changing the first file.
    targets = {name: safe_target(home, name) for name in entries}
    backup = backup_root(home)
    manifest = {'home': str(home), 'entries': []}
    try:
        for name, source in entries.items():
            target = targets[name]
            previous = exists(target)
            item = {'path': name, 'previous': previous}
            if previous:
                archived = backup / 'home' / name
                archived.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(target), archived)
            manifest['entries'].append(item)
            (backup / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
            if source is not None:
                target.parent.mkdir(parents=True, exist_ok=True)
                deploy(source, target, home, shell and name == '.config/quickshell/juarchy')
    except Exception:
        # Restore all completed moves if deployment fails.
        for item in reversed(manifest['entries']):
            target = targets[item['path']]
            remove(target)
            if item['previous']:
                shutil.move(str(backup / 'home' / item['path']), target)
        (backup / 'FAILED').write_text('Deployment failed and changes were rolled back.\n')
        raise
    return backup


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='write files; without this flag only preview')
    parser.add_argument('--home', type=Path, default=Path.home(), help='target home (also useful for staging)')
    profiles = sorted(p.name for p in (ROOT / 'profiles').iterdir() if (p / 'home').is_dir())
    parser.add_argument('--profile', choices=profiles, help='optional hardware profile')
    parser.add_argument('--shared-only', action='store_true', help='ignore local/home overrides when installing on another computer')
    parser.add_argument('--restore', type=Path, help='restore one installer backup; current files are backed up again')
    args = parser.parse_args()
    home = args.home.expanduser().absolute()
    if not home.is_dir() or home.is_symlink():
        raise ValueError('Target home must be an existing real directory.')
    if args.restore and (args.profile or args.shared_only):
        raise ValueError('--restore cannot be combined with --profile or --shared-only.')
    if args.apply and not args.restore and home == Path.home().absolute():
        if os.geteuid() == 0:
            raise ValueError('Run the desktop installer as your regular user, without sudo.')
        for variable, directory in (('XDG_CONFIG_HOME', '.config'), ('XDG_DATA_HOME', '.local/share'),
                                    ('XDG_STATE_HOME', '.local/state')):
            if os.environ.get(variable) and Path(os.environ[variable]) != home / directory:
                raise ValueError(variable + ' uses a custom path; this installer requires ' + str(home / directory))
    if args.restore:
        backup = args.restore.expanduser().resolve()
        if (backup / 'FAILED').exists():
            raise ValueError('This deployment failed and was already rolled back.')
        manifest = json.loads((backup / 'manifest.json').read_text())
        if manifest['home'] != str(home):
            raise ValueError('Backup belongs to a different home directory.')
        entries = {}
        for item in manifest['entries']:
            safe_target(home, item['path'])
            source = backup / 'home' / item['path'] if item['previous'] else None
            if source is not None and not exists(source):
                raise ValueError('Incomplete backup: ' + item['path'])
            entries[item['path']] = source
    else:
        entries = plan(args.profile, home, args.shared_only)
    for name in entries:
        target = safe_target(home, name)
        print(('Replace ' if exists(target) else 'Create  ') + str(target))
    if not args.apply:
        print('\nPreview only. Add --apply to install. No services or packages are changed.')
        return
    backup = apply(entries, home, shell=not bool(args.restore))
    print('\nInstalled. Backup: ' + str(backup))
    print('Log out and back in to activate the desktop. No running services were restarted.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError) as error:
        print('Install failed: ' + str(error), file=sys.stderr)
        raise SystemExit(1)
