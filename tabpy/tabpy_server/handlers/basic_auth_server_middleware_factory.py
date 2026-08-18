import base64
import binascii
import secrets
import threading
import time

from pyarrow.flight import ServerMiddlewareFactory, ServerMiddleware
from pyarrow.flight import FlightUnauthenticatedError

from tabpy.tabpy_server.handlers.flight_headers import (
    get_flight_authorization_header,
)
from tabpy.tabpy_server.handlers.util import hash_password

# A successful Basic call mints an opaque token and hands it back to the
# client via sending_headers(). The client may replay it as a Bearer
# credential, so it is a real credential and gets an expiry. Once it
# lapses the client re-authenticates with Basic, which it can always do:
# that is how it obtained the token.
FLIGHT_TOKEN_TTL_SECONDS = 3600

# Avoid handing a freshly authenticated client a token that is about to
# expire. Rotation still happens under the per-factory lock and retains
# only one active token for the username.
FLIGHT_TOKEN_RENEWAL_WINDOW_SECONDS = 300


class BasicAuthServerMiddleware(ServerMiddleware):
    def __init__(self, token):
        self.token = token

    def sending_headers(self):
        return {"authorization": f"Bearer {self.token}"}


class BasicAuthServerMiddlewareFactory(ServerMiddlewareFactory):
    def __init__(self, creds):
        self.creds = creds
        # token -> (username, monotonic expiry). Read from the gRPC thread
        # pool on every call. One active token is retained per username,
        # bounding request-driven growth without evicting another user's
        # unexpired credential.
        self.tokens = {}
        self._tokens_by_username = {}
        self._tokens_lock = threading.Lock()

    def is_valid_user(self, username, password):
        if username not in self.creds:
            return False
        hashed_pwd = hash_password(username, password)
        return self.creds[username].lower() == hashed_pwd.lower()

    def is_valid_token(self, token):
        with self._tokens_lock:
            entry = self.tokens.get(token)
            if entry is None:
                return False
            username, expiry = entry
            if time.monotonic() >= expiry:
                self._remove_token(token, username)
                return False
            return True

    def _issue_token(self, username):
        with self._tokens_lock:
            now = time.monotonic()
            self._evict_expired_tokens(now)

            existing = self._tokens_by_username.get(username)
            if existing is not None:
                _, expiry = self.tokens[existing]
                if expiry - now > FLIGHT_TOKEN_RENEWAL_WINDOW_SECONDS:
                    return existing
                self._remove_token(existing, username)

            token = secrets.token_urlsafe(32)
            self.tokens[token] = (username, now + FLIGHT_TOKEN_TTL_SECONDS)
            self._tokens_by_username[username] = token
            return token

    def _remove_token(self, token, username):
        self.tokens.pop(token, None)
        if self._tokens_by_username.get(username) == token:
            self._tokens_by_username.pop(username, None)

    def _evict_expired_tokens(self, now):
        for token in [t for t, (_, expiry) in self.tokens.items() if expiry <= now]:
            username, _ = self.tokens[token]
            self._remove_token(token, username)

    def start_call(self, info, headers):
        auth_header = get_flight_authorization_header(headers)

        if not auth_header:
            raise FlightUnauthenticatedError("No credentials supplied")

        parts = auth_header.split(" ")
        if len(parts) != 2:
            raise FlightUnauthenticatedError("No credentials supplied")
        auth_type, value = parts

        if auth_type.lower() == "basic":
            try:
                decoded = base64.b64decode(value, validate=True).decode("utf-8")
            except (binascii.Error, UnicodeDecodeError):
                raise FlightUnauthenticatedError("Invalid credentials") from None

            username, separator, password = decoded.partition(":")
            if not separator or not username:
                raise FlightUnauthenticatedError("Invalid credentials")
            if not self.is_valid_user(username, password):
                raise FlightUnauthenticatedError("Invalid credentials")
            return BasicAuthServerMiddleware(self._issue_token(username))

        if auth_type.lower() == "bearer" and self.is_valid_token(value):
            return BasicAuthServerMiddleware(value)

        raise FlightUnauthenticatedError("No credentials supplied")
