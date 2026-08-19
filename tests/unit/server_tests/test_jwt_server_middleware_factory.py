import base64
import datetime
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric import rsa
from pyarrow.flight import FlightUnauthenticatedError

from tabpy.tabpy_server.handlers.basic_auth_server_middleware_factory import (
    BasicAuthServerMiddleware,
    BasicAuthServerMiddlewareFactory,
)
from tabpy.tabpy_server.handlers.jwt_server_middleware_factory import (
    JwtAuthServerMiddleware,
    JwtAuthServerMiddlewareFactory,
)
from tabpy.tabpy_server.handlers.util import hash_password
from tests.unit.server_tests.jwt_test_helpers import (
    AUDIENCE,
    ISSUER,
    JWKS_URI,
    make_token,
    patched_jwks_client,
    reset_jwks_state,
)


class TestJwtServerMiddlewareFactory(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    def setUp(self):
        reset_jwks_state()
        self.factory = JwtAuthServerMiddlewareFactory(
            issuer=ISSUER, jwks_uri=JWKS_URI, audience=AUDIENCE
        )

    def _make_token(self, claims_override=None):
        return make_token(self.private_key, claims_override=claims_override)

    def _headers(self, authorization=None):
        if authorization is None:
            return {}
        return {"authorization": [authorization]}

    def _basic_header(self, username, password):
        encoded = base64.b64encode(f"{username}:{password}".encode()).decode()
        return f"Basic {encoded}"

    def test_valid_token_is_accepted(self):
        token = self._make_token()
        with patched_jwks_client(self.private_key):
            middleware = self.factory.start_call(
                None, self._headers(f"Bearer {token}")
            )
        self.assertIsInstance(middleware, JwtAuthServerMiddleware)
        self.assertEqual(middleware.claims["sub"], "user1")

    def test_expired_token_is_rejected(self):
        past = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
            hours=1
        )
        token = self._make_token(
            {"iat": past - datetime.timedelta(minutes=5), "exp": past}
        )
        with patched_jwks_client(self.private_key):
            with self.assertRaises(FlightUnauthenticatedError):
                self.factory.start_call(None, self._headers(f"Bearer {token}"))

    def test_wrong_issuer_is_rejected(self):
        token = self._make_token({"iss": "https://wrong-idp.example.com/"})
        with patched_jwks_client(self.private_key):
            with self.assertRaises(FlightUnauthenticatedError):
                self.factory.start_call(None, self._headers(f"Bearer {token}"))

    def test_wrong_audience_is_rejected(self):
        token = self._make_token({"aud": "wrong-audience"})
        with patched_jwks_client(self.private_key):
            with self.assertRaises(FlightUnauthenticatedError):
                self.factory.start_call(None, self._headers(f"Bearer {token}"))

    def test_missing_token_is_rejected(self):
        with self.assertRaises(FlightUnauthenticatedError) as err:
            self.factory.start_call(None, {})
        self.assertIn("No credentials supplied", str(err.exception))

    def test_empty_bearer_is_rejected(self):
        with self.assertRaises(FlightUnauthenticatedError):
            self.factory.start_call(None, self._headers("Bearer"))

    def test_bearer_with_extra_whitespace_is_rejected(self):
        token = self._make_token()
        with patched_jwks_client(self.private_key):
            with self.assertRaises(FlightUnauthenticatedError):
                self.factory.start_call(
                    None, self._headers(f"Bearer  {token}")
                )

    def test_unknown_scheme_is_rejected(self):
        with self.assertRaises(FlightUnauthenticatedError):
            self.factory.start_call(None, self._headers("Token abc"))

    def test_repeated_identical_authorization_value_is_accepted(self):
        token = self._make_token()
        headers = {"authorization": [f"Bearer {token}", f"Bearer {token}"]}
        with patched_jwks_client(self.private_key):
            middleware = self.factory.start_call(None, headers)
        self.assertIsInstance(middleware, JwtAuthServerMiddleware)

    def test_case_varied_identical_authorization_headers_are_accepted(self):
        token = self._make_token()
        headers = {
            "Authorization": [f"Bearer {token}"],
            "authorization": [f"Bearer {token}"],
        }
        with patched_jwks_client(self.private_key):
            middleware = self.factory.start_call(None, headers)
        self.assertIsInstance(middleware, JwtAuthServerMiddleware)

    def test_conflicting_authorization_values_are_rejected(self):
        token = self._make_token()
        headers = {
            "authorization": [f"Bearer {token}"],
            "Authorization": [self._basic_header("user1", "P@ssw0rd")],
        }
        with patched_jwks_client(self.private_key):
            with self.assertRaises(FlightUnauthenticatedError) as err:
                self.factory.start_call(None, headers)
        self.assertIn("No credentials supplied", str(err.exception))

    def test_unexpected_validation_error_is_unauthenticated(self):
        token = self._make_token()
        with patch(
            "tabpy.tabpy_server.handlers.jwt_server_middleware_factory.validate_jwt",
            side_effect=RuntimeError("boom"),
        ):
            with self.assertRaises(FlightUnauthenticatedError) as err:
                self.factory.start_call(None, self._headers(f"Bearer {token}"))
        self.assertIn("Invalid credentials", str(err.exception))

    def test_basic_is_rejected_when_no_basic_factory(self):
        with self.assertRaises(FlightUnauthenticatedError):
            self.factory.start_call(
                None, self._headers(self._basic_header("user1", "P@ssw0rd"))
            )

    def test_valid_basic_is_accepted_when_basic_factory_provided(self):
        creds = {"user1": hash_password("user1", "P@ssw0rd")}
        factory = JwtAuthServerMiddlewareFactory(
            issuer=ISSUER,
            jwks_uri=JWKS_URI,
            audience=AUDIENCE,
            basic_factory=BasicAuthServerMiddlewareFactory(creds),
        )
        middleware = factory.start_call(
            None, self._headers(self._basic_header("user1", "P@ssw0rd"))
        )
        self.assertIsInstance(middleware, BasicAuthServerMiddleware)

    def test_basic_issued_bearer_token_is_accepted_on_next_call(self):
        creds = {"user1": hash_password("user1", "P@ssw0rd")}
        basic_factory = BasicAuthServerMiddlewareFactory(creds)
        factory = JwtAuthServerMiddlewareFactory(
            issuer=ISSUER,
            jwks_uri=JWKS_URI,
            audience=AUDIENCE,
            basic_factory=basic_factory,
        )

        handshake = factory.start_call(
            None, self._headers(self._basic_header("user1", "P@ssw0rd"))
        )
        subsequent_call = factory.start_call(
            None, self._headers(f"Bearer {handshake.token}")
        )

        self.assertIsInstance(subsequent_call, BasicAuthServerMiddleware)
        self.assertEqual(subsequent_call.token, handshake.token)

    def test_lowercase_basic_is_accepted_when_basic_factory_provided(self):
        creds = {"user1": hash_password("user1", "P@ssw0rd")}
        factory = JwtAuthServerMiddlewareFactory(
            issuer=ISSUER,
            jwks_uri=JWKS_URI,
            audience=AUDIENCE,
            basic_factory=BasicAuthServerMiddlewareFactory(creds),
        )
        encoded = base64.b64encode(b"user1:P@ssw0rd").decode()
        middleware = factory.start_call(
            None, self._headers(f"basic {encoded}")
        )
        self.assertIsInstance(middleware, BasicAuthServerMiddleware)

    def test_invalid_basic_is_rejected_when_basic_factory_provided(self):
        creds = {"user1": hash_password("user1", "P@ssw0rd")}
        factory = JwtAuthServerMiddlewareFactory(
            issuer=ISSUER,
            jwks_uri=JWKS_URI,
            audience=AUDIENCE,
            basic_factory=BasicAuthServerMiddlewareFactory(creds),
        )
        with self.assertRaises(FlightUnauthenticatedError):
            factory.start_call(
                None,
                self._headers(self._basic_header("user1", "wrong_password")),
            )

    def test_invalid_base64_basic_is_unauthenticated(self):
        creds = {"user1": hash_password("user1", "P@ssw0rd")}
        factory = JwtAuthServerMiddlewareFactory(
            issuer=ISSUER,
            jwks_uri=JWKS_URI,
            audience=AUDIENCE,
            basic_factory=BasicAuthServerMiddlewareFactory(creds),
        )
        with self.assertRaises(FlightUnauthenticatedError) as err:
            factory.start_call(None, self._headers("Basic !!!not-base64!!!"))
        self.assertIn("Invalid credentials", str(err.exception))

    def test_invalid_utf8_basic_is_unauthenticated(self):
        creds = {"user1": hash_password("user1", "P@ssw0rd")}
        factory = JwtAuthServerMiddlewareFactory(
            issuer=ISSUER,
            jwks_uri=JWKS_URI,
            audience=AUDIENCE,
            basic_factory=BasicAuthServerMiddlewareFactory(creds),
        )
        encoded = base64.b64encode(b"\xff\xfe").decode()
        with self.assertRaises(FlightUnauthenticatedError) as err:
            factory.start_call(None, self._headers(f"Basic {encoded}"))
        self.assertIn("Invalid credentials", str(err.exception))

    def test_basic_without_password_separator_is_unauthenticated(self):
        creds = {"user1": hash_password("user1", "P@ssw0rd")}
        factory = JwtAuthServerMiddlewareFactory(
            issuer=ISSUER,
            jwks_uri=JWKS_URI,
            audience=AUDIENCE,
            basic_factory=BasicAuthServerMiddlewareFactory(creds),
        )
        encoded = base64.b64encode(b"user1").decode()
        with self.assertRaises(FlightUnauthenticatedError) as err:
            factory.start_call(None, self._headers(f"Basic {encoded}"))
        self.assertIn("Invalid credentials", str(err.exception))
