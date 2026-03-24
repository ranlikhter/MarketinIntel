"""
Unit Tests — SSRF Validator

Ensures the validate_external_url guard blocks private/internal
network addresses and only allows public http/https URLs.
"""

import pytest
from fastapi import HTTPException
from services.ssrf_validator import validate_external_url


class TestAllowedURLs:

    def test_valid_public_https_url(self):
        url = "https://www.example.com/products"
        result = validate_external_url(url)
        assert result == url

    def test_valid_public_http_url(self):
        url = "http://shop.example.com"
        result = validate_external_url(url)
        assert result == url

    def test_url_with_path_and_query(self):
        url = "https://competitor.com/products?page=1&limit=50"
        result = validate_external_url(url)
        assert result == url

    def test_url_with_port(self):
        url = "https://example.com:8443/api"
        result = validate_external_url(url)
        assert result == url


class TestBlockedPrivateNetworks:

    def _assert_blocked(self, url: str):
        with pytest.raises(HTTPException) as exc_info:
            validate_external_url(url)
        assert exc_info.value.status_code == 422

    def test_blocks_localhost(self):
        self._assert_blocked("http://localhost/admin")

    def test_blocks_127_0_0_1(self):
        self._assert_blocked("http://127.0.0.1:8000/api")

    def test_blocks_private_10_network(self):
        self._assert_blocked("http://10.0.0.1/secret")

    def test_blocks_private_192_168_network(self):
        self._assert_blocked("http://192.168.1.1/router")

    def test_blocks_private_172_network(self):
        self._assert_blocked("http://172.16.0.1/internal")

    def test_blocks_link_local_aws_metadata(self):
        # AWS metadata endpoint — critical SSRF target
        self._assert_blocked("http://169.254.169.254/latest/meta-data")

    def test_blocks_ipv6_loopback(self):
        self._assert_blocked("http://[::1]/admin")

    def test_blocks_bare_private_ip(self):
        self._assert_blocked("https://10.10.10.10/api")


class TestBlockedSchemes:

    def _assert_blocked(self, url: str):
        with pytest.raises(HTTPException) as exc_info:
            validate_external_url(url)
        assert exc_info.value.status_code == 422

    def test_blocks_ftp_scheme(self):
        self._assert_blocked("ftp://files.example.com/data.csv")

    def test_blocks_file_scheme(self):
        self._assert_blocked("file:///etc/passwd")

    def test_blocks_gopher_scheme(self):
        self._assert_blocked("gopher://internal.host/")

    def test_blocks_javascript_scheme(self):
        self._assert_blocked("javascript:alert(1)")


class TestEdgeCases:

    def test_empty_url_raises(self):
        with pytest.raises(HTTPException):
            validate_external_url("")

    def test_url_without_hostname_raises(self):
        with pytest.raises(HTTPException):
            validate_external_url("https:///no-host")

    def test_custom_field_name_in_error(self):
        with pytest.raises(HTTPException) as exc_info:
            validate_external_url("http://localhost", field_name="base_url")
        assert "base_url" in str(exc_info.value.detail)

    def test_returns_original_url_string(self):
        url = "https://example.com/shop"
        result = validate_external_url(url, field_name="store_url")
        assert result == url
