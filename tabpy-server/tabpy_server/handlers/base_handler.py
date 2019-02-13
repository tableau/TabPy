import tornado.web
import simplejson
import logging


logger = logging.getLogger(__name__)


class BaseHandler(tornado.web.RequestHandler):
    KEYS_TO_SANITIZE = ("api key", "api_key", "admin key", "admin_key")

    def initialize(self, tabpy_state, python_service):
        self.tabpy_state = tabpy_state
        # set content type to application/json
        self.set_header("Content-Type", "application/json")
        self.port = self.settings['port']
        self.python_service = python_service

    def error_out(self, code, log_message, info=None):
        self.set_status(code)
        self.write(simplejson.dumps(
            {'message': log_message, 'info': info or {}}))

        # We want to duplicate error message in console for
        # loggers are misconfigured or causing the failure
        # themselves
        print(info)
        logger.error('message: {}, info: {}'.format(log_message, info))
        self.finish()

    def options(self):
        # add CORS headers if TabPy has a cors_origin specified
        self._add_CORS_header()
        self.write({})

    def _add_CORS_header(self):
        """
        Add CORS header if the TabPy has attribute _cors_origin
        and _cors_origin is not an empty string.
        """
        origin = self.tabpy_state.get_access_control_allow_origin()
        if len(origin) > 0:
            self.set_header("Access-Control-Allow-Origin", origin)
            logger.debug("Access-Control-Allow-Origin:{}".format(origin))

        headers = self.tabpy_state.get_access_control_allow_headers()
        if len(headers) > 0:
            self.set_header("Access-Control-Allow-Headers",headers)
            logger.debug("Access-Control-Allow-Headers:{}".format(headers))

        methods = self.tabpy_state.get_access_control_allow_methods()
        if len(methods) > 0:
            self.set_header("Access-Control-Allow-Methods",methods)
            logger.debug("Access-Control-Allow-Methods:{}".format(methods))

    def _sanitize_request_data(self, data, keys=KEYS_TO_SANITIZE):
        """Remove keys so that we can log safely"""
        for key in keys:
            data.pop(key, None)