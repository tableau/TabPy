import base64
import datetime
import hmac
import hashlib
import json
import threading
import time
import unittest
from unittest.mock import patch

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from tabpy.tabpy_server.handlers.jwt_auth import (
    SCOPE_DEPLOY,
    SCOPE_EVALUATE,
    SCOPE_QUERY,
    JwtValidationError,
    endpoint_scope_for_path,
    endpoint_scope_names,
    token_has_scope,
    validate_jwt,
)
from tests.unit.server_tests.jwt_test_helpers import (
    AUDIENCE,
    ISSUER,
    JWKS_URI,
    make_token,
    patched_jwks_client,
    reset_jwks_state,
)


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


class TestJwtAuth(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    def setUp(self):
        reset_jwks_state()

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
        TabPy's HTTP path serves requests on a single IO-loop thread, so
        the JWKS HTTP client must not be allowed to hang indefinitely on a
        slow/unreachable IdP -- that would stall concurrent HTTP requests.
        Arrow Flight auth shares the same client on the gRPC thread pool.
        """
        import tabpy.tabpy_server.handlers.jwt_auth as jwt_auth_module

        reset_jwks_state()
        client = jwt_auth_module._get_jwks_client(JWKS_URI)
        self.assertEqual(client.timeout, jwt_auth_module.JWKS_FETCH_TIMEOUT_SECONDS)
        self.assertEqual(
            client.jwk_set_cache.lifespan,
            jwt_auth_module.JWKS_CACHE_LIFESPAN_SECONDS,
        )
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
        a blocking network call (HTTP IO-loop or a Flight gRPC thread). The
        cooldown is keyed only by jwks_uri (not by kid, since kid is
        attacker-controlled pre-signature-check): only one forced refresh
        per jwks_uri is allowed within JWKS_MIN_REFRESH_INTERVAL_SECONDS,
        no matter how many distinct bogus kids are tried.
        """
        reset_jwks_state()

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
        reset_jwks_state()

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

    def test_unknown_kid_refresh_recovers_after_cooldown_expires(self):
        import tabpy.tabpy_server.handlers.jwt_auth as jwt_auth_module

        cached_token = self._make_token(headers={"kid": "cached-kid"})
        with self._patched_jwks_client(kid="cached-kid"):
            validate_jwt(
                cached_token, issuer=ISSUER, jwks_uri=JWKS_URI, audience=AUDIENCE
            )

        jwt_auth_module._jwks_last_failed_refresh[JWKS_URI] = (
            time.monotonic()
            - jwt_auth_module.JWKS_MIN_REFRESH_INTERVAL_SECONDS
            - 1
        )
        rotated_token = self._make_token(headers={"kid": "rotated-kid"})
        rotated_signing_key = self._signing_key(kid="rotated-kid")

        with patch(
            "tabpy.tabpy_server.handlers.jwt_auth.PyJWKClient.get_signing_keys",
            return_value=[rotated_signing_key],
        ) as mock_get_signing_keys:
            claims = validate_jwt(
                rotated_token,
                issuer=ISSUER,
                jwks_uri=JWKS_URI,
                audience=AUDIENCE,
            )

        self.assertEqual(claims["sub"], "user1")
        mock_get_signing_keys.assert_called_once_with(refresh=True)

    def test_failed_jwks_fetch_is_rate_limited(self):
        """
        A down/unreachable IdP must not be hammered with a fresh blocking
        fetch (see JWKS_FETCH_TIMEOUT_SECONDS) on every single request --
        that fetch blocks the HTTP IO-loop or a Flight gRPC thread. After
        one failed fetch, subsequent requests within
        JWKS_MIN_REFRESH_INTERVAL_SECONDS must fail fast without calling
        get_signing_keys again.
        """
        reset_jwks_state()

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

    def test_empty_cooldown_store_is_not_recent_just_after_host_boot(self):
        """
        time.monotonic() is host-uptime based. An absent entry must not use
        zero as a timestamp or JWT auth fails during the first cooldown
        interval after a host boot.
        """
        import tabpy.tabpy_server.handlers.jwt_auth as jwt_auth_module

        store = {}
        with patch(
            "tabpy.tabpy_server.handlers.jwt_auth.time.monotonic",
            return_value=12,
        ):
            self.assertFalse(
                jwt_auth_module._recently_recorded(store, JWKS_URI)
            )
            jwt_auth_module._record_now(store, JWKS_URI)
            self.assertTrue(
                jwt_auth_module._recently_recorded(store, JWKS_URI)
            )

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

    def _signing_key(self, kid=None):
        signing_key = type("SigningKey", (), {})()
        signing_key.key = self.private_key.public_key()
        signing_key.algorithm_name = "RS256"
        signing_key.key_id = kid
        return signing_key

    def test_cached_key_lookup_does_not_wait_on_a_refresh(self):
        """
        A forged unknown kid can start a per-URI JWKS refresh. Valid tokens
        that already have a cached key must still validate while that
        refresh is in flight, instead of being rejected behind the lock.
        """
        import tabpy.tabpy_server.handlers.jwt_auth as jwt_auth_module

        token = self._make_token()
        with self._patched_jwks_client():
            validate_jwt(token, issuer=ISSUER, jwks_uri=JWKS_URI, audience=AUDIENCE)

        fetch_lock = jwt_auth_module._fetch_lock_for(JWKS_URI)
        acquired = threading.Event()
        release = threading.Event()

        def hold_refresh():
            with fetch_lock:
                acquired.set()
                release.wait(10)

        holder = threading.Thread(target=hold_refresh)
        holder.start()
        try:
            self.assertTrue(acquired.wait(5))
            started = time.monotonic()
            claims = validate_jwt(
                token, issuer=ISSUER, jwks_uri=JWKS_URI, audience=AUDIENCE
            )
            elapsed = time.monotonic() - started
        finally:
            release.set()
            holder.join()

        self.assertEqual(claims["sub"], "user1")
        self.assertLess(elapsed, 1)

    def test_in_flight_fetch_only_blocks_refresh_for_bounded_time(self):
        """
        A forced refresh may wait briefly for the per-URI fetch owner, but
        must not wait for the full outbound JWKS timeout.
        """
        import tabpy.tabpy_server.handlers.jwt_auth as jwt_auth_module

        warm_token = self._make_token()
        with self._patched_jwks_client():
            validate_jwt(
                warm_token, issuer=ISSUER, jwks_uri=JWKS_URI, audience=AUDIENCE
            )

        token = self._make_token(headers={"kid": "unknown-kid"})
        fetch_lock = jwt_auth_module._fetch_lock_for(JWKS_URI)
        acquired = threading.Event()
        release = threading.Event()

        def hold_refresh():
            with fetch_lock:
                acquired.set()
                release.wait(10)

        holder = threading.Thread(target=hold_refresh)
        holder.start()
        try:
            self.assertTrue(acquired.wait(5))
            started = time.monotonic()
            with patch.object(
                jwt_auth_module, "JWKS_REFRESH_WAIT_SECONDS", 0.05
            ):
                with self.assertRaises(JwtValidationError):
                    validate_jwt(
                        token,
                        issuer=ISSUER,
                        jwks_uri=JWKS_URI,
                        audience=AUDIENCE,
                    )
            elapsed = time.monotonic() - started
        finally:
            release.set()
            holder.join()

        self.assertLess(elapsed, 1)

    def test_concurrent_cold_cache_performs_one_jwks_fetch(self):
        """
        Concurrent cache-cold validations for the same jwks_uri must
        single-flight one outbound JWKS fetch, then reuse that snapshot.
        """
        token = self._make_token()
        signing_key = self._signing_key()
        started = threading.Event()
        release = threading.Event()
        call_count = []
        count_lock = threading.Lock()

        def fake_get_signing_keys(refresh=False):
            with count_lock:
                call_count.append(refresh)
            started.set()
            self.assertTrue(release.wait(5))
            return [signing_key]

        workers = 8
        barrier = threading.Barrier(workers)
        results = []
        errors = []

        def worker():
            try:
                barrier.wait(5)
                claims = validate_jwt(
                    token, issuer=ISSUER, jwks_uri=JWKS_URI, audience=AUDIENCE
                )
                results.append(claims)
            except Exception as ex:
                errors.append(ex)

        with patch(
            "tabpy.tabpy_server.handlers.jwt_auth.PyJWKClient.get_signing_keys",
            side_effect=fake_get_signing_keys,
        ):
            threads = [threading.Thread(target=worker) for _ in range(workers)]
            for thread in threads:
                thread.start()
            self.assertTrue(started.wait(5))
            time.sleep(0.1)
            release.set()
            for thread in threads:
                thread.join(5)

        self.assertEqual(errors, [])
        self.assertEqual(len(results), workers)
        self.assertEqual(call_count, [False])

    def test_concurrent_expired_cache_performs_one_jwks_fetch(self):
        """
        Concurrent lookups against an expired snapshot must also
        single-flight one outbound JWKS fetch per URI.
        """
        import tabpy.tabpy_server.handlers.jwt_auth as jwt_auth_module

        token = self._make_token()
        with self._patched_jwks_client():
            validate_jwt(token, issuer=ISSUER, jwks_uri=JWKS_URI, audience=AUDIENCE)

        keys, _fetched_at = jwt_auth_module._jwks_cached_keys[JWKS_URI]
        jwt_auth_module._jwks_cached_keys[JWKS_URI] = (
            keys,
            time.monotonic() - jwt_auth_module.JWKS_CACHE_LIFESPAN_SECONDS - 1,
        )

        signing_key = self._signing_key()
        started = threading.Event()
        release = threading.Event()
        call_count = []
        count_lock = threading.Lock()

        def fake_get_signing_keys(refresh=False):
            with count_lock:
                call_count.append(refresh)
            started.set()
            self.assertTrue(release.wait(5))
            return [signing_key]

        workers = 8
        barrier = threading.Barrier(workers)
        results = []
        errors = []

        def worker():
            try:
                barrier.wait(5)
                claims = validate_jwt(
                    token, issuer=ISSUER, jwks_uri=JWKS_URI, audience=AUDIENCE
                )
                results.append(claims)
            except Exception as ex:
                errors.append(ex)

        with patch(
            "tabpy.tabpy_server.handlers.jwt_auth.PyJWKClient.get_signing_keys",
            side_effect=fake_get_signing_keys,
        ):
            threads = [threading.Thread(target=worker) for _ in range(workers)]
            for thread in threads:
                thread.start()
            self.assertTrue(started.wait(5))
            time.sleep(0.1)
            release.set()
            for thread in threads:
                thread.join(5)

        self.assertEqual(errors, [])
        self.assertEqual(len(results), workers)
        self.assertEqual(call_count, [False])

    def test_unknown_kid_refresh_and_cooldown_publication_are_atomic(self):
        """
        Pause the first caller after its refresh returns but before the
        unknown-kid result is published. A second caller must not fetch in
        that window, and the cooldown must be recorded before lock release.
        """
        import tabpy.tabpy_server.handlers.jwt_auth as jwt_auth_module

        cached_token = self._make_token(headers={"kid": "cached-kid"})
        with self._patched_jwks_client(kid="cached-kid"):
            validate_jwt(
                cached_token, issuer=ISSUER, jwks_uri=JWKS_URI, audience=AUDIENCE
            )

        unknown = self._make_token(headers={"kid": "unknown-kid"})
        refreshed_key = self._signing_key(kid="the-real-kid")
        fetch_returned = threading.Event()
        first_matching = threading.Event()
        release_first = threading.Event()
        second_finished = threading.Event()
        refresh_calls = []
        outcomes = []
        errors = []
        record_lock_states = []
        fetch_lock = jwt_auth_module._fetch_lock_for(JWKS_URI)
        original_match_kid = jwt_auth_module.PyJWKClient.match_kid
        original_record_now = jwt_auth_module._record_now

        def fake_get_signing_keys(refresh=False):
            refresh_calls.append(refresh)
            fetch_returned.set()
            return [refreshed_key]

        def gated_match_kid(signing_keys, kid):
            if (
                threading.current_thread() is first_thread
                and fetch_returned.is_set()
                and not first_matching.is_set()
            ):
                first_matching.set()
                self.assertTrue(release_first.wait(5))
            return original_match_kid(signing_keys, kid)

        def checked_record_now(store, uri):
            if store is jwt_auth_module._jwks_last_failed_refresh:
                record_lock_states.append(fetch_lock.locked())
            return original_record_now(store, uri)

        def validate_unknown(label):
            try:
                validate_jwt(
                    unknown, issuer=ISSUER, jwks_uri=JWKS_URI, audience=AUDIENCE
                )
            except JwtValidationError:
                outcomes.append(label)
            except Exception as ex:
                errors.append(ex)

        first_thread = threading.Thread(
            target=validate_unknown, args=("first",)
        )

        def run_second():
            validate_unknown("second")
            second_finished.set()

        second_thread = threading.Thread(target=run_second)

        with patch(
            "tabpy.tabpy_server.handlers.jwt_auth.PyJWKClient.get_signing_keys",
            side_effect=fake_get_signing_keys,
        ), patch.object(
            jwt_auth_module.PyJWKClient,
            "match_kid",
            side_effect=gated_match_kid,
        ), patch(
            "tabpy.tabpy_server.handlers.jwt_auth._record_now",
            side_effect=checked_record_now,
        ):
            first_thread.start()
            self.assertTrue(first_matching.wait(5))

            second_thread.start()
            self.assertFalse(second_finished.wait(0.05))
            self.assertEqual(refresh_calls, [True])

            release_first.set()
            self.assertTrue(second_finished.wait(5))
            first_thread.join(5)
            second_thread.join(5)

            # Once the first caller releases the lock, a later unknown-kid
            # request must observe the published cooldown without fetching.
            validate_unknown("third")

        self.assertFalse(first_thread.is_alive())
        self.assertFalse(second_thread.is_alive())
        self.assertEqual(errors, [])
        self.assertCountEqual(outcomes, ["first", "second", "third"])
        self.assertEqual(refresh_calls, [True])
        self.assertEqual(record_lock_states, [True])

    def test_concurrent_requests_for_new_kid_share_one_refresh(self):
        """
        Requests for the same newly rotated kid wait briefly for one
        refresh owner, then all validate against the published snapshot.
        """
        import tabpy.tabpy_server.handlers.jwt_auth as jwt_auth_module

        cached_token = self._make_token(headers={"kid": "cached-kid"})
        with self._patched_jwks_client(kid="cached-kid"):
            validate_jwt(
                cached_token, issuer=ISSUER, jwks_uri=JWKS_URI, audience=AUDIENCE
            )

        rotated_private_key = rsa.generate_private_key(
            public_exponent=65537, key_size=2048
        )
        rotated_token = make_token(
            rotated_private_key, headers={"kid": "rotated-kid"}
        )
        refreshed_key = type("SigningKey", (), {})()
        refreshed_key.key = rotated_private_key.public_key()
        refreshed_key.algorithm_name = "RS256"
        refreshed_key.key_id = "rotated-kid"

        workers = 8
        barrier = threading.Barrier(workers)
        all_refresh_callers_entered = threading.Event()
        refresh_callers = 0
        refresh_callers_lock = threading.Lock()
        refresh_calls = []
        results = []
        errors = []
        original_refresh = jwt_auth_module._refresh_signing_key

        def fake_get_signing_keys(refresh=False):
            refresh_calls.append(refresh)
            self.assertTrue(all_refresh_callers_entered.wait(5))
            return [refreshed_key]

        def counted_refresh(*args):
            nonlocal refresh_callers
            with refresh_callers_lock:
                refresh_callers += 1
                if refresh_callers == workers:
                    all_refresh_callers_entered.set()
            return original_refresh(*args)

        def worker():
            try:
                barrier.wait(5)
                claims = validate_jwt(
                    rotated_token,
                    issuer=ISSUER,
                    jwks_uri=JWKS_URI,
                    audience=AUDIENCE,
                )
                results.append(claims)
            except Exception as ex:
                errors.append(ex)

        with patch(
            "tabpy.tabpy_server.handlers.jwt_auth.PyJWKClient.get_signing_keys",
            side_effect=fake_get_signing_keys,
        ), patch.object(
            jwt_auth_module,
            "_refresh_signing_key",
            side_effect=counted_refresh,
        ), patch.object(
            jwt_auth_module,
            "JWKS_REFRESH_WAIT_SECONDS",
            5,
        ):
            threads = [threading.Thread(target=worker) for _ in range(workers)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(5)

        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual(errors, [])
        self.assertEqual(len(results), workers)
        self.assertTrue(all(claims["sub"] == "user1" for claims in results))
        self.assertEqual(refresh_calls, [True])

    def test_jwks_client_is_reused_for_same_uri(self):
        """
        _get_jwks_client must return the same PyJWKClient instance for
        repeat calls with the same jwks_uri, so PyJWKClient's own JWK Set
        cache (avoiding per-request JWKS fetches) is actually effective.
        """
        import tabpy.tabpy_server.handlers.jwt_auth as jwt_auth_module

        reset_jwks_state()
        first = jwt_auth_module._get_jwks_client(JWKS_URI)
        second = jwt_auth_module._get_jwks_client(JWKS_URI)
        self.assertIs(first, second)

    def test_validation_failure_does_not_expose_raw_token(self):
        token = self._make_token({"iss": "https://wrong-idp.example.com/"})
        with self._patched_jwks_client():
            with self.assertRaises(JwtValidationError) as error:
                validate_jwt(
                    token, issuer=ISSUER, jwks_uri=JWKS_URI, audience=AUDIENCE
                )
        self.assertNotIn(token, str(error.exception))


class TestEndpointScopeHelpers(unittest.TestCase):
    def test_token_has_scope_reads_space_separated_claim(self):
        claims = {"scope": "tabpy:query tabpy:evaluate"}
        self.assertTrue(token_has_scope(claims, SCOPE_QUERY))
        self.assertTrue(token_has_scope(claims, SCOPE_EVALUATE))
        self.assertFalse(token_has_scope(claims, "tabpy:deploy"))

    def test_token_has_scope_fails_closed_for_non_string_claim(self):
        self.assertFalse(
            token_has_scope({"scope": ["tabpy:query"]}, SCOPE_QUERY)
        )

    def test_endpoint_scope_for_path_maps_query_and_evaluate(self):
        self.assertEqual(endpoint_scope_for_path("/query/add"), SCOPE_QUERY)
        self.assertEqual(
            endpoint_scope_for_path("/query/add", method="POST"), SCOPE_QUERY
        )
        self.assertEqual(endpoint_scope_for_path("/evaluate"), SCOPE_EVALUATE)
        self.assertIsNone(endpoint_scope_for_path("/info"))
        self.assertIsNone(endpoint_scope_for_path("/status"))
        self.assertIsNone(endpoint_scope_for_path("/endpoints"))
        self.assertIsNone(endpoint_scope_for_path("/endpoints/add"))

    def test_endpoint_scope_for_path_maps_mutating_management_to_deploy(self):
        self.assertEqual(
            endpoint_scope_for_path("/endpoints", method="POST"), SCOPE_DEPLOY
        )
        self.assertEqual(
            endpoint_scope_for_path("/endpoints/add", method="PUT"), SCOPE_DEPLOY
        )
        self.assertEqual(
            endpoint_scope_for_path("/endpoints/add", method="DELETE"), SCOPE_DEPLOY
        )
        self.assertEqual(
            endpoint_scope_for_path(
                "/configurations/endpoint_upload_destination", method="GET"
            ),
            SCOPE_DEPLOY,
        )
        self.assertIsNone(
            endpoint_scope_for_path("/endpoints/add", method="GET")
        )

    def test_endpoint_scope_for_path_honors_subdirectory(self):
        self.assertEqual(
            endpoint_scope_for_path("/tabpy/query/add", "/tabpy"), SCOPE_QUERY
        )
        self.assertEqual(
            endpoint_scope_for_path("/tabpy/evaluate", "/tabpy"), SCOPE_EVALUATE
        )
        self.assertIsNone(endpoint_scope_for_path("/tabpy/info", "/tabpy"))
        self.assertEqual(
            endpoint_scope_for_path(
                "/tabpy/endpoints/add", "/tabpy", method="DELETE"
            ),
            SCOPE_DEPLOY,
        )
        self.assertIsNone(
            endpoint_scope_for_path(
                "/tabpy/endpoints/add", "/tabpy", method="GET"
            )
        )

    def test_endpoint_scope_names_can_be_overridden(self):
        overrides = {
            SCOPE_QUERY: "tabpy/query",
            SCOPE_EVALUATE: "tabpy/evaluate",
            SCOPE_DEPLOY: "tabpy/deploy",
        }
        self.assertEqual(
            endpoint_scope_names(overrides),
            ("tabpy/query", "tabpy/evaluate", "tabpy/deploy"),
        )
        self.assertEqual(
            endpoint_scope_for_path(
                "/query/model", method="POST", scope_overrides=overrides
            ),
            "tabpy/query",
        )
        self.assertEqual(
            endpoint_scope_for_path(
                "/endpoints/model", method="DELETE", scope_overrides=overrides
            ),
            "tabpy/deploy",
        )
        self.assertEqual(
            endpoint_scope_for_path(
                "/query/model", scope_overrides={SCOPE_QUERY: ""}
            ),
            SCOPE_QUERY,
        )


if __name__ == "__main__":
    unittest.main()
