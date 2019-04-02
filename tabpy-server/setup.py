try:
    from setuptools import setup
except ImportError as err:
    print("Missing Python module requirement: setuptools.")
    raise err

from tabpy_server import __version__

setup(
    name='tabpy-server',
    version=__version__,
    description='Web server Tableau uses to run Python scripts.',
    url='https://github.com/tableau/TabPy',
    author='Tableau',
    author_email='github@tableau.com',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3.6',
        "Topic :: Scientific/Engineering",
        "Topic :: Scientific/Engineering :: Information Analysis",
    ],
    packages=['tabpy_server',
              'tabpy_server.common',
              'tabpy_server.management',
              'tabpy_server.psws',
              'tabpy_server.static'],
    package_data={'tabpy_server.static': ['*.*'],
                  'tabpy_server': ['startup.*', 'state.ini']},
    license='MIT',
    # Note: many of these required packages are included in base python
    # but are listed here because different linux distros use custom
    # python installations.  And users can remove packages at any point
    install_requires=[
        'backports_abc',
        'cloudpickle',
        'configparser',
        'decorator',
        'future',
        'genson',
        'jsonschema~=2.3.0',
        'mock',
        'numpy',
        'pyopenssl',
        'python-dateutil',
        'requests',
        'simplejson',
        'singledispatch',
        'six',
        'tornado==5.1.1',
        'Tornado-JSON',
        'urllib3'
    ]
)
