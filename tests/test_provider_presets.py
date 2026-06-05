import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from shared_intake_governance.provider_presets import (  # noqa: E402
    provider_command_hash,
    provider_preset_ids,
    provider_request_matches_preset,
    resolve_provider_preset,
)


class ProviderPresetTests(unittest.TestCase):
    def test_repo_owned_provider_presets_are_explicit_allowlist(self):
        self.assertEqual(
            provider_preset_ids(),
            (
                "claude_readonly_local",
                "gemini_readonly_local",
                "agy_readonly_local",
                "vibe_readonly_local",
            ),
        )

        preset = resolve_provider_preset("claude_readonly_local")

        self.assertEqual(preset["provider"], "claude")
        self.assertEqual(preset["preset_id"], "claude_readonly_local")
        self.assertIsInstance(preset["resolved_command"], list)
        self.assertGreater(len(preset["resolved_command"]), 0)
        self.assertEqual(
            preset["command_hash"],
            provider_command_hash(preset["resolved_command"]),
        )

        agy_preset = resolve_provider_preset("agy_readonly_local")

        self.assertEqual(agy_preset["provider"], "agy")
        self.assertEqual(agy_preset["preset_id"], "agy_readonly_local")
        self.assertEqual(
            agy_preset["resolved_command"][:2],
            ["agy", "--sandbox"],
        )
        self.assertIn("--print", agy_preset["resolved_command"])
        self.assertEqual(
            agy_preset["command_hash"],
            provider_command_hash(agy_preset["resolved_command"]),
        )

    def test_provider_request_must_match_repo_owned_preset(self):
        preset = resolve_provider_preset("claude_readonly_local")
        request = {
            "provider": preset["provider"],
            "preset_id": preset["preset_id"],
            "resolved_command": preset["resolved_command"],
            "command_hash": preset["command_hash"],
        }

        self.assertTrue(provider_request_matches_preset(request))

        tampered = dict(request)
        tampered["resolved_command"] = ["python3", "evil_wrapper.py"]
        tampered["command_hash"] = provider_command_hash(tampered["resolved_command"])

        self.assertFalse(provider_request_matches_preset(tampered))

    def test_unknown_preset_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "unsupported provider preset"):
            resolve_provider_preset("unknown_provider")
