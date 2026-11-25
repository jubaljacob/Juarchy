#!/usr/bin/env python3
"""Install Omarchy's themes (palettes, wallpapers, previews) for Juarchy.

The themes come from https://github.com/basecamp/omarchy (MIT licensed) at a
pinned revision, or from a local checkout given with --source.  Only colour
palettes, preview images and still backgrounds are installed; intro videos
and other Omarchy files are left out.  Without --apply this only previews.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'home/.local/lib'))

from juarchy_omarchy import colors  # noqa: E402

REPOSITORY = 'https://github.com/basecamp/omarchy'
REVISION = 'd4985887d6a1cfe6fc2f87b84585ec15958ab6ae'
IMAGE_SUFFIXES = ('.jpg', '.jpeg', '.png', '.webp')
MANIFEST = 'SOURCE.json'


def destination():
    base = os.environ.get('XDG_DATA_HOME') or Path.home() / '.local/share'
    return Path(base) / 'juarchy/omarchy-themes'


def fetch(revision, target):
    """Sparse, shallow checkout of just the files Juarchy uses."""
    def git(*arguments):
        subprocess.run(['git', '-C', str(target), *arguments], check=True, timeout=600)
    git('init', '-q')
    git('remote', 'add', 'origin', REPOSITORY)
    patterns = ['/LICENSE', '/themes/*/colors.toml', '/themes/*/preview.png']
    patterns += ['/themes/*/backgrounds/*' + suffix for suffix in IMAGE_SUFFIXES]
    git('sparse-checkout', 'set', '--no-cone', *patterns)
    git('fetch', '-q', '--depth', '1', '--filter=blob:none', 'origin', revision)
    git('checkout', '-q', 'FETCH_HEAD')
    return target


def locate(source):
    """Accept an Omarchy checkout or its themes directory."""
    source = Path(source).expanduser().resolve()
    themes = source / 'themes' if (source / 'themes').is_dir() else source
    if not themes.is_dir():
        raise ValueError('No themes directory under ' + str(source))
    licence = next((path for path in (source / 'LICENSE', source.parent / 'LICENSE') if path.is_file()), None)
    return themes, licence


def plan(themes):
    chosen, skipped = {}, {}
    for entry in sorted(themes.iterdir()):
        palette = entry / 'colors.toml'
        if not palette.is_file():
            continue
        try:
            colors.load_palette(palette)
        except (OSError, ValueError) as error:
            skipped[entry.name] = str(error)
            continue
        images = [path for path in sorted((entry / 'backgrounds').glob('*'))
                  if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES]
        chosen[entry.name] = {'palette': palette, 'preview': entry / 'preview.png', 'images': images}
    return chosen, skipped


def install(chosen, licence, target, revision):
    target.mkdir(parents=True, exist_ok=True)
    try:
        previous = set(json.loads((target / MANIFEST).read_text()).get('themes', []))
    except (OSError, ValueError):
        previous = set()
    for name, files in chosen.items():
        staging = Path(tempfile.mkdtemp(prefix='.install-', dir=target))
        try:
            shutil.copy2(files['palette'], staging / 'colors.toml')
            if files['preview'].is_file():
                shutil.copy2(files['preview'], staging / 'preview.png')
            (staging / 'backgrounds').mkdir()
            for image in files['images']:
                shutil.copy2(image, staging / 'backgrounds' / image.name)
            live = target / name
            if live.exists():
                shutil.rmtree(live)
            staging.rename(live)
            os.chmod(live, 0o755)
        finally:
            shutil.rmtree(staging, ignore_errors=True)
    for name in previous - set(chosen):  # Themes Omarchy has since dropped.
        shutil.rmtree(target / name, ignore_errors=True)
    if licence:
        shutil.copy2(licence, target / 'LICENSE')
    (target / MANIFEST).write_text(json.dumps({
        'source': REPOSITORY, 'revision': revision, 'themes': sorted(chosen)}, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='write files; without this flag only preview')
    parser.add_argument('--source', type=Path, help='an Omarchy checkout (or its themes directory) instead of downloading')
    parser.add_argument('--revision', default=REVISION, help='Omarchy commit to download (default: the pinned one)')
    parser.add_argument('--destination', type=Path, default=destination(), help='install location')
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix='omarchy-themes-') as scratch:
        if args.source:
            themes, licence = locate(args.source)
            revision = 'local checkout'
        else:
            if not shutil.which('git'):
                raise ValueError('git is required to download the themes')
            print('Downloading Omarchy themes at %s ...' % args.revision[:12], flush=True)
            checkout = fetch(args.revision, Path(scratch))
            themes, licence = locate(checkout)
            revision = args.revision
        chosen, skipped = plan(themes)
        if not chosen:
            raise ValueError('No usable themes were found')
        for name, files in chosen.items():
            print('%-18s %d backgrounds%s' % (name, len(files['images']), '' if files['preview'].is_file() else ', no preview'))
        for name, reason in skipped.items():
            print('Skipped %s: %s' % (name, reason), file=sys.stderr)
        if not args.apply:
            print('\nPreview only. Run again with --apply to install into', args.destination)
            return 0
        install(chosen, licence, args.destination, revision)
    print('\nInstalled %d themes into %s' % (len(chosen), args.destination))
    print('Pick one in Settings → Wallpaper & style, or run: juarchy-theme omarchy list')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
