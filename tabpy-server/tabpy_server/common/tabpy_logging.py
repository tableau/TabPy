import simplejson
class PYLogging(object): 
    @classmethod
    def initialize(cls, logger):
        cls.logger = logger
    

def log_error(msg, **kwargs):
    kwargs.update({"ERROR": msg})
    try:
        PYLogging.logger.error(simplejson.dumps(kwargs))
    except:
        pass

def log_info(msg, **kwargs):
    kwargs.update({"INFO": msg})
    try:
        PYLogging.logger.info(simplejson.dumps(kwargs))
    except:
        pass

def log_debug(msg, **kwargs):
    kwargs.update({"DEBUG": msg})
    try:
        PYLogging.logger.debug(simplejson.dumps(kwargs))
    except:
        pass

def log_warning(msg, **kwargs):
    kwargs.update({"WARNING": msg})
    try:
        PYLogging.logger.warning(simplejson.dumps(kwargs))
    except:
        pass
