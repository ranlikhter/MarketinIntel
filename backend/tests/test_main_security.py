"""
Security-focused tests for FastAPI debug surfaces and health responses.
"""

import json

from api.main import _build_deep_health_response, _debug_surfaces_enabled, create_app


class TestMainSecurity:
    def test_debug_surfaces_are_only_enabled_in_safe_local_envs(self):
        assert _debug_surfaces_enabled("development") is True
        assert _debug_surfaces_enabled("testing") is True
        assert _debug_surfaces_enabled("production") is False
        assert _debug_surfaces_enabled("staging") is False

    def test_create_app_disables_openapi_and_docs_in_production(self):
        app = create_app("production")

        assert app.docs_url is None
        assert app.redoc_url is None
        assert app.openapi_url is None

    def test_create_app_keeps_docs_enabled_in_development(self):
        app = create_app("development")

        assert app.docs_url == "/docs"
        assert app.redoc_url == "/redoc"
        assert app.openapi_url == "/openapi.json"

    def test_deep_health_hides_dependency_details_in_production(self):
        response = _build_deep_health_response(
            {
                "database": "ok",
                "redis": "error: connection refused",
                "celery": "no_workers",
            },
            "production",
        )

        assert response.status_code == 503
        assert json.loads(response.body) == {"status": "degraded"}

    def test_deep_health_includes_dependency_details_in_development(self):
        checks = {
            "database": "ok",
            "redis": "error: connection refused",
            "celery": "no_workers",
        }
        response = _build_deep_health_response(checks, "development")

        assert response.status_code == 503
        assert json.loads(response.body) == {"status": "degraded", "checks": checks}
