import configparser
from pathlib import Path
import getpass
import sys

def get_default_config_file_path():
    config_file_path = str(Path(__file__).resolve().parent.parent.parent
                           / 'tabpy-server' / 'tabpy_server' / 'common'
                           / 'default.conf')
    return config_file_path

def parse_config(config_file_path):
    config = configparser.ConfigParser()
    config.read(config_file_path)
    tabpy_config = config['TabPy']
    port = tabpy_config['TABPY_PORT']
    auth_on = 'TABPY_PWD_FILE' in tabpy_config
    ssl_on = 'TABPY_TRANSFER_PROTOCOL' in tabpy_config and 'TABPY_CERTIFICATE_FILE' in tabpy_config and 'TABPY_KEY_FILE' in tabpy_config
    prefix = "https" if ssl_on else "http"
    return port, auth_on, prefix


def get_creds():
    if sys.stdin.isatty():
        user = input("Username: ")
        passwd = getpass.getpass("Password: ")
    else:
        user = sys.stdin.readline().rstrip()
        passwd = sys.stdin.readline().rstrip()
    return [user, passwd]
