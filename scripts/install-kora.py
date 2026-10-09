#!/usr/bin/env python3
"""Compatibility entry point for installing Kora."""
from pathlib import Path
import subprocess
import sys

if __name__ == '__main__':
    sys.exit(subprocess.run([sys.executable, str(Path(__file__).with_name('install-icon-theme.py')), 'kora'], check=False).returncode)
