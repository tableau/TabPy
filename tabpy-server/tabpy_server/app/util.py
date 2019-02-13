import logging

logger = logging.getLogger(__name__)

def log_and_raise(msg, exception_type):
    '''
    Log the message and raise an exception of specified type
    '''
    logger.fatal(msg)
    raise exception_type(msg)
