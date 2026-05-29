import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from shared_intake_governance.cli.pipeline import _load_source_config  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]


class SourceConfigExampleTests(unittest.TestCase):
    def test_tracked_source_config_examples_load(self):
        example_paths = sorted((ROOT / "sources" / "examples").glob("*.json"))

        self.assertEqual(
            [path.name for path in example_paths],
            [
                "arxiv-code-agents.json",
                "github-signum.json",
            ],
        )

        configs = [_load_source_config(path) for path in example_paths]

        self.assertEqual(
            [config["schema_version"] for config in configs],
            ["source-config.v1", "source-config.v1"],
        )
        self.assertEqual(
            [config["source_type"] for config in configs],
            ["arxiv_rss_keywords", "github_repo"],
        )
        self.assertEqual(
            [config["source_id"] for config in configs],
            ["arxiv-code-agents", "github-signum"],
        )


if __name__ == "__main__":
    unittest.main()
