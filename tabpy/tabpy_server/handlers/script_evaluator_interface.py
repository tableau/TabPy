from tornado import gen


class ScriptEvaluatorInterface:
    def __init__(self, protocol, port, logger, eval_timeout):
        self.protocol = protocol
        self.port = port
        self.logger = logger
        self.eval_timeout = eval_timeout

    @gen.coroutine
    def evaluate(self, script, arguments):
        """Evaluate provided script with arguments."""
        pass
