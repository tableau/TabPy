import concurrent.futures
from datetime import timedelta
import json
import logging
import multiprocessing
import requests
from tabpy.tabpy_server.handlers.script_evaluator_interface import ScriptEvaluatorInterface
from tornado import gen


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


class PythonEvaluator(ScriptEvaluatorInterface):
    @gen.coroutine
    def evaluate(self, script, arguments):
        self.logger.log(logging.DEBUG, "Evaluating Python script...")
        args_str = ""
        if arguments is not None and len(arguments) > 0:
            args_in = sorted(arguments.keys())
            args_str = ", " + ", ".join(args_in)

        function_to_evaluate = f"def _user_script(tabpy{args_str}):\n"
        for u in script.splitlines():
            function_to_evaluate += " " + u + "\n"

        self.logger.log(
            logging.INFO,
            f"User script:\n{function_to_evaluate}")

        ret = yield self._call_subprocess(function_to_evaluate, arguments)
        return ret

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
        executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=multiprocessing.cpu_count()
        )

        if arguments is None:
            future = executor.submit(_user_script,  # noqa: F821
                                          restricted_tabpy)
        else:
            future = executor.submit(_user_script,  # noqa: F821
                                          restricted_tabpy, **arguments)

        ret = yield gen.with_timeout(timedelta(seconds=self.eval_timeout), future)
        raise gen.Return(ret)
