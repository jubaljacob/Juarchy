from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class LockTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node is required for lock handler checks')
    def test_retry_recovery_keeps_authentication_required(self):
        result = subprocess.run(['node', 'tests/lock_runtime.cjs'], cwd=ROOT,
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
