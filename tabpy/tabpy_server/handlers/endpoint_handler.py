"""
HTTP handeler to serve specific endpoint request like
http://myserver:9004/endpoints/mymodel

For how generic endpoints requests is served look
at endpoints_handler.py
"""

import json
import logging
from tabpy.tabpy_server.handlers import MainHandler


class EndpointHandler(MainHandler):
    def initialize(self, app):
        super(EndpointHandler, self).initialize(app)

    def get(self, endpoint_name):
        if self.should_fail_with_not_authorized():
            self.fail_with_not_authorized()
            return

        self.logger.log(logging.DEBUG, f"Processing GET for /endpoints/{endpoint_name}...")

        self._add_CORS_header()

        if endpoint_name in self.app.models:
            self.write(json.dumps(endpoint_name))
        else:
            self.error_out(
                404,
                f"Unknown endpoint {endpoint_name}",
                info=f"Endpoint {endpoint_name} is not found",
            )
