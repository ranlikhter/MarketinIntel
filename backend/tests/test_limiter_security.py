"""
Security tests for global rate-limit key derivation.
"""

from starlette.requests import Request

from api.limiter import _rate_limit_key
from services.auth_service import create_access_token


def _make_request(headers: dict[str, str] | None = None, client_host: str = "198.51.100.10") -> Request:
    normalized_headers = []
    for key, value in (headers or {}).items():
        normalized_headers.append((key.lower().encode("latin-1"), value.encode("latin-1")))

    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/api/products",
        "raw_path": b"/api/products",
        "query_string": b"",
        "headers": normalized_headers,
        "client": (client_host, 12345),
        "server": ("testserver", 80),
    }
    return Request(scope)


class TestLimiterSecurity:
    def test_rate_limit_key_ignores_untrusted_x_user_id_header(self):
        request = _make_request(headers={"X-User-ID": "999"})
        assert _rate_limit_key(request) == "198.51.100.10"

    def test_rate_limit_key_uses_verified_bearer_token_subject(self):
        token = create_access_token({"sub": "42"})
        request = _make_request(
            headers={
                "Authorization": f"Bearer {token}",
                "X-User-ID": "999",
            }
        )
        assert _rate_limit_key(request) == "user:42"

    def test_rate_limit_key_falls_back_to_ip_for_invalid_bearer_token(self):
        request = _make_request(
            headers={
                "Authorization": "Bearer not-a-real-token",
                "X-User-ID": "123",
            }
        )
        assert _rate_limit_key(request) == "198.51.100.10"
