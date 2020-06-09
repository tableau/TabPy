import logging
from tabpy.tabpy_server.handlers.python_evaluator import PythonEvaluator


def buildScriptEvaluator(evaluate_with, protocol, port, logger, eval_timeout):
    logger.log(logging.DEBUG, f"Building evaluator for '{evaluate_with}'...")
    script_evaluator = None

    if evaluate_with == "python":
        script_evaluator = PythonEvaluator(protocol, port, logger, eval_timeout)
    else:
        msg = f"Unknown evaluation engine '{evaluate_with}'"
        logger.log(logging.FATAL, msg)
        raise RuntimeError(msg)

    return script_evaluator
