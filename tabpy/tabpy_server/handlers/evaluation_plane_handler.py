import json
import simplejson
import logging
from tabpy.tabpy_server.app.app_parameters import SettingsParameters
from tabpy.tabpy_server.common.util import format_exception
from tabpy.tabpy_server.handlers import BaseHandler
from tabpy.tabpy_server.handlers.script_evaluator_builder import buildScriptEvaluator
import requests
from tornado import gen
from datetime import timedelta


class EvaluationPlaneHandler(BaseHandler):
    """
    EvaluationPlaneHandler is responsible for running arbitrary python scripts.
    """

    @gen.coroutine
    def _post_impl(self):
        body = json.loads(self.request.body.decode("utf-8"))
        self.logger.log(logging.DEBUG, "Processing POST request...")
        if "script" not in body:
            self.error_out(400, "Script is empty.")
            return

        # Transforming user script into a proper function.
        script = body["script"]
        arguments = None
        if "data" in body:
            arguments = body["data"]

        # validate arguments
        if arguments is not None:
            # check if arguments are dictioanary
            if not isinstance(arguments, dict):
                self.error_out(
                    400, "Script parameters need to be provided as a dictionary."
                )
                return

            # check if arguments names are corrent and no
            # arguments are missing
            args_in = sorted(arguments.keys())
            n = len(arguments)
            if sorted('_arg'+str(i+1) for i in range(n)) != args_in:
                self.error_out(
                    400,
                    "Variables names should follow "
                    "the format _arg1, _arg2, _argN",
                )
                return

        evaluator = buildScriptEvaluator(
            self.settings[SettingsParameters.EvaluateWith].lower(),
            self.protocol,
            self.port,
            self.logger,
            self.eval_timeout)

        try:
            result = yield evaluator.evaluate(script, arguments)
        except (
            gen.TimeoutError,
            requests.exceptions.ConnectTimeout,
            requests.exceptions.ReadTimeout,
        ):
            msg = f"User defined script timed out. Timeout is set to {self.eval_timeout}s."

            self.logger.log(logging.ERROR, msg)
            self.error_out(408, msg)
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
