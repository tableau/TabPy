import logging

from pyarrow.flight import FlightUnauthenticatedError
from pyarrow.flight import ServerMiddleware, ServerMiddlewareFactory

from tabpy.tabpy_server.handlers.flight_headers import (
    get_flight_authorization_header,
)
from tabpy.tabpy_server.handlers.jwt_auth import JwtValidationError, validate_jwt

logger = logging.getLogger(__name__)


class JwtAuthServerMiddleware(ServerMiddleware):
    def __init__(self, claims):
        self.claims = claims


class JwtAuthServerMiddlewareFactory(ServerMiddlewareFactory):
    """
    Arrow Flight middleware that validates JWT Bearer tokens via
    jwt_auth.validate_jwt. When a Basic-auth factory is provided, Basic
    credentials are delegated to it so both methods can coexist on Flight.
    """

    def __init__(
        self,
        issuer,
        jwks_uri,
        audience,
        required_scopes=None,
        basic_factory=None,
    ):
        self.issuer = issuer
        self.jwks_uri = jwks_uri
        self.audience = audience
        self.required_scopes = required_scopes
        self.basic_factory = basic_factory

    def start_call(self, info, headers):
        auth_header = get_flight_authorization_header(headers)
        if not auth_header:
            raise FlightUnauthenticatedError("No credentials supplied")

        # Match HTTP: exactly two Authorization parts (scheme + value).
        parts = auth_header.split(" ")
        if len(parts) != 2:
            raise FlightUnauthenticatedError("No credentials supplied")
        auth_type, value = parts

        if auth_type.lower() == "bearer":
            if (
                self.basic_factory is not None
                and self.basic_factory.is_valid_token(value)
            ):
                return self.basic_factory.start_call(info, headers)

            try:
                claims = validate_jwt(
                    value,
                    issuer=self.issuer,
                    jwks_uri=self.jwks_uri,
                    audience=self.audience,
                    required_scopes=self.required_scopes,
                )
            except JwtValidationError as ex:
                logger.log(
                    logging.ERROR, f"Flight JWT authentication failed: {ex}"
                )
                raise FlightUnauthenticatedError("Invalid credentials") from ex
            except Exception as ex:
                # Must surface as UNAUTHENTICATED, not an ArrowInvalid
                # carrying a traceback back to an unauthenticated caller.
                logger.log(
                    logging.ERROR,
                    f"Unexpected error validating Flight JWT: {ex}",
                )
                raise FlightUnauthenticatedError("Invalid credentials") from ex
            return JwtAuthServerMiddleware(claims)

        if auth_type.lower() == "basic" and self.basic_factory is not None:
            return self.basic_factory.start_call(info, headers)

        raise FlightUnauthenticatedError("No credentials supplied")
