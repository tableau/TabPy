'''
TabPy application.
This file main() function is an entry point for
'tabpy' command.
'''

import os
from pathlib import Path


def read_version():
    ver = 'unknonw'

    import tabpy
    pkg_path = os.path.dirname(tabpy.__file__)
    ver_file_path = os.path.join(pkg_path, os.path.pardir, 'VERSION')
    if Path(ver_file_path).exists():
        with open(ver_file_path) as f:
            ver = f.read().strip()
    else:
        ver = f'Version Unknown, (file {ver_file_path} not found)'

    return ver


__version__ = read_version()


def main():
    from tabpy.tabpy_server.app.app import TabPyApp
    app = TabPyApp()
    app.run()


if __name__ == '__main__':
    main()
