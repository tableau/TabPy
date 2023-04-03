from pyarrow.flight import ServerAuthHandler

class NoOpAuthHandler(ServerAuthHandler):
    def authenticate(self, outgoing, incoming):
        pass
    
    def is_valid(self, token):
        return ""
