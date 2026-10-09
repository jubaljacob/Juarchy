from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

loader = SourceFileLoader('night_light', str(Path(__file__).resolve().parents[1] / 'home/.local/bin/juarchy-night-light'))
helper = module_from_spec(spec_from_loader(loader.name, loader))
loader.exec_module(helper)


class NightLightTests(unittest.TestCase):
    def test_absent_daemon_status_does_not_start_or_change_display(self):
        socket = Mock()
        socket.exists.return_value = False
        with patch.object(helper, 'socket_path', return_value=socket), patch.object(helper.shutil, 'which', return_value='/bin/tool'), patch.object(helper, 'ipc') as ipc:
            self.assertFalse(helper.control('status')['enabled'])
            ipc.assert_not_called()

    def test_toggle_reads_actual_state_and_restores_identity_without_gamma_change(self):
        socket = Mock()
        socket.exists.return_value = True
        state = {'identity': 'true', 'temperature': 6000}
        commands = []

        def ipc(*args):
            commands.append(args)
            if args == ('identity', 'get'):
                return state['identity']
            if args == ('temperature',):
                return str(state['temperature'])
            if args[0] == 'temperature':
                state.update(identity='false', temperature=int(args[1]))
            elif args == ('identity',):
                state['identity'] = 'true'
            return 'ok'

        with patch.object(helper, 'socket_path', return_value=socket), patch.object(helper, 'ipc', side_effect=ipc), patch.object(helper, 'ensure_daemon') as ensure:
            result = helper.control('toggle')
            self.assertTrue(result['enabled'])
            self.assertEqual(result['temperature'], 4500)
            result = helper.control('toggle')
            self.assertFalse(result['enabled'])
            ensure.assert_called_once()
            self.assertIn(('identity',), commands)
            self.assertFalse(any(command[0] == 'gamma' for command in commands))

    def test_existing_daemon_is_reused(self):
        socket = Mock()
        socket.exists.return_value = True
        with patch.object(helper, 'socket_path', return_value=socket), patch.object(helper, 'ipc', return_value='true'), patch.object(helper.subprocess, 'Popen') as spawn:
            helper.ensure_daemon()
            spawn.assert_not_called()

    def test_daemon_start_waits_until_ipc_ready(self):
        socket = Mock()
        socket.exists.side_effect = [False, True]
        process = Mock()
        process.poll.return_value = None
        with tempfile.TemporaryDirectory() as folder, patch.dict(helper.os.environ, {'WAYLAND_DISPLAY': 'wayland-test', 'HYPRLAND_INSTANCE_SIGNATURE': 'test', 'XDG_STATE_HOME': folder}), patch.object(helper, 'socket_path', return_value=socket), patch.object(helper.shutil, 'which', return_value='/bin/hyprsunset'), patch.object(helper.subprocess, 'Popen', return_value=process) as spawn, patch.object(helper, 'ipc', return_value='true'):
            helper.ensure_daemon()
            self.assertEqual(spawn.call_args.args[0], ['hyprsunset', '--identity'])
            process.terminate.assert_not_called()

    def test_failed_start_does_not_report_enabled(self):
        socket = Mock()
        socket.exists.return_value = False
        process = Mock()
        process.poll.return_value = 1
        with tempfile.TemporaryDirectory() as folder, patch.dict(helper.os.environ, {'WAYLAND_DISPLAY': 'wayland-test', 'HYPRLAND_INSTANCE_SIGNATURE': 'test', 'XDG_STATE_HOME': folder}), patch.object(helper, 'socket_path', return_value=socket), patch.object(helper.shutil, 'which', return_value='/bin/hyprsunset'), patch.object(helper.subprocess, 'Popen', return_value=process):
            with self.assertRaisesRegex(RuntimeError, 'could not start'):
                helper.control('enable')

    def test_ipc_rejection_with_zero_exit_status_is_an_error(self):
        result = subprocess.CompletedProcess([], 0, 'invalid command', '')
        with patch.object(helper.subprocess, 'run', return_value=result):
            with self.assertRaisesRegex(RuntimeError, 'invalid command'):
                helper.ipc('temperature', '4500')

    def test_invalid_temperature_changes_nothing(self):
        with patch.object(helper, 'status') as status:
            with self.assertRaises(ValueError):
                helper.control('enable', 999)
            status.assert_not_called()
