'''
HTTP handeler to serve general endpoints request, specifically
http://myserver:9004/endpoints

For how individual endpoint requests are served look
at endpoint_handler.py
'''

from tabpy_server.handlers import ManagementHandler
import json
import tornado.web
from tornado import gen
import logging
from tabpy_server.common.util import format_exception


logger = logging.getLogger(__name__)


class EndpointsHandler(ManagementHandler):
    def initialize(self, app):
        super(EndpointsHandler, self).initialize(app)

    def get(self):
        if self.should_fail_with_not_authorized():
            self.fail_with_not_authorized()
            return

        self._add_CORS_header()
        self.write(json.dumps(self.tabpy_state.get_endpoints()))

    @tornado.web.asynchronous
    @gen.coroutine
    def post(self):
        logger.debug('Processing POST for /endpoints')
        if self.should_fail_with_not_authorized():
            self.fail_with_not_authorized()
            return

        try:
            if not self.request.body:
                self.error_out(400, "Input body cannot be empty")
                self.finish()
                return

            try:
                request_data = json.loads(
                    self.request.body.decode('utf-8'))
            except Exception as ex:
                self.error_out(
                    400,
                    "Failed to decode input body",
                    str(ex))
                self.finish()
                return

            if 'name' not in request_data:
                self.error_out(400,
                               "name is required to add an endpoint.")
                self.finish()
                return

            name = request_data['name']

            # check if endpoint already exist
            if name in self.tabpy_state.get_endpoints():
                self.error_out(400, "endpoint %s already exists." % name)
                self.finish()
                return

            logger.debug("Adding endpoint '{}'".format(name))
            err_msg = yield self._add_or_update_endpoint('add', name, 1,
                                                         request_data)
            if err_msg:
                self.error_out(400, err_msg)
            else:
                logger.debug("Endpoint {} successfully added".format(name))
                self.set_status(201)
                self.write(self.tabpy_state.get_endpoints(name))
                self.finish()
                return

        except Exception as e:
            err_msg = format_exception(e, '/add_endpoint')
            self.error_out(500, "error adding endpoint", err_msg)
            self.finish()
            return
