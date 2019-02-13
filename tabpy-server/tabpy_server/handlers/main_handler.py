from tabpy_server.handlers import BaseHandler


class MainHandler(BaseHandler):
    def initialize(self, tabpy_state):
        super(MainHandler, self).initialize(tabpy_state)

    def get(self):
        self._add_CORS_header()
        self.render('/static/index.html')