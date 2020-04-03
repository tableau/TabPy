"""
HTTP handeler to serve general endpoints request, specifically
http://myserver:9004/endpoints

For how individual endpoint requests are served look
at endpoint_handler.py
"""

import json
from tabpy.tabpy_server.handlers import BaseHandler


class EndpointsHandler(BaseHandler):
    def initialize(self, app):
        super(EndpointsHandler, self).initialize(app)

    def get(self):
        if self.should_fail_with_not_authorized():
            self.fail_with_not_authorized()
            return

        self._add_CORS_header()
        self.write(json.dumps(self.tabpy_state.get_endpoints()))
