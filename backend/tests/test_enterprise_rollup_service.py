from datetime import datetime, timedelta, timezone

from services.enterprise_rollup_service import _elapsed_seconds_since


class TestEnterpriseRollupService:
    def test_elapsed_seconds_since_handles_timezone_aware_timestamp(self):
        timestamp = datetime.now(timezone.utc) - timedelta(seconds=15)
        elapsed = _elapsed_seconds_since(timestamp)
        assert 10 <= elapsed <= 20

    def test_elapsed_seconds_since_handles_naive_timestamp(self):
        timestamp = datetime.utcnow() - timedelta(seconds=15)
        elapsed = _elapsed_seconds_since(timestamp)
        assert 10 <= elapsed <= 20

    def test_elapsed_seconds_since_returns_zero_for_none(self):
        assert _elapsed_seconds_since(None) == 0
