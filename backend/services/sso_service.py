"""
SSO provider helpers.
"""

import os
import time
from urllib.parse import urlencode

import httpx
from jose import jwt, jwk
from jose.utils import base64url_decode


class SSOValidationError(Exception):
    """Raised when an external identity token cannot be trusted."""


def _get_allowed_google_client_ids() -> list[str]:
    raw = os.getenv("GOOGLE_CLIENT_ID", "")
    return [client_id.strip() for client_id in raw.split(",") if client_id.strip()]


def _get_microsoft_client_id() -> str:
    return os.getenv("MICROSOFT_CLIENT_ID", "").strip()


def _get_microsoft_client_secret() -> str:
    return os.getenv("MICROSOFT_CLIENT_SECRET", "").strip()


def _get_microsoft_tenant_id() -> str:
    return os.getenv("MICROSOFT_TENANT_ID", "common").strip() or "common"


def _get_microsoft_base_url() -> str:
    tenant_id = _get_microsoft_tenant_id()
    return f"https://login.microsoftonline.com/{tenant_id}"


async def validate_google_id_token(id_token: str) -> dict:
    """
    Validate a Google Identity Services ID token and return normalized claims.
    """
    allowed_client_ids = _get_allowed_google_client_ids()
    if not allowed_client_ids:
        raise SSOValidationError("Google SSO is not configured")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://oauth2.googleapis.com/tokeninfo",
                params={"id_token": id_token},
            )
    except httpx.HTTPError as exc:
        raise SSOValidationError("Unable to validate Google sign-in right now") from exc

    if response.status_code != 200:
        raise SSOValidationError("Google sign-in token is invalid or expired")

    payload = response.json()
    audience = payload.get("aud")
    if audience not in allowed_client_ids:
        raise SSOValidationError("Google sign-in token was issued for a different app")

    if payload.get("iss") not in {"accounts.google.com", "https://accounts.google.com"}:
        raise SSOValidationError("Google sign-in issuer is invalid")

    email = payload.get("email")
    subject = payload.get("sub")
    if not email or not subject:
        raise SSOValidationError("Google sign-in payload is missing required identity fields")

    return {
        "email": email,
        "sub": subject,
        "full_name": payload.get("name"),
        "avatar_url": payload.get("picture"),
        "email_verified": str(payload.get("email_verified", "")).lower() == "true",
    }


def build_microsoft_authorize_url(state_token: str, nonce: str, redirect_uri: str) -> str:
    """
    Build the Microsoft authorize URL for the OAuth code flow.
    """
    client_id = _get_microsoft_client_id()
    if not client_id or not _get_microsoft_client_secret():
        raise SSOValidationError("Microsoft SSO is not configured")

    query = urlencode({
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "response_mode": "query",
        "scope": "openid profile email",
        "state": state_token,
        "nonce": nonce,
    })
    return f"{_get_microsoft_base_url()}/oauth2/v2.0/authorize?{query}"


async def _validate_microsoft_id_token(id_token: str, expected_nonce: str) -> dict:
    client_id = _get_microsoft_client_id()
    if not client_id:
        raise SSOValidationError("Microsoft SSO is not configured")

    try:
        headers = jwt.get_unverified_header(id_token)
        payload = jwt.get_unverified_claims(id_token)
    except Exception as exc:
        raise SSOValidationError("Microsoft sign-in token is invalid or expired") from exc

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            jwks_response = await client.get(f"{_get_microsoft_base_url()}/discovery/v2.0/keys")
    except httpx.HTTPError as exc:
        raise SSOValidationError("Unable to validate Microsoft sign-in right now") from exc

    if jwks_response.status_code != 200:
        raise SSOValidationError("Unable to validate Microsoft sign-in right now")

    key_data = next(
        (key for key in jwks_response.json().get("keys", []) if key.get("kid") == headers.get("kid")),
        None,
    )
    if not key_data:
        raise SSOValidationError("Microsoft sign-in token is invalid or expired")

    public_key = jwk.construct(key_data)

    try:
        message, encoded_signature = id_token.rsplit(".", 1)
        decoded_signature = base64url_decode(encoded_signature.encode("utf-8"))
        if not public_key.verify(message.encode("utf-8"), decoded_signature):
            raise SSOValidationError("Microsoft sign-in token is invalid or expired")
    except ValueError as exc:
        raise SSOValidationError("Microsoft sign-in token is invalid or expired") from exc

    now = int(time.time())
    exp = payload.get("exp")
    nbf = payload.get("nbf")

    if not exp or int(exp) < now:
        raise SSOValidationError("Microsoft sign-in token is invalid or expired")
    if nbf and int(nbf) > now:
        raise SSOValidationError("Microsoft sign-in token is not valid yet")

    audience = payload.get("aud")
    if audience != client_id:
        raise SSOValidationError("Microsoft sign-in token was issued for a different app")

    issuer = payload.get("iss", "")
    if not issuer.startswith("https://login.microsoftonline.com/") or not issuer.endswith("/v2.0"):
        raise SSOValidationError("Microsoft sign-in issuer is invalid")

    if payload.get("nonce") != expected_nonce:
        raise SSOValidationError("Microsoft sign-in nonce did not match")

    email = payload.get("email") or payload.get("preferred_username")
    subject = payload.get("oid") or payload.get("sub")
    if not email or not subject:
        raise SSOValidationError("Microsoft sign-in payload is missing required identity fields")

    return {
        "email": email,
        "sub": subject,
        "full_name": payload.get("name"),
        "avatar_url": None,
        "email_verified": True,
    }


async def exchange_microsoft_code_for_claims(
    code: str,
    redirect_uri: str,
    expected_nonce: str,
) -> dict:
    """
    Exchange a Microsoft OAuth code for validated user claims.
    """
    client_id = _get_microsoft_client_id()
    client_secret = _get_microsoft_client_secret()
    if not client_id or not client_secret:
        raise SSOValidationError("Microsoft SSO is not configured")

    token_url = f"{_get_microsoft_base_url()}/oauth2/v2.0/token"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                token_url,
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "scope": "openid profile email",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
    except httpx.HTTPError as exc:
        raise SSOValidationError("Unable to validate Microsoft sign-in right now") from exc

    if response.status_code != 200:
        raise SSOValidationError("Microsoft sign-in code is invalid or expired")

    payload = response.json()
    id_token = payload.get("id_token")
    if not id_token:
        raise SSOValidationError("Microsoft sign-in response did not include an ID token")

    return await _validate_microsoft_id_token(id_token, expected_nonce)
