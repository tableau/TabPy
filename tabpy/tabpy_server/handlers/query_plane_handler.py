from tabpy.tabpy_server.handlers import BaseHandler
import logging
import time
from tabpy.tabpy_server.common.messages import (
    Query, QuerySuccessful, QueryError, UnknownURI)
from hashlib import md5
import uuid
import json
from tabpy.tabpy_server.common.util import format_exception
import urllib
import tornado.web
from tornado import gen


def _get_uuid():
    """Generate a unique identifier string"""
    return str(uuid.uuid4())


class QueryPlaneHandler(BaseHandler):
    def initialize(self, app):
        super(QueryPlaneHandler, self).initialize(app)

    def _query(self, po_name, data, uid, qry):
        """
        Parameters
        ----------
        po_name : str
            The name of the query object to query

        data : dict
            The deserialized request body

        uid: str
            A unique identifier for the request

        qry: str
            The incoming query object. This object maintains
            raw incoming request, which is different from the sanitied data

        Returns
        -------
        out : (result type, dict, int)
            A triple containing a result type, the result message
            as a dictionary, and the time in seconds that it took to complete
            the request.
        """
        self.logger.log(logging.DEBUG,
                        f'Collecting query info for {po_name}...')
        start_time = time.time()
        response = self.python_service.ps.query(po_name, data, uid)
        gls_time = time.time() - start_time
        self.logger.log(logging.DEBUG, f'Query info: {response}')

        if isinstance(response, QuerySuccessful):
            response_json = response.to_json()
            md5_tag = md5(response_json.encode('utf-8')).hexdigest()
            self.set_header("Etag", f'"{md5_tag}"')
            return (QuerySuccessful, response.for_json(), gls_time)
        else:
            self.logger.log(
                logging.ERROR,
                f'Failed query, response: {response}')
            return (type(response), response.for_json(), gls_time)

    # handle HTTP Options requests to support CORS
    # don't check API key (client does not send or receive data for OPTIONS,
    # it just allows the client to subsequently make a POST request)
    def options(self, pred_name):
        if self.should_fail_with_not_authorized():
            self.fail_with_not_authorized()
            return

        self.logger.log(
            logging.DEBUG,
            f'Processing OPTIONS for /query/{pred_name}')

        # add CORS headers if TabPy has a cors_origin specified
        self._add_CORS_header()
        self.write({})

    def _handle_result(self, po_name, data, qry, uid):
        (response_type, response, gls_time) = \
            self._query(po_name, data, uid, qry)

        if response_type == QuerySuccessful:
            result_dict = {
                'response': response['response'],
                'version': response['version'],
                'model': po_name,
                'uuid': uid
            }
            self.write(result_dict)
            self.finish()
            return (gls_time, response['response'])
        else:
            if response_type == UnknownURI:
                self.error_out(404, 'UnknownURI',
                               info=('No query object has been registered'
                                     f' with the name "{po_name}"'))
            elif response_type == QueryError:
                self.error_out(400, 'QueryError', info=response)
            else:
                self.error_out(500, 'Error querying GLS', info=response)

            return (None, None)

    def _sanitize_request_data(self, data):
        if not isinstance(data, dict):
            msg = 'Input data must be a dictionary'
            self.logger.log(logging.CRITICAL, msg)
            raise RuntimeError(msg)

        if "method" in data:
            return {"data": data.get("data"), "method": data.get("method")}
        elif "data" in data:
            return data.get("data")
        else:
            msg = 'Input data must be a dictionary with a key called "data"'
            self.logger.log(logging.CRITICAL, msg)
            raise RuntimeError(msg)

    def _process_query(self, endpoint_name, start):
        self.logger.log(logging.DEBUG,
                        f'Processing query {endpoint_name}...')
        try:
            self._add_CORS_header()

            if not self.request.body:
                self.request.body = {}

            # extract request data explicitly for caching purpose
            request_json = self.request.body.decode('utf-8')

            # Sanitize input data
            data = self._sanitize_request_data(json.loads(request_json))
        except Exception as e:
            err_msg = format_exception(e, "Invalid Input Data")
            self.error_out(400, err_msg)
            return

        try:
            (po_name, _) = self._get_actual_model(
                endpoint_name)

            # po_name is None if self.python_service.ps.query_objects.get(
            # endpoint_name) is None
            if not po_name:
                self.error_out(
                    404,
                    'UnknownURI',
                    info=f'Endpoint "{endpoint_name}" does not exist')
                return

            po_obj = self.python_service.ps.query_objects.get(po_name)

            if not po_obj:
                self.error_out(404, 'UnknownURI',
                               info=f'Endpoint "{po_name}" does not exist')
                return

            if po_name != endpoint_name:
                self.logger.log(
                    logging.INFO,
                    f'Querying actual model: po_name={po_name}')

            uid = _get_uuid()

            # record query w/ request ID in query log
            qry = Query(po_name, request_json)
            gls_time = 0
            # send a query to PythonService and return
            (gls_time, _) = self._handle_result(po_name, data, qry, uid)

            # if error occurred, GLS time is None.
            if not gls_time:
                return

        except Exception as e:
            err_msg = format_exception(e, 'process query')
            self.error_out(500, 'Error processing query', info=err_msg)
            return

    def _get_actual_model(self, endpoint_name):
        # Find the actual query to run from given endpoint
        all_endpoint_names = []

        while True:
            endpoint_info = self.python_service.ps.query_objects.get(
                endpoint_name)
            if not endpoint_info:
                return [None, None]

            all_endpoint_names.append(endpoint_name)

            endpoint_type = endpoint_info.get('type', 'model')

            if endpoint_type == 'alias':
                endpoint_name = endpoint_info['endpoint_obj']
            elif endpoint_type == 'model':
                break
            else:
                self.error_out(
                    500,
                    'Unknown endpoint type',
                    info=f'Endpoint type "{endpoint_type}" does not exist')
                return

        return (endpoint_name, all_endpoint_names)

    @gen.coroutine
    def get(self, endpoint_name):
        if self.should_fail_with_not_authorized():
            self.fail_with_not_authorized()
            return

        start = time.time()
        endpoint_name = urllib.parse.unquote(endpoint_name)
        self._process_query(endpoint_name, start)

    @gen.coroutine
    def post(self, endpoint_name):
        self.logger.log(logging.DEBUG,
                        f'Processing POST for /query/{endpoint_name}...')

        if self.should_fail_with_not_authorized():
            self.fail_with_not_authorized()
            return

        start = time.time()
        endpoint_name = urllib.parse.unquote(endpoint_name)
        self._process_query(endpoint_name, start)
