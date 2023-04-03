import pandas
import pyarrow
import uuid

from tabpy.tabpy_server.handlers import BaseHandler
import json
import simplejson
import logging
from tabpy.tabpy_server.common.util import format_exception
import requests
from tornado import gen
from datetime import timedelta
from tabpy.tabpy_server.handlers.util import AuthErrorStates

class RestrictedTabPy:
    def __init__(self, protocol, port, logger, timeout, headers):
        self.protocol = protocol
        self.port = port
        self.logger = logger
        self.timeout = timeout
        self.headers = headers

    def query(self, name, *args, **kwargs):
        url = f"{self.protocol}://localhost:{self.port}/query/{name}"
        self.logger.log(logging.DEBUG, f"Querying {url}...")
        internal_data = {"data": args or kwargs}
        data = json.dumps(internal_data)
        headers = self.headers
        response = requests.post(
            url=url, data=data, headers=headers, timeout=self.timeout, verify=False
        )
        return response.json()


class EvaluationPlaneDisabledHandler(BaseHandler):
    """
    EvaluationPlaneDisabledHandler responds with error message when ad-hoc scripts have been disabled.
    """

    def initialize(self, executor, app):
        super(EvaluationPlaneDisabledHandler, self).initialize(app)
        self.executor = executor

    @gen.coroutine
    def post(self):
        if self.should_fail_with_auth_error() != AuthErrorStates.NONE:
            self.fail_with_auth_error()
            return
        self.error_out(404, "Ad-hoc scripts have been disabled on this analytics extension, please contact your "
                            "administrator.")


class EvaluationPlaneHandler(BaseHandler):
    """
    EvaluationPlaneHandler is responsible for running arbitrary python scripts.
    """

    def initialize(self, executor, app):
        super(EvaluationPlaneHandler, self).initialize(app)
        self.arrow_server = app.arrow_server
        self.executor = executor
        self._error_message_timeout = (
            f"User defined script timed out. "
            f"Timeout is set to {self.eval_timeout} s."
        )

    @gen.coroutine
    def _post_impl(self):
        body = json.loads(self.request.body.decode("utf-8"))
        self.logger.log(logging.DEBUG, f"Processing POST request...")
        if "script" not in body:
            self.error_out(400, "Script is empty.")
            return

        # Transforming user script into a proper function.
        user_code = body["script"]
        arguments = None
        arguments_str = ""
        if "dataPath" in body:
            # arrow flight scenario
            print("arrow flight scenario")
            arrow_data = self.get_arrow_data(body["dataPath"])
            if arrow_data is not None:
                arguments = {"_arg1": arrow_data}
        elif "data" in body:
            # backwarding
            arguments = body["data"]

        if arguments is not None:
            if not isinstance(arguments, dict):
                self.error_out(
                    400, "Script parameters need to be provided as a dictionary."
                )
                return
            args_in = sorted(arguments.keys())
            n = len(arguments)
            if sorted('_arg'+str(i+1) for i in range(n)) == args_in:
                arguments_str = ", " + ", ".join(args_in)
            else:
                self.error_out(
                    400,
                    "Variables names should follow "
                    "the format _arg1, _arg2, _argN",
                )
                return
        function_to_evaluate = f"def _user_script(tabpy{arguments_str}):\n"
        for u in user_code.splitlines():
            function_to_evaluate += " " + u + "\n"

        self.logger.log(
            logging.INFO, f"function to evaluate={function_to_evaluate}"
        )

        try:
            result = yield self._call_subprocess(function_to_evaluate, arguments)
        except (
            gen.TimeoutError,
            requests.exceptions.ConnectTimeout,
            requests.exceptions.ReadTimeout,
        ):
            self.logger.log(logging.ERROR, self._error_message_timeout)
            self.error_out(408, self._error_message_timeout)
            return

        if result is not None:
            if "dataPath" in body:
                # arrow flight scenario
                output_data_id = str(uuid.uuid4())
                self.upload_arrow_data(result, output_data_id, {
                    'removeOnDelete': 'True',
                    'linkedIDs': body["dataPath"]
                })
                result = { 'outputDataPath': output_data_id }
                self.logger.log(logging.WARN, f'outputDataPath={output_data_id}')
            else:
                if isinstance(result, pandas.DataFrame):
                    result = result.to_dict(orient='list')
            self.write(simplejson.dumps(result, ignore_nan=True))
        else:
            self.write("null")
        self.finish()

    def get_arrow_data(self, filename):
        descriptor = pyarrow.flight.FlightDescriptor.for_path(filename)
        info = self.arrow_server.get_flight_info(None, descriptor)
        for endpoint in info.endpoints:
            print('Ticket:', endpoint.ticket)
            for location in endpoint.locations:
                print(location)
                key = (descriptor.descriptor_type.value, descriptor.command,
                       tuple(descriptor.path or tuple()))
                df = self.arrow_server.flights.pop(key).to_pandas()
                return df
        print('no data found for get')
        return ''

    def upload_arrow_data(self, data, filename, metadata):
        my_table = pyarrow.table(data)
        if metadata is not None:
            my_table.schema.with_metadata(metadata)
        print('Table rows=', str(len(my_table)))
        print("Uploading", data.head())
        descriptor = pyarrow.flight.FlightDescriptor.for_path(filename)
        key = (descriptor.descriptor_type.value, descriptor.command,
                tuple(descriptor.path or tuple()))
        self.arrow_server.flights[key] = my_table

    @gen.coroutine
    def post(self):
        if self.should_fail_with_auth_error() != AuthErrorStates.NONE:
            self.fail_with_auth_error()
            return

        self._add_CORS_header()
        try:
            yield self._post_impl()
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            err_msg = f"{e.__class__.__name__} : {str(e)}"
            if err_msg != "KeyError : 'response'":
                err_msg = format_exception(e, "POST /evaluate")
                self.error_out(500, "Error processing script", info=err_msg)
            else:
                self.error_out(
                    404,
                    "Error processing script",
                    info="The endpoint you're "
                    "trying to query did not respond. Please make sure the "
                    "endpoint exists and the correct set of arguments are "
                    "provided.",
                )

    @gen.coroutine
    def _call_subprocess(self, function_to_evaluate, arguments):
        restricted_tabpy = RestrictedTabPy(
            self.protocol, self.port, self.logger, self.eval_timeout, self.request.headers
        )
        # Exec does not run the function, so it does not block.
        exec(function_to_evaluate, globals())

        # 'noqa' comments below tell flake8 to ignore undefined _user_script
        # name - the name is actually defined with user script being wrapped
        # in _user_script function (constructed as a striong) and then executed
        # with exec() call above.
        future = self.executor.submit(_user_script,  # noqa: F821
                                      restricted_tabpy,
                                      **arguments if arguments is not None else None)

        ret = yield gen.with_timeout(timedelta(seconds=self.eval_timeout), future)
        raise gen.Return(ret)
