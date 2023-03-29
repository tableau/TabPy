import base64
from requests.auth import HTTPBasicAuth
from pyarrow.flight import ClientMiddlewareFactory, ClientMiddleware

class BasicAuthClientMiddleware(ClientMiddleware):
    def __init__(self, username, password):
        self.username = username
        self.password = password

    def sending_headers(self):
        headers = {}
        creds = f'{self.username}:{self.password}'
        encoded_creds = base64.b64encode(creds.encode()).decode()
        headers['authorization'] = f'Basic {encoded_creds}'
        return headers

class BasicAuthClientMiddlewareFactory(ClientMiddlewareFactory):
    
    def __init__(self, username, password):
        self.username = username
        self.password = password

    def start_call(self, instance):
        return BasicAuthClientMiddleware(self.username, self.password)
