"""Optional local GitHub API authentication headers."""

from __future__ import annotations

import os


def github_auth_headers() -> dict[str, str]:
    """Return optional GitHub auth headers from local environment."""
    token = (os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or "").strip()
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}
