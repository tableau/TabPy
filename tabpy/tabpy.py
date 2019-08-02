from pathlib import Path

def read_version():
    f = None
    for path in ['VERSION', '../VERSION', '../../VERSION']:
        if Path(path).exists():
            f = path
            break

    if f is not None:
        with open(f) as h:
            return h.read().strip()
    else:
        return 'dev'


__version__ = read_version()


def main():
    from tabpy_server.app.app import TabPyApp
    app = TabPyApp()
    app.run()


if __name__ == '__main__':
    main()