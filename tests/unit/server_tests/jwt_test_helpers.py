"""
Shared JWT test fixtures for test_jwt_auth.py, test_oauth_handler.py,
and test_jwt_server_middleware_factory.py, so the suites can't silently
drift apart on how tokens/signing keys are faked or how JWKS module
state is reset.
"""
import datetime
from unittest.mock import patch

import jwt

ISSUER = "https://idp.example.com/"
AUDIENCE = "tabpy"
JWKS_URI = "https://idp.example.com/.well-known/jwks.json"


def reset_jwks_state():
    """Clears process-global JWKS caches used by jwt_auth."""
    import tabpy.tabpy_server.handlers.jwt_auth as jwt_auth_module

    jwt_auth_module._jwks_clients.clear()
    jwt_auth_module._jwks_last_failed_refresh.clear()
    jwt_auth_module._jwks_last_fetch_failure.clear()


def make_token(private_key, claims_override=None, headers=None):
    now = datetime.datetime.now(datetime.timezone.utc)
    claims = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "sub": "user1",
        "iat": now,
        "exp": now + datetime.timedelta(minutes=5),
    }
    if claims_override:
        claims.update(claims_override)
    return jwt.encode(claims, private_key, algorithm="RS256", headers=headers)


def patched_jwks_client(private_key, kid=None):
    """Patches PyJWKClient.get_signing_keys to return private_key's public
    key instead of making a network call."""
    signing_key = type("SigningKey", (), {})()
    signing_key.key = private_key.public_key()
    signing_key.algorithm_name = "RS256"
    signing_key.key_id = kid
    return patch(
        "tabpy.tabpy_server.handlers.jwt_auth.PyJWKClient.get_signing_keys",
        return_value=[signing_key],
    )
