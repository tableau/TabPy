import versioneer
try:
    from setuptools import setup
except ImportError as err:
    print("Missing Python module requirement: setuptools.")
    raise err


setup(
    name='tabpy-server',
    version=versioneer.get_version(),
    description='Web server Tableau uses to run Python scripts.',
    url='https://github.com/tableau/TabPy',
    author='Tableau',
    author_email='github@tableau.com',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3.5',
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
    install_requires=[
        'backports_abc',
        'cloudpickle',
        'configparser',
        'decorator',
        'genson',
        'jsonschema>=2.3.0',
        'mock',
        'numpy',
        'python-dateutil',
        'pyOpenSSL',
        'requests',
        'singledispatch',
        'simplejson',
        'tornado==5.1.1',
        'Tornado-JSON'
    ],
    cmdclass=versioneer.get_cmdclass(),
)
