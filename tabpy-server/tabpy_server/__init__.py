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
