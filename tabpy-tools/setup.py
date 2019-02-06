try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

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


__version__=read_version()


setup(
    name='tabpy-tools',
    version=__version__,
    description='Python library of tools to manage TabPy Server.',
    url='https://github.com/tableau/TabPy',
    author='Tableau',
    author_email='github@tableau.com',
    # see classifiers at https://pypi.org/pypi?:action=list_classifiers
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3.5',
        "Topic :: Scientific/Engineering",
        "Topic :: Scientific/Engineering :: Information Analysis",
    ],
    packages=['tabpy_tools'],
    license='MIT',
    install_requires=[
        'cloudpickle',
        'decorator',
        'python-dateutil',
        'requests',
        'genson',
        'jsonschema'
    ]
)
