import json
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from shared_intake_governance.projector.profile_state import (  # noqa: E402
    update_seen_records_state,
    validate_profile_state,
)
from shared_intake_governance.runtime import RuntimePaths  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
SAFE_SEGMENT_PATTERN = "^[A-Za-z0-9][A-Za-z0-9._-]*$"


class ProfileStateUpdateTests(unittest.TestCase):
    def test_update_seen_records_state_merges_report_items_deterministically(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = RuntimePaths(Path(tmp_dir) / "runtime")
            existing_path = paths.profile_state_path("code-intel-kernel", "seen-records")
            existing_path.parent.mkdir(parents=True, exist_ok=True)
            existing_path.write_text(
                json.dumps(
                    {
                        "schema_version": "profile-state.v1",
                        "profile_id": "code-intel-kernel",
                        "state_id": "seen-records",
                        "state_kind": "seen_records",
                        "updated_at": "2026-05-28T12:30:45Z",
                        "record_ids": ["github_repo-good", "github_repo-old"],
                    },
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )

            result = update_seen_records_state(
                paths=paths,
                profile_id="code-intel-kernel",
                profile_report=_profile_report("code-intel-kernel"),
                state_id="seen-records",
                updated_at="2026-05-29T12:30:45Z",
            )

            self.assertEqual(result.path, existing_path)
            self.assertEqual(
                result.state,
                {
                    "schema_version": "profile-state.v1",
                    "profile_id": "code-intel-kernel",
                    "state_id": "seen-records",
                    "state_kind": "seen_records",
                    "updated_at": "2026-05-29T12:30:45Z",
                    "record_ids": [
                        "arxiv_query-good",
                        "github_repo-good",
                        "github_repo-old",
                    ],
                },
            )
            self.assertEqual(json.loads(existing_path.read_text()), result.state)
            validate_profile_state(result.state)

    def test_update_seen_records_state_rejects_mismatched_profile_report(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = RuntimePaths(Path(tmp_dir) / "runtime")

            with self.assertRaises(ValueError):
                update_seen_records_state(
                    paths=paths,
                    profile_id="code-intel-kernel",
                    profile_report=_profile_report("other-profile"),
                    state_id="seen-records",
                    updated_at="2026-05-29T12:30:45Z",
                )

    def test_update_seen_records_state_rejects_malformed_profile_report(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = RuntimePaths(Path(tmp_dir) / "runtime")
            malformed_report = _profile_report("code-intel-kernel")
            malformed_report["items"] = [{"record_id": "github_repo-good"}]

            with self.assertRaises(ValueError):
                update_seen_records_state(
                    paths=paths,
                    profile_id="code-intel-kernel",
                    profile_report=malformed_report,
                    state_id="seen-records",
                    updated_at="2026-05-29T12:30:45Z",
                )

    def test_update_seen_records_state_rejects_malformed_existing_state(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = RuntimePaths(Path(tmp_dir) / "runtime")
            existing_path = paths.profile_state_path("code-intel-kernel", "seen-records")
            existing_path.parent.mkdir(parents=True, exist_ok=True)
            existing_state = _profile_state()
            existing_state["score"] = 1
            existing_path.write_text(
                json.dumps(existing_state, sort_keys=True) + "\n",
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                update_seen_records_state(
                    paths=paths,
                    profile_id="code-intel-kernel",
                    profile_report=_profile_report("code-intel-kernel"),
                    state_id="seen-records",
                    updated_at="2026-05-29T12:30:45Z",
                )

    def test_profile_state_validation_rejects_contract_drift(self):
        valid_state = _profile_state()

        missing_required = dict(valid_state)
        missing_required.pop("state_kind")
        with self.assertRaises(ValueError):
            validate_profile_state(missing_required)

        unknown_field = dict(valid_state)
        unknown_field["score"] = 1
        with self.assertRaises(ValueError):
            validate_profile_state(unknown_field)

        bad_schema = dict(valid_state)
        bad_schema["schema_version"] = "profile-state.v0"
        with self.assertRaises(ValueError):
            validate_profile_state(bad_schema)

        bad_profile_id = dict(valid_state)
        bad_profile_id["profile_id"] = "../code-intel-kernel"
        with self.assertRaisesRegex(ValueError, "profile_id must be a safe path segment"):
            validate_profile_state(bad_profile_id)

        bad_state_id = dict(valid_state)
        bad_state_id["state_id"] = "../seen-records"
        with self.assertRaisesRegex(ValueError, "state_id must be a safe path segment"):
            validate_profile_state(bad_state_id)

        bad_kind = dict(valid_state)
        bad_kind["state_kind"] = "seen"
        with self.assertRaises(ValueError):
            validate_profile_state(bad_kind)

        bad_record_ids = dict(valid_state)
        bad_record_ids["record_ids"] = ["github_repo-good", ""]
        with self.assertRaises(ValueError):
            validate_profile_state(bad_record_ids)

        unsafe_record_ids = dict(valid_state)
        unsafe_record_ids["record_ids"] = ["../github_repo-good"]
        with self.assertRaisesRegex(ValueError, "record_id must be a safe path segment"):
            validate_profile_state(unsafe_record_ids)

        bad_updated_at = dict(valid_state)
        bad_updated_at["updated_at"] = "not-a-date-time"
        with self.assertRaisesRegex(
            ValueError, "updated_at must be a date-time string"
        ):
            validate_profile_state(bad_updated_at)

        duplicate_seen_records = dict(valid_state)
        duplicate_seen_records["record_ids"] = [
            "github_repo-good",
            "github_repo-good",
        ]
        with self.assertRaisesRegex(
            ValueError, "seen_records profile state record_ids must be unique"
        ):
            validate_profile_state(duplicate_seen_records)

        unsorted_seen_records = dict(valid_state)
        unsorted_seen_records["record_ids"] = [
            "github_repo-old",
            "github_repo-good",
        ]
        with self.assertRaisesRegex(
            ValueError, "seen_records profile state record_ids must be sorted"
        ):
            validate_profile_state(unsorted_seen_records)

    def test_profile_state_schema_tracks_runtime_id_constraints(self):
        schema = _read_schema("profile-state.schema.json")

        self.assertEqual(
            schema["properties"]["profile_id"].get("pattern"),
            SAFE_SEGMENT_PATTERN,
        )
        self.assertEqual(
            schema["properties"]["state_id"].get("pattern"),
            SAFE_SEGMENT_PATTERN,
        )
        self.assertEqual(
            schema["properties"]["record_ids"]["items"].get("pattern"),
            SAFE_SEGMENT_PATTERN,
        )


def _profile_report(profile_id):
    return {
        "schema_version": "profile-projection.v1",
        "profile_id": profile_id,
        "output_mode": "research_digest",
        "generated_at": "2026-05-29T12:30:45Z",
        "counts": {
            "clean_records_seen": 2,
            "items_written": 2,
            "excluded_by_source": 0,
            "excluded_by_keyword": 0,
            "excluded_by_risk": 0,
            "excluded_quarantined": 0,
        },
        "items": [
            _projection_item(
                "github_repo-good",
                source_type="github_repo",
                source_trust="platform",
            ),
            _projection_item(
                "arxiv_query-good",
                source_type="arxiv_query",
                source_trust="official",
            ),
        ],
    }


def _projection_item(record_id, *, source_type, source_trust):
    return {
        "record_id": record_id,
        "source_id": "test-source",
        "source_type": source_type,
        "canonical_url": f"https://example.test/{record_id}",
        "title": record_id,
        "sanitized_summary": "Test summary.",
        "source_trust": source_trust,
        "risk_flags": [],
        "raw_hash": f"raw-{record_id}",
    }


def _profile_state():
    return {
        "schema_version": "profile-state.v1",
        "profile_id": "code-intel-kernel",
        "state_id": "seen-records",
        "state_kind": "seen_records",
        "updated_at": "2026-05-28T12:30:45Z",
        "record_ids": ["github_repo-good", "github_repo-old"],
    }


def _read_schema(filename):
    path = ROOT / "schemas" / filename
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
