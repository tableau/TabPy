import os
import sys
import base64
from time import sleep
from tornado import gen
from tornado.httpclient import AsyncHTTPClient
from common.messages import (LoadObject, DeleteObjects, Msg,
                            ListObjects, ObjectList)

from common.endpoint_file_mgr import cleanup_endpoint_files, \
                        get_local_endpoint_file_path
from common.util import format_exception
from management.state import TabPyState, get_query_object_path
from common.config import TABPY_QUERY_OBJECT_PATH

from management import util

from common.tabpy_logging import PYLogging, log_error, log_info, log_debug, log_warning

import logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)
PYLogging.initialize(logger)

def wait_for_endpoint_loaded(py_handler, object_uri):
    '''
    This method waits for the object to be loaded.
    '''
    log_info('Waiting for object to be loaded...')
    while True:
        msg = ListObjects()
        list_object_msg = py_handler.manage_request(msg)
        if not isinstance(list_object_msg, ObjectList):
            log_error("Error loading endpoint %s: %s" % (object_uri, list_object_msg))
            return
        for (uri, info) in (list_object_msg.objects.items() if sys.version_info > (3,0) else list_object_msg.objects.iteritems()):
            if uri == object_uri:
                if info['status'] != 'LoadInProgress':
                    log_info("Object load status: %s" % info['status'])
                    return


        sleep(0.1)

@gen.coroutine
def init_ps_server(settings):
    tabpy = settings['tabpy']
    existing_pos = tabpy.get_endpoints()
    for (object_name, obj_info) in (existing_pos.items() if sys.version_info > (3,0) else existing_pos.iteritems()):
        try:
            object_version = obj_info['version']
            object_type = obj_info['type']
            object_path = get_query_object_path(
                                os.environ['TABPY_STATE_PATH'],
                                object_name, object_version)
        except Exception as e:
            log_error('Exception encounted when downloading object: %s, error: %s' % \
                                            (object_name, e))


@gen.coroutine
def init_model_evaluator(settings):
    '''
    This will go through all models that the service currently have and initialize them.
    '''
    try:
        tabpy = settings['tabpy']
        py_handler = settings['py_handler']

        existing_pos = tabpy.get_endpoints()
        
        for (object_name, obj_info) in (existing_pos.items() if sys.version_info > (3,0) else existing_pos.iteritems()):
            object_version = obj_info['version']
            object_type = obj_info['type']
            object_path = get_query_object_path(
                os.environ['TABPY_STATE_PATH'],
                object_name, object_version)

            log_info('Load endpoint: %s, version: %s, type: %s' % \
                                (object_name, object_version, object_type))
            if object_type == 'alias':
                msg = LoadObject(object_name, obj_info['target'], object_version,
                    False, 'alias')
            else:
                local_path = object_path                    
                msg = LoadObject(object_name, local_path, object_version,
                            False, object_type)
            py_handler.manage_request(msg)

    except Exception as e:
        err_msg = format_exception(e, "Exception encounted when initializing evaluator host:%s" % host_to_initialize)
        log_error(err_msg)

def _get_latest_service_state(settings, new_ps_state):
    '''
    Update the endpoints from the latest remote state file.
    
    Returns
    --------
    (has_changes, endpoint_diff):
        has_changes: True or False
        endpoint_diff: Summary of what has changed, one entry for each changes
    '''
    tabpy = settings['tabpy']

    # Shortcut when nothing is changed
    changes = {'endpoints': {}}

    # update endpoints
    new_endpoints = new_ps_state.get_endpoints()
    diff = {}
    current_endpoints = settings['py_handler'].ps.query_objects
    for (endpoint_name, endpoint_info) in new_endpoints.items():
        existing_endpoint = current_endpoints.get(endpoint_name)
        if (existing_endpoint is None) or \
                endpoint_info['version'] != existing_endpoint['version']:
            # Either a new endpoint or new endpoint version
            path_to_new_version = get_query_object_path(
                os.environ['TABPY_STATE_PATH'],
                endpoint_name, endpoint_info['version'])
            endpoint_type = endpoint_info.get('type', 'model')
            diff[endpoint_name] = \
                    (endpoint_type, 
                     endpoint_info['version'],\
                     path_to_new_version)

    # add removed models too
    for (endpoint_name, endpoint_info) in current_endpoints.items():
        if endpoint_name not in new_endpoints.keys():
            endpoint_type = current_endpoints[endpoint_name].get('type', 'model')
            diff[endpoint_name] = (endpoint_type, None, None)

    if diff:
        changes['endpoints'] = diff

    settings['tabpy'] = new_ps_state
    return (True, changes)

@gen.coroutine
def on_state_change(settings):
    try:
        tabpy = settings['tabpy']
        py_handler = settings['py_handler']

        log_info("Loading state from state file")
        state_file_path = os.environ['TABPY_STATE_PATH']
        config = util._get_state_from_file(state_file_path)
        new_ps_state = TabPyState(config=config)

        (has_changes, changes) = _get_latest_service_state(settings, new_ps_state)
        if not has_changes:
            log_info("Nothing changed, return.")
            return

        new_endpoints = new_ps_state.get_endpoints()
        for object_name in changes['endpoints']:
            (object_type, object_version, object_path) = changes['endpoints'][object_name]

            if not object_path and not object_version:  # removal
                log_info("Removing object", uri=object_name)

                py_handler.manage_request(DeleteObjects([object_name]))

                cleanup_endpoint_files(object_name)

            else:
                endpoint_info = new_endpoints[object_name]
                is_update = object_version > 1
                if object_type == 'alias':
                    msg = LoadObject(object_name, endpoint_info['target'], object_version,
                                       is_update, 'alias')
                else:
                    local_path = object_path
                    msg = LoadObject(object_name, local_path, object_version,
                                       is_update, object_type)

                py_handler.manage_request(msg)
                wait_for_endpoint_loaded(py_handler, object_name)

                # cleanup old version of endpoint files
                if object_version > 2:
                    cleanup_endpoint_files(object_name, [object_version, object_version - 1])

    except Exception as e:
        err_msg = format_exception(e, 'on_state_change')
        log_warning("Error submitting update model request", error=err_msg)
