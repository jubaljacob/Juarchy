#!/usr/bin/env python3
"""Create the private GitHub repository and push the local baseline after login."""
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def run(*args, capture=False):
    return subprocess.run(args, cwd=ROOT, check=True, text=True,
                          stdout=subprocess.PIPE if capture else None).stdout


def main():
    if not shutil.which('gh'):
        raise SystemExit('GitHub CLI is missing. Run:\n  sudo pacman -S --needed github-cli\n  gh auth login\nThen run this script again.')
    status = subprocess.run(['gh', 'auth', 'status'], cwd=ROOT, capture_output=True)
    if status.returncode:
        raise SystemExit('Sign in first with: gh auth login\nThen run this script again.')
    user = json.loads(run('gh', 'api', 'user', capture=True))
    login = user['login']
    run('git', 'config', 'user.name', user.get('name') or login)
    run('git', 'config', 'user.email', str(user['id']) + '+' + login + '@users.noreply.github.com')
    remote_name = login + '/jubal-desktop'
    existing = subprocess.run(['git', 'remote', 'get-url', 'origin'], cwd=ROOT, capture_output=True, text=True)
    if existing.returncode == 0:
        raise SystemExit('An origin remote already exists. Verify it before pushing:\n  ' + existing.stdout.strip())
    # Do not take over an existing repository with the same name.
    existing_repo = subprocess.run(['gh', 'repo', 'view', remote_name], cwd=ROOT, capture_output=True)
    if existing_repo.returncode == 0:
        raise SystemExit(remote_name + ' already exists. Choose a new name before publishing.')
    run('gh', 'repo', 'create', remote_name, '--private', '--source', str(ROOT), '--remote', 'origin',
        '--description', 'Personal Hyprland desktop based on Caelestia, with a portable baseline and hardware profiles')
    run('gh', 'auth', 'setup-git')
    run('git', 'push', '-u', 'origin', 'main')
    run('git', 'push', 'origin', 'baseline-2026-10-05')
    print('Published private repository: https://github.com/' + remote_name)


if __name__ == '__main__':
    main()
