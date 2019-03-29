import csv
import logging
import os

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
                      f'The certificate provided expired on {not_after}.',
                      RuntimeError)


def parse_pwd_file(pwd_file_name):
    '''
    Parses passwords file and returns set of credentials.

    Parameters
    ----------
    pwd_file_name : str
        Passwords file name.

    Returns
    -------
    succeeded : bool
        True if specified file was parsed successfully.
        False if there were any issues with parsing specified file.

    credentials : dict
        Credentials from the file. Empty if succeeded is False.
    '''
    logger.info('Parsing passwords file {}...'.format(pwd_file_name))

    if not os.path.isfile(pwd_file_name):
        logger.fatal('Passwords file {} not found'.format(pwd_file_name))
        return False, {}

    credentials = {}
    with open(pwd_file_name) as pwd_file:
        pwd_file_reader = csv.reader(pwd_file, delimiter=' ')
        for row in pwd_file_reader:
            # skip empty lines
            if len(row) == 0:
                continue

            # skip commented lines
            if row[0][0] == '#':
                continue

            if len(row) != 2:
                logger.error(
                    'Incorrect entry "{}" '
                    'in password file'.format(row))
                return False, {}

            login = row[0].lower()
            if login in credentials:
                logger.error(
                    'Multiple entries for username {} '
                    'in password file'.format(login))
                return False, {}

            credentials[login] = row[1]
            logger.debug('Found username {}'.format(login))

    return True, credentials
