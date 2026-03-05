"""
SSRF (Server-Side Request Forgery) Validator

Prevents the crawler and competitor URL endpoints from being used to make
requests to internal/private network resources.
"""

import socket
import ipaddress
from urllib.parse import urlparse

from fastapi import HTTPException, status

# Private and reserved IP ranges that must never be crawled
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),       # RFC-1918 private
    ipaddress.ip_network("172.16.0.0/12"),     # RFC-1918 private
    ipaddress.ip_network("192.168.0.0/16"),    # RFC-1918 private
    ipaddress.ip_network("127.0.0.0/8"),       # Loopback
    ipaddress.ip_network("::1/128"),           # IPv6 loopback
    ipaddress.ip_network("169.254.0.0/16"),    # Link-local (AWS metadata endpoint)
    ipaddress.ip_network("100.64.0.0/10"),     # Shared address space (RFC-6598)
    ipaddress.ip_network("0.0.0.0/8"),         # "This" network
    ipaddress.ip_network("fc00::/7"),          # IPv6 unique local
    ipaddress.ip_network("fe80::/10"),         # IPv6 link-local
]

# Only these schemes are allowed for external URLs
_ALLOWED_SCHEMES = {"http", "https"}


def validate_external_url(url: str, field_name: str = "url") -> str:
    """
    Validate that a URL is safe to fetch/crawl:
      - Must use http or https
      - Must not resolve to a private/reserved IP address
      - Must have a non-empty hostname

    Args:
        url: The URL string to validate
        field_name: Name of the field (for error messages)

    Returns:
        The original URL string if valid

    Raises:
        HTTPException 422 if the URL is unsafe or unresolvable
    """
    parsed = urlparse(url)

    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{field_name}: only http/https URLs are allowed",
        )

    hostname = parsed.hostname
    if not hostname:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{field_name}: URL must have a hostname",
        )

    # Block bare IP addresses that are obviously private without a DNS lookup
    try:
        addr = ipaddress.ip_address(hostname)
        _assert_not_private(addr, field_name)
        return url
    except ValueError:
        pass  # Not a bare IP address — fall through to DNS resolution

    # Resolve hostname and check every returned address
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{field_name}: cannot resolve hostname '{hostname}'",
        )

    for *_, sockaddr in infos:
        raw_addr = sockaddr[0]
        try:
            addr = ipaddress.ip_address(raw_addr)
            _assert_not_private(addr, field_name)
        except ValueError:
            pass  # Malformed addr from getaddrinfo — skip

    return url


def _assert_not_private(addr: ipaddress.IPv4Address | ipaddress.IPv6Address, field_name: str) -> None:
    """Raise HTTPException if addr falls in any blocked network."""
    for net in _BLOCKED_NETWORKS:
        try:
            if addr in net:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        f"{field_name}: requests to private or reserved IP addresses "
                        "are not allowed"
                    ),
                )
        except TypeError:
            # Mixed IPv4/IPv6 comparison — skip
            pass
