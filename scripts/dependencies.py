#!/usr/bin/env python3
"""Print prerequisite commands or check installed Arch packages; never install."""
import argparse
from pathlib import Path
import shlex
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def packages(source):
    return [line.strip() for line in (ROOT / 'packages' / (source + '.txt')).read_text().splitlines()
            if line.strip() and not line.startswith('#')]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    arch, aur = packages('arch'), packages('aur')
    if args.check:
        if not shutil.which('pacman'):
            raise SystemExit('This baseline supports Arch Linux and Arch-based systems.')
        installed = set(subprocess.check_output(['pacman', '-Qq'], text=True).split())
        # Either packaged Quickshell satisfies the executable check; plugin ABI
        # compatibility still needs checking after upstream updates.
        if shutil.which('quickshell') or shutil.which('qs'):
            installed.add('quickshell-git')
        missing = sorted(set(arch + aur) - installed)
        print('Missing prerequisites: ' + ', '.join(missing) if missing else 'All package prerequisites are installed.')
        raise SystemExit(bool(missing))
    print('Official repositories (full upgrade avoids a partial upgrade):')
    print(shlex.join(['sudo', 'pacman', '-Syu', '--needed', *arch]))
    print('\nAUR dependencies (requires an AUR helper you have already set up):')
    print(shlex.join(['yay', '-S', '--needed', *aur]))


if __name__ == '__main__':
    main()
