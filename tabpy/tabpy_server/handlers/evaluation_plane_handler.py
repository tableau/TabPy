from tabpy.tabpy_server.handlers import BaseHandler
import json
import simplejson
import logging
from tabpy.tabpy_server.common.util import format_exception
import requests
from tornado import gen
from datetime import timedelta


class RestrictedTabPy:
    def __init__(self, protocol, port, logger, timeout):
        self.protocol = protocol
        self.port = port
        self.logger = logger
        self.timeout = timeout

    def query(self, name, *args, **kwargs):
        url = f"{self.protocol}://localhost:{self.port}/query/{name}"
        self.logger.log(logging.DEBUG, f"Querying {url}...")
        internal_data = {"data": args or kwargs}
        data = json.dumps(internal_data)
        headers = {"content-type": "application/json"}
        response = requests.post(
            url=url, data=data, headers=headers, timeout=self.timeout, verify=False
        )
        return response.json()


class EvaluationPlaneHandler(BaseHandler):
    """
    EvaluationPlaneHandler is responsible for running arbitrary python scripts.
    """

    def initialize(self, executor, app):
        super(EvaluationPlaneHandler, self).initialize(app)
        self.executor = executor
        self._error_message_timeout = (
            f"User defined script timed out. "
            f"Timeout is set to {self.eval_timeout} s."
        )

    @gen.coroutine
    def _post_impl(self):
        body = json.loads(self.request.body.decode("utf-8"))
        self.logger.log(logging.DEBUG, f"Processing POST request '{body}'...")
        if "script" not in body:
            self.error_out(400, "Script is empty.")
            return

        # Transforming user script into a proper function.
        user_code = body["script"]
        arguments = None
        arguments_str = ""
        if "data" in body:
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
            self.write(simplejson.dumps(result, ignore_nan=True))
        else:
            self.write("null")
        self.finish()

    @gen.coroutine
    def post(self):
        if self.should_fail_with_not_authorized():
            self.fail_with_not_authorized()
            return

        self._add_CORS_header()
        try:
            yield self._post_impl()
        except Exception as e:
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
            self.protocol, self.port, self.logger, self.eval_timeout
        )
        # Exec does not run the function, so it does not block.
        exec(function_to_evaluate, globals())

        # 'noqa' comments below tell flake8 to ignore undefined _user_script
        # name - the name is actually defined with user script being wrapped
        # in _user_script function (constructed as a striong) and then executed
        # with exec() call above.
        if arguments is None:
            future = self.executor.submit(_user_script,  # noqa: F821
                                          restricted_tabpy)
        else:
            future = self.executor.submit(_user_script,  # noqa: F821
                                          restricted_tabpy, **arguments)

        ret = yield gen.with_timeout(timedelta(seconds=self.eval_timeout), future)
        raise gen.Return(ret)
