import json
import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from shared_intake_governance.source_config import load_source_config  # noqa: E402
from shared_intake_governance.source_set import validate_source_set  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
SAFE_SEGMENT_PATTERN = "^[A-Za-z0-9][A-Za-z0-9._-]*$"
SOURCE_CONFIG_PATH_PATTERN = "^sources/examples/[A-Za-z0-9][A-Za-z0-9._-]*\\.json$"


class SourceSetContractTests(unittest.TestCase):
    def test_tracked_source_set_examples_reference_valid_source_configs(self):
        example_paths = sorted((ROOT / "sources" / "sets").glob("*.json"))

        self.assertEqual(
            [path.name for path in example_paths],
            ["code-intel-source-set.json"],
        )

        source_set = json.loads(example_paths[0].read_text(encoding="utf-8"))
        self.assertEqual(source_set["schema_version"], "source-set.v1")
        self.assertEqual(source_set["source_set_id"], "code-intel-source-set")
        self.assertEqual(
            [source["source_config_path"] for source in source_set["sources"]],
            [
                "sources/examples/github-search-code-agents.json",
                "sources/examples/github-releases-repo-governance.json",
                "sources/examples/arxiv-query-code-agents.json",
                "sources/examples/rss-github-blog.json",
                "sources/examples/news-openai-blog.json",
            ],
        )

        loaded_source_ids = []
        for source_ref in source_set["sources"]:
            config_path = ROOT / source_ref["source_config_path"]
            config = load_source_config(config_path)
            loaded_source_ids.append(config["source_id"])
            self.assertEqual(source_ref["source_id"], config["source_id"])

        self.assertEqual(
            loaded_source_ids,
            [
                "github-search-code-agents",
                "github-releases-repo-governance",
                "arxiv-query-code-agents",
                "rss-github-blog",
                "news-openai-blog",
            ],
        )
        for forbidden_field in (
            "profile",
            "profile_id",
            "runtime_root",
            "schedule",
            "credentials",
            "seen_state",
            "publication",
        ):
            self.assertNotIn(forbidden_field, source_set)

    def test_source_set_schema_keeps_contract_narrow(self):
        schema = json.loads(
            (ROOT / "schemas" / "source-set.schema.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(
            schema["$id"],
            "https://shared-intake-governance.local/schemas/source-set.schema.json",
        )
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(
            schema["required"],
            ["schema_version", "source_set_id", "sources"],
        )
        self.assertEqual(
            schema["properties"]["schema_version"]["const"],
            "source-set.v1",
        )
        self.assertEqual(
            schema["properties"]["source_set_id"]["pattern"],
            SAFE_SEGMENT_PATTERN,
        )

        source_ref_schema = schema["properties"]["sources"]["items"]
        self.assertFalse(source_ref_schema["additionalProperties"])
        self.assertEqual(
            source_ref_schema["required"],
            ["source_id", "source_config_path"],
        )
        self.assertEqual(
            source_ref_schema["properties"]["source_id"]["pattern"],
            SAFE_SEGMENT_PATTERN,
        )
        self.assertEqual(
            source_ref_schema["properties"]["source_config_path"]["pattern"],
            SOURCE_CONFIG_PATH_PATTERN,
        )
        for forbidden_field in (
            "profile",
            "profile_id",
            "runtime_root",
            "schedule",
            "credentials",
            "seen_state",
            "publication",
        ):
            self.assertNotIn(forbidden_field, schema["properties"])
            self.assertNotIn(forbidden_field, source_ref_schema["properties"])

    def test_runtime_rejects_duplicate_source_ids(self):
        source_set = {
            "schema_version": "source-set.v1",
            "source_set_id": "code-intel-source-set",
            "sources": [
                {
                    "source_id": "github-search-code-agents",
                    "source_config_path": (
                        "sources/examples/github-search-code-agents.json"
                    ),
                },
                {
                    "source_id": "github-search-code-agents",
                    "source_config_path": (
                        "sources/examples/github-search-python-agents.json"
                    ),
                },
            ],
        }

        with self.assertRaisesRegex(ValueError, "duplicate source_id"):
            validate_source_set(source_set)

    def test_runtime_rejects_duplicate_source_config_paths(self):
        source_set = {
            "schema_version": "source-set.v1",
            "source_set_id": "code-intel-source-set",
            "sources": [
                {
                    "source_id": "github-search-code-agents",
                    "source_config_path": (
                        "sources/examples/github-search-code-agents.json"
                    ),
                },
                {
                    "source_id": "github-search-code-agents-copy",
                    "source_config_path": (
                        "sources/examples/github-search-code-agents.json"
                    ),
                },
            ],
        }

        with self.assertRaisesRegex(ValueError, "duplicate source_config_path"):
            validate_source_set(source_set)

    def test_docs_index_lists_source_set_contract(self):
        index_text = (ROOT / "docs" / "INDEX.md").read_text(encoding="utf-8")

        self.assertIn("../schemas/source-set.schema.json", index_text)
        self.assertIn("../sources/sets/code-intel-source-set.json", index_text)


if __name__ == "__main__":
    unittest.main()
