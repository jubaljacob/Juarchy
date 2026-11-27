from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

loader = SourceFileLoader('juarchy_screenshot', str(Path(__file__).resolve().parents[1] / 'home/.local/bin/juarchy-screenshot'))
spec = spec_from_loader(loader.name, loader)
helper = module_from_spec(spec)
loader.exec_module(helper)


class ScreenshotTests(unittest.TestCase):
    def test_cancel_creates_no_image_or_clipboard(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(helper.subprocess, 'run') as run, \
                patch.object(helper, 'preview', return_value='false'):
            run.return_value = subprocess.CompletedProcess(['slurp'], 1, '', '')
            self.assertIsNone(helper.screenshot(Path(folder) / 'shots'))
            self.assertEqual(run.call_count, 1)
            self.assertFalse((Path(folder) / 'shots').exists())

    def test_failed_selector_reports_connection_error(self):
        with patch.object(helper.subprocess, 'run') as run, patch.object(helper, 'preview', return_value=None):
            run.return_value = subprocess.CompletedProcess(['slurp'], 1, '', 'failed to connect to display')
            with self.assertRaisesRegex(RuntimeError, 'connect'):
                helper.screenshot(Path('/unused'))

    def capture(self, full=False, failure=False, clipboard_failure=False, shell_running=True,
                preview_visible=False):
        commands = []
        self.notifications = []
        def run(command, **kwargs):
            commands.append(command)
            if command[0] == 'qs':
                if not shell_running:
                    return subprocess.CompletedProcess(command, 1, '', 'No running instances')
                visible = command[-1] == 'dismiss' and preview_visible
                return subprocess.CompletedProcess(command, 0, 'true\n' if visible else 'false\n', '')
            if command[0] == 'slurp':
                return subprocess.CompletedProcess(command, 0, '-1920,20 200x100\n', '')
            if command[0] == 'grim':
                Path(command[-1]).write_bytes(b'PNG')
                return subprocess.CompletedProcess(command, int(failure), '', 'capture failed' if failure else '')
            if command[0] == 'wl-copy':
                self.assertEqual(kwargs['stdin'].read(), b'PNG')
                # The forked wl-copy daemon keeps captured pipes open, which
                # blocks run() until the clipboard changes.
                self.assertNotIn('capture_output', kwargs)
                self.assertEqual(kwargs.get('stdout'), subprocess.DEVNULL)
                self.assertEqual(kwargs.get('stderr'), subprocess.DEVNULL)
                return subprocess.CompletedProcess(command, int(clipboard_failure))
        def notify(title, message):
            self.notifications.append(title)
        with tempfile.TemporaryDirectory() as folder, patch.object(helper.subprocess, 'run', side_effect=run), \
                patch.object(helper, 'notify', side_effect=notify), patch.object(helper.time, 'sleep') as sleep:
            directory = Path(folder) / 'screenshots with spaces'
            if failure:
                with self.assertRaisesRegex(RuntimeError, 'capture failed'):
                    helper.screenshot(directory, full)
                self.assertEqual(list(directory.iterdir()), [])
                self.assertFalse(any(c[0] == 'wl-copy' for c in commands))
            else:
                image = helper.screenshot(directory, full)
                self.assertTrue(image.is_file())
                self.assertEqual(image.stat().st_mode & 0o777, 0o600)
                grim = next(c for c in commands if c[0] == 'grim')
                self.assertEqual('-g' in grim, not full)
                if not full:
                    self.assertIn('-1920,20 200x100', grim)
                preview = [c for c in commands if c[0] == 'qs']
                self.assertEqual(preview[0][-1], 'dismiss')
                self.assertLess(commands.index(preview[0]), commands.index(grim))
                self.assertEqual(preview[-1][-2:], ['open', str(image)])
            self.assertEqual(sleep.called, preview_visible)
        return commands

    def test_region_saved_and_copied_with_negative_monitor_coordinates(self):
        self.capture()

    def test_fullscreen_does_not_open_selector(self):
        self.assertFalse(any(c[0] == 'slurp' for c in self.capture(full=True)))

    def test_failed_capture_removes_partial_image(self):
        self.capture(failure=True)

    def test_clipboard_failure_keeps_saved_image(self):
        self.capture(clipboard_failure=True)
        self.assertEqual(self.notifications, ['Screenshot saved'])

    def test_preview_replaces_notification(self):
        self.capture()
        self.assertEqual(self.notifications, [])

    def test_notification_when_shell_is_down(self):
        self.capture(shell_running=False)
        self.assertEqual(self.notifications, ['Screenshot saved and copied'])

    def test_previous_preview_fades_before_capture(self):
        self.capture(full=True, preview_visible=True)
