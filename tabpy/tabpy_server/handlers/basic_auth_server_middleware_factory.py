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
# expire. Rotation keeps the prior token valid until its original expiry,
# so another client using the same username is not disconnected.
FLIGHT_TOKEN_RENEWAL_WINDOW_SECONDS = 300
MAX_ACTIVE_FLIGHT_TOKENS_PER_USER = 2


class BasicAuthServerMiddleware(ServerMiddleware):
    def __init__(self, token):
        self.token = token

    def sending_headers(self):
        return {"authorization": f"Bearer {self.token}"}


class BasicAuthServerMiddlewareFactory(ServerMiddlewareFactory):
    def __init__(self, creds):
        self.creds = creds
        # token -> (username, monotonic expiry). Read from the gRPC thread
        # pool on every call. Normally one token is retained per username;
        # rotation briefly permits the old and new tokens to overlap.
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

            active_tokens = self._tokens_by_username.get(username, [])
            if active_tokens:
                existing = active_tokens[-1]
                _, expiry = self.tokens[existing]
                if expiry - now > FLIGHT_TOKEN_RENEWAL_WINDOW_SECONDS:
                    return existing

            token = secrets.token_urlsafe(32)
            self.tokens[token] = (username, now + FLIGHT_TOKEN_TTL_SECONDS)
            active_tokens = self._tokens_by_username.setdefault(username, [])
            active_tokens.append(token)
            if len(active_tokens) > MAX_ACTIVE_FLIGHT_TOKENS_PER_USER:
                self._remove_token(active_tokens[0], username)
            return token

    def _remove_token(self, token, username):
        self.tokens.pop(token, None)
        active_tokens = self._tokens_by_username.get(username)
        if active_tokens is None:
            return
        active_tokens.remove(token)
        if not active_tokens:
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
            username = username.lower()
            if not self.is_valid_user(username, password):
                raise FlightUnauthenticatedError("Invalid credentials")
            return BasicAuthServerMiddleware(self._issue_token(username))

        if auth_type.lower() == "bearer" and self.is_valid_token(value):
            return BasicAuthServerMiddleware(value)

        raise FlightUnauthenticatedError("No credentials supplied")
