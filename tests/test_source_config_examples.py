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
SAFE_SEGMENT_PATTERN = "^[A-Za-z0-9][A-Za-z0-9._-]*$"


class SourceConfigExampleTests(unittest.TestCase):
    def test_tracked_source_config_examples_load(self):
        example_paths = sorted((ROOT / "sources" / "examples").glob("*.json"))

        self.assertEqual(
            [path.name for path in example_paths],
            [
                "arxiv-query-code-agents.json",
                "github-releases-shared-intake.json",
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
                "arxiv_query",
                "github_releases",
                "github_search",
                "github_repo",
                "news",
                "rss",
            ],
        )
        self.assertEqual(
            [config["source_id"] for config in configs],
            [
                "arxiv-query-code-agents",
                "github-releases-shared-intake",
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

    def test_github_releases_source_config_requires_owner_repo_and_max_results(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "source-config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "schema_version": "source-config.v1",
                        "source_type": "github_releases",
                        "source_id": "github-releases-shared-intake",
                        "owner": "heurema",
                        "repo": "shared-intake-governance",
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "missing required fields"):
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

        bad_source_id = dict(valid)
        bad_source_id["source_id"] = "../github-search-code-agents"
        with self.assertRaisesRegex(ValueError, "source_id must be a safe path segment"):
            validate_source_config(bad_source_id)

        bad_max_results = dict(valid)
        bad_max_results["max_results"] = 0
        with self.assertRaisesRegex(ValueError, "between 1 and 100"):
            validate_source_config(bad_max_results)

    def test_github_source_configs_reject_unsafe_owner_or_repo_segments(self):
        valid_configs = [
            {
                "schema_version": "source-config.v1",
                "source_type": "github_repo",
                "source_id": "github-signum",
                "owner": "heurema",
                "repo": "signum",
            },
            {
                "schema_version": "source-config.v1",
                "source_type": "github_releases",
                "source_id": "github-releases-shared-intake",
                "owner": "heurema",
                "repo": "shared-intake-governance",
                "max_results": 5,
            },
        ]
        invalid_values = ["../heurema", "heurema/project", "bad space", ""]

        for valid in valid_configs:
            for field in ("owner", "repo"):
                for invalid_value in invalid_values:
                    config = dict(valid)
                    config[field] = invalid_value
                    with self.subTest(
                        source_type=valid["source_type"],
                        field=field,
                        invalid_value=invalid_value,
                    ):
                        with self.assertRaisesRegex(
                            ValueError,
                            f"{field} must be a safe GitHub path segment",
                        ):
                            validate_source_config(config)

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
                ("github_releases", "api_base_url"),
                ("github_search", "api_base_url"),
                ("arxiv_query", "api_base_url"),
                ("rss", "feed_url"),
                ("news", "feed_url"),
            ],
        )
        for _source_type, _field, definition in url_fields:
            self.assertEqual(definition["format"], "uri")
            self.assertEqual(definition.get("pattern"), "^https://")

    def test_source_config_schema_tracks_runtime_source_id_constraint(self):
        schema = json.loads(
            (ROOT / "schemas" / "source-config.schema.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(
            [
                (
                    variant["properties"]["source_type"]["const"],
                    variant["properties"]["source_id"].get("pattern"),
                )
                for variant in schema["oneOf"]
            ],
            [
                ("github_repo", SAFE_SEGMENT_PATTERN),
                ("github_releases", SAFE_SEGMENT_PATTERN),
                ("github_search", SAFE_SEGMENT_PATTERN),
                ("arxiv_query", SAFE_SEGMENT_PATTERN),
                ("rss", SAFE_SEGMENT_PATTERN),
                ("news", SAFE_SEGMENT_PATTERN),
            ],
        )

    def test_source_config_schema_tracks_github_owner_repo_constraints(self):
        schema = json.loads(
            (ROOT / "schemas" / "source-config.schema.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(
            [
                (
                    variant["properties"]["source_type"]["const"],
                    variant["properties"].get("owner", {}).get("pattern"),
                    variant["properties"].get("repo", {}).get("pattern"),
                )
                for variant in schema["oneOf"]
                if variant["properties"]["source_type"]["const"]
                in {"github_repo", "github_releases"}
            ],
            [
                ("github_repo", SAFE_SEGMENT_PATTERN, SAFE_SEGMENT_PATTERN),
                ("github_releases", SAFE_SEGMENT_PATTERN, SAFE_SEGMENT_PATTERN),
            ],
        )


if __name__ == "__main__":
    unittest.main()
