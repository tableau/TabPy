import base64
import secrets

from pyarrow.flight import ServerMiddlewareFactory, ServerMiddleware
from pyarrow.flight import FlightUnauthenticatedError

from tabpy.tabpy_server.handlers.util import hash_password

class BasicAuthServerMiddleware(ServerMiddleware):
    def __init__(self, token):
        self.token = token

    def sending_headers(self):
        return {"authorization": f"Bearer {self.token}"}

class BasicAuthServerMiddlewareFactory(ServerMiddlewareFactory):
    def __init__(self, creds):
        self.creds = creds
        self.tokens = {}

    def is_valid_user(self, username, password):
        if username not in self.creds:
            return False
        hashed_pwd = hash_password(username, password)
        return self.creds[username].lower() == hashed_pwd.lower()

    def start_call(self, info, headers):
        auth_header = None
        for header in headers:
            if header.lower() == "authorization":
                auth_header = headers[header][0]
                break

        if not auth_header:
            raise FlightUnauthenticatedError("No credentials supplied")
        
        auth_type, _, value = auth_header.partition(" ")

        if auth_type == "Basic":
            decoded = base64.b64decode(value).decode("utf-8")
            username, _, password = decoded.partition(":")
            if not self.is_valid_user(username, password):
                raise FlightUnauthenticatedError("Invalid credentials")
            token = secrets.token_urlsafe(32)
            self.tokens[token] = username
            return BasicAuthServerMiddleware(token)
        
        raise FlightUnauthenticatedError("No credentials supplied")