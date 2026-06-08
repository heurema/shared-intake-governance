import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SourceTypeConsistencyTests(unittest.TestCase):
    def test_source_type_consistency_guard_passes(self):
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "check_source_type_consistency.py"),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(
            result.returncode,
            0,
            result.stdout + result.stderr,
        )


if __name__ == "__main__":
    unittest.main()
