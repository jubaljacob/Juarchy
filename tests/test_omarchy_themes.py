import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'home/.local/lib'))

from juarchy_omarchy import cli, colors, themes  # noqa: E402

TOKYO = '''
mode = "dark"
accent = "#7aa2f7"
selection = "#292e42"
muted = "#414868"
background = "#1a1b26"
dark_background = "#13141c"
darker_background = "#0e0e14"
lighter_background = "#24283b"
foreground = "#a9b1d6"
dark_foreground = "#565f89"
light_foreground = "#b4bee6"
bright_foreground = "#c0caf5"
red = "#f7768e"
yellow = "#e0af68"
orange = "#eb927b"
green = "#9ece6a"
cyan = "#449dab"
blue = "#7aa2f7"
magenta = "#ad8ee6"
brown = "#75493d"
bright_red = "#ff7a93"
bright_yellow = "#ff9e64"
bright_green = "#b9f27c"
bright_cyan = "#0db9d7"
bright_blue = "#7da6ff"
bright_magenta = "#bb9af7"
'''

LATTE = TOKYO.replace('mode = "dark"', 'mode = "light"') \
    .replace('#1a1b26', '#eff1f5').replace('#13141c', '#e3e4e8').replace('#0e0e14', '#d7d8dc') \
    .replace('#24283b', '#dce0e8').replace('#a9b1d6', '#4c4f69')

VANTA = TOKYO.replace('#1a1b26', '#000000').replace('#13141c', '#090909').replace('#0e0e14', '#070707') \
    .replace('#24283b', '#1a1a1a').replace('#292e42', '#1a1a1a').replace('#7aa2f7', '#8d8d8d')

# The least a theme may say.
MINIMAL = 'accent = "#ff8800"\nbackground = "#101010"\nforeground = "#dddddd"\n'


def write_theme(root, name, palette=TOKYO, backgrounds=('0-first.webp', '1-second.png', 'notes.txt'), preview=True):
    folder = Path(root) / name
    (folder / 'backgrounds' / 'intros').mkdir(parents=True)
    (folder / 'colors.toml').write_text(palette)
    for image in backgrounds:
        (folder / 'backgrounds' / image).write_bytes(b'img')
    (folder / 'backgrounds/intros/0-first.mp4').write_bytes(b'video')
    if preview:
        (folder / 'preview.png').write_bytes(b'png')
    return folder


def write_colours(path, text):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(text)
    return Path(path)


class ColourMapping(unittest.TestCase):
    def palette(self, text):
        with tempfile.TemporaryDirectory() as directory:
            return colors.load_palette(write_colours(Path(directory) / 'colors.toml', text))

    def test_hex_forms(self):
        self.assertEqual(colors.normalise('#ABC'), 'aabbcc')
        self.assertEqual(colors.normalise('#112233ff'), '112233')
        self.assertEqual(colors.normalise('445566'), '445566')
        with self.assertRaises(ValueError):
            colors.normalise('#12345')

    def test_terminal_colours_follow_omarchys_own_mapping(self):
        scheme = colors.scheme_for('tokyo-night', self.palette(TOKYO))
        c = scheme['colours']
        self.assertEqual((c['term0'], c['term7'], c['term8'], c['term15']), ('1a1b26', 'a9b1d6', '414868', 'c0caf5'))
        self.assertEqual((c['term1'], c['term2'], c['term3'], c['term4'], c['term5'], c['term6']),
                         ('f7768e', '9ece6a', 'e0af68', '7aa2f7', 'ad8ee6', '449dab'))
        self.assertEqual((c['term9'], c['term10'], c['term11'], c['term12'], c['term13'], c['term14']),
                         ('ff7a93', 'b9f27c', 'ff9e64', '7da6ff', 'bb9af7', '0db9d7'))

    def test_surface_text_and_accent_come_straight_from_the_theme(self):
        scheme = colors.scheme_for('tokyo-night', self.palette(TOKYO))
        c = scheme['colours']
        self.assertEqual((scheme['name'], scheme['flavour'], scheme['mode']), ('tokyo-night', 'omarchy', 'dark'))
        self.assertEqual((c['primary'], c['surface'], c['background'], c['onSurface'], c['error']),
                         ('7aa2f7', '1a1b26', '1a1b26', 'a9b1d6', 'f7768e'))
        self.assertEqual(c['surfaceContainerLowest'], '0e0e14')
        self.assertEqual(c['surfaceContainer'], '24283b')
        self.assertEqual(c['surfaceContainerHighest'], '292e42')

    def test_every_key_a_built_in_scheme_has_is_present(self):
        reference = Path('/usr/lib/python3.14/site-packages/caelestia/data/schemes/gruvbox/soft/dark.txt')
        if not reference.exists():
            self.skipTest('Caelestia CLI is not installed')
        wanted = {line.split()[0] for line in reference.read_text().splitlines() if line.strip()}
        for text in (TOKYO, LATTE, VANTA, MINIMAL):
            self.assertEqual(wanted - set(colors.scheme_for('t', self.palette(text))['colours']), set())

    def test_every_value_is_a_bare_hex_colour(self):
        for text in (TOKYO, LATTE, VANTA, MINIMAL):
            for name, value in colors.scheme_for('t', self.palette(text))['colours'].items():
                self.assertRegex(value, r'^[0-9a-f]{6}$', name)

    def test_surfaces_step_towards_the_text_in_dark_and_light_themes(self):
        for text, dark in ((TOKYO, True), (LATTE, False), (VANTA, True), (MINIMAL, True)):
            c = colors.scheme_for('t', self.palette(text))['colours']
            levels = [colors.luminance(c[key]) for key in ('surface', 'surfaceContainerLow', 'surfaceContainer',
                                                           'surfaceContainerHigh', 'surfaceContainerHighest')]
            steps = [b - a for a, b in zip(levels, levels[1:])]
            self.assertTrue(all(step > 0 for step in steps) if dark else all(step < 0 for step in steps), (text[:30], levels))

    def test_text_and_labels_stay_readable(self):
        for text in (TOKYO, LATTE, VANTA, MINIMAL):
            c = colors.scheme_for('t', self.palette(text))['colours']
            for on, over in (('onSurface', 'surface'), ('onSurfaceVariant', 'surface'), ('onPrimary', 'primary'),
                             ('onPrimaryContainer', 'primaryContainer'), ('onSecondaryContainer', 'secondaryContainer'),
                             ('onTertiary', 'tertiary'), ('onError', 'error')):
                self.assertGreaterEqual(colors.contrast(c[on], c[over]), 4.5, (on, over, text[:40]))

    def test_light_mode_comes_from_the_file_and_defaults_from_the_background(self):
        self.assertEqual(self.palette(LATTE)['mode'], 'light')
        self.assertEqual(self.palette(MINIMAL)['mode'], 'dark')
        self.assertEqual(self.palette(MINIMAL.replace('#101010', '#f0f0f0'))['mode'], 'light')

    def test_a_palette_missing_optional_keys_is_completed(self):
        palette = self.palette(MINIMAL)
        for key in ('dark_background', 'lighter_background', 'selection', 'muted', 'bright_red', 'orange', 'brown', 'bright_foreground'):
            self.assertRegex(palette[key], r'^[0-9a-f]{6}$', key)

    def test_non_colour_values_such_as_border_gradients_are_ignored(self):
        palette = self.palette(TOKYO + 'hyprland_active_border = "rgba(33ccffee) rgba(00ff99ee) 45deg"\n')
        self.assertNotIn('hyprland_active_border', palette)

    def test_missing_core_colours_are_an_error(self):
        for text in ('accent = "#fff"\nbackground = "#000"\n', 'foreground = "#fff"\nbackground = "#000"\n'):
            with self.assertRaises(ValueError):
                self.palette(text)

    def test_tertiary_stands_apart_from_the_accent(self):
        palette = self.palette(TOKYO)
        self.assertGreaterEqual(colors.hue_distance(colors.pick_tertiary(palette), palette['accent']), 40)

    @unittest.skipUnless((Path.home() / '.local/share/juarchy/omarchy-themes').is_dir(), 'Omarchy themes are not installed')
    def test_every_installed_omarchy_theme_maps_cleanly(self):
        found = 0
        for entry in sorted((Path.home() / '.local/share/juarchy/omarchy-themes').glob('*/colors.toml')):
            palette = colors.load_palette(entry)
            c = colors.scheme_for(entry.parent.name, palette)['colours']
            dark = palette['mode'] == 'dark'
            levels = [colors.luminance(c[k]) for k in ('surface', 'surfaceContainerLow', 'surfaceContainer',
                                                       'surfaceContainerHigh', 'surfaceContainerHighest')]
            self.assertTrue(all((b > a) == dark for a, b in zip(levels, levels[1:])), entry.parent.name)
            self.assertGreaterEqual(colors.contrast(c['onSurface'], c['surface']), 4.5, entry.parent.name)
            self.assertGreaterEqual(colors.contrast(c['onPrimary'], c['primary']), 4.5, entry.parent.name)
            self.assertEqual(c['primary'], palette['accent'])
            found += 1
        self.assertGreaterEqual(found, 20)


class FakeCaelestia:
    """Stands in for the Caelestia CLI modules, recording what would be applied."""

    def __init__(self, fail_for=None):
        self.events = []
        self.fail_for = fail_for
        events = self.events
        fail = lambda: self.fail_for

        class Scheme:
            def __init__(self, data):
                self.data = data

            @property
            def colours(self):
                return self.data['colours']

            @property
            def mode(self):
                return self.data['mode']

            def update_colours(self):
                self._update_colours()
                self.save()

            def _update_colours(self):
                raise FileNotFoundError('built-in scheme file')  # What Caelestia does for an unknown name.

            def save(self):
                events.append(('save', self.data['name'], self.data['colours'].get('primary')))

        schemes = types.ModuleType('caelestia.utils.scheme')
        schemes.Scheme = Scheme
        schemes.scheme = None
        schemes.scheme_data_dir = Path('/nonexistent')
        schemes.read_colours_from_file = lambda path: (_ for _ in ()).throw(OSError('no file'))
        wallpapers = types.ModuleType('caelestia.utils.wallpaper')
        wallpapers.apply_colours = lambda colours, mode: events.append(('colours', colours.get('primary'), mode))

        def set_wallpaper(path, no_smart):
            if fail() and Path(path).name == fail():
                raise OSError('could not set')
            events.append(('wallpaper', Path(path).name, no_smart))
            schemes.scheme.update_colours()
            wallpapers.apply_colours(schemes.scheme.colours, schemes.scheme.mode)

        wallpapers.set_wallpaper = set_wallpaper
        utils = types.ModuleType('caelestia.utils')
        utils.scheme, utils.wallpaper = schemes, wallpapers
        package = types.ModuleType('caelestia')
        package.utils = utils
        self.modules = {'caelestia': package, 'caelestia.utils': utils,
                        'caelestia.utils.scheme': schemes, 'caelestia.utils.wallpaper': wallpapers}


class ThemeSwitching(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.home = Path(self.directory.name)
        self.catalogue = self.home / 'themes'
        environment = {'HOME': str(self.home), 'XDG_CONFIG_HOME': str(self.home / 'config'),
                       'XDG_DATA_HOME': str(self.home / 'data'), 'XDG_STATE_HOME': str(self.home / 'state'),
                       'JUARCHY_OMARCHY_THEMES': str(self.catalogue)}
        patcher = patch.dict(os.environ, environment)
        patcher.start()
        self.addCleanup(patcher.stop)
        write_theme(self.catalogue, 'tokyo-night')
        write_theme(self.catalogue, 'catppuccin-latte', LATTE, ('1-b.webp', '0-a.jpg'))
        write_theme(self.catalogue, 'plain', MINIMAL, ('only.png',), preview=False)
        self.fake = FakeCaelestia()
        modules = patch.dict(sys.modules, self.fake.modules)
        modules.start()
        self.addCleanup(modules.stop)

    def current(self, theme_id):
        """Pretend Caelestia saved this scheme, as the CLI does."""
        scheme = colors.scheme_for(theme_id, themes.find(theme_id).palette())
        path = themes.scheme_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(scheme))

    def test_titles_and_discovery_are_sorted_and_need_a_palette(self):
        (self.catalogue / 'not-a-theme').mkdir()
        self.assertEqual([theme.id for theme in themes.discover()], ['catppuccin-latte', 'plain', 'tokyo-night'])
        self.assertEqual(themes.find('catppuccin-latte').title, 'Catppuccin Latte')
        with self.assertRaises(ValueError):
            themes.find('nope')

    def test_later_roots_override_earlier_ones(self):
        mine = self.home / 'mine'
        write_theme(mine, 'tokyo-night', MINIMAL, ('mine.png',))
        with patch.dict(os.environ, {'JUARCHY_OMARCHY_THEMES': '%s:%s' % (self.catalogue, mine)}):
            self.assertEqual([image.name for image in themes.find('tokyo-night').backgrounds()], ['mine.png'])

    def test_only_still_images_are_backgrounds_and_videos_are_left_out(self):
        names = [image.name for image in themes.find('tokyo-night').backgrounds()]
        self.assertEqual(names, ['0-first.webp', '1-second.png'])

    def test_your_own_backgrounds_join_the_theme_and_come_first(self):
        overlay = themes.overlay_directory('tokyo-night')
        overlay.mkdir(parents=True)
        (overlay / 'mine.jpg').write_bytes(b'x')
        names = [image.name for image in themes.find('tokyo-night').backgrounds()]
        self.assertEqual(names, ['mine.jpg', '0-first.webp', '1-second.png'])
        self.assertTrue(themes.describe()['themes'][2]['backgrounds'][0]['user'])

    def test_applying_a_theme_keeps_its_own_colours_through_caelestia(self):
        theme, image = themes.apply_theme('tokyo-night')
        self.assertEqual((theme.id, image.name), ('tokyo-night', '0-first.webp'))
        self.assertEqual(self.fake.events, [('wallpaper', '0-first.webp', True), ('save', 'tokyo-night', '7aa2f7'),
                                            ('colours', '7aa2f7', 'dark')])
        self.assertEqual(themes.read_state()['theme'], 'tokyo-night')

    def test_light_themes_apply_as_light(self):
        themes.apply_theme('catppuccin-latte', '1-b')
        self.assertEqual(self.fake.events[-1][2], 'light')
        self.assertEqual(self.fake.events[0][1], '1-b.webp')

    def test_backgrounds_can_be_picked_by_name_stem_number_or_path(self):
        theme = themes.find('tokyo-night')
        for wanted in ('1-second.png', '1-second', '1', str(theme.directory / 'backgrounds/1-second.png')):
            self.assertEqual(themes.choose_background(theme, wanted).name, '1-second.png')
        picture = self.home / 'mine.png'
        picture.write_bytes(b'x')
        self.assertEqual(themes.choose_background(theme, str(picture)), picture.resolve())
        for bad in ('missing', '9', str(self.home / 'nope.png'), str(self.home / 'notes.txt')):
            with self.assertRaises(ValueError):
                themes.choose_background(theme, bad)

    def test_an_unknown_theme_or_background_changes_nothing(self):
        for arguments in (('nope',), ('tokyo-night', 'missing')):
            with self.assertRaises(ValueError):
                themes.apply_theme(*arguments)
        self.assertEqual(self.fake.events, [])
        self.assertEqual(themes.read_state(), {})

    def test_changing_the_background_keeps_the_palette_and_skips_recolouring(self):
        themes.apply_theme('tokyo-night')
        self.current('tokyo-night')
        self.fake.events.clear()
        themes.set_background('1-second')
        self.assertEqual(self.fake.events, [('wallpaper', '1-second.png', True), ('save', 'tokyo-night', '7aa2f7')])
        self.assertTrue(themes.read_state()['background'].endswith('1-second.png'))

    def test_cycling_backgrounds_wraps_in_both_directions(self):
        themes.apply_theme('tokyo-night')
        self.current('tokyo-night')
        seen = [themes.cycle_background(1)[1].name for _ in range(3)]
        self.assertEqual(seen, ['1-second.png', '0-first.webp', '1-second.png'])
        self.assertEqual(themes.cycle_background(-1)[1].name, '0-first.webp')
        self.assertEqual(themes.cycle_background(-1)[1].name, '1-second.png')

    def test_cycling_themes_wraps_and_starts_from_the_first_when_none_is_active(self):
        self.assertEqual(themes.cycle_theme(1)[0].id, 'catppuccin-latte')
        self.current('catppuccin-latte')
        self.assertEqual(themes.cycle_theme(1)[0].id, 'plain')
        self.current('tokyo-night')
        self.assertEqual(themes.cycle_theme(1)[0].id, 'catppuccin-latte')
        self.assertEqual(themes.cycle_theme(-1)[0].id, 'tokyo-night')

    def test_background_commands_need_an_active_omarchy_theme(self):
        with self.assertRaisesRegex(ValueError, 'No Omarchy theme is active'):
            themes.cycle_background()
        themes.apply_theme('tokyo-night')
        scheme = colors.scheme_for('gruvbox', themes.find('tokyo-night').palette())
        scheme['flavour'] = 'soft'  # Another scheme took over after the theme was applied.
        themes.scheme_path().parent.mkdir(parents=True, exist_ok=True)
        themes.scheme_path().write_text(json.dumps(scheme))
        self.assertEqual(themes.active_theme_id(), '')
        with self.assertRaises(ValueError):
            themes.set_background('1')

    def test_a_failed_switch_puts_the_previous_look_back(self):
        picture = self.home / 'old.png'
        picture.write_bytes(b'x')
        self.current('tokyo-night')
        path = themes.state_home() / 'caelestia/wallpaper/path.txt'
        path.parent.mkdir(parents=True)
        path.write_text(str(picture))
        self.fake.fail_for = '0-a.jpg'
        with self.assertRaises(OSError):
            themes.apply_theme('catppuccin-latte')
        self.assertEqual(self.fake.events[-3:], [('wallpaper', 'old.png', True), ('save', 'tokyo-night', '7aa2f7'),
                                                 ('colours', '7aa2f7', 'dark')])
        self.assertEqual(themes.read_state(), {})

    def test_the_scheme_saved_for_caelestia_never_reads_a_built_in_file(self):
        # FakeCaelestia raises FileNotFoundError from _update_colours, as Caelestia does for unknown names.
        themes.apply_theme('plain')

    def test_describe_lists_everything_the_settings_page_needs(self):
        themes.apply_theme('tokyo-night')
        self.current('tokyo-night')
        data = themes.describe()
        self.assertEqual((data['active'], data['theme']), (True, 'tokyo-night'))
        card = next(theme for theme in data['themes'] if theme['id'] == 'tokyo-night')
        self.assertEqual((card['title'], card['mode'], card['accent'], card['active']), ('Tokyo Night', 'dark', '#7aa2f7', True))
        self.assertEqual(len(card['swatches']), 7)
        self.assertTrue(card['preview'].endswith('preview.png'))
        self.assertEqual([image['current'] for image in card['backgrounds']], [True, False])
        self.assertEqual(next(t for t in data['themes'] if t['id'] == 'plain')['preview'], '')

    def test_a_theme_with_a_broken_palette_is_left_out_of_the_list(self):
        write_theme(self.catalogue, 'broken', 'accent = "nonsense"\n')
        self.assertNotIn('broken', [theme['id'] for theme in themes.describe()['themes']])

    def test_command_line(self):
        with patch('builtins.print') as printed:
            self.assertEqual(cli.main(['set', 'tokyo-night']), 0)
            printed.assert_called_with('Tokyo Night · 0-first.webp')
        self.assertEqual(cli.main(['set', 'nope']), 1)
        self.assertEqual(cli.main(['background', 'next']), 1)  # The fake never wrote the scheme file.

    def test_saved_presets_of_omarchy_themes_apply_through_the_theme_library(self):
        loader = importlib.machinery.SourceFileLoader('juarchy_theme_helper', str(ROOT / 'home/.local/bin/juarchy-theme'))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        helper = importlib.util.module_from_spec(spec)
        loader.exec_module(helper)
        picture = self.home / 'saved.png'
        picture.write_bytes(b'x')
        preset = {'wallpaper': str(picture), 'smart': False, 'scheme': {'name': 'tokyo-night', 'flavour': 'omarchy',
                                                                      'mode': 'dark', 'variant': 'tonalspot'}}
        before = {'wallpaper': str(picture), 'scheme': {}}
        with patch.object(helper, 'current_preset', return_value=before), \
                patch.object(helper, 'validate_wallpaper', side_effect=lambda x: Path(x)):
            helper.apply_preset(preset)
        self.assertEqual(self.fake.events[0], ('wallpaper', 'saved.png', True))
        self.assertEqual(self.fake.events[-1], ('colours', '7aa2f7', 'dark'))


class InstallerPlan(unittest.TestCase):
    def test_only_valid_palettes_and_still_images_are_installed(self):
        loader = importlib.machinery.SourceFileLoader('install_omarchy_themes', str(ROOT / 'scripts/install-omarchy-themes.py'))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        installer = importlib.util.module_from_spec(spec)
        loader.exec_module(installer)
        with tempfile.TemporaryDirectory() as directory:
            source, destination = Path(directory) / 'themes', Path(directory) / 'out'
            write_theme(source, 'good', TOKYO, ('a.webp', 'b.JPG', 'c.mp4', 'd.txt'))
            write_theme(source, 'bad', 'accent = "x"\n')
            (source / 'readme').mkdir()
            chosen, skipped = installer.plan(source)
            self.assertEqual((list(chosen), list(skipped)), (['good'], ['bad']))
            installer.install(chosen, None, destination, 'abc')
            installed = sorted(path.name for path in (destination / 'good/backgrounds').iterdir())
            self.assertEqual(installed, ['a.webp', 'b.JPG'])
            self.assertEqual(json.loads((destination / 'SOURCE.json').read_text())['themes'], ['good'])
            # Reinstalling replaces a theme and drops one Omarchy has removed.
            installer.install({}, None, destination, 'def')
            self.assertFalse((destination / 'good').exists())


if __name__ == '__main__':
    unittest.main()
