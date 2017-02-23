import os
import sys
import time
import uuid
import urllib
import requests
import functools
import subprocess
import concurrent.futures

from tabpy_client.query_object import QueryObject
from common.util import format_exception
from common.messages import *

from common.tabpy_logging import (
    PYLogging,
    log_error,
    log_info,
    log_debug,
    log_warning,
)

import logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)
PYLogging.initialize(logger)

if sys.version_info.major == 3:
    unicode = str

class PythonServiceHandler:
    """
    A wrapper around PythonService object that receives requests and calls the
    corresponding methods.
    """
    def __init__(self, ps):
        self.ps = ps

    def manage_request(self, msg):
        try:
            log_info("Received request", request_type=type(msg).__name__)
            if isinstance(msg, LoadObject):
                response = self.ps.load_object(*msg)
            elif isinstance(msg, DeleteObjects):
                response = self.ps.delete_objects(msg.uris)
            elif isinstance(msg, FlushObjects):
                response = self.ps.flush_objects()
            elif isinstance(msg, CountObjects):
                response = self.ps.count_objects()
            elif isinstance(msg, ListObjects):
                response = self.ps.list_objects()
            else:
                response = UnknownMessage(msg)

            return response
        except Exception as e:
            log_error("Error processing request", error=e.message)
            return UnknownMessage(e.message)

class PythonService(object):
    """
    This class is a simple wrapper maintaining loaded query objects from
    the current TabPy instance. `query_objects` is a dictionary that
    maps query object URI to query objects

    The query_objects schema is as follow:

    {'version': <current-successfuly-loaded-version>,
     'last_error':<your-recent-error-to-load-model>,
     'endpoint_obj':<loaded_query_objects>,
     'type':<object-type>,
     'status':<LoadSuccessful-or-LoadFailed-or-LoadInProgress>}

    """
    def __init__(self,
                 query_objects=None):

        self.EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.query_objects = query_objects or {}

    def _load_object(self, object_uri, object_url, object_version, is_update, object_type):
        try:
            log_info(msg="Loading object",
                uri=object_uri, url=object_url,
                version=object_version, is_update=is_update)
            if object_type == 'model':
                po = QueryObject.load(object_url)
            elif object_type == 'alias':
                po = object_url
            else:
                raise RuntimeError('Unknown object type: %s' % object_type)

            self.query_objects[object_uri] = {'version': object_version,
                                                   'type': object_type,
                                                   'endpoint_obj': po,
                                                   'status': 'LoadSuccessful',
                                                   'last_error': None}
        except Exception as e:
            log_error("Unable to load QueryObject", path=object_url, error=str(e))

            self.query_objects[object_uri] = {'version': object_version,
                                                   'type': object_type,
                                                   'endpoint_obj': None,
                                                   'status': 'LoadFailed',
                                                   'last_error': 'Load failed: %s' % str(e)}

    def load_object(self, object_uri, object_url, object_version, is_update, object_type):
            try:
                obj_info = self.query_objects.get(object_uri)
                if obj_info and obj_info['endpoint_obj'] and obj_info['version'] >= object_version:
                    log_info("Received load message for object already loaded")

                    return DownloadSkipped(object_uri, obj_info['version'], "Object with greater " \
                                           "or equal version already loaded")
                else:
                    if object_uri not in self.query_objects:
                        self.query_objects[object_uri] = {'version': object_version,
                                                               'type': object_type,
                                                               'endpoint_obj': None,
                                                               'status': 'LoadInProgress',
                                                               'last_error': None}
                    else:
                        self.query_objects[object_uri]['status'] = 'LoadInProgress'

                    self.EXECUTOR.submit(self._load_object, object_uri, object_url,\
                             object_version, is_update, object_type)

                    return LoadInProgress(
                            object_uri, object_url, object_version, is_update, object_type)
            except Exception as e:
                log_error("Unable to load QueryObject", path=object_url, error=str(e))

                self.query_objects[object_uri] = {'version': object_version,
                                                       'type': object_type,
                                                       'endpoint_obj': None,
                                                       'status': 'LoadFailed',
                                                       'last_error': str(e)}

                return LoadFailed(object_uri, object_version, str(e))

    def delete_objects(self, object_uris):
        """Delete one or more objects from the query_objects map"""
        if isinstance(object_uris, list):
            deleted = []
            for uri in object_uris:
                deleted.extend(self.delete_objects(uri).uris)
            return ObjectsDeleted(deleted)
        elif isinstance(object_uris, str) or isinstance(object_uris, unicode):
            deleted_obj = self.query_objects.pop(object_uris, None)
            if deleted_obj:
                return ObjectsDeleted([object_uris])
            else:
                log_warning("Received message to delete query object " \
                            "that doesn't exist", object_uris=object_uris)
                return ObjectsDeleted([])
        else:
            log_error("Unexpected input to delete objects", input=object_uris,
                    info="Input should be list or str. Type: %s" % type(object_uris))
            return ObjectsDeleted([])

    def flush_objects(self):
        """Flush objects from the query_objects map"""
        n = len(self.query_objects)
        self.query_objects.clear()
        return ObjectsFlushed(n, 0)

    def count_objects(self):
        """Count the number of Loaded QueryObjects stored in memory"""
        count = 0
        for uri, po in (self.query_objects.items() if sys.version_info > (3, 0) else self.query_objects.iteritems()):
            if po['endpoint_obj'] is not None:
                count += 1
        return ObjectCount(count)

    def list_objects(self):
        """List the objects as (URI, version) pairs"""

        objects = {}
        for (uri, obj_info) in (self.query_objects.items() if sys.version_info > (3, 0) else self.query_objects.iteritems()):
            objects[uri] = {'version': obj_info['version'],
                            'type': obj_info['type'],
                            'status': obj_info['status'],
                            'reason': obj_info['last_error']}

        return ObjectList(objects)

    def query(self, object_uri, params, uid):
        """Execute a QueryObject query"""
        try:
            if not isinstance(params, dict) and not isinstance(params, list):
                return QueryFailed(
                    uri=object_uri,
                    error="Query parameter needs to be a dictionary or a list. Given value is of type %s." % type(params))

            obj_info = self.query_objects.get(object_uri)
            if obj_info:
                pred_obj = obj_info['endpoint_obj']
                version = obj_info['version']

                if not pred_obj:
                    return QueryFailed(uri=object_uri,
                        error= "There is no query object associated to the endpoint: %s" % object_uri)

                if isinstance(params, dict):
                    result = pred_obj.query(**params)
                else:
                    result = pred_obj.query(*params)

                return QuerySuccessful(object_uri, version, result)
            else:
                return UnknownURI(object_uri)
        except Exception as e:
            err_msg = format_exception(e, '/query')
            log_error(err_msg)
            return QueryFailed(uri=object_uri, error=err_msg)
