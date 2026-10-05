import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('notification_history', ROOT / 'home/.local/bin/juarchy-notification-history')
from importlib.machinery import SourceFileLoader
helper = SourceFileLoader('notification_history', str(ROOT / 'home/.local/bin/juarchy-notification-history')).load_module()


class PrivacyHistoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='juarchy-privacy-test-')
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.state = self.home / '.local/state/caelestia'
        self.cache = self.home / '.cache/caelestia/imagecache/notifs'
        self.state.mkdir(parents=True)
        self.cache.mkdir(parents=True)

    def test_erasure_removes_private_content_and_preserves_other_data(self):
        (self.state / 'notifs.json').write_text('[{"body":"private message"}]')
        (self.cache / 'private.png').write_text('private image')
        (self.state / 'scheme.json').write_text('theme')
        (self.cache.parent / 'album.png').write_text('music')
        helper.clear_history(self.home, {})
        self.assertFalse((self.state / 'notifs.json').exists())
        self.assertFalse(self.cache.exists())
        self.assertEqual((self.state / 'scheme.json').read_text(), 'theme')
        self.assertEqual((self.cache.parent / 'album.png').read_text(), 'music')
        helper.clear_history(self.home, {})

    def test_expired_notification_images_are_removed(self):
        keep = self.cache / 'keep.png'
        keep.write_text('retained')
        old = self.cache / 'expired.png'
        old.write_text('expired')
        (self.state / 'notifs.json').write_text(json.dumps([{'image': str(keep)}]))
        helper.prune_images(self.home, {})
        self.assertTrue(keep.exists())
        self.assertFalse(old.exists())

    def test_defaults_and_runtime_privacy_logic(self):
        defaults = json.loads((ROOT / 'examples/privacy.json').read_text())
        self.assertEqual(defaults, {'remoteMediaArtwork': False, 'musicVisualisers': False,
                                    'notificationRetentionDays': 0})
        if not shutil.which('node'):
            self.skipTest('Node is required to exercise QML JavaScript functions')
        result = subprocess.run(['node', str(ROOT / 'tests/privacy_runtime.cjs')],
                                cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
