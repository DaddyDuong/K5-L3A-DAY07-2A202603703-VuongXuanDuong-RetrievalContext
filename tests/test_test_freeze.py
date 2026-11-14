"""Freeze guards tested on temporary data, not on held-out questions."""
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'starter'))
from benchmark_agent_test import verify_freeze


class FreezeGuardTests(unittest.TestCase):
    def test_changed_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            path=root/'config.json'
            path.write_text('frozen config')
            manifest={'files_sha256':{'config.json':hashlib.sha256(path.read_bytes()).hexdigest()}}
            verify_freeze(root,manifest)
            path.write_text('tuned after test')
            with self.assertRaisesRegex(ValueError,'Frozen file changed'):
                verify_freeze(root,manifest)


if __name__=='__main__':unittest.main()
