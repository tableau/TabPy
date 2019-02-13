from tabpy_server.handlers import BaseHandler


class MainHandler(BaseHandler):
    def initialize(self):
        super(MainHandler, self).initialize()

    def get(self):
        self._add_CORS_header()
        self.render('/static/index.html')