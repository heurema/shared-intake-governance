import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ProviderSurfaceConsistencyTests(unittest.TestCase):
    def test_provider_surface_consistency_guard_passes(self):
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "check_provider_surface_consistency.py"),
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
