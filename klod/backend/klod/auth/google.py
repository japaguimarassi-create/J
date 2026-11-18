from __future__ import annotations

from collections.abc import Callable
from typing import Any


class InvalidGoogleIdentity(ValueError):
    pass


def verify_google_identity(
    credential: str,
    client_id: str,
    verifier: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, str]:
    if not credential or not client_id:
        raise InvalidGoogleIdentity("Google sign-in is not configured")
    if verifier is None:
        try:
            from google.auth.transport.requests import Request
            from google.oauth2 import id_token
        except ImportError as error:
            raise RuntimeError("google-auth is required for Google sign-in") from error
        verifier = id_token.verify_oauth2_token
        request = Request()
    else:
        request = object()
    try:
        claims = verifier(credential, request, audience=client_id)
    except Exception as error:
        raise InvalidGoogleIdentity("Google credential could not be verified") from error
    if claims.get("iss") not in {"accounts.google.com", "https://accounts.google.com"}:
        raise InvalidGoogleIdentity("Unexpected Google token issuer")
    if claims.get("email_verified") is not True:
        raise InvalidGoogleIdentity("Google email is not verified")
    subject = claims.get("sub")
    email = claims.get("email")
    if not isinstance(subject, str) or not subject or not isinstance(email, str) or not email:
        raise InvalidGoogleIdentity("Google token is missing required identity claims")
    return {
        "google_sub": subject,
        "email": email,
        "display_name": str(claims.get("name") or "")[:160],
        "picture": str(claims.get("picture") or "")[:2048],
    }
