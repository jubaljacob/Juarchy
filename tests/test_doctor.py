import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('desktop_doctor', ROOT / 'scripts/doctor.py')
doctor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(doctor)


class DoctorTests(unittest.TestCase):
    def setUp(self):
        self.installed = dict.fromkeys(doctor.packages('arch') + doctor.packages('aur'), '1.0.0-1')
        self.installed.update({'hyprland': '0.56.2-4', 'caelestia-shell': '2.5.0-1',
                               'caelestia-cli': '1.1.3-1'})

    def check(self, **kwargs):
        return doctor.assess(self.installed, home=Path('/home/friend'),
                             environ=kwargs.pop('environ', {'HYPRLAND_INSTANCE_SIGNATURE': 'test'}),
                             uid=kwargs.pop('uid', 1000),
                             which=kwargs.pop('which', lambda command: '/usr/bin/' + command), **kwargs)

    def test_baseline_passes_for_another_user(self):
        self.assertEqual(self.check(), ([], []))

    def test_missing_packages_and_commands_fail(self):
        del self.installed['hyprsunset']
        errors, _ = self.check(which=lambda command: None if command == 'qs' else command)
        self.assertTrue(any('hyprsunset' in item for item in errors))
        self.assertIn('Missing executable: qs', errors)

    def test_old_hyprland_fails_and_new_runtime_warns(self):
        self.installed['hyprland'] = '0.54.3-1'
        self.assertTrue(any('Lua configuration' in item for item in self.check()[0]))
        self.installed['hyprland'] = '0.57.0-1'
        errors, warnings = self.check()
        self.assertFalse(errors)
        self.assertTrue(any('differs from the tested baseline' in item for item in warnings))

    def test_custom_layout_and_root_fail(self):
        errors, _ = self.check(uid=0, environ={'XDG_CONFIG_HOME': '/tmp/config'})
        self.assertEqual(len(errors), 2)

    def test_stable_quickshell_with_qs_is_accepted(self):
        del self.installed['quickshell-git']
        self.installed['quickshell'] = '0.3.1-1'
        self.assertEqual(self.check(), ([], []))
