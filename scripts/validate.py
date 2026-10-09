#!/usr/bin/env python3
"""Validate portable source and exercise deployment/restore and package guidance."""
import ast
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    count = 0
    for directory in ('shell', 'home', 'profiles', 'scripts', 'tests', 'examples'):
        for path in (ROOT / directory).rglob('*'):
            if '__pycache__' in path.parts:
                continue
            if path.is_symlink():
                raise ValueError('Repository source must be self-contained: ' + str(path.relative_to(ROOT)))
            if not path.is_file():
                continue
            if path.suffix == '.py' or (path.parent.name == 'bin' and path.read_bytes().startswith(b'#!/usr/bin/env python')):
                ast.parse(path.read_text(), filename=str(path))
            if path.suffix == '.json':
                json.loads(path.read_text())
            if path.suffix in ('.qml', '.js', '.json', '.lua', '.py', '.sh', '.desktop', '.ini', '.css', '.yaml') or path.parent.name == 'bin':
                text = path.read_text()
                if directory in ('shell', 'home', 'profiles') and '/home/jubal/' in text:
                    raise ValueError('Personal home path: ' + str(path.relative_to(ROOT)))
                if re.search(r'(ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|-----BEGIN (?:OPENSSH|RSA|EC) PRIVATE KEY-----)', text):
                    raise ValueError('Possible credential: ' + str(path.relative_to(ROOT)))
            count += 1
    print('Validated source paths, Python syntax, JSON, and credential exclusions:', count, 'files', flush=True)
    if shutil.which('luac'):
        subprocess.run(['luac', '-p', str(ROOT / 'home/.config/hypr/hyprland.lua')], check=True)
    if shutil.which('bash'):
        for directory in ('shell', 'home', 'profiles'):
            for path in (ROOT / directory).rglob('*'):
                if path.is_file() and (path.suffix == '.sh' or path.read_bytes().startswith((b'#!/bin/sh', b'#!/usr/bin/env bash'))):
                    subprocess.run(['bash', '-n', str(path)], check=True)
    subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'], cwd=ROOT, check=True)
    subprocess.run([sys.executable, 'home/.local/lib/jubal_launcher/test_package_guidance.py'], cwd=ROOT, check=True,
                   env={**os.environ, 'PYTHONPATH': str(ROOT / 'home/.local/lib')})
    qml_runner = shutil.which('qmltestrunner') or shutil.which('qmltestrunner6')
    if not qml_runner and Path('/usr/lib/qt6/bin/qmltestrunner').exists():
        qml_runner = '/usr/lib/qt6/bin/qmltestrunner'
    if qml_runner:
        subprocess.run([qml_runner, '-input', str(ROOT / 'tests/qml'), '-o', '-,txt'],
                       check=True, timeout=30, env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen'})
    print('Validation passed. Live QML rendering and hardware behavior still require a desktop session.')


if __name__ == '__main__':
    main()
