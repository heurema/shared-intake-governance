"""Shared validation helpers for public artifact contracts."""

from __future__ import annotations

from urllib.parse import urlparse


def require_absolute_uri(value: object, field: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be an absolute URI")

    parsed = urlparse(value)
    if not parsed.scheme:
        raise ValueError(f"{field} must be an absolute URI")
    if parsed.scheme in {"http", "https"} and not parsed.netloc:
        raise ValueError(f"{field} must be an absolute URI")
