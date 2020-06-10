import concurrent.futures
from datetime import timedelta
import json
import logging
import multiprocessing
import numpy
import pyRserve
from tornado import gen
from tabpy.tabpy_server.handlers.script_evaluator_interface import ScriptEvaluatorInterface


logger = logging.getLogger(__name__)


def RserveEval(**kwargs):
    def _trace_rserve_call(conn, expr):
        logger.debug(f"Rserve call: {expr}")
        res = conn.eval(expr)
        logger.debug(f"Rserve result: {res}")
        return res

    conn = pyRserve.connect(host=kwargs["host"], port=kwargs["port"])
    conn.voidEval("library(jsonlite)")

    args_list = ''
    for key, value in kwargs.items():
        if key.startswith("_arg"):
            r_key = key.replace("_", ".")
            if not len(args_list) == 0:
                args_list += ', '
            args_list += r_key

            # escape strings in JSON so "ab" becomes \"ab\"
            esc_value = json.dumps(value).replace('"', '\\"').replace("'", "\\'")
            conn.voidEval(f"{r_key} <- list(fromJSON('{esc_value}'))")
            # uncomment next line to trace creation of variables
            # _trace_rserve_call(conn, f"{r_key} <- list(fromJSON('{esc_value}'))")

    script = kwargs["script"]
    user_script = "userScript<-function(" + args_list + "){" + script + "}"
    _trace_rserve_call(conn, user_script)

    res = conn.eval(f"list(userScript({args_list}))")

    # result can be:
    # - single value
    # - list
    # - list of arrays
    if isinstance(res, numpy.ndarray) or isinstance(res, list):
        res = res[0]

    # only get rid of first level of
    # arrays
    if ((isinstance(res, numpy.ndarray) or isinstance(res, list)) and
       isinstance(res[0], numpy.ndarray)):
        res = res[0]

    # for TabPy to be able to build JSON from the
    # result convert it to native list
    if isinstance(res, numpy.ndarray):
        res = res.tolist()

    logger.debug(f"res = {res}")
    return res


class RserveEvaluator(ScriptEvaluatorInterface):
    def initialize(self, settings_provider):
        self.host = settings_provider.get_setting("extsvc_host")
        self.port = settings_provider.get_setting("extsvc_port")
        self.logger = settings_provider.get_setting("logger")
        self.eval_timeout = settings_provider.get_setting("evaluate_timeout")

    @gen.coroutine
    def evaluate(self, script, args):
        self.script = script
        self.logger.log(
            logging.DEBUG,
            f"Evaluating R script with Rserve on {self.host}:{self.port}...")

        ret = yield self._call_subprocess(args)
        return ret

    @gen.coroutine
    def _call_subprocess(self, arguments):
        executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=multiprocessing.cpu_count()
        )

        if arguments is None:
            arguments = {}

        arguments["host"] = self.host
        arguments["port"] = self.port
        arguments["script"] = self.script

        future = executor.submit(RserveEval, **arguments)

        ret = yield gen.with_timeout(timedelta(seconds=self.eval_timeout), future)
        raise gen.Return(ret)
