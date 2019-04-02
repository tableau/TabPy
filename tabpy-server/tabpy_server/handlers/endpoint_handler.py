'''
HTTP handeler to serve specific endpoint request like
http://myserver:9004/endpoints/mymodel

For how generic endpoints requests is served look
at endpoints_handler.py
'''

from tabpy_server.handlers import ManagementHandler
import simplejson
import logging
import tornado.web
from tornado import gen
from tabpy_server.management.state import get_query_object_path
from tabpy_server.common.util import format_exception
from tabpy_server.handlers.base_handler import STAGING_THREAD
from tabpy_server.psws.callbacks import on_state_change
import concurrent
import shutil


logger = logging.getLogger(__name__)


class EndpointHandler(ManagementHandler):
    def initialize(self, app):
        super(EndpointHandler, self).initialize(app)

    def get(self, endpoint_name):
        logger.debug('Processing GET for /endpoints/{}'.format(endpoint_name))
        if self.should_fail_with_not_authorized():
            self.fail_with_not_authorized()
            return

        self._add_CORS_header()
        if not endpoint_name:
            self.write(simplejson.dumps(self.tabpy_state.get_endpoints()))
        else:
            if endpoint_name in self.tabpy_state.get_endpoints():
                self.write(simplejson.dumps(
                    self.tabpy_state.get_endpoints()[endpoint_name]))
            else:
                self.error_out(404, 'Unknown endpoint',
                               info='Endpoint %s is not found' % endpoint_name)

    @tornado.web.asynchronous
    @gen.coroutine
    def put(self, name):
        logger.debug('Processing PUT for /endpoints/{}'.format(name))
        if self.should_fail_with_not_authorized():
            self.fail_with_not_authorized()
            return

        try:
            if not self.request.body:
                self.error_out(400, "Input body cannot be empty")
                self.finish()
                return
            try:
                request_data = simplejson.loads(
                    self.request.body.decode('utf-8'))
            except BaseException as ex:
                self.error_out(
                    400,
                    log_message="Failed to decode input body",
                    info=str(ex))
                self.finish()
                return

            # check if endpoint exists
            endpoints = self.tabpy_state.get_endpoints(name)
            if len(endpoints) == 0:
                self.error_out(404,
                               "endpoint %s does not exist." % name)
                self.finish()
                return

            new_version = int(endpoints[name]['version']) + 1
            logger.info('Endpoint info: %s' % request_data)
            err_msg = yield self._add_or_update_endpoint(
                'update', name, new_version, request_data)
            if err_msg:
                self.error_out(400, err_msg)
                self.finish()
            else:
                self.write(self.tabpy_state.get_endpoints(name))
                self.finish()

        except Exception as e:
            err_msg = format_exception(e, 'update_endpoint')
            self.error_out(500, err_msg)
            self.finish()

    @tornado.web.asynchronous
    @gen.coroutine
    def delete(self, name):
        logger.debug('Processing DELETE for /endpoints/{}'.format(name))
        if self.should_fail_with_not_authorized():
            self.fail_with_not_authorized()
            return

        try:
            endpoints = self.tabpy_state.get_endpoints(name)
            if len(endpoints) == 0:
                self.error_out(404,
                               "endpoint %s does not exist." % name)
                self.finish()
                return

            # update state
            try:
                endpoint_info = self.tabpy_state.delete_endpoint(name)
            except Exception as e:
                self.error_out(400,
                               "Error when removing endpoint: %s" % e.message)
                self.finish()
                return

            # delete files
            if endpoint_info['type'] != 'alias':
                delete_path = get_query_object_path(
                    self.settings['state_file_path'], name, None)
                try:
                    yield self._delete_po_future(delete_path)
                except Exception as e:
                    self.error_out(400,
                                   "Error while deleting: %s" % e)
                    self.finish()
                    return

            self.set_status(204)
            self.finish()

        except Exception as e:
            err_msg = format_exception(e, 'delete endpoint')
            self.error_out(500, err_msg)
            self.finish()

        on_state_change(self.settings, self.tabpy_state, self.python_service)

    @gen.coroutine
    def _delete_po_future(self, delete_path):
        future = STAGING_THREAD.submit(shutil.rmtree, delete_path)
        ret = yield future
        raise gen.Return(ret)
