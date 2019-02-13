import concurrent.futures
import logging
import logging.config
import os
import shutil
import sys
import tempfile
import time
import tornado
import urllib
import uuid
from hashlib import md5
from io import StringIO
from pathlib import Path
from re import compile
from uuid import uuid4 as random_uuid

import requests
import tornado
import tornado.ioloop
import tornado.options
import tornado.web
from tornado import gen

import simplejson

from tabpy_server import __app__
from tabpy_server.common.messages import (Query, QueryError, QuerySuccessful,
                                          UnknownURI)
from tabpy_server.common.util import format_exception
from tabpy_server.management.state import TabPyState, get_query_object_path
from tabpy_server.psws.callbacks import (init_model_evaluator, init_ps_server,
                                         on_state_change)


STAGING_THREAD = concurrent.futures.ThreadPoolExecutor(max_workers=3)
_QUERY_OBJECT_STAGING_FOLDER = 'staging'

logger = logging.getLogger(__name__)

if sys.version_info.major == 3:
    unicode = str


def copy_from_local(localpath, remotepath, is_dir=False):
    if is_dir:
        if not os.path.exists(remotepath):
            # remote folder does not exist
            shutil.copytree(localpath, remotepath)
        else:
            # remote folder exists, copy each file
            src_files = os.listdir(localpath)
            for file_name in src_files:
                full_file_name = os.path.join(localpath, file_name)
                if os.path.isdir(full_file_name):
                    # copy folder recursively
                    full_remote_path = os.path.join(remotepath, file_name)
                    shutil.copytree(full_file_name, full_remote_path)
                else:
                    # copy each file
                    shutil.copy(full_file_name, remotepath)
    else:
        shutil.copy(localpath, remotepath)


if __name__ == '__main__':
    __app__.run()
