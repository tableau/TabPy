try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

version = '../VERSION'

def read_version():
    with open(version) as h:
        return h.read().strip()

setup(
    name='tabpy-tools',
    version=read_version(),
    description='Python library of tools to manage Tableau Python Server.',
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
