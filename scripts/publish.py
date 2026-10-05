#!/usr/bin/env python3
"""Push the local desktop to the existing private Juarchy GitHub repository."""
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = 'jubaljacob/Juarchy'
URL = 'https://github.com/' + REPOSITORY


def run(*args, capture=False):
    return subprocess.run(args, cwd=ROOT, check=True, text=True,
                          stdout=subprocess.PIPE if capture else None).stdout


def main():
    if not shutil.which('gh'):
        raise SystemExit('GitHub CLI is missing. Run:\n  sudo pacman -S --needed github-cli\n  gh auth login\nThen run this script again.')
    status = subprocess.run(['gh', 'auth', 'status'], cwd=ROOT, capture_output=True)
    if status.returncode:
        raise SystemExit('Sign in first with: gh auth login\nThen run this script again.')
    if run('git', 'status', '--porcelain', capture=True).strip():
        raise SystemExit('Commit or save your local changes before publishing. Check: git status')
    repository = json.loads(run('gh', 'api', 'repos/' + REPOSITORY, capture=True))
    if not repository['private']:
        raise SystemExit('You chose a private repository. Set Juarchy to private in GitHub Settings before publishing.')
    if not repository.get('permissions', {}).get('push', False):
        raise SystemExit('The signed-in GitHub account does not have push access to ' + REPOSITORY)
    user = json.loads(run('gh', 'api', 'user', capture=True))
    login = user['login']
    run('git', 'config', 'user.name', user.get('name') or login)
    run('git', 'config', 'user.email', str(user['id']) + '+' + login + '@users.noreply.github.com')
    existing = subprocess.run(['git', 'remote', 'get-url', 'origin'], cwd=ROOT, capture_output=True, text=True)
    if existing.returncode == 0:
        allowed = {URL, URL + '.git', 'git@github.com:' + REPOSITORY + '.git',
                   'ssh://git@github.com/' + REPOSITORY + '.git'}
        if existing.stdout.strip().rstrip('/') not in allowed:
            raise SystemExit('Origin points to another repository; it was not changed:\n  ' + existing.stdout.strip())
    else:
        run('git', 'remote', 'add', 'origin', URL + '.git')
    run('gh', 'auth', 'setup-git')
    run('git', 'fetch', 'origin')
    # Preserve any commits used to initialize the GitHub repository. Never force-push.
    branch = repository.get('default_branch') or 'main'
    reference = 'refs/remotes/origin/' + branch
    remote_branch = subprocess.run(['git', 'rev-parse', '--verify', reference], cwd=ROOT, capture_output=True)
    if remote_branch.returncode == 0:
        merged = subprocess.run(['git', 'merge', '--allow-unrelated-histories', '--no-edit', reference], cwd=ROOT)
        if merged.returncode:
            raise SystemExit('GitHub has existing files that need a merge resolution.\n'
                             'Check git status, resolve and commit the merge, then run this script again. No files were pushed.')
    run('git', 'push', '-u', 'origin', 'main')
    run('git', 'push', 'origin', 'baseline-2026-10-05')
    print('Published private repository: ' + URL)


if __name__ == '__main__':
    main()
