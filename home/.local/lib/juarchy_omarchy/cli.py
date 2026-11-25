"""Command line for Omarchy themes: ``juarchy-theme omarchy ...``."""
import argparse
import json
import shutil
import subprocess
import sys

from . import themes


def parser():
    main = argparse.ArgumentParser(prog='juarchy-theme omarchy', description=__doc__)
    sub = main.add_subparsers(dest='action', required=True)

    listing = sub.add_parser('list', help='installed themes')
    listing.add_argument('--json', action='store_true')

    sub.add_parser('current', help='the active theme and background')

    chosen = sub.add_parser('set', help='apply a theme: palette, wallpaper and every app')
    chosen.add_argument('theme')
    chosen.add_argument('--background', help='background name, number or path (default: the first)')
    chosen.add_argument('--notify', action='store_true')

    for name, text in (('next', 'switch to the next theme'), ('prev', 'switch to the previous theme')):
        sub.add_parser(name, help=text).add_argument('--notify', action='store_true')

    background = sub.add_parser('background', help='change the background, keeping the theme')
    steps = background.add_subparsers(dest='step', required=True)
    steps.add_parser('list', help="the active theme's backgrounds").add_argument('--json', action='store_true')
    for name in ('next', 'prev'):
        steps.add_parser(name).add_argument('--notify', action='store_true')
    steps.add_parser('set').add_argument('image', help='background name, number or image path')
    return main


def notify(summary, body=''):
    if shutil.which('notify-send'):
        subprocess.run(['notify-send', '-a', 'Juarchy', '-t', '2500', summary, body],
                       check=False, timeout=5)


def report(theme, image, announce):
    print('%s · %s' % (theme.title, image.name))
    if announce:
        notify('Theme: ' + theme.title, image.name)


def run(argv):
    args = parser().parse_args(argv)
    if args.action == 'list':
        data = themes.describe()
        if args.json:
            print(json.dumps(data))
        else:
            for theme in data['themes']:
                marker = '*' if theme['active'] else ' '
                print('%s %-18s %-5s %d backgrounds' % (marker, theme['id'], theme['mode'], len(theme['backgrounds'])))
    elif args.action == 'current':
        data = themes.describe()
        print(json.dumps({key: data[key] for key in ('active', 'theme', 'background')}))
    elif args.action == 'set':
        report(*themes.apply_theme(args.theme, args.background), args.notify)
    elif args.action in ('next', 'prev'):
        report(*themes.cycle_theme(1 if args.action == 'next' else -1), args.notify)
    elif args.action == 'background':
        if args.step == 'list':
            data = themes.describe()
            current = next((theme for theme in data['themes'] if theme['active']), None)
            images = current['backgrounds'] if current else []
            if args.json:
                print(json.dumps(images))
            else:
                for image in images:
                    print('%s %s' % ('*' if image['current'] else ' ', image['name']))
        elif args.step == 'set':
            report(*themes.set_background(args.image), False)
        else:
            report(*themes.cycle_background(1 if args.step == 'next' else -1), args.notify)
    return 0


def main(argv=None):
    try:
        return run(sys.argv[1:] if argv is None else argv)
    except (OSError, ValueError, ImportError) as error:
        print(str(error), file=sys.stderr)
        return 1
