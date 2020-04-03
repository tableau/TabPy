from tabpy.tabpy_server.handlers import BaseHandler
import logging
import time
import uuid
import json
import urllib
from tornado import gen


def _get_uuid():
    """Generate a unique identifier string"""
    return str(uuid.uuid4())


class QueryPlaneHandler(BaseHandler):
    def initialize(self, app):
        super(QueryPlaneHandler, self).initialize(app)

    def _query(self, model, data):
        """
        Parameters
        ----------
        model :
            Model (function) to execute

        data : dict
            The deserialized request body

        Returns
        -------
        out : object
            Result.
        """
        response = model(data)
        response_json = response.to_json()
        return response_json

    # handle HTTP Options requests to support CORS
    # don't check API key (client does not send or receive data for OPTIONS,
    # it just allows the client to subsequently make a POST request)
    def options(self, pred_name):
        if self.should_fail_with_not_authorized():
            self.fail_with_not_authorized()
            return

        self.logger.log(logging.DEBUG, f"Processing OPTIONS for /query/{pred_name}...")

        # add CORS headers if TabPy has a cors_origin specified
        self._add_CORS_header()
        self.write({})

    def _handle_result(self, model, data):
        response = self._query(model, data)

        result = {
            "response": response["response"],
        }
        self.write(result)
        self.finish()
        return response["response"]

    def _sanitize_request_data(self, data):
        if not isinstance(data, dict):
            raise RuntimeError("Input data must be a dictionary")

        if "data" in data:
            return data.get("data")
        else:
            raise RuntimeError('Input data must be a dictionary with a key called "data"')

    def _process_query(self, endpoint_name):
        try:
            self._add_CORS_header()

            if not self.request.body:
                self.request.body = {}

            # extract request data explicitly for caching purpose
            request_json = self.request.body.decode("utf-8")

            # Sanitize input data
            data = self._sanitize_request_data(json.loads(request_json))
        except Exception as e:
            msg = str(e)
            self.logger.log(logging.ERROR, msg)
            self.error_out(400, f"Invalid Input Data: {msg}")
            return

        try:
            if endpoint_name not in self.app.models:
                self.error_out(
                    404, "UnknownURI", info=f'Endpoint "{endpoint_name}" does not exist'
                )
                return

            self.logger.log(logging.INFO, f"Executing model '{endpoint_name}'...")
            model = self.app.models[endpoint_name]

            self._handle_result(model, data)
        except Exception as e:
            msg = str(e)
            self.logger.log(logging.ERROR, msg)
            err_msg = f"Error processing query: {msg}"
            self.error_out(500, err_msg, info=err_msg)

    @gen.coroutine
    def post(self, endpoint_name):
        self.logger.log(logging.DEBUG, f"Processing POST for /query/{endpoint_name}...")

        if self.should_fail_with_not_authorized():
            self.fail_with_not_authorized()
            return

        endpoint_name = urllib.parse.unquote(endpoint_name)
        self._process_query(endpoint_name)
