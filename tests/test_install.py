import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('desktop_installer', ROOT / 'scripts/install.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='jubal-desktop-test-')
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name) / 'home with spaces'
        self.home.mkdir()

    def command(self, *args):
        return subprocess.run([sys.executable, str(ROOT / 'scripts/install.py'), '--home', str(self.home), *args],
                              capture_output=True, text=True)

    def test_preview_does_not_change_home(self):
        before = list(self.home.iterdir())
        result = self.command()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Preview only', result.stdout)
        self.assertNotIn('__pycache__', result.stdout)
        self.assertEqual(before, list(self.home.iterdir()))

    def test_full_deployment_restores_original_shell_and_files(self):
        shell = self.home / '.config/quickshell/juarchy'
        shell.mkdir(parents=True)
        original = Path(self.temp.name) / 'original-source'
        original.write_text('original shell')
        (shell / 'shell.qml').symlink_to(original)
        config = self.home / '.config/caelestia/shell.json'
        config.parent.mkdir(parents=True)
        config.write_text('original settings')
        machine = self.home / '.config/hypr/machine.lua'
        machine.parent.mkdir(parents=True)
        machine.write_text('-- my monitor settings\n')
        backup = installer.apply(installer.plan(home=self.home), self.home)
        self.assertFalse((shell / 'shell.qml').is_symlink())
        self.assertIn('ShellRoot', (shell / 'shell.qml').read_text())
        self.assertEqual(machine.read_text(), '-- my monitor settings\n')
        self.assertEqual(json.loads(config.read_text())['bar']['statusIcons'][2]['id'], 'audio')
        menu = (self.home / '.config/jubal-launcher/menu.json').read_text()
        self.assertNotIn('/home/jubal', menu)
        desktop = (self.home / '.local/share/applications/jubal-launcher.desktop').read_text()
        self.assertIn('Exec="' + str(self.home) + '/.local/bin/jubal-launcher"', desktop)
        self.assertFalse((self.home / '.config/libcamera').exists())
        preview = self.command('--restore', str(backup))
        self.assertEqual(preview.returncode, 0, preview.stderr)
        self.assertIn('ShellRoot', (shell / 'shell.qml').read_text())
        result = self.command('--restore', str(backup), '--apply')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(config.read_text(), 'original settings')
        self.assertTrue((shell / 'shell.qml').is_symlink())
        self.assertEqual((shell / 'shell.qml').read_text(), 'original shell')
        self.assertFalse((self.home / '.local/bin/jubal-launcher').exists())
        self.assertEqual(machine.read_text(), '-- my monitor settings\n')

    def test_profile_and_reinstall_preserve_machine_settings(self):
        installer.apply(installer.plan('intel-nvidia', self.home), self.home)
        self.assertIn('force_shm = true', (self.home / '.config/hypr/xdph.conf').read_text())
        machine = self.home / '.config/hypr/machine.lua'
        machine.write_text('-- customized here\n')
        installer.apply(installer.plan('intel-nvidia', self.home), self.home)
        self.assertEqual(machine.read_text(), '-- customized here\n')

    def test_asus_profile_seeds_machine_settings_once(self):
        installer.apply(installer.plan('asus-g15', self.home), self.home)
        machine = self.home / '.config/hypr/machine.lua'
        self.assertIn('power-mode watch', machine.read_text())
        self.assertTrue(os.access(self.home / '.local/bin/power-mode', os.X_OK))
        self.assertTrue((self.home / '.config/hypr/hypridle.conf').exists())
        machine.write_text('-- customized here\n')
        installer.apply(installer.plan('asus-g15', self.home), self.home)
        self.assertEqual(machine.read_text(), '-- customized here\n')

    def test_install_preserves_original_caelestia_configuration(self):
        original = self.home / '.config/quickshell/caelestia/shell.qml'
        original.parent.mkdir(parents=True)
        original.write_text('original desktop')
        installer.apply(installer.plan(home=self.home), self.home)
        self.assertEqual(original.read_text(), 'original desktop')
        new = self.home / '.config/quickshell/juarchy'
        self.assertIn('target: "juarchy"', (new / 'shell.qml').read_text())
        self.assertFalse(any(p.is_symlink() for p in new.rglob('*')))

    def test_reinstall_preserves_explicit_privacy_preferences(self):
        installer.apply(installer.plan(home=self.home), self.home)
        prefs = self.home / '.config/juarchy/privacy.json'
        chosen = {'remoteMediaArtwork': True, 'musicVisualisers': True, 'notificationRetentionDays': 7}
        prefs.write_text(json.dumps(chosen))
        installer.apply(installer.plan(home=self.home), self.home)
        self.assertEqual(json.loads(prefs.read_text()), chosen)

    def test_destination_parent_symlinks_fail_before_any_write(self):
        external = Path(self.temp.name) / 'external'
        external.mkdir()
        (self.home / '.config').symlink_to(external, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'symlink'):
            installer.apply(installer.plan(home=self.home), self.home)
        self.assertEqual(list(external.iterdir()), [])
        self.assertFalse((self.home / '.local').exists())

    def test_local_overrides_cannot_replace_existing_machine_or_consent(self):
        fake_root = Path(self.temp.name) / 'repository'
        for name in ('.config/hypr/machine.lua', '.config/juarchy/privacy.json'):
            source = fake_root / 'local/home' / name
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_text('local override')
            target = self.home / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text('friend settings')
        with patch.object(installer, 'ROOT', fake_root):
            entries = installer.plan(home=self.home)
        self.assertNotIn('.config/hypr/machine.lua', entries)
        self.assertNotIn('.config/juarchy/privacy.json', entries)

    def test_shared_only_ignores_personal_overrides_on_first_install(self):
        fake_root = Path(self.temp.name) / 'repository'
        local_machine = fake_root / 'local/home/.config/hypr/machine.lua'
        local_machine.parent.mkdir(parents=True)
        local_machine.write_text('personal monitor')
        with patch.object(installer, 'ROOT', fake_root):
            self.assertEqual(installer.plan(home=self.home)['.config/hypr/machine.lua'], local_machine)
            shared = installer.plan(home=self.home, shared_only=True)
            self.assertEqual(shared['.config/hypr/machine.lua'], fake_root / 'examples/machine.lua')

    def test_failed_deployment_rolls_back_changed_files(self):
        a = self.home / 'a'
        a.write_text('before')
        source = Path(self.temp.name) / 'source'
        source.write_text('after')
        entries = {'a': source, 'b': source}
        original_deploy = installer.deploy

        def fail_second(source, target, home, shell=False):
            if target.name == 'b':
                raise OSError('simulated failure')
            return original_deploy(source, target, home, shell)

        with patch.object(installer, 'deploy', side_effect=fail_second):
            with self.assertRaisesRegex(OSError, 'simulated failure'):
                installer.apply(entries, self.home)
        self.assertEqual(a.read_text(), 'before')
        self.assertFalse((self.home / 'b').exists())

    def test_restore_cannot_escape_home(self):
        backup = Path(self.temp.name) / 'invalid-backup'
        backup.mkdir()
        (backup / 'manifest.json').write_text(json.dumps({'home': str(self.home),
                                                        'entries': [{'path': '../../outside', 'previous': False}]}))
        result = self.command('--restore', str(backup), '--apply')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Invalid destination', result.stderr)
        self.assertEqual(list(self.home.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
