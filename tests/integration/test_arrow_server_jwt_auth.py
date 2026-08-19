import contextlib
import threading
import unittest

from cryptography.hazmat.primitives.asymmetric import rsa
import pyarrow.flight

from tabpy.tabpy_server.app.arrow_server import FlightServer
from tabpy.tabpy_server.handlers.jwt_server_middleware_factory import (
    JwtAuthServerMiddlewareFactory,
)
from tabpy.tabpy_server.handlers.no_op_auth_handler import NoOpAuthHandler
from tests.unit.server_tests.jwt_test_helpers import (
    AUDIENCE,
    ISSUER,
    JWKS_URI,
    make_token,
    patched_jwks_client,
    reset_jwks_state,
)


class TestArrowServerJwtAuth(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.private_key = rsa.generate_private_key(
            public_exponent=65537, key_size=2048
        )

    def setUp(self):
        reset_jwks_state()

    @contextlib.contextmanager
    def _server_and_client(self, required_scopes=None):
        middleware = JwtAuthServerMiddlewareFactory(
            issuer=ISSUER,
            jwks_uri=JWKS_URI,
            audience=AUDIENCE,
            required_scopes=required_scopes,
        )
        server = FlightServer(
            host="localhost",
            location="grpc+tcp://localhost:0",
            auth_handler=NoOpAuthHandler(),
            middleware={"jwt": middleware},
        )
        server_thread = threading.Thread(target=server.serve, daemon=True)
        server_thread.start()
        client = pyarrow.flight.FlightClient(
            f"grpc+tcp://localhost:{server.port}"
        )
        try:
            yield client
        finally:
            server.shutdown()
            server_thread.join(5)

    def _options(self, token):
        return pyarrow.flight.FlightCallOptions(
            headers=[(b"authorization", f"Bearer {token}".encode())]
        )

    def test_valid_jwt_authenticates_through_flight_transport(self):
        token = make_token(self.private_key)

        with self._server_and_client() as client, patched_jwks_client(
            self.private_key
        ):
            actions = list(client.list_actions(options=self._options(token)))

        self.assertTrue(actions)

    def test_invalid_jwt_is_rejected_by_flight_transport(self):
        invalid_token = make_token(
            self.private_key, claims_override={"aud": "wrong-audience"}
        )

        with self._server_and_client() as client, patched_jwks_client(
            self.private_key
        ):
            with self.assertRaises(pyarrow.flight.FlightUnauthenticatedError):
                list(client.list_actions(options=self._options(invalid_token)))

    def test_required_scope_is_enforced_through_flight_transport(self):
        allowed = make_token(
            self.private_key, claims_override={"scope": "read execute"}
        )
        denied = make_token(
            self.private_key, claims_override={"scope": "read"}
        )

        with self._server_and_client(
            required_scopes="execute"
        ) as client, patched_jwks_client(self.private_key):
            self.assertTrue(
                list(client.list_actions(options=self._options(allowed)))
            )
            with self.assertRaises(pyarrow.flight.FlightUnauthenticatedError):
                list(client.list_actions(options=self._options(denied)))


if __name__ == "__main__":
    unittest.main()
