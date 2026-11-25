"""Discover and apply Omarchy themes on a Juarchy desktop.

A theme is a directory with a ``colors.toml`` and, usually, ``backgrounds/``
and ``preview.png``.  Applying one hands Caelestia a complete scheme built from
the palette and sets one of the theme's backgrounds, so the shell, GTK and Qt
apps, terminals and Hyprland all follow.  Changing the background inside a
theme never touches the palette, as in Omarchy.
"""
import fcntl
import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path

from . import colors

IMAGE_SUFFIXES = ('.jpg', '.jpeg', '.png', '.webp')
SWATCHES = ('red', 'orange', 'yellow', 'green', 'cyan', 'blue', 'magenta')


def _home_dir(variable, fallback):
    value = os.environ.get(variable)
    return Path(value) if value else Path.home() / fallback


def data_home():
    return _home_dir('XDG_DATA_HOME', '.local/share')


def config_home():
    return _home_dir('XDG_CONFIG_HOME', '.config')


def state_home():
    return _home_dir('XDG_STATE_HOME', '.local/state')


def theme_roots():
    """Where themes live; a theme in a later directory replaces an earlier one.

    ``JUARCHY_OMARCHY_THEMES`` (a ``:`` separated list) replaces the defaults,
    which are the installed Omarchy themes and your own under the config home.
    """
    override = os.environ.get('JUARCHY_OMARCHY_THEMES')
    if override:
        return [Path(part) for part in override.split(':') if part]
    return [data_home() / 'juarchy/omarchy-themes', config_home() / 'juarchy/omarchy-themes']


def overlay_directory(theme_id):
    """Your own backgrounds for a theme, listed beside the theme's."""
    return config_home() / 'juarchy/omarchy-backgrounds' / theme_id


def state_path():
    return state_home() / 'juarchy/omarchy-theme.json'


def scheme_path():
    return state_home() / 'caelestia/scheme.json'


def title_for(theme_id):
    return ' '.join(part.capitalize() for part in theme_id.replace('_', '-').split('-'))


class Theme:
    def __init__(self, theme_id, directory):
        self.id = theme_id
        self.directory = Path(directory)

    @property
    def title(self):
        return title_for(self.id)

    @property
    def preview(self):
        path = self.directory / 'preview.png'
        return path if path.is_file() else None

    def palette(self):
        return colors.load_palette(self.directory / 'colors.toml')

    def backgrounds(self):
        """Your overlay images first, then the theme's own, each by name."""
        found = []
        for folder in (overlay_directory(self.id), self.directory / 'backgrounds'):
            if not folder.is_dir():
                continue
            found.extend(sorted((entry for entry in folder.iterdir()
                                 if entry.is_file() and entry.suffix.lower() in IMAGE_SUFFIXES),
                                key=lambda entry: entry.name.lower()))
        return found


def discover():
    themes = {}
    for root in theme_roots():
        if not root.is_dir():
            continue
        for entry in root.iterdir():
            if entry.is_dir() and (entry / 'colors.toml').is_file():
                themes[entry.name] = Theme(entry.name, entry)
    return [themes[key] for key in sorted(themes)]


def find(theme_id):
    for theme in discover():
        if theme.id == theme_id:
            return theme
    raise ValueError('Unknown theme "%s". Run: juarchy-theme omarchy list' % theme_id)


def read_state():
    try:
        data = json.loads(state_path().read_text())
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def write_state(theme_id, background):
    path = state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(handle, 'w') as stream:
            json.dump({'theme': theme_id, 'background': str(background)}, stream, indent=2)
            stream.write('\n')
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def current_scheme():
    try:
        data = json.loads(scheme_path().read_text())
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def active_theme_id():
    """The Omarchy theme driving the desktop, or '' when another scheme is."""
    scheme = current_scheme()
    state = read_state()
    if scheme.get('flavour') == 'omarchy' and scheme.get('name') == state.get('theme'):
        return state['theme']
    return ''


@contextmanager
def exclusive():
    """Serialise theme changes so quick key presses cannot interleave."""
    lock = state_home() / 'juarchy/omarchy-theme.lock'
    lock.parent.mkdir(parents=True, exist_ok=True)
    with lock.open('a') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        yield


def choose_background(theme, wanted=None):
    images = theme.backgrounds()
    if not images:
        raise ValueError('%s has no background images' % theme.title)
    if wanted is None or wanted == '':
        return images[0]
    wanted = str(wanted)
    for image in images:
        if wanted in (image.name, image.stem, str(image)):
            return image
    if wanted.isdigit() and int(wanted) < len(images):
        return images[int(wanted)]
    # Any image of your own can sit under a theme's palette.
    path = Path(wanted).expanduser()
    if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES:
        return path.resolve()
    raise ValueError('%s has no background "%s"' % (theme.title, wanted))


def _backfill(colours, mode, schemes):
    """Cover keys a newer Caelestia asks for that a theme palette lacks."""
    try:
        reference = schemes.read_colours_from_file(schemes.scheme_data_dir / 'gruvbox/soft' / (mode + '.txt'))
    except (OSError, ValueError):
        return colours
    return {**{key: value for key, value in reference.items() if key not in colours}, **colours}


def _through_caelestia(scheme, image, recolour):
    """Set the wallpaper with Caelestia while keeping ``scheme``'s colours.

    Caelestia re-reads built-in scheme files whenever the wallpaper changes,
    and Omarchy themes are not among them, so the scheme is kept as given.
    ``recolour`` False leaves GTK, Qt, terminals and the rest alone, for when
    only the background moves and the palette is already applied.
    """
    import caelestia.utils.scheme as schemes
    import caelestia.utils.wallpaper as wallpapers

    class Fixed(schemes.Scheme):
        def _update_colours(self):
            pass

    data = dict(scheme, colours=_backfill(scheme['colours'], scheme['mode'], schemes))
    previous_scheme = schemes.scheme
    original = wallpapers.apply_colours
    schemes.scheme = Fixed(data)
    if not recolour:
        wallpapers.apply_colours = lambda *args, **kwargs: None
    try:
        wallpapers.set_wallpaper(Path(image), no_smart=True)
    finally:
        wallpapers.apply_colours = original
        schemes.scheme = previous_scheme


def _previous_look():
    scheme = current_scheme()
    try:
        wallpaper = Path(state_home().joinpath('caelestia/wallpaper/path.txt').read_text().strip())
    except OSError:
        wallpaper = None
    ready = isinstance(scheme.get('colours'), dict) and all(
        key in scheme for key in ('name', 'flavour', 'mode', 'variant'))
    return (scheme, wallpaper) if ready and wallpaper and wallpaper.is_file() else (None, None)


def apply_theme(theme_id, background=None):
    """Switch palette and background together.  Returns (theme, background)."""
    theme = find(theme_id)
    palette = theme.palette()
    image = choose_background(theme, background)
    scheme = colors.scheme_for(theme.id, palette)
    with exclusive():
        before, wallpaper = _previous_look()
        try:
            _through_caelestia(scheme, image, recolour=True)
        except Exception:
            if before:  # Put back what was on screen rather than a half-applied theme.
                try:
                    _through_caelestia(before, wallpaper, recolour=True)
                except Exception:
                    pass
            raise
        write_state(theme.id, image)
    return theme, image


def set_background(wanted):
    """Change the image, keeping the palette.

    With an Omarchy theme active ``wanted`` is a name or index from its
    backgrounds, or any image path; the palette stays the theme's.
    """
    theme_id = active_theme_id()
    if not theme_id:
        raise ValueError('No Omarchy theme is active. Choose one first: juarchy-theme omarchy set NAME')
    theme = find(theme_id)
    image = choose_background(theme, wanted)
    with exclusive():
        _through_caelestia(current_scheme(), image, recolour=False)
        write_state(theme.id, image)
    return theme, image


def cycle_background(step=1):
    theme_id = active_theme_id()
    if not theme_id:
        raise ValueError('No Omarchy theme is active. Choose one first: juarchy-theme omarchy set NAME')
    theme = find(theme_id)
    images = theme.backgrounds()
    if not images:
        raise ValueError('%s has no background images' % theme.title)
    current = read_state().get('background', '')
    names = [str(image) for image in images]
    index = names.index(current) if current in names else (-1 if step > 0 else 0)
    return set_background(str(images[(index + step) % len(images)]))


def cycle_theme(step=1):
    themes = discover()
    if not themes:
        raise ValueError('No Omarchy themes are installed. Run scripts/install-omarchy-themes.py')
    ids = [theme.id for theme in themes]
    current = active_theme_id()
    index = ids.index(current) if current in ids else (-1 if step > 0 else 0)
    return apply_theme(ids[(index + step) % len(ids)])


def describe():
    """Everything the settings page needs, as plain JSON-able data."""
    active = active_theme_id()
    background = read_state().get('background', '') if active else ''
    themes = []
    for theme in discover():
        try:
            palette = theme.palette()
        except (OSError, ValueError):
            continue
        overlay = overlay_directory(theme.id)
        themes.append({
            'id': theme.id,
            'title': theme.title,
            'mode': palette['mode'],
            'accent': '#' + palette['accent'],
            'background': '#' + palette['background'],
            'foreground': '#' + palette['foreground'],
            'swatches': ['#' + palette[name] for name in SWATCHES],
            'preview': str(theme.preview) if theme.preview else '',
            'active': theme.id == active,
            'backgrounds': [{'name': image.name, 'path': str(image),
                             'user': overlay in image.parents,
                             'current': str(image) == background}
                            for image in theme.backgrounds()],
        })
    return {'active': bool(active), 'theme': active, 'background': background, 'themes': themes}
