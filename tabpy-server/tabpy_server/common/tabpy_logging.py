import json as simplejson
import logging
from logging import handlers
import tempfile
import os

if os.path.isfile('./common/config.py'):
    import common.config as config
    LOG_LEVEL = config.TABPY_LOG_LEVEL
else:
    LOG_LEVEL = "INFO"

class PYLogging(object):
    @classmethod
    def initialize(cls, logger):
        cls.logger = logger
        cls.logger.setLevel = logging.getLevelName(LOG_LEVEL)

        # create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        temp_dir = tempfile.gettempdir()
        fh_info = handlers.RotatingFileHandler(filename=os.path.join(temp_dir, "tabpy_info.log",),
                                               maxBytes=10000000, backupCount=5)
        fh_info.setLevel(logging.INFO)
        fh_info.setFormatter(formatter)

        fh_debug = handlers.RotatingFileHandler(filename=os.path.join(temp_dir, "tabpy_debug.log"),
                                                maxBytes=10000000, backupCount=5)
        fh_debug.setLevel(logging.DEBUG)
        fh_debug.setFormatter(formatter)

        # add fh to logger
        logger.addHandler(fh_info)
        logger.addHandler(fh_debug)
    

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
