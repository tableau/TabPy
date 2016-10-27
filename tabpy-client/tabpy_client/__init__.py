"""
TabPy client is a Python client to interact with a Tornado-Python-Connector server process.
"""

__version__ = 'dev'

import logging
logging.getLogger(__name__).addHandler(logging.NullHandler())

from .client import Client

from .schema import generate_schema as generate_schema
