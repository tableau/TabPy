"""
TabPy Server.

Usage:
  tabpy [-h] | [--help]
  tabpy [--config <CONFIG>] [--disable-auth-warning]

Options:
  -h --help                 Show this screen.
  --config <CONFIG>         Path to a config file.
  --disable-auth-warning    Disable authentication warning.
"""

import docopt
import os
from pathlib import Path


def read_version():
    ver = "unknown"

    import tabpy

    pkg_path = os.path.dirname(tabpy.__file__)
    ver_file_path = os.path.join(pkg_path, "VERSION")
    if Path(ver_file_path).exists():
        with open(ver_file_path) as f:
            ver = f.read().strip()
    else:
        ver = f"Version Unknown, (file {ver_file_path} not found)"

    return ver


__version__ = read_version()


def main():
    args = docopt.docopt(__doc__)
    config = args["--config"] or None

    disable_auth_warning = False
    if args["--disable-auth-warning"]:
        disable_auth_warning = True

    from tabpy.tabpy_server.app.app import TabPyApp

    app = TabPyApp(config, disable_auth_warning)
    app.run()


if __name__ == "__main__":
    main()
