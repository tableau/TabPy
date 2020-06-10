import logging
from tabpy.tabpy_server.handlers.python_evaluator import PythonEvaluator
from tabpy.tabpy_server.handlers.rserve_evaluator import RserveEvaluator


def buildScriptEvaluator(evaluate_with, settings_provider, logger):
    logger.log(logging.DEBUG, f"Building evaluator for '{evaluate_with}'...")
    script_evaluator = None

    if evaluate_with == "python":
        script_evaluator = PythonEvaluator()
    elif evaluate_with == "rserve":
        script_evaluator = RserveEvaluator()
    else:
        msg = f"Unknown evaluation engine '{evaluate_with}'"
        logger.log(logging.FATAL, msg)
        raise RuntimeError(msg)

    script_evaluator.initialize(settings_provider)
    return script_evaluator
