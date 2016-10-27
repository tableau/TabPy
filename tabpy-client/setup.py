try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(
    name='tabpy-client',
    version='0.1',
    description='Python client library to manage Tableau Python Server.',
    url='https://github.com/tableau/TabPy',
    author='Tableau',
    author_email='github@tableau.com',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 2.7',
        "Topic :: Scientific/Engineering",
        "Topic :: Scientific/Engineering :: Information Analysis",
    ],
    packages=['tabpy_client'],
    license='MIT',
    install_requires=[
        'cloudpickle',
        'decorator',
        'python-dateutil',
        'requests',
        'genson',
        'jsonschema',
        'tabpy_client'
    ],
)
