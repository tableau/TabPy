from tabpy_server import __version__
from tabpy_server.app.app import TabPyApp


def main():
    app = TabPyApp()
    app.run()


if __name__ == '__main__':
    main()
