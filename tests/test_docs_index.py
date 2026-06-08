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

    def test_source_config_recipes_doc_is_canonical(self):
        index_text = (ROOT / "docs" / "INDEX.md").read_text(encoding="utf-8")
        recipe_path = ROOT / "docs" / "13-source-config-recipes.md"

        self.assertTrue(recipe_path.exists())
        self.assertIn("13-source-config-recipes.md", index_text)

        recipe_text = recipe_path.read_text(encoding="utf-8")
        self.assertIn("--exclude-seen-state", recipe_text)
        self.assertIn("--update-seen-state", recipe_text)

    def test_consumer_onboarding_points_to_source_config_recipe(self):
        onboarding_text = (
            ROOT / "docs" / "08-consumer-onboarding.md"
        ).read_text(encoding="utf-8")

        expected_fragments = [
            "13-source-config-recipes.md",
            "`SIG_PROFILE`",
            "`SIG_SOURCE_CONFIG`",
            "`SIG_RUNTIME_ROOT`",
            "`seen_records`",
            "`smoke-source-config`",
        ]
        missing = [
            fragment
            for fragment in expected_fragments
            if fragment not in onboarding_text
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
