import logging

from datetime import datetime
from OpenSSL import crypto

logger = logging.getLogger(__name__)


def log_and_raise(msg, exception_type):
    '''
    Log the message and raise an exception of specified type
    '''
    logger.fatal(msg)
    raise exception_type(msg)


def validate_cert(cert_file_path):
    with open(cert_file_path, 'r') as f:
        cert_buf = f.read()

    cert = crypto.load_certificate(crypto.FILETYPE_PEM, cert_buf)

    date_format, encoding = '%Y%m%d%H%M%SZ', 'ascii'
    not_before = datetime.strptime(
        cert.get_notBefore().decode(encoding), date_format)
    not_after = datetime.strptime(
        cert.get_notAfter().decode(encoding), date_format)
    now = datetime.now()

    https_error = 'Error using HTTPS: '
    if now < not_before:
        log_and_raise(https_error +
                      'The certificate provided is not valid until {}.'.format(
                          not_before), RuntimeError)
    if now > not_after:
        log_and_raise(https_error +
                      'The certificate provided expired on {}.'.format(not_after), RuntimeError)
