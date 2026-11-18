from __future__ import annotations

import pytest

from klod.auth.google import InvalidGoogleIdentity, verify_google_identity


def valid_claims() -> dict:
    return {
        "iss": "https://accounts.google.com",
        "sub": "google-sub-123",
        "email": "user@example.com",
        "email_verified": True,
        "name": "Klod User",
        "picture": "https://example.com/avatar.png",
    }


def test_google_identity_uses_server_verifier_and_stable_subject() -> None:
    calls = []

    def verifier(token, request, audience):
        calls.append((token, audience))
        return valid_claims()

    identity = verify_google_identity("signed-id-token", "google-client-id", verifier=verifier)
    assert calls == [("signed-id-token", "google-client-id")]
    assert identity["google_sub"] == "google-sub-123"
    assert identity["email"] == "user@example.com"


def test_unverified_email_is_rejected() -> None:
    claims = valid_claims()
    claims["email_verified"] = False
    with pytest.raises(InvalidGoogleIdentity):
        verify_google_identity("id-token", "client-id", verifier=lambda *_args, **_kwargs: claims)


def test_wrong_issuer_is_rejected() -> None:
    claims = valid_claims()
    claims["iss"] = "https://attacker.example"
    with pytest.raises(InvalidGoogleIdentity):
        verify_google_identity("id-token", "client-id", verifier=lambda *_args, **_kwargs: claims)


def test_missing_identity_subject_is_rejected() -> None:
    claims = valid_claims()
    claims.pop("sub")
    with pytest.raises(InvalidGoogleIdentity):
        verify_google_identity("id-token", "client-id", verifier=lambda *_args, **_kwargs: claims)


def test_verification_library_error_is_rejected() -> None:
    def reject(*_args, **_kwargs):
        raise ValueError("bad signature")

    with pytest.raises(InvalidGoogleIdentity):
        verify_google_identity("bad-token", "client-id", verifier=reject)
