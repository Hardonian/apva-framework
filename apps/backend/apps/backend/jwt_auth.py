"""Cryptographic JWT token signing and verification for APVA sessions."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any, cast

from .config import settings

_SIGNING_SECRET = settings.jwt_secret


def create_access_token(
    payload: dict[str, Any],
    secret: str = _SIGNING_SECRET,
    expires_in: int = 86400,
) -> str:
    """Generate a signed HMAC-SHA256 JWT access token.

    Args:
        payload: Dictionary of token claims (e.g. sub, tenant_id).
        secret: HMAC secret key.
        expires_in: Expiration lifetime in seconds.

    Returns:
        str: Encoded JWT string in header.payload.signature format.
    """
    header = {"alg": "HS256", "typ": "JWT"}
    exp = int(time.time()) + expires_in
    data = {**payload, "exp": exp, "iat": int(time.time())}

    header_b64 = (
        base64.urlsafe_b64encode(json.dumps(header, separators=(",", ":")).encode())
        .decode()
        .rstrip("=")
    )
    payload_b64 = (
        base64.urlsafe_b64encode(json.dumps(data, separators=(",", ":")).encode())
        .decode()
        .rstrip("=")
    )
    signing_input = f"{header_b64}.{payload_b64}".encode()
    signature = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(signature).decode().rstrip("=")

    return f"{header_b64}.{payload_b64}.{sig_b64}"


def decode_access_token(token: str, secret: str = _SIGNING_SECRET) -> dict[str, Any] | None:
    """Verify signature and parse claims from a JWT access token.

    Args:
        token: Raw JWT string.
        secret: HMAC secret key.

    Returns:
        dict[str, Any] | None: Parsed claims dictionary if valid and unexpired; None otherwise.
    """
    parts = token.strip().split(".")
    if len(parts) != 3:
        return None

    header_b64, payload_b64, sig_b64 = parts
    try:
        header_padding = "=" * (-len(header_b64) % 4)
        header = json.loads(base64.urlsafe_b64decode(header_b64 + header_padding))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if header != {"alg": "HS256", "typ": "JWT"}:
        return None

    signing_input = f"{header_b64}.{payload_b64}".encode()
    expected_sig = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    expected_sig_b64 = base64.urlsafe_b64encode(expected_sig).decode().rstrip("=")

    if not hmac.compare_digest(sig_b64, expected_sig_b64):
        return None

    rem = len(payload_b64) % 4
    if rem:
        payload_b64 += "=" * (4 - rem)

    try:
        data = json.loads(base64.urlsafe_b64decode(payload_b64.encode()).decode())
    except Exception:
        return None

    if not isinstance(data, dict):
        return None

    if not isinstance(data.get("exp"), int) or time.time() > data["exp"]:
        return None
    if "iat" in data and not isinstance(data["iat"], int):
        return None

    return cast(dict[str, Any], data)
