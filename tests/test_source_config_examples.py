import sys
import json
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from shared_intake_governance.source_config import (  # noqa: E402
    load_source_config,
    validate_source_config,
)


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
                "news-openai-blog.json",
                "rss-github-blog.json",
            ],
        )

        configs = [load_source_config(path) for path in example_paths]

        self.assertEqual(
            [config["schema_version"] for config in configs],
            [
                "source-config.v1",
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
                "news",
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
                "news-openai-blog",
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
                load_source_config(config_path)

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
                load_source_config(config_path)

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
                load_source_config(config_path)

    def test_news_source_config_requires_feed_url(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "source-config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "schema_version": "source-config.v1",
                        "source_type": "news",
                        "source_id": "news-example",
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                load_source_config(config_path)

    def test_source_config_validation_rejects_contract_drift(self):
        valid = {
            "schema_version": "source-config.v1",
            "source_type": "github_search",
            "source_id": "github-search-code-agents",
            "query": "topic:coding-agent",
            "max_results": 5,
        }
        validate_source_config(valid)

        missing_required = dict(valid)
        del missing_required["query"]
        with self.assertRaisesRegex(ValueError, "missing required fields"):
            validate_source_config(missing_required)

        unknown_field = dict(valid)
        unknown_field["credentials"] = {"token": "do-not-load"}
        with self.assertRaisesRegex(ValueError, "unknown fields"):
            validate_source_config(unknown_field)

        bad_schema = dict(valid)
        bad_schema["schema_version"] = "source-config.v0"
        with self.assertRaisesRegex(ValueError, "source-config.v1"):
            validate_source_config(bad_schema)

        bad_max_results = dict(valid)
        bad_max_results["max_results"] = 0
        with self.assertRaisesRegex(ValueError, "between 1 and 100"):
            validate_source_config(bad_max_results)

    def test_rss_source_config_rejects_unsupported_source_trust(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "source-config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "schema_version": "source-config.v1",
                        "source_type": "rss",
                        "source_id": "rss-example",
                        "feed_url": "https://example.test/feed.xml",
                        "source_trust": "private",
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "unsupported source_trust"):
                load_source_config(config_path)

    def test_news_source_config_rejects_unsupported_source_trust(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "source-config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "schema_version": "source-config.v1",
                        "source_type": "news",
                        "source_id": "news-example",
                        "feed_url": "https://example.test/news.xml",
                        "source_trust": "private",
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "unsupported source_trust"):
                load_source_config(config_path)

    def test_source_config_schema_keeps_url_fields_https_only(self):
        schema = json.loads(
            (ROOT / "schemas" / "source-config.schema.json").read_text(
                encoding="utf-8"
            )
        )
        url_fields = []

        for variant in schema["oneOf"]:
            source_type = variant["properties"]["source_type"]["const"]
            for field in ("api_base_url", "feed_url"):
                if field in variant["properties"]:
                    url_fields.append((source_type, field, variant["properties"][field]))

        self.assertEqual(
            [(source_type, field) for source_type, field, _ in url_fields],
            [
                ("github_repo", "api_base_url"),
                ("github_search", "api_base_url"),
                ("arxiv_query", "api_base_url"),
                ("arxiv_rss_keywords", "api_base_url"),
                ("rss", "feed_url"),
                ("news", "feed_url"),
            ],
        )
        for _source_type, _field, definition in url_fields:
            self.assertEqual(definition["format"], "uri")
            self.assertEqual(definition.get("pattern"), "^https://")


if __name__ == "__main__":
    unittest.main()
