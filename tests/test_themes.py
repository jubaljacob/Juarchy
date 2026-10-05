import importlib.machinery
import importlib.util
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

HELPER = Path(__file__).resolve().parents[1] / 'home/.local/bin/juarchy-theme'
loader = importlib.machinery.SourceFileLoader('juarchy_theme', str(HELPER))
spec = importlib.util.spec_from_loader(loader.name, loader)
theme = importlib.util.module_from_spec(spec)
loader.exec_module(theme)


class ThemeTests(unittest.TestCase):
    def test_store_roundtrip_with_unicode_and_spaces(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'themes.json'
            data = {'Forest 🌲': {'wallpaper': '/pictures/my forest.png', 'smart': False}}
            theme.write_store(path, data)
            self.assertEqual(theme.read_store(path), data)
            self.assertEqual(list(Path(directory).iterdir()), [path])

    def test_corrupt_store_is_not_silently_replaced(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'themes.json'
            path.write_text('broken')
            with self.assertRaises(ValueError):
                theme.read_store(path)
            self.assertEqual(path.read_text(), 'broken')

    def apply(self, name='dynamic', fail=False, missing=False, smart=False):
        events = []
        class Scheme:
            def __init__(self, data):
                self.data = data
            def save(self):
                events.append(('scheme', self.data['name']))
        schemes = types.ModuleType('caelestia.utils.scheme')
        schemes.Scheme = Scheme
        schemes.get_scheme_names = lambda: ['dynamic', 'gruvbox']
        schemes.get_scheme_flavours = lambda name: ['default']
        schemes.get_scheme_modes = lambda name, flavour: ['dark', 'light']
        schemes.scheme_variants = ['tonalspot']
        wallpapers = types.ModuleType('caelestia.utils.wallpaper')
        def set_wallpaper(path, no_smart):
            events.append(('wallpaper', str(path), no_smart))
            if fail and str(path) == '/new.png':
                raise OSError('generation failed')
        wallpapers.set_wallpaper = set_wallpaper
        utils = types.ModuleType('caelestia.utils')
        utils.scheme = schemes
        package = types.ModuleType('caelestia')
        package.utils = utils
        modules = {'caelestia': package, 'caelestia.utils': utils,
                   'caelestia.utils.scheme': schemes, 'caelestia.utils.wallpaper': wallpapers}
        preset = {'wallpaper': '/new.png', 'smart': smart,
                  'scheme': {'name': name, 'flavour': 'default', 'mode': 'dark', 'variant': 'tonalspot'}}
        before = {'wallpaper': '/old.png', 'scheme': {'name': 'gruvbox'}}
        with patch.dict(sys.modules, modules), patch.object(theme, 'current_preset', return_value=before), \
                patch.object(theme, 'validate_wallpaper', side_effect=ValueError('missing') if missing else lambda x: Path(x)):
            if fail or missing or name == 'removed':
                with self.assertRaises((ValueError, OSError)):
                    theme.apply_preset(preset)
            else:
                theme.apply_preset(preset)
        return events

    def test_missing_wallpaper_and_removed_scheme_make_no_changes(self):
        self.assertEqual(self.apply(missing=True), [])
        self.assertEqual(self.apply(name='removed'), [])

    def test_restore_dynamic_keeps_manual_mode(self):
        self.assertEqual(self.apply(), [('scheme', 'dynamic'), ('wallpaper', '/new.png', True)])
        self.assertEqual(self.apply(smart=True), [('scheme', 'dynamic'), ('wallpaper', '/new.png', True)])

    def test_failure_restores_palette_and_wallpaper(self):
        self.assertEqual(self.apply(fail=True), [('scheme', 'dynamic'), ('wallpaper', '/new.png', True),
                                               ('scheme', 'gruvbox'), ('wallpaper', '/old.png', True)])
