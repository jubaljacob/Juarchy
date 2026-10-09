import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('juarchy_activation', ROOT / 'scripts/activate.py')
activation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(activation)


class ActivationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='juarchy-switch-test-')
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.originals = {}
        for name in activation.FILES:
            # Reverse the new routing to construct an original desktop fixture.
            text = (ROOT / 'home' / name).read_text()
            if name.endswith('hyprland.lua'):
                text = text.replace('~/.local/bin/juarchy-shell lock lock', 'caelestia shell lock lock')
                text = text.replace('~/.local/bin/juarchy-shell nexus open', 'caelestia shell nexus open')
                text = text.replace('~/.local/bin/juarchy-shell start', 'caelestia shell -d')
            elif name.endswith('monitor-brightness'):
                text = text.replace('"-c", "juarchy"', '"-c", "caelestia"')
                text = text.replace('    response = run(*command).strip()\n',
                                    '    try:\n        response = run(*command).strip()\n'
                                    '    except subprocess.CalledProcessError:\n'
                                    '        response = run(command[0], "-p", "/etc/xdg/quickshell/caelestia", *command[3:]).strip()\n')
            else:
                text = text.replace('"qs", "-c", "juarchy"', '"qs", "-c", "caelestia"')
            target = self.home / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text)
            self.originals[name] = text

    def test_socket_rejection_changes_no_files(self):
        error = subprocess.CalledProcessError(1, ['qs'], stderr='SocketAccessError')
        with patch.object(activation, 'instances', side_effect=[[{'pid': 123}], []]), \
             patch.object(activation, 'run', side_effect=error), \
             patch.object(activation.install, 'apply') as apply:
            with self.assertRaises(subprocess.CalledProcessError):
                activation.activate(self.home)
        apply.assert_not_called()
        for name, text in self.originals.items():
            self.assertEqual((self.home / name).read_text(), text)

    def test_locked_session_changes_no_files(self):
        with patch.object(activation, 'instances', side_effect=[[{'pid': 123}], []]), \
             patch.object(activation, 'run', side_effect=['Hyprland', 'true']), \
             patch.object(activation.install, 'apply') as apply:
            with self.assertRaisesRegex(RuntimeError, 'Unlock'):
                activation.activate(self.home)
        apply.assert_not_called()

    def test_failed_start_restores_original_controls(self):
        with patch.object(activation, 'instances', side_effect=[[{'pid': 123}], []]), \
             patch.object(activation, 'run', side_effect=['Hyprland', 'false', 'ok']), \
             patch.object(activation, 'stop') as stop, \
             patch.object(activation, 'start', side_effect=[RuntimeError('load failed'), None]) as start:
            with self.assertRaisesRegex(RuntimeError, 'load failed'):
                activation.activate(self.home)
        self.assertEqual([c.args for c in stop.call_args_list], [('caelestia',), ('juarchy',)])
        self.assertEqual([c.args for c in start.call_args_list], [('juarchy',), ('caelestia',)])
        for name, text in self.originals.items():
            self.assertEqual((self.home / name).read_text(), text)
        self.assertFalse((self.home / '.config/quickshell/juarchy').exists())
        self.assertFalse((self.home / '.local/state/juarchy/activation.json').exists())

    def test_success_preserves_machine_settings_and_legacy_paths(self):
        machine = self.home / '.config/hypr/machine.lua'
        machine.write_text('-- personal monitors\n')
        self.originals['.config/hypr/hyprland.lua'] += '\n-- untouched personal additions\n'
        (self.home / '.config/hypr/hyprland.lua').write_text(self.originals['.config/hypr/hyprland.lua'])
        with patch.object(activation, 'instances', side_effect=[[{'pid': 123}], []]), \
             patch.object(activation, 'run', side_effect=['Hyprland', 'false', 'ok', '']), \
             patch.object(activation, 'stop'), patch.object(activation, 'start'):
            activation.activate(self.home)
        self.assertEqual(machine.read_text(), '-- personal monitors\n')
        self.assertIn('-- untouched personal additions', (self.home / '.config/hypr/hyprland.lua').read_text())
        self.assertIn('juarchy-shell start', (self.home / '.config/hypr/hyprland.lua').read_text())
        self.assertIn('}/caelestia', (self.home / '.config/quickshell/juarchy/utils/Paths.qml').read_text())
        self.assertTrue((self.home / '.local/state/juarchy/activation.json').exists())

    def test_menu_routes_only_shell_commands_and_region_picker(self):
        commands = [['caelestia', 'shell', 'lock', 'lock'],
                    ['caelestia', 'shell', 'nexus', 'open'],
                    ['caelestia', 'screenshot', '-r'],
                    ['caelestia', 'screenshot'], ['caelestia', 'record']]
        menu = {'title': 'Test', 'items': [{'label': str(i), 'command': command}
                                          for i, command in enumerate(commands)]}
        migrated = json.loads(activation.transform('menu.json', json.dumps(menu)))
        actions = [item['command'] for item in migrated['items']]
        self.assertEqual(actions[:3], [['~/.local/bin/juarchy-shell', 'lock', 'lock'],
                                      ['~/.local/bin/juarchy-shell', 'nexus', 'open'],
                                      ['~/.local/bin/juarchy-screenshot']])
        self.assertEqual(actions[3:], [['~/.local/bin/juarchy-screenshot', '--full'], commands[4]])


if __name__ == '__main__':
    unittest.main()
