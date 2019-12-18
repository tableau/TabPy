import configparser
import getpass
import os
import sys
from tabpy.tabpy_tools.client import Client


def get_default_config_file_path():
    import tabpy

    pkg_path = os.path.dirname(tabpy.__file__)
    config_file_path = os.path.join(pkg_path, "tabpy_server", "common", "default.conf")
    return config_file_path


def parse_config(config_file_path):
    config = configparser.ConfigParser()
    config.read(config_file_path)
    tabpy_config = config["TabPy"]

    port = 9004
    if "TABPY_PORT" in tabpy_config:
        port = tabpy_config["TABPY_PORT"]

    auth_on = "TABPY_PWD_FILE" in tabpy_config
    ssl_on = (
        "TABPY_TRANSFER_PROTOCOL" in tabpy_config
        and "TABPY_CERTIFICATE_FILE" in tabpy_config
        and "TABPY_KEY_FILE" in tabpy_config
    )
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


def deploy_model(funcName, func, funcDescription):
    # running from deploy_models.py
    if len(sys.argv) > 1:
        config_file_path = sys.argv[1]
    else:
        config_file_path = get_default_config_file_path()
    port, auth_on, prefix = parse_config(config_file_path)

    connection = Client(f"{prefix}://localhost:{port}/")

    if auth_on:
        # credentials are passed in from setup.py
        if len(sys.argv) == 4:
            user, passwd = sys.argv[2], sys.argv[3]
        # running Sentiment Analysis independently
        else:
            user, passwd = get_creds()
        connection.set_credentials(user, passwd)

    connection.deploy(funcName, func, funcDescription, override=True)
    print(f"Successfully deployed {funcName}")
