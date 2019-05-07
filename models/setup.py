import pip
import os
import sys
import platform
import subprocess
import getpass
from pathlib import Path
import configparser

# pip 10.0 introduced a breaking change that moves the location of main
try:
    from pip import main
except ImportError:
    from pip._internal import main


def install_dependencies(packages):
    pip_arg = ['install'] + packages + ['--no-cache-dir']
    if hasattr(pip, 'main'):
        pip.main(pip_arg)
    else:
        pip._internal.main(pip_arg)


if __name__ == '__main__':
    install_dependencies(['sklearn', 'pandas', 'numpy',
                          'textblob', 'nltk', 'scipy'])
    print('===================================================================')
    # Determine if we run python or python3
    if platform.system() == 'Windows':
        py = 'python '
    else:
        py = 'python3 '

    if (len(sys.argv) > 1):
        config_file_path = sys.argv[1]
    else:  
        config_file_path = str(Path(__file__).resolve().parent.parent
                               / 'tabpy-server' / 'tabpy_server'
                               / 'common' / 'default.conf')
    print(f'Using config file at {config_file_path}')
    config = configparser.ConfigParser()
    config.read(config_file_path)
    auth_on = 'TABPY_PWD_FILE' in config['TabPy']
    if (auth_on):
        if sys.stdin.isatty():
            user = input("Username: ")
            passwd = getpass.getpass("Password: ")
        else:
            user = sys.stdin.readline().rstrip()
            passwd = sys.stdin.readline().rstrip()
        auth_args = [user, passwd]
    else:
        auth_args = []

    directory = str(Path(__file__).resolve().parent / 'scripts')
    # Deploy each model in the scripts directory
    for filename in os.listdir(directory):
        subprocess.call([py, f'{directory}/{filename}', config_file_path]
                        + auth_args)

