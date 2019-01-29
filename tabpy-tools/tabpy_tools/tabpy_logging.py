import json as simplejson
import logging
from logging import handlers
import tempfile
import os
import platform

LOG_LEVEL = 'INFO'


class PYLogging(object):
    @classmethod
    def initialize(cls, logger):
        cls.logger = logger
        cls.logger.setLevel = logging.getLevelName(LOG_LEVEL)

        # create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        # log file will be saved under /tmp in Linux , c:\temp in Windows
        temp_dir = '/tmp' if platform.system() == 'Darwin' else tempfile.gettempdir()

        fh = handlers.RotatingFileHandler(filename=os.path.join(temp_dir, "tabpy.log"),
                                          maxBytes=10000000, backupCount=5)
        fh.setLevel(LOG_LEVEL)
        fh.setFormatter(formatter)
        # add fh to logger
        logger.addHandler(fh)

        #format console output
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        logger.addHandler(ch)


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
