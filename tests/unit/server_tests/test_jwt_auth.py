import base64
import datetime
import hmac
import hashlib
import json
import unittest
from unittest.mock import patch

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from tabpy.tabpy_server.handlers.jwt_auth import JwtValidationError, validate_jwt
from tests.unit.server_tests.jwt_test_helpers import (
    AUDIENCE,
    ISSUER,
    JWKS_URI,
    make_token,
    patched_jwks_client,
)


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


class TestJwtAuth(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    def setUp(self):
        import tabpy.tabpy_server.handlers.jwt_auth as jwt_auth_module

        jwt_auth_module._jwks_clients.clear()
        jwt_auth_module._jwks_last_failed_refresh.clear()
        jwt_auth_module._jwks_last_fetch_failure.clear()

    def _make_token(self, claims_override=None, headers=None):
        return make_token(
            self.private_key, claims_override=claims_override, headers=headers
        )

    def _patched_jwks_client(self, kid=None):
        return patched_jwks_client(self.private_key, kid=kid)

    def test_valid_jwt_is_accepted(self):
        token = self._make_token()
        with self._patched_jwks_client():
            claims = validate_jwt(token, issuer=ISSUER, jwks_uri=JWKS_URI, audience=AUDIENCE)
        self.assertEqual(claims["sub"], "user1")

    def test_missing_token_raises(self):
        with self.assertRaises(JwtValidationError):
            validate_jwt("", issuer=ISSUER, jwks_uri=JWKS_URI, audience=AUDIENCE)

    def test_expired_jwt_is_rejected(self):
        past = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)
        token = self._make_token({"iat": past - datetime.timedelta(minutes=5), "exp": past})
        with self._patched_jwks_client():
            with self.assertRaises(JwtValidationError):
                validate_jwt(token, issuer=ISSUER, jwks_uri=JWKS_URI, audience=AUDIENCE)

    def test_wrong_issuer_is_rejected(self):
        token = self._make_token({"iss": "https://wrong-idp.example.com/"})
        with self._patched_jwks_client():
            with self.assertRaises(JwtValidationError):
                validate_jwt(token, issuer=ISSUER, jwks_uri=JWKS_URI, audience=AUDIENCE)

    def test_wrong_audience_is_rejected(self):
        token = self._make_token({"aud": "wrong-audience"})
        with self._patched_jwks_client():
            with self.assertRaises(JwtValidationError):
                validate_jwt(token, issuer=ISSUER, jwks_uri=JWKS_URI, audience=AUDIENCE)

    def test_missing_required_scope_is_rejected(self):
        token = self._make_token({"scope": "tabpy:query"})
        with self._patched_jwks_client():
            with self.assertRaises(JwtValidationError):
                validate_jwt(
                    token,
                    issuer=ISSUER,
                    jwks_uri=JWKS_URI,
                    audience=AUDIENCE,
                    required_scopes="tabpy:query,tabpy:evaluate",
                )

    def test_non_string_scope_claim_is_rejected_not_raised(self):
        """
        Some IdPs emit `scope`/permissions as a JSON list rather than a
        space-separated string. That must still fail closed as a
        JwtValidationError (401), not escape as an uncaught exception (500).
        """
        token = self._make_token({"scope": ["tabpy:query", "tabpy:evaluate"]})
        with self._patched_jwks_client():
            with self.assertRaises(JwtValidationError):
                validate_jwt(
                    token,
                    issuer=ISSUER,
                    jwks_uri=JWKS_URI,
                    audience=AUDIENCE,
                    required_scopes="tabpy:query",
                )

    def test_present_required_scopes_are_accepted(self):
        token = self._make_token({"scope": "tabpy:query tabpy:evaluate"})
        with self._patched_jwks_client():
            claims = validate_jwt(
                token,
                issuer=ISSUER,
                jwks_uri=JWKS_URI,
                audience=AUDIENCE,
                required_scopes="tabpy:query,tabpy:evaluate",
            )
        self.assertEqual(claims["sub"], "user1")

    def test_malformed_token_is_rejected(self):
        with self.assertRaises(JwtValidationError):
            validate_jwt(
                "not-a-real-jwt", issuer=ISSUER, jwks_uri=JWKS_URI, audience=AUDIENCE
            )

    def test_wrong_signing_key_is_rejected(self):
        token = self._make_token()
        other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        signing_key = type("SigningKey", (), {})()
        signing_key.key = other_key.public_key()
        signing_key.algorithm_name = "RS256"
        signing_key.key_id = None
        with patch(
            "tabpy.tabpy_server.handlers.jwt_auth.PyJWKClient.get_signing_keys",
            return_value=[signing_key],
        ):
            with self.assertRaises(JwtValidationError):
                validate_jwt(token, issuer=ISSUER, jwks_uri=JWKS_URI, audience=AUDIENCE)

    def test_not_yet_valid_token_is_rejected(self):
        future = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=10)
        token = self._make_token({"nbf": future})
        with self._patched_jwks_client():
            with self.assertRaises(JwtValidationError):
                validate_jwt(token, issuer=ISSUER, jwks_uri=JWKS_URI, audience=AUDIENCE)

    def test_unresolvable_signing_key_is_rejected(self):
        token = self._make_token()
        with patch(
            "tabpy.tabpy_server.handlers.jwt_auth.PyJWKClient.get_signing_keys",
            side_effect=jwt.exceptions.PyJWKClientError("Unable to find a signing key"),
        ):
            with self.assertRaises(JwtValidationError):
                validate_jwt(token, issuer=ISSUER, jwks_uri=JWKS_URI, audience=AUDIENCE)

    def test_unexpected_jwks_error_is_rejected_not_raised(self):
        """
        A malformed JWKS response or other network-layer failure that PyJWT
        doesn't wrap as PyJWKClientError/InvalidTokenError must still come
        out as JwtValidationError (401), not an uncaught exception (500).
        """
        token = self._make_token()
        with patch(
            "tabpy.tabpy_server.handlers.jwt_auth.PyJWKClient.get_signing_keys",
            side_effect=ValueError("Expecting value: line 1 column 1 (char 0)"),
        ):
            with self.assertRaises(JwtValidationError):
                validate_jwt(token, issuer=ISSUER, jwks_uri=JWKS_URI, audience=AUDIENCE)

    def test_jwks_client_is_created_with_bounded_timeout(self):
        """
        TabPy serves requests on a single IO-loop thread, so the JWKS HTTP
        client must not be allowed to hang indefinitely on a slow/unreachable
        IdP -- that would stall the entire server, not just one request.
        """
        import tabpy.tabpy_server.handlers.jwt_auth as jwt_auth_module

        jwt_auth_module._jwks_clients.clear()
        client = jwt_auth_module._get_jwks_client(JWKS_URI)
        self.assertEqual(client.timeout, jwt_auth_module.JWKS_FETCH_TIMEOUT_SECONDS)
        self.assertLess(jwt_auth_module.JWKS_FETCH_TIMEOUT_SECONDS, 30)

    def test_algorithm_is_pinned_to_jwks_key_not_token_header(self):
        """
        Guards against algorithm-confusion attacks: even if a forged token
        claims alg=none in its header, validate_jwt only ever decodes using
        the algorithm associated with the resolved JWKS signing key.
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        header = b64url(json.dumps({"alg": "none", "typ": "JWT"}).encode())
        payload = b64url(
            json.dumps(
                {
                    "iss": ISSUER,
                    "aud": AUDIENCE,
                    "sub": "attacker",
                    "iat": int(now.timestamp()),
                    "exp": int((now + datetime.timedelta(minutes=5)).timestamp()),
                }
            ).encode()
        )
        forged_token = f"{header}.{payload}."

        with self._patched_jwks_client():
            with self.assertRaises(JwtValidationError):
                validate_jwt(forged_token, issuer=ISSUER, jwks_uri=JWKS_URI, audience=AUDIENCE)

    def test_matching_kid_is_selected_from_multi_key_jwks(self):
        """
        Every other test in this suite mocks a single signing key with
        key_id=None matching a header-less token, which trivially matches
        via `None == None` -- unrepresentative of a real JWKS, where every
        entry has a non-empty kid (PyJWT filters out keys without one).
        This exercises the actual kid-comparison logic against a JWKS with
        multiple keys, matching the token's real `kid` header.
        """
        token = self._make_token(headers={"kid": "key-2"})

        other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        wrong_key = type("SigningKey", (), {})()
        wrong_key.key = other_key.public_key()
        wrong_key.algorithm_name = "RS256"
        wrong_key.key_id = "key-1"

        right_key = type("SigningKey", (), {})()
        right_key.key = self.private_key.public_key()
        right_key.algorithm_name = "RS256"
        right_key.key_id = "key-2"

        with patch(
            "tabpy.tabpy_server.handlers.jwt_auth.PyJWKClient.get_signing_keys",
            return_value=[wrong_key, right_key],
        ):
            claims = validate_jwt(token, issuer=ISSUER, jwks_uri=JWKS_URI, audience=AUDIENCE)
        self.assertEqual(claims["sub"], "user1")

    def test_repeated_unknown_kid_does_not_force_unbounded_jwks_refresh(self):
        """
        An unauthenticated caller can send a token with a made-up `kid`
        (read from the unverified header, before any signature check).
        Repeatedly retrying an unknown `kid` -- even a different one each
        time -- must not each force a fresh JWKS fetch, since that fetch is
        a blocking network call on TabPy's single IO-loop thread. The
        cooldown is keyed only by jwks_uri (not by kid, since kid is
        attacker-controlled pre-signature-check): only one forced refresh
        per jwks_uri is allowed within JWKS_MIN_REFRESH_INTERVAL_SECONDS,
        no matter how many distinct bogus kids are tried.
        """
        import tabpy.tabpy_server.handlers.jwt_auth as jwt_auth_module

        jwt_auth_module._jwks_clients.clear()
        jwt_auth_module._jwks_last_failed_refresh.clear()

        token1 = self._make_token(headers={"kid": "unknown-kid-1"})
        token2 = self._make_token(headers={"kid": "unknown-kid-2"})

        signing_key = type("SigningKey", (), {})()
        signing_key.key = self.private_key.public_key()
        signing_key.algorithm_name = "RS256"
        signing_key.key_id = "the-real-kid"

        with patch(
            "tabpy.tabpy_server.handlers.jwt_auth.PyJWKClient.get_signing_keys",
            return_value=[signing_key],
        ) as mock_get_signing_keys:
            with self.assertRaises(JwtValidationError):
                validate_jwt(token1, issuer=ISSUER, jwks_uri=JWKS_URI, audience=AUDIENCE)
            with self.assertRaises(JwtValidationError):
                validate_jwt(token2, issuer=ISSUER, jwks_uri=JWKS_URI, audience=AUDIENCE)

        # get_signing_keys(refresh=True) is only allowed once per token
        # (the first cache-miss lookup), plus at most one forced refresh
        # shared across both requests -- not one forced refresh per
        # request, regardless of how many distinct kids were tried.
        refresh_calls = [
            call for call in mock_get_signing_keys.call_args_list
            if call.kwargs.get("refresh") or (call.args and call.args[0])
        ]
        self.assertLessEqual(len(refresh_calls), 1)

    def test_unknown_kid_refresh_cooldown_blocks_a_different_kid(self):
        """
        The forced-refresh cooldown is keyed only by jwks_uri, not by kid:
        a bogus `kid` arms a cooldown that also blocks a forced refresh for
        a *different* kid seen shortly after, even a legitimately rotated
        one. This is a deliberate tradeoff -- keying by kid would let an
        attacker force a fresh blocking JWKS fetch on every request just by
        varying the kid, which is a worse (unauthenticated DoS) outcome
        than briefly delaying visibility of a rotated key.
        """
        import tabpy.tabpy_server.handlers.jwt_auth as jwt_auth_module

        jwt_auth_module._jwks_clients.clear()
        jwt_auth_module._jwks_last_failed_refresh.clear()

        bogus_token = self._make_token(headers={"kid": "unknown-kid"})
        with patch(
            "tabpy.tabpy_server.handlers.jwt_auth.PyJWKClient.get_signing_keys",
            return_value=[],
        ):
            with self.assertRaises(JwtValidationError):
                validate_jwt(bogus_token, issuer=ISSUER, jwks_uri=JWKS_URI, audience=AUDIENCE)

        rotated_token = self._make_token(headers={"kid": "rotated-kid"})
        rotated_signing_key = type("SigningKey", (), {})()
        rotated_signing_key.key = self.private_key.public_key()
        rotated_signing_key.algorithm_name = "RS256"
        rotated_signing_key.key_id = "rotated-kid"

        with patch(
            "tabpy.tabpy_server.handlers.jwt_auth.PyJWKClient.get_signing_keys",
            side_effect=[[], [rotated_signing_key]],
        ) as mock_get_signing_keys:
            with self.assertRaises(JwtValidationError):
                validate_jwt(
                    rotated_token, issuer=ISSUER, jwks_uri=JWKS_URI, audience=AUDIENCE
                )
        # The forced refresh for "rotated-kid" must have been skipped due
        # to the cooldown armed by the bogus kid moments earlier.
        self.assertEqual(mock_get_signing_keys.call_count, 1)

    def test_failed_jwks_fetch_is_rate_limited(self):
        """
        A down/unreachable IdP must not be hammered with a fresh blocking
        fetch (see JWKS_FETCH_TIMEOUT_SECONDS) on every single request --
        that fetch runs directly on TabPy's single IO-loop thread. After
        one failed fetch, subsequent requests within
        JWKS_MIN_REFRESH_INTERVAL_SECONDS must fail fast without calling
        get_signing_keys again.
        """
        import tabpy.tabpy_server.handlers.jwt_auth as jwt_auth_module

        jwt_auth_module._jwks_clients.clear()
        jwt_auth_module._jwks_last_fetch_failure.clear()

        token = self._make_token()
        with patch(
            "tabpy.tabpy_server.handlers.jwt_auth.PyJWKClient.get_signing_keys",
            side_effect=jwt.exceptions.PyJWKClientError("Unable to fetch JWKS"),
        ) as mock_get_signing_keys:
            with self.assertRaises(JwtValidationError):
                validate_jwt(token, issuer=ISSUER, jwks_uri=JWKS_URI, audience=AUDIENCE)
            with self.assertRaises(JwtValidationError):
                validate_jwt(token, issuer=ISSUER, jwks_uri=JWKS_URI, audience=AUDIENCE)
        self.assertEqual(mock_get_signing_keys.call_count, 1)

    def test_hs256_substitution_using_public_key_is_rejected(self):
        """
        Guards against the classic RS256->HS256 confusion attack: an
        attacker who knows the RSA public key forges an HS256 token using
        that public key as the HMAC secret. This must be rejected because
        the algorithm is pinned to the JWKS-resolved key's own
        algorithm_name (RS256), never trusted from the token header.
        """
        public_pem = self.private_key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        now = datetime.datetime.now(datetime.timezone.utc)
        header = b64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
        payload = b64url(
            json.dumps(
                {
                    "iss": ISSUER,
                    "aud": AUDIENCE,
                    "sub": "attacker",
                    "iat": int(now.timestamp()),
                    "exp": int((now + datetime.timedelta(minutes=5)).timestamp()),
                }
            ).encode()
        )
        signing_input = f"{header}.{payload}".encode()
        signature = hmac.new(public_pem, signing_input, hashlib.sha256).digest()
        forged_token = f"{header}.{payload}.{b64url(signature)}"

        with self._patched_jwks_client():
            with self.assertRaises(JwtValidationError):
                validate_jwt(forged_token, issuer=ISSUER, jwks_uri=JWKS_URI, audience=AUDIENCE)

    def test_jwks_client_is_reused_for_same_uri(self):
        """
        _get_jwks_client must return the same PyJWKClient instance for
        repeat calls with the same jwks_uri, so PyJWKClient's own JWK Set
        cache (avoiding per-request JWKS fetches) is actually effective.
        """
        import tabpy.tabpy_server.handlers.jwt_auth as jwt_auth_module

        jwt_auth_module._jwks_clients.clear()
        first = jwt_auth_module._get_jwks_client(JWKS_URI)
        second = jwt_auth_module._get_jwks_client(JWKS_URI)
        self.assertIs(first, second)

    def test_validation_failure_does_not_log_raw_token(self):
        token = self._make_token({"iss": "https://wrong-idp.example.com/"})
        with self._patched_jwks_client():
            with self.assertLogs(
                "tabpy.tabpy_server.handlers.jwt_auth", level="ERROR"
            ) as log_ctx:
                with self.assertRaises(JwtValidationError):
                    validate_jwt(token, issuer=ISSUER, jwks_uri=JWKS_URI, audience=AUDIENCE)
        logged_text = " ".join(log_ctx.output)
        self.assertNotIn(token, logged_text)


if __name__ == "__main__":
    unittest.main()
