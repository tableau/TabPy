try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup
import sys
setup(
    name='tabpy-server',
    version='0.2',
    description='Web server Tableau uses to run Python scripts.',
    url='https://github.com/tableau/TabPy',
    author='Tableau',
    author_email='github@tableau.com',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.5',
        "Topic :: Scientific/Engineering",
        "Topic :: Scientific/Engineering :: Information Analysis",
    ],
    packages=['tabpy_server',
              'tabpy_server.common',
              'tabpy_server.management',
              'tabpy_server.psws',
              'tabpy_server.static'],
    package_data={'tabpy_server.static':['*.*'],
                'tabpy_server':['startup.*','state.ini.template']},
    license='MIT',
    install_requires=[
        'future',
        'futures',
        'requests',
        'simplejson',
        'Tornado-JSON',
        'tornado',
        'cloudpickle',
        'decorator',
        'python-dateutil',
        'genson',
        'jsonschema',
        'tabpy_client',
        'numpy'
    ]
)
