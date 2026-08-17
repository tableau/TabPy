import base64
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

    def _authenticate(self):
        return self.factory.start_call(
            None, self._headers(self._basic_header("user1", "P@ssw0rd"))
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

    def test_token_store_is_bounded(self):
        with patch.object(mod, "MAX_FLIGHT_TOKENS", 4):
            first = self._authenticate()
            for _ in range(20):
                latest = self._authenticate()

        self.assertLessEqual(len(self.factory.tokens), 4)
        self.assertNotIn(first.token, self.factory.tokens)
        self.assertTrue(self.factory.is_valid_token(latest.token))

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
