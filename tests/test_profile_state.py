import json
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from shared_intake_governance.projector.profile_state import (  # noqa: E402
    update_seen_records_state,
)
from shared_intake_governance.runtime import RuntimePaths  # noqa: E402


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
                        "record_ids": ["github_repo-old", "github_repo-good"],
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
                        "arxiv_rss_keywords-good",
                        "github_repo-good",
                        "github_repo-old",
                    ],
                },
            )
            self.assertEqual(json.loads(existing_path.read_text()), result.state)

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
                "arxiv_rss_keywords-good",
                source_type="arxiv_rss_keywords",
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


if __name__ == "__main__":
    unittest.main()
