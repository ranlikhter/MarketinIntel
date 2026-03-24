"""Timezone-aware datetime helpers."""
from datetime import datetime, timezone


def utcnow() -> datetime:
    """Return the current UTC time as a timezone-naive datetime (compatible with
    existing DB columns that store naive datetimes) while using the correct
    timezone-aware API under the hood, avoiding the Python 3.12 deprecation of
    datetime.utcnow()."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
