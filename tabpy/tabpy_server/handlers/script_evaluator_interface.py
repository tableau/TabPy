from tornado import gen


class ScriptEvaluatorInterface:
    def initialize(self, settings_provider):
        raise NotImplementedError()

    @gen.coroutine
    def evaluate(self, script, arguments):
        """Evaluate provided script with arguments."""
        pass
