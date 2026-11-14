"""Submitted labels and frozen files must match the hashes recorded for them."""
import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def sha256(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


class SubmissionIntegrityTests(unittest.TestCase):
    def test_frozen_files_unchanged(self):
        manifest = json.loads((ROOT / 'artifacts/test-freeze.json').read_text())
        for path, digest in manifest['files_sha256'].items():
            with self.subTest(path=path):
                self.assertEqual(sha256(path), digest)

    def test_confirmed_labels_unchanged(self):
        record = json.loads((ROOT / 'artifacts/student_confirmation.json').read_text())
        self.assertFalse(record['labels_changed'])
        for path, digest in record['files_sha256'].items():
            with self.subTest(path=path):
                self.assertEqual(sha256(path), digest)


if __name__ == '__main__':
    unittest.main()
