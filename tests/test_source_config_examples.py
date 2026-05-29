import sys
import json
import tempfile
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
                "arxiv-query-code-agents.json",
                "github-search-code-agents.json",
                "github-signum.json",
                "rss-github-blog.json",
            ],
        )

        configs = [_load_source_config(path) for path in example_paths]

        self.assertEqual(
            [config["schema_version"] for config in configs],
            [
                "source-config.v1",
                "source-config.v1",
                "source-config.v1",
                "source-config.v1",
                "source-config.v1",
            ],
        )
        self.assertEqual(
            [config["source_type"] for config in configs],
            [
                "arxiv_rss_keywords",
                "arxiv_query",
                "github_search",
                "github_repo",
                "rss",
            ],
        )
        self.assertEqual(
            [config["source_id"] for config in configs],
            [
                "arxiv-code-agents",
                "arxiv-query-code-agents",
                "github-search-code-agents",
                "github-signum",
                "rss-github-blog",
            ],
        )

    def test_github_search_source_config_requires_query(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "source-config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "schema_version": "source-config.v1",
                        "source_type": "github_search",
                        "source_id": "github-search-code-agents",
                        "max_results": 5,
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                _load_source_config(config_path)

    def test_arxiv_query_source_config_requires_query(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "source-config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "schema_version": "source-config.v1",
                        "source_type": "arxiv_query",
                        "source_id": "arxiv-query-code-agents",
                        "max_results": 5,
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                _load_source_config(config_path)

    def test_rss_source_config_requires_feed_url(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "source-config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "schema_version": "source-config.v1",
                        "source_type": "rss",
                        "source_id": "rss-example",
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                _load_source_config(config_path)


if __name__ == "__main__":
    unittest.main()
