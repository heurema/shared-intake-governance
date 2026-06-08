import json
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from shared_intake_governance.projector import load_profile  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
SAFE_SEGMENT_PATTERN = "^[A-Za-z0-9][A-Za-z0-9._-]*$"


class ProfileConfigSchemaTests(unittest.TestCase):
    def test_schema_tracks_runtime_profile_id_constraint(self):
        schema = _read_schema("profile.schema.json")

        self.assertEqual(
            schema["properties"]["profile_id"].get("pattern"),
            SAFE_SEGMENT_PATTERN,
        )

    def test_schema_tracks_supported_profile_source_types(self):
        profile_schema = _read_schema("profile.schema.json")
        clean_record_schema = _read_schema("clean-record.schema.json")

        self.assertEqual(
            profile_schema["properties"]["accepted_sources"]["items"].get("enum"),
            clean_record_schema["properties"]["source_type"]["enum"],
        )

    def test_schema_requires_at_least_one_accepted_source(self):
        schema = _read_schema("profile.schema.json")

        self.assertEqual(
            schema["properties"]["accepted_sources"].get("minItems"),
            1,
        )

    def test_schema_tracks_supported_provider_preferences(self):
        schema = _read_schema("profile.schema.json")

        self.assertEqual(
            schema["properties"]["provider_preferences"]["items"].get("enum"),
            [
                "claude",
                "gemini",
                "agy",
                "vibe",
            ],
        )

    def test_example_profile_sources_are_schema_supported(self):
        schema = _read_schema("profile.schema.json")
        supported_sources = set(
            schema["properties"]["accepted_sources"]["items"]["enum"]
        )

        for profile_path in sorted((ROOT / "profiles" / "examples").glob("*.json")):
            profile = json.loads(profile_path.read_text(encoding="utf-8"))
            self.assertLessEqual(set(profile["accepted_sources"]), supported_sources)

    def test_runtime_rejects_unsupported_profile_source_types(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            profile_path = Path(tmp_dir) / "profile.json"
            profile_path.write_text(
                json.dumps(
                    {
                        "profile_id": "code-intel-kernel",
                        "description": "Code intelligence research intake.",
                        "accepted_sources": ["github_reop"],
                        "keywords": ["coding agent"],
                        "output_mode": "research_digest",
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                ValueError,
                "profile has unsupported accepted source",
            ):
                load_profile(profile_path)

    def test_runtime_rejects_empty_accepted_sources(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            profile_path = Path(tmp_dir) / "profile.json"
            profile_path.write_text(
                json.dumps(
                    {
                        "profile_id": "code-intel-kernel",
                        "description": "Code intelligence research intake.",
                        "accepted_sources": [],
                        "keywords": ["coding agent"],
                        "output_mode": "research_digest",
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                ValueError,
                "accepted_sources must be a non-empty list",
            ):
                load_profile(profile_path)


def _read_schema(filename):
    path = ROOT / "schemas" / filename
    return json.loads(path.read_text(encoding="utf-8"))
