import simplejson
import logging
from tabpy_server.handlers import BaseHandler


logger = logging.getLogger(__name__)


class StatusHandler(BaseHandler):
    def initialize(self, tabpy_state, python_service):
        super(StatusHandler, self).initialize(tabpy_state, python_service)

    def get(self):
        self._add_CORS_header()

        logger.debug("Obtaining service status")
        status_dict = {}
        for k, v in self.python_service.ps.query_objects.items():
            status_dict[k] = {
                'version': v['version'],
                'type': v['type'],
                'status': v['status'],
                'last_error': v['last_error']}

        logger.debug("Found models: {}".format(status_dict))
        self.write(simplejson.dumps(status_dict))
        self.finish()
        return
