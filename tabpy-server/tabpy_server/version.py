from pathlib import Path

def read_version():
    if Path('VERSION').exists():
        f = 'VERSION'
    else:
        f = '../../VERSION'

    with open(f) as h:
        return h.read().strip()
    

_version = read_version()