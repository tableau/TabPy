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

# Expiry alone doesn't bound the store, since a client that ignores the
# token still mints one per call. Cap it and drop the soonest-to-expire
# entries once full.
MAX_FLIGHT_TOKENS = 1024


class BasicAuthServerMiddleware(ServerMiddleware):
    def __init__(self, token):
        self.token = token

    def sending_headers(self):
        return {"authorization": f"Bearer {self.token}"}


class BasicAuthServerMiddlewareFactory(ServerMiddlewareFactory):
    def __init__(self, creds):
        self.creds = creds
        # token -> (username, monotonic expiry). Read from the gRPC thread
        # pool on every call; every mutation goes through _issue_token
        # under _tokens_lock, so readers never see the store being
        # resized and concurrent calls can't grow it past
        # MAX_FLIGHT_TOKENS.
        self.tokens = {}
        self._tokens_lock = threading.Lock()

    def is_valid_user(self, username, password):
        if username not in self.creds:
            return False
        hashed_pwd = hash_password(username, password)
        return self.creds[username].lower() == hashed_pwd.lower()

    def is_valid_token(self, token):
        entry = self.tokens.get(token)
        return entry is not None and time.monotonic() < entry[1]

    def _issue_token(self, username):
        token = secrets.token_urlsafe(32)
        with self._tokens_lock:
            self._evict_tokens()
            self.tokens[token] = (username, time.monotonic() + FLIGHT_TOKEN_TTL_SECONDS)
        return token

    def _evict_tokens(self):
        now = time.monotonic()
        for token in [t for t, (_, expiry) in self.tokens.items() if expiry <= now]:
            self.tokens.pop(token, None)
        while len(self.tokens) >= MAX_FLIGHT_TOKENS:
            oldest = min(self.tokens, key=lambda t: self.tokens[t][1])
            self.tokens.pop(oldest, None)

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
