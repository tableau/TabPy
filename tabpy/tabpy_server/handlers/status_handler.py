import json
import logging
from tabpy.tabpy_server.handlers import BaseHandler
from tabpy.tabpy_server.handlers.util import AuthErrorStates

class StatusHandler(BaseHandler):
    def initialize(self, app):
        super(StatusHandler, self).initialize(app)

    def get(self):
        if self.should_fail_with_auth_error() != AuthErrorStates.NONE:
            self.fail_with_auth_error()
            return

        self._add_CORS_header()

        status_dict = {}
        for k, v in self.python_service.ps.query_objects.items():
            status_dict[k] = {
                "version": v["version"],
                "type": v["type"],
                "status": v["status"],
                "last_error": v["last_error"],
            }

        self.logger.log(logging.DEBUG, f"Found models: {status_dict}")
        self.write(json.dumps(status_dict))
        self.finish()
        return
