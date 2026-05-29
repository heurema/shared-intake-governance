import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


ROOT = Path(__file__).resolve().parents[1]


class DocsIndexTests(unittest.TestCase):
    def test_docs_index_lists_runtime_source_and_focused_tests(self):
        index_text = (ROOT / "docs" / "INDEX.md").read_text(encoding="utf-8")

        expected_paths = _runtime_source_paths() + _focused_test_paths()
        missing = [
            path
            for path in expected_paths
            if f"../{path}" not in index_text
        ]

        self.assertEqual(missing, [])


def _runtime_source_paths():
    source_root = ROOT / "src" / "shared_intake_governance"
    return sorted(
        str(path.relative_to(ROOT))
        for path in source_root.rglob("*.py")
        if path.name not in {"__init__.py", "__main__.py"}
    )


def _focused_test_paths():
    return sorted(
        str(path.relative_to(ROOT))
        for path in (ROOT / "tests").glob("test_*.py")
    )
