"""Shared validation helpers for public artifact contracts."""

from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse


def require_absolute_uri(value: object, field: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be an absolute URI")

    parsed = urlparse(value)
    if not parsed.scheme:
        raise ValueError(f"{field} must be an absolute URI")
    if parsed.scheme in {"http", "https"} and not parsed.netloc:
        raise ValueError(f"{field} must be an absolute URI")


def require_https_url(value: object, field: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be an https URL")

    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError(f"{field} must be an https URL")


def parse_date_time(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None

    parsed_value = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(parsed_value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed


def require_date_time(value: object, field: str) -> None:
    if parse_date_time(value) is None:
        raise ValueError(f"{field} must be a date-time string")


def normalize_external_date_time(value: object) -> str | None:
    parsed = parse_date_time(value)
    if parsed is None:
        if not isinstance(value, str) or not value:
            return None
        try:
            parsed = parsedate_to_datetime(value)
        except (TypeError, ValueError, IndexError, OverflowError):
            return None
        if parsed.tzinfo is None:
            return None

    return format_utc(parsed)


def format_utc(value: datetime) -> str:
    return (
        value.astimezone(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )
