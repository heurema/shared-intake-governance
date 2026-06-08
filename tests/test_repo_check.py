import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class RepoCheckTests(unittest.TestCase):
    def test_check_repo_lists_canonical_verification_steps(self):
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "check_repo.py"),
                "--list",
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
        self.assertEqual(
            result.stdout.splitlines(),
            [
                "PYTHONPATH=src python3 -m unittest discover -s tests",
                "python3 scripts/check_surface_consistency.py",
                "python3 scripts/check_source_type_consistency.py",
                "python3 scripts/check_provider_surface_consistency.py",
                "python3 scripts/check_contract_anchor_consistency.py",
                (
                    "jq empty schemas/*.json profiles/examples/*.json "
                    "sources/examples/*.json sources/sets/*.json"
                ),
                "git diff --check",
                "PYTHONPATH=src python3 -m compileall -q src tests scripts",
                "PYTHONPATH=src python3 -m shared_intake_governance.cli --help",
                "remove generated __pycache__ directories",
            ],
        )


if __name__ == "__main__":
    unittest.main()
