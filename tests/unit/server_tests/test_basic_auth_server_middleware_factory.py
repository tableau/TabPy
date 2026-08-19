import base64
import time
import unittest
from unittest.mock import patch

from pyarrow.flight import FlightUnauthenticatedError

from tabpy.tabpy_server.handlers import basic_auth_server_middleware_factory as mod
from tabpy.tabpy_server.handlers.basic_auth_server_middleware_factory import (
    BasicAuthServerMiddleware,
    BasicAuthServerMiddlewareFactory,
)
from tabpy.tabpy_server.handlers.util import hash_password


class TestBasicAuthServerMiddlewareFactory(unittest.TestCase):
    def setUp(self):
        creds = {"user1": hash_password("user1", "P@ssw0rd")}
        self.factory = BasicAuthServerMiddlewareFactory(creds)

    def _headers(self, authorization=None):
        if authorization is None:
            return {}
        return {"authorization": [authorization]}

    def _basic_header(self, username, password):
        encoded = base64.b64encode(f"{username}:{password}".encode()).decode()
        return f"Basic {encoded}"

    def _authenticate(self, username="user1", password="P@ssw0rd", factory=None):
        target = factory or self.factory
        return target.start_call(
            None, self._headers(self._basic_header(username, password))
        )

    def test_valid_basic_is_accepted(self):
        middleware = self._authenticate()
        self.assertIsInstance(middleware, BasicAuthServerMiddleware)
        self.assertEqual(
            middleware.sending_headers(),
            {"authorization": f"Bearer {middleware.token}"},
        )

    def test_issued_token_records_the_username(self):
        middleware = self._authenticate()
        username, _ = self.factory.tokens[middleware.token]
        self.assertEqual(username, "user1")

    def test_basic_username_is_case_insensitive(self):
        middleware = self._authenticate(username="UsEr1")
        username, _ = self.factory.tokens[middleware.token]
        self.assertEqual(username, "user1")

    def test_invalid_password_is_rejected(self):
        with self.assertRaises(FlightUnauthenticatedError):
            self.factory.start_call(
                None, self._headers(self._basic_header("user1", "wrong"))
            )

    def test_missing_credentials_are_rejected(self):
        with self.assertRaises(FlightUnauthenticatedError):
            self.factory.start_call(None, {})

    def test_issued_token_is_accepted_on_the_next_call(self):
        handshake = self._authenticate()
        subsequent_call = self.factory.start_call(
            None, self._headers(f"Bearer {handshake.token}")
        )
        self.assertEqual(subsequent_call.token, handshake.token)
        self.assertEqual(len(self.factory.tokens), 1)

    def test_unknown_bearer_token_is_rejected(self):
        with self.assertRaises(FlightUnauthenticatedError):
            self.factory.start_call(None, self._headers("Bearer not-a-real-token"))

    def test_jwt_shaped_bearer_is_rejected_without_oauth(self):
        with self.assertRaises(FlightUnauthenticatedError):
            self.factory.start_call(
                None, self._headers("Bearer header.payload.signature")
            )

    def test_expired_token_is_rejected(self):
        with patch.object(mod, "FLIGHT_TOKEN_TTL_SECONDS", -1):
            handshake = self._authenticate()
        self.assertFalse(self.factory.is_valid_token(handshake.token))
        with self.assertRaises(FlightUnauthenticatedError):
            self.factory.start_call(None, self._headers(f"Bearer {handshake.token}"))

    def test_expired_tokens_are_evicted_on_the_next_mint(self):
        with patch.object(mod, "FLIGHT_TOKEN_TTL_SECONDS", -1):
            expired = self._authenticate()
        self._authenticate()
        self.assertNotIn(expired.token, self.factory.tokens)

    def test_repeated_basic_auth_reuses_one_unexpired_token_per_user(self):
        first = self._authenticate()
        first_expiry = self.factory.tokens[first.token][1]
        for _ in range(20):
            latest = self._authenticate()

        self.assertEqual(latest.token, first.token)
        self.assertEqual(self.factory.tokens[first.token][1], first_expiry)
        self.assertEqual(len(self.factory.tokens), 1)
        self.assertTrue(self.factory.is_valid_token(first.token))

    def test_basic_auth_rotates_a_token_near_expiry(self):
        first = self._authenticate()
        username, _ = self.factory.tokens[first.token]
        self.factory.tokens[first.token] = (
            username,
            time.monotonic() + mod.FLIGHT_TOKEN_RENEWAL_WINDOW_SECONDS - 1,
        )

        renewed = self._authenticate()

        self.assertNotEqual(renewed.token, first.token)
        self.assertTrue(self.factory.is_valid_token(first.token))
        self.assertTrue(self.factory.is_valid_token(renewed.token))
        self.assertEqual(len(self.factory.tokens), 2)
        remaining = self.factory.tokens[renewed.token][1] - time.monotonic()
        self.assertGreater(remaining, mod.FLIGHT_TOKEN_TTL_SECONDS - 1)

    def test_token_overlap_is_bounded_per_username(self):
        latest = self._authenticate()
        issued_tokens = [latest.token]

        for _ in range(3):
            username, _ = self.factory.tokens[latest.token]
            self.factory.tokens[latest.token] = (
                username,
                time.monotonic() + mod.FLIGHT_TOKEN_RENEWAL_WINDOW_SECONDS - 1,
            )
            latest = self._authenticate()
            issued_tokens.append(latest.token)

        self.assertEqual(len(self.factory.tokens), 2)
        self.assertNotIn(issued_tokens[0], self.factory.tokens)
        self.assertTrue(self.factory.is_valid_token(issued_tokens[-2]))
        self.assertTrue(self.factory.is_valid_token(issued_tokens[-1]))

    def test_tied_expiries_evict_oldest_issued_token(self):
        first = self._authenticate()
        username, _ = self.factory.tokens[first.token]
        near_expiry = (
            time.monotonic() + mod.FLIGHT_TOKEN_RENEWAL_WINDOW_SECONDS - 1
        )
        self.factory.tokens[first.token] = (username, near_expiry)
        second = self._authenticate()
        self.factory.tokens[first.token] = (username, near_expiry)
        self.factory.tokens[second.token] = (username, near_expiry)

        third = self._authenticate()

        self.assertNotIn(first.token, self.factory.tokens)
        self.assertTrue(self.factory.is_valid_token(second.token))
        self.assertTrue(self.factory.is_valid_token(third.token))

    def test_other_users_cannot_evict_an_unexpired_token(self):
        creds = {
            "user1": hash_password("user1", "P@ssw0rd"),
            "user2": hash_password("user2", "OtherP@ssw0rd"),
        }
        factory = BasicAuthServerMiddlewareFactory(creds)
        first = self._authenticate(factory=factory)

        for _ in range(20):
            second = self._authenticate(
                username="user2",
                password="OtherP@ssw0rd",
                factory=factory,
            )

        self.assertEqual(len(factory.tokens), 2)
        self.assertTrue(factory.is_valid_token(first.token))
        self.assertTrue(factory.is_valid_token(second.token))

    def test_invalid_base64_is_unauthenticated(self):
        with self.assertRaises(FlightUnauthenticatedError) as err:
            self.factory.start_call(None, self._headers("Basic !!!not-base64!!!"))
        self.assertIn("Invalid credentials", str(err.exception))

    def test_invalid_utf8_is_unauthenticated(self):
        encoded = base64.b64encode(b"\xff\xfe").decode()
        with self.assertRaises(FlightUnauthenticatedError) as err:
            self.factory.start_call(None, self._headers(f"Basic {encoded}"))
        self.assertIn("Invalid credentials", str(err.exception))

    def test_missing_password_separator_is_unauthenticated(self):
        encoded = base64.b64encode(b"user1").decode()
        with self.assertRaises(FlightUnauthenticatedError) as err:
            self.factory.start_call(None, self._headers(f"Basic {encoded}"))
        self.assertIn("Invalid credentials", str(err.exception))

    def test_conflicting_authorization_values_are_rejected(self):
        headers = {
            "authorization": [self._basic_header("user1", "P@ssw0rd")],
            "Authorization": [self._basic_header("user1", "wrong")],
        }
        with self.assertRaises(FlightUnauthenticatedError):
            self.factory.start_call(None, headers)


if __name__ == "__main__":
    unittest.main()
