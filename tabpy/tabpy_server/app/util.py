import csv
from datetime import datetime
import logging
from OpenSSL import crypto
import os


logger = logging.getLogger(__name__)


def validate_cert(cert_file_path):
    with open(cert_file_path, "r") as f:
        cert_buf = f.read()

    cert = crypto.load_certificate(crypto.FILETYPE_PEM, cert_buf)

    date_format, encoding = "%Y%m%d%H%M%SZ", "ascii"
    not_before = datetime.strptime(cert.get_notBefore().decode(encoding), date_format)
    not_after = datetime.strptime(cert.get_notAfter().decode(encoding), date_format)
    now = datetime.now()

    https_error = "Error using HTTPS: "
    if now < not_before:
        msg = https_error + f"The certificate provided is not valid until {not_before}."
        logger.critical(msg)
        raise RuntimeError(msg)
    if now > not_after:
        msg = https_error + f"The certificate provided expired on {not_after}."
        logger.critical(msg)
        raise RuntimeError(msg)


def parse_pwd_file(pwd_file_name):
    """
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
    """
    logger.info(f"Parsing passwords file {pwd_file_name}...")

    if not os.path.isfile(pwd_file_name):
        logger.critical(f"Passwords file {pwd_file_name} not found")
        return False, {}

    credentials = {}
    with open(pwd_file_name) as pwd_file:
        pwd_file_reader = csv.reader(pwd_file, delimiter=" ")
        for row in pwd_file_reader:
            # skip empty lines
            if len(row) == 0:
                continue

            # skip commented lines
            if row[0][0] == "#":
                continue

            if len(row) != 2:
                logger.error(f'Incorrect entry "{row}" in password file')
                return False, {}

            login = row[0].lower()
            if login in credentials:
                logger.error(
                    f"Multiple entries for username {login} in password file"
                )
                return False, {}

            if len(row[1]) > 0:
                credentials[login] = row[1]
                logger.debug(f"Found username {login}")
            else:
                logger.warning(f"Found username {row[0]} but no password")
                return False, {}

    logger.info("Authentication is enabled")
    return True, credentials
