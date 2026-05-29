import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from shared_intake_governance.projector.profile import ProfileProjector  # noqa: E402
from shared_intake_governance.runtime import RuntimePaths  # noqa: E402


FETCHED_AT = datetime(2026, 5, 29, 12, 30, 45, tzinfo=timezone.utc)
RUN_ID = "20260529T123045Z-deadbeef"


class ProfileProjectionSchemaTests(unittest.TestCase):
    def test_schema_tracks_projector_report_shape(self):
        schema = _read_schema("profile-projection.schema.json")

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            paths = RuntimePaths(root / "runtime")
            _write_clean_record(paths)
            profile_path = _write_profile(root)

            projection = ProfileProjector(paths).project(
                profile_path,
                output_id=RUN_ID,
                generated_at=FETCHED_AT,
            )

        self.assertEqual(schema["$id"], _schema_id("profile-projection.schema.json"))
        self.assertEqual(
            schema["properties"]["schema_version"]["const"],
            "profile-projection.v1",
        )
        _assert_object_matches_schema_shape(self, schema, projection.report)
        _assert_object_matches_schema_shape(
            self,
            schema["properties"]["counts"],
            projection.report["counts"],
        )
        item_schema = schema["properties"]["items"]["items"]
        for item in projection.report["items"]:
            _assert_object_matches_schema_shape(self, item_schema, item)


def _read_schema(filename):
    path = Path(__file__).resolve().parents[1] / "schemas" / filename
    return json.loads(path.read_text(encoding="utf-8"))


def _schema_id(filename):
    return f"https://shared-intake-governance.local/schemas/{filename}"


def _assert_object_matches_schema_shape(testcase, schema, payload):
    testcase.assertEqual(schema["type"], "object")
    testcase.assertFalse(schema.get("additionalProperties", True))
    testcase.assertLessEqual(set(schema["required"]), set(payload))
    testcase.assertLessEqual(set(payload), set(schema["properties"]))


def _write_clean_record(paths):
    record = {
        "record_id": "github_repo-good",
        "source_id": "github-signum",
        "source_type": "github_repo",
        "canonical_url": "https://github.com/heurema/signum",
        "title": "heurema/signum",
        "sanitized_summary": "Coding agent benchmark toolkit.",
        "published_at": "2025-01-02T03:04:05Z",
        "license_or_terms_note": "license: Apache-2.0",
        "source_trust": "platform",
        "risk_flags": [],
        "quarantined": False,
        "raw_hash": "raw-github",
        "sanitizer_version": "clean-record.v1",
    }
    path = paths.clean_record_path(record["record_id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, sort_keys=True) + "\n", encoding="utf-8")


def _write_profile(root):
    profile = {
        "profile_id": "code-intel-kernel",
        "description": "Code intelligence research intake.",
        "accepted_sources": ["github_repo"],
        "keywords": ["coding agent"],
        "required_risk_flags_absent": ["instruction_like_content"],
        "output_mode": "research_digest",
    }
    path = root / "profile.json"
    path.write_text(json.dumps(profile, sort_keys=True) + "\n", encoding="utf-8")
    return path
