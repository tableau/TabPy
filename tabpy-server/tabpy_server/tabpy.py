from argparse import ArgumentParser
import concurrent.futures
import configparser
from datetime import datetime
from hashlib import md5
from io import StringIO
import logging
import logging.config
import multiprocessing
from OpenSSL import crypto
import os
from pathlib import Path
from re import compile as _compile
import requests
import shutil
import simplejson
import sys
from tabpy_server import __version__
from tabpy_server.psws.python_service import PythonService
from tabpy_server.psws.python_service import PythonServiceHandler
from tabpy_server.common.util import format_exception
from tabpy_server.common.messages import (
    Query, QuerySuccessful, QueryError, UnknownURI)
from tabpy_server.psws.callbacks import (
    init_ps_server, init_model_evaluator, on_state_change)
from tabpy_server.management.util import _get_state_from_file
from tabpy_server.management.state import TabPyState, get_query_object_path
import tempfile
import time
import tornado
import tornado.options
import tornado.web
import tornado.ioloop
from tornado import gen
from tornado_json.constants import TORNADO_MAJOR
from uuid import uuid4 as random_uuid
import urllib
import uuid


STAGING_THREAD = concurrent.futures.ThreadPoolExecutor(max_workers=3)
_QUERY_OBJECT_STAGING_FOLDER = 'staging'

if sys.version_info.major == 3:
    unicode = str

def parse_arguments():
    '''
    Parse input arguments and return the parsed arguments. Expected arguments:
    * --port : int
    '''
    parser = ArgumentParser(description='Run Python27 Service.')
    parser.add_argument('--port', type=int,
                        help='Listening port for this service.')
    parser.add_argument('--config', help='Path to a config file.')
    return parser.parse_args()


cli_args = parse_arguments()
config_file = cli_args.config if cli_args.config is not None else os.path.join(os.path.dirname(__file__), 'common',
                                                                        'default.conf')
loggingConfigured = False
if os.path.isfile(config_file):
    try:
        logging.config.fileConfig(config_file, disable_existing_loggers=False)
        loggingConfigured = True
    except:
        pass

if not loggingConfigured:
    logging.basicConfig(level=logging.DEBUG)

logger = logging.getLogger(__name__)


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

def _sanitize_request_data(data):
    if not isinstance(data, dict):
        raise RuntimeError("Expect input data to be a dictionary")

    if "method" in data:
        return {"data": data.get("data"), "method": data.get("method")}
    elif "data" in data:
        return data.get("data")
    else:
        raise RuntimeError("Expect input data is a dictionary with at least a "
                           "key called 'data'")


def _get_uuid():
    """Generate a unique identifier string"""
    return str(uuid.uuid4())


class BaseHandler(tornado.web.RequestHandler):
    KEYS_TO_SANITIZE = ("api key", "api_key", "admin key", "admin_key")

    def initialize(self):
        self.tabpy = self.settings['tabpy']
        # set content type to application/json
        self.set_header("Content-Type", "application/json")
        self.port = self.settings['port']
        self.py_handler = self.settings['py_handler']

    def error_out(self, code, log_message, info=None):
        self.set_status(code)
        self.write(simplejson.dumps(
            {'message': log_message, 'info': info or {}}))

        # We want to duplicate error message in console for
        # loggers are misconfigured or causing the failure
        # themselves
        print(info)
        logger.error('message: {}, info: {}'.format(log_message, info))
        self.finish()

    def options(self):
        # add CORS headers if TabPy has a cors_origin specified
        self._add_CORS_header()
        self.write({})

    def _add_CORS_header(self):
        """
        Add CORS header if the TabPy has attribute _cors_origin
        and _cors_origin is not an empty string.
        """
        origin = self.tabpy.get_access_control_allow_origin()
        if len(origin) > 0:
            self.set_header("Access-Control-Allow-Origin", origin)
            logger.debug("Access-Control-Allow-Origin:{}".format(origin))

        headers = self.tabpy.get_access_control_allow_headers()
        if len(headers) > 0:
            self.set_header("Access-Control-Allow-Headers",headers)
            logger.debug("Access-Control-Allow-Headers:{}".format(headers))

        methods = self.tabpy.get_access_control_allow_methods()
        if len(methods) > 0:
            self.set_header("Access-Control-Allow-Methods",methods)
            logger.debug("Access-Control-Allow-Methods:{}".format(methods))

    def _sanitize_request_data(self, data, keys=KEYS_TO_SANITIZE):
        """Remove keys so that we can log safely"""
        for key in keys:
            data.pop(key, None)


class MainHandler(BaseHandler):

    def get(self):
        self._add_CORS_header()
        self.render('/static/index.html')


class ManagementHandler(MainHandler):
    def initialize(self):
        super(ManagementHandler, self).initialize()
        self.port = self.settings['port']

    def _get_protocol(self):
        return 'http://'

    @gen.coroutine
    def _add_or_update_endpoint(self, action, name, version, request_data):
        '''
        Add or update an endpoint
        '''
        logging.debug("Adding/updating model {}...".format(name))
        _name_checker = _compile('^[a-zA-Z0-9-_\ ]+$')
        if not isinstance(name, (str, unicode)):
            raise TypeError("Endpoint name must be a string or unicode")

        if not _name_checker.match(name):
            raise gen.Return('endpoint name can only contain: a-z, A-Z, 0-9,'
                             ' underscore, hyphens and spaces.')

        if self.settings.get('add_or_updating_endpoint'):
            raise RuntimeError("Another endpoint update is already in progress"
                               ", please wait a while and try again")

        request_uuid = random_uuid()
        self.settings['add_or_updating_endpoint'] = request_uuid
        try:
            description = (request_data['description'] if 'description' in
                                                          request_data else None)
            if 'docstring' in request_data:
                if sys.version_info > (3, 0):
                    docstring = str(bytes(request_data['docstring'],
                                          "utf-8").decode('unicode_escape'))
                else:
                    docstring = request_data['docstring'].decode(
                        'string_escape')
            else:
                docstring = None
            endpoint_type = (request_data['type'] if 'type' in request_data
                             else None)
            methods = (request_data['methods'] if 'methods' in request_data
                       else [])
            dependencies = (request_data['dependencies'] if 'dependencies' in
                                                            request_data else None)
            target = (request_data['target'] if 'target' in request_data
                      else None)
            schema = (request_data['schema'] if 'schema' in request_data
                      else None)

            src_path = (request_data['src_path'] if 'src_path' in request_data
                        else None)
            target_path = get_query_object_path(
                self.settings['state_file_path'], name, version)
            _path_checker = _compile('^[\\a-zA-Z0-9-_\ /]+$')
            # copy from staging
            if src_path:
                if not isinstance(request_data['src_path'], (str, unicode)):
                    raise gen.Return("src_path must be a string.")
                if not _path_checker.match(src_path):
                    raise gen.Return('Endpoint name can only contain: a-z, A-'
                                     'Z, 0-9,underscore, hyphens and spaces.')

                yield self._copy_po_future(src_path, target_path)
            elif endpoint_type != 'alias':
                raise gen.Return("src_path is required to add/update an "
                                 "endpoint.")

            # alias special logic:
            if endpoint_type == 'alias':
                if not target:
                    raise gen.Return('Target is required for alias endpoint.')
                dependencies = [target]

            # update local config
            try:
                if action == 'add':
                    self.tabpy.add_endpoint(
                        name=name,
                        description=description,
                        docstring=docstring,
                        endpoint_type=endpoint_type,
                        methods=methods,
                        dependencies=dependencies,
                        target=target,
                        schema=schema)
                else:
                    self.tabpy.update_endpoint(
                        name=name,
                        description=description,
                        docstring=docstring,
                        endpoint_type=endpoint_type,
                        methods=methods,
                        dependencies=dependencies,
                        target=target,
                        schema=schema,
                        version=version)

            except Exception as e:
                raise gen.Return("Error when changing TabPy state: %s" % e)

            on_state_change(self.settings)

        finally:
            self.settings['add_or_updating_endpoint'] = None

    @gen.coroutine
    def _copy_po_future(self, src_path, target_path):
        future = STAGING_THREAD.submit(copy_from_local, src_path,
                                       target_path, is_dir=True)
        ret = yield future
        raise gen.Return(ret)


class ServiceInfoHandler(ManagementHandler):

    def get(self):
        self._add_CORS_header()
        info = {}
        info['state_path'] = self.settings['state_file_path']
        info['name'] = self.tabpy.name
        info['description'] = self.tabpy.get_description()
        info['server_version'] = self.settings['server_version']
        info['creation_time'] = self.tabpy.creation_time
        self.write(simplejson.dumps(info))


class StatusHandler(BaseHandler):

    def get(self):
        self._add_CORS_header()

        logger.debug("Obtaining service status")
        status_dict = {}
        for k, v in self.py_handler.ps.query_objects.items():
            status_dict[k] = {
                'version': v['version'],
                'type': v['type'],
                'status': v['status'],
                'last_error': v['last_error']}

        logger.debug("Found models: {}".format(status_dict))
        self.write(simplejson.dumps(status_dict))
        self.finish()
        return


class UploadDestinationHandler(ManagementHandler):

    def get(self):
        path = self.settings['state_file_path']
        path = os.path.join(path, _QUERY_OBJECT_STAGING_FOLDER)
        self.write({"path": path})


class EndpointsHandler(ManagementHandler):

    def get(self):
        self._add_CORS_header()
        self.write(simplejson.dumps(self.tabpy.get_endpoints()))

    @tornado.web.asynchronous
    @gen.coroutine
    def post(self):
        try:
            if not self.request.body:
                self.error_out(400, "Input body cannot be empty")
                self.finish()
                return

            try:
                request_data = simplejson.loads(
                    self.request.body.decode('utf-8'))
            except:
                self.error_out(400, "Failed to decode input body")
                self.finish()
                return

            if 'name' not in request_data:
                self.error_out(400,
                               "name is required to add an endpoint.")
                self.finish()
                return

            name = request_data['name']

            # check if endpoint already exist
            if name in self.tabpy.get_endpoints():
                self.error_out(400, "endpoint %s already exists." % name)
                self.finish()
                return

            logger.debug("Adding endpoint '{}'".format(name))
            err_msg = yield self._add_or_update_endpoint('add', name, 1,
                                                         request_data)
            if err_msg:
                self.error_out(400, err_msg)
            else:
                logger.debug("Endopoint {} successfully added".format(name))
                self.set_status(201)
                self.write(self.tabpy.get_endpoints(name))
                self.finish()
                return

        except Exception as e:
            err_msg = format_exception(e, '/add_endpoint')
            self.error_out(500, "error adding endpoint", err_msg)
            self.finish()
            return


class EndpointHandler(ManagementHandler):

    def get(self, endpoint_name):
        self._add_CORS_header()
        if not endpoint_name:
            self.write(simplejson.dumps(self.tabpy.get_endpoints()))
        else:
            if endpoint_name in self.tabpy.get_endpoints():
                self.write(simplejson.dumps(
                    self.tabpy.get_endpoints()[endpoint_name]))
            else:
                self.error_out(404, 'Unknown endpoint',
                               info='Endpoint %s is not found' % endpoint_name)

    @tornado.web.asynchronous
    @gen.coroutine
    def put(self, name):
        try:
            if not self.request.body:
                self.error_out(400, "Input body cannot be empty")
                self.finish()
                return
            try:
                request_data = simplejson.loads(
                    self.request.body.decode('utf-8'))
            except:
                self.error_out(400, "Failed to decode input body")
                self.finish()
                return

            # check if endpoint exists
            endpoints = self.tabpy.get_endpoints(name)
            if len(endpoints) == 0:
                self.error_out(404,
                               "endpoint %s does not exist." % name)
                self.finish()
                return

            new_version = int(endpoints[name]['version']) + 1
            logger.info('Endpoint info: %s' % request_data)
            err_msg = yield self._add_or_update_endpoint(
                'update', name, new_version, request_data)
            if err_msg:
                self.error_out(400, err_msg)
                self.finish()
            else:
                self.write(self.tabpy.get_endpoints(name))
                self.finish()

        except Exception as e:
            err_msg = format_exception(e, 'update_endpoint')
            self.error_out(500, err_msg)
            self.finish()

    @tornado.web.asynchronous
    @gen.coroutine
    def delete(self, name):
        try:
            endpoints = self.tabpy.get_endpoints(name)
            if len(endpoints) == 0:
                self.error_out(404,
                               "endpoint %s does not exist." % name)
                self.finish()
                return

            # update state
            try:
                endpoint_info = self.tabpy.delete_endpoint(name)
            except Exception as e:
                self.error_out(400,
                               "Error when removing endpoint: %s" % e.message)
                self.finish()
                return

            # delete files
            if endpoint_info['type'] != 'alias':
                delete_path = get_query_object_path(
                    self.settings['state_file_path'], name, None)
                try:
                    yield self._delete_po_future(delete_path)
                except Exception as e:
                    self.error_out(400,
                                   "Error while deleting: %s" % e)
                    self.finish()
                    return

            self.set_status(204)
            self.finish()

        except Exception as e:
            err_msg = format_exception(e, 'delete endpoint')
            self.error_out(500, err_msg)
            self.finish()

        on_state_change(self.settings)

    @gen.coroutine
    def _delete_po_future(self, delete_path):
        future = STAGING_THREAD.submit(shutil.rmtree, delete_path)
        ret = yield future
        raise gen.Return(ret)


class EvaluationPlaneHandler(BaseHandler):
    '''
    EvaluationPlaneHandler is responsible for running arbitrary python scripts.
    '''

    def initialize(self, executor):
        super(EvaluationPlaneHandler, self).initialize()
        self.executor = executor

    @tornado.web.asynchronous
    @gen.coroutine
    def post(self):
        self._add_CORS_header()
        try:
            body = simplejson.loads(self.request.body.decode('utf-8'))
            if 'script' not in body:
                self.error_out(400, 'Script is empty.')
                return

            # Transforming user script into a proper function.
            user_code = body['script']
            arguments = None
            arguments_str = ''
            if 'data' in body:
                arguments = body['data']

            if arguments is not None:
                if not isinstance(arguments, dict):
                    self.error_out(400, 'Script parameters need to be '
                                        'provided as a dictionary.')
                    return
                else:
                    arguments_expected = []
                    for i in range(1, len(arguments.keys()) + 1):
                        arguments_expected.append('_arg' + str(i))
                    if sorted(arguments_expected) == sorted(arguments.keys()):
                        arguments_str = ', ' + ', '.join(arguments.keys())
                    else:
                        self.error_out(400, 'Variables names should follow '
                                            'the format _arg1, _arg2, _argN')
                        return

            function_to_evaluate = ('def _user_script(tabpy'
                                    + arguments_str + '):\n')
            for u in user_code.splitlines():
                function_to_evaluate += ' ' + u + '\n'

            logger.info(
                "function to evaluate=%s" % function_to_evaluate)

            result = yield self.call_subprocess(function_to_evaluate,
                                                arguments)
            if result is None:
                self.error_out(400, 'Error running script. No return value')
            else:
                self.write(simplejson.dumps(result))
                self.finish()

        except Exception as e:
            err_msg = "%s : " % e.__class__.__name__
            err_msg += "%s" % str(e)
            if err_msg != "KeyError : 'response'":
                err_msg = format_exception(e, 'POST /evaluate')
                self.error_out(500, 'Error processing script', info=err_msg)
            else:
                self.error_out(
                    404, 'Error processing script', info="The endpoint you're "
                                                         "trying to query did not respond. Please make sure the "
                                                         "endpoint exists and the correct set of arguments are "
                                                         "provided.")

    @gen.coroutine
    def call_subprocess(self, function_to_evaluate, arguments):
        restricted_tabpy = RestrictedTabPy(self.port)
        # Exec does not run the function, so it does not block.
        if sys.version_info > (3, 0):
            exec(function_to_evaluate, globals())
        else:
            exec(function_to_evaluate)

        if arguments is None:
            future = self.executor.submit(_user_script, restricted_tabpy)
        else:
            future = self.executor.submit(_user_script, restricted_tabpy,
                                          **arguments)
        ret = yield future
        raise gen.Return(ret)


class RestrictedTabPy:
    def __init__(self, port):
        self.port = port

    def query(self, name, *args, **kwargs):
        url = 'http://localhost:%d/query/%s' % (self.port, name)
        internal_data = {'data': args or kwargs}
        data = simplejson.dumps(internal_data)
        headers = {'content-type': 'application/json'}
        response = requests.post(url=url, data=data, headers=headers,
                                 timeout=30)

        return response.json()


class QueryPlaneHandler(BaseHandler):

    def _query(self, po_name, data, uid, qry):
        """
        Parameters
        ----------
        po_name : str
            The name of the query object to query

        data : dict
            The deserialized request body

        uid: str
            A unique identifier for the request

        qry: str
            The incoming query object. This object maintains
            raw incoming request, which is different from the sanitied data

        Returns
        -------
        out : (result type, dict, int)
            A triple containing a result type, the result message
            as a dictionary, and the time in seconds that it took to complete
            the request.
        """
        start_time = time.time()
        response = self.py_handler.ps.query(po_name, data, uid)
        gls_time = time.time() - start_time

        if isinstance(response, QuerySuccessful):
            response_json = response.to_json()
            self.set_header("Etag", '"%s"' % md5(response_json.encode(
                'utf-8')).hexdigest())
            return (QuerySuccessful, response.for_json(), gls_time)
        else:
            logger.error("Failed query, response: {}".format(response))
            return (type(response), response.for_json(), gls_time)

    # handle HTTP Options requests to support CORS
    # don't check API key (client does not send or receive data for OPTIONS,
    # it just allows the client to subsequently make a POST request)
    def options(self, pred_name):
        # add CORS headers if TabPy has a cors_origin specified
        self._add_CORS_header()
        self.write({})

    def _handle_result(self, po_name, data, qry, uid):

        (response_type, response, gls_time) = \
            self._query(po_name, data, uid, qry)

        if response_type == QuerySuccessful:
            result_dict = {
                'response': response['response'],
                'version': response['version'],
                'model': po_name,
                'uuid': uid
            }
            self.write(result_dict)
            self.finish()
            return (gls_time, response['response'])
        else:
            if response_type == UnknownURI:
                self.error_out(404, 'UnknownURI',
                               info="No query object has been registered"
                                    " with the name '%s'" % po_name)
            elif response_type == QueryError:
                self.error_out(400, 'QueryError', info=response)
            else:
                self.error_out(500, 'Error querying GLS', info=response)

            return (None, None)

    def _process_query(self, endpoint_name, start):
        try:
            self._add_CORS_header()

            if not self.request.body:
                self.request.body = {}

            # extract request data explicitly for caching purpose
            request_json = self.request.body.decode('utf-8')

            # Sanitize input data
            data = _sanitize_request_data(simplejson.loads(request_json))
        except Exception as e:
            err_msg = format_exception(e, "Invalid Input Data")
            self.error_out(400, err_msg)
            return

        try:
            (po_name, all_endpoint_names) = self._get_actual_model(
                endpoint_name)

            # po_name is None if self.py_handler.ps.query_objects.get(
            # endpoint_name) is None
            if not po_name:
                self.error_out(404, 'UnknownURI',
                               info="Endpoint '%s' does not exist"
                                    % endpoint_name)
                return

            po_obj = self.py_handler.ps.query_objects.get(po_name)

            if not po_obj:
                self.error_out(404, 'UnknownURI',
                               info="Endpoint '%s' does not exist" % po_name)
                return

            if po_name != endpoint_name:
                logger.info("Querying actual model: po_name={}".format(po_name))

            uid = _get_uuid()

            # record query w/ request ID in query log
            qry = Query(po_name, request_json)
            gls_time = 0
            # send a query to PythonService and return
            (gls_time, result) = self._handle_result(po_name, data, qry, uid)

            # if error occurred, GLS time is None.
            if not gls_time:
                return

        except Exception as e:
            err_msg = format_exception(e, 'process query')
            self.error_out(500, 'Error processing query', info=err_msg)
            return

    def _get_actual_model(self, endpoint_name):
        # Find the actual query to run from given endpoint
        all_endpoint_names = []

        while True:
            endpoint_info = self.py_handler.ps.query_objects.get(endpoint_name)
            if not endpoint_info:
                return [None, None]

            all_endpoint_names.append(endpoint_name)

            endpoint_type = endpoint_info.get('type', 'model')

            if endpoint_type == 'alias':
                endpoint_name = endpoint_info['endpoint_obj']
            elif endpoint_type == 'model':
                break
            else:
                self.error_out(500, 'Unknown endpoint type',
                               info="Endpoint type '%s' does not exist"
                                    % endpoint_type)
                return

        return (endpoint_name, all_endpoint_names)

    @tornado.web.asynchronous
    def get(self, endpoint_name):
        start = time.time()
        if sys.version_info > (3, 0):
            endpoint_name = urllib.parse.unquote(endpoint_name)
        else:
            endpoint_name = urllib.unquote(endpoint_name)
        logger.debug("GET /query/{}".format(endpoint_name))
        self._process_query(endpoint_name, start)

    @tornado.web.asynchronous
    def post(self, endpoint_name):
        start = time.time()
        if sys.version_info > (3, 0):
            endpoint_name = urllib.parse.unquote(endpoint_name)
        else:
            endpoint_name = urllib.unquote(endpoint_name)
        logger.debug("POST /query/{}".format(endpoint_name))
        self._process_query(endpoint_name, start)


def get_config(config_file):
    """Provide consistent mechanism for pulling in configuration.

    Attempt to retain backward compatibility for existing implementations by
    grabbing port setting from CLI first.

    Take settings in the following order:

    1. CLI arguments, if present - port only - may be able to deprecate
    2. common.config file, and
    3. OS environment variables (for ease of setting defaults if not present)
    4. current defaults if a setting is not present in any location

    Additionally provide similar configuration capabilities in between
    common.config and environment variables.
    For consistency use the same variable name in the config file as in the os
    environment.
    For naming standards use all capitals and start with 'TABPY_'
    """
    parser = configparser.ConfigParser()

    if os.path.isfile(config_file):
        with open(config_file) as f:
            parser.read_string(f.read())
    else:
        logger.warning("Unable to find config file at '{}', using default settings.".format(config_file))

    settings = {}
    for section in parser.sections():
        if section == "TabPy":
            for key, val in parser.items(section):
                settings[key] = val
            break

    def set_parameter(settings_key, config_key, default_val=None, check_env_var=False):
        if config_key is not None and parser.has_option('TabPy', config_key):
            settings[settings_key] = parser.get('TabPy', config_key)
        elif check_env_var:
            settings[settings_key] = os.getenv(config_key, default_val)
        elif default_val is not None:
            settings[settings_key] = default_val

    if cli_args is not None and cli_args.port is not None:
        settings['port'] = cli_args.port
    else:
        set_parameter('port', 'TABPY_PORT', default_val=9004, check_env_var=True)
        try:
            settings['port'] = int(settings['port'])
        except ValueError:
            logger.warning('Error during config validation, invalid port: {}. '
                           'Using default port 9004'.format(settings['port']))
            settings['port'] = 9004

    set_parameter('server_version', None, default_val=__version__)
    set_parameter('bind_ip', 'TABPY_BIND_IP', default_val='0.0.0.0', check_env_var=True)

    set_parameter('upload_dir', 'TABPY_QUERY_OBJECT_PATH', default_val='/tmp/query_objects', check_env_var=True)
    if not os.path.exists(settings['upload_dir']):
        os.makedirs(settings['upload_dir'])

    set_parameter('state_file_path', 'TABPY_STATE_PATH', default_val='./', check_env_var=True)
    settings['state_file_path'] = os.path.realpath(
        os.path.normpath(
            os.path.expanduser(settings['state_file_path'])))

    # set and validate transfer protocol
    set_parameter('transfer_protocol', 'TABPY_TRANSFER_PROTOCOL', default_val='http')
    settings['transfer_protocol'] = settings['transfer_protocol'].lower()

    set_parameter('certificate_file', 'TABPY_CERTIFICATE_FILE')
    set_parameter('key_file', 'TABPY_KEY_FILE')
    validate_transfer_protocol_settings(settings)

    # if state.ini does not exist try and create it - remove last dependence
    # on batch/shell script
    state_file_path = settings['state_file_path']
    logger.info("Loading state from state file {}".format(os.path.join(state_file_path, "state.ini")))
    tabpy_state = _get_state_from_file(state_file_path)
    settings['tabpy'] = TabPyState(config=tabpy_state, settings=settings)

    settings['py_handler'] = PythonServiceHandler(PythonService())
    settings['compress_response'] = True if TORNADO_MAJOR >= 4 else "gzip"
    settings['static_path'] = os.path.join(os.path.dirname(__file__), "static")

    # Set subdirectory from config if applicable
    subdirectory = ""
    if tabpy_state.has_option("Service Info", "Subdirectory"):
        subdirectory = "/" + tabpy_state.get("Service Info", "Subdirectory")

    return settings, subdirectory


def validate_transfer_protocol_settings(settings):
    if 'transfer_protocol' not in settings:
        logger.error('Missing transfer protocol information.')
        raise RuntimeError('Missing transfer protocol information.')

    protocol = settings['transfer_protocol']

    if protocol == 'http':
        return

    if protocol != 'https':
        err = 'Unsupported transfer protocol: {}.'.format(protocol)
        logger.fatal(err)
        raise RuntimeError(err)

    validate_cert_key_state('The parameter(s) {} must be set.', 'certificate_file' in settings, 'key_file' in settings)
    cert = settings['certificate_file']

    validate_cert_key_state('The parameter(s) {} must point to an existing file.', os.path.isfile(cert),
                            os.path.isfile(settings['key_file']))
    validate_cert(cert)
    return


def validate_cert_key_state(msg, cert_valid, key_valid):
    cert_param, key_param = 'TABPY_CERTIFICATE_FILE', 'TABPY_KEY_FILE'
    cert_and_key_param = '{} and {}'.format(cert_param, key_param)
    https_error = 'Error using HTTPS: '
    err = None
    if not cert_valid and not key_valid:
        err = https_error + msg.format(cert_and_key_param)
    elif not cert_valid:
        err = https_error + msg.format(cert_param)
    elif not key_valid:
        err = https_error + msg.format(key_param)
    if err is not None:
        logger.fatal(err)
        raise RuntimeError(err)


def validate_cert(cert_file_path):
    with open(cert_file_path, 'r') as f:
        cert_buf = f.read()

    cert = crypto.load_certificate(crypto.FILETYPE_PEM, cert_buf)

    date_format, encoding = '%Y%m%d%H%M%SZ', 'ascii'
    not_before = datetime.strptime(cert.get_notBefore().decode(encoding), date_format)
    not_after = datetime.strptime(cert.get_notAfter().decode(encoding), date_format)
    now = datetime.now()

    https_error = 'Error using HTTPS: '
    if now < not_before:
        raise RuntimeError(https_error + 'The certificate provided is not valid until {}.'.format(not_before))
    if now > not_after:
        raise RuntimeError(https_error + 'The certificate provided expired on {}.'.format(not_after))


def main():
    settings, subdirectory = get_config(config_file)

    logger.info('Initializing TabPy...')
    tornado.ioloop.IOLoop.instance().run_sync(lambda: init_ps_server(settings))
    logger.info('Done initializing TabPy.')

    executor = concurrent.futures.ThreadPoolExecutor(
        max_workers=multiprocessing.cpu_count())

    # initialize Tornado application
    application = tornado.web.Application([
        # skip MainHandler to use StaticFileHandler .* page requests and
        # default to index.html
        # (r"/", MainHandler),
        (subdirectory + r'/query/([^/]+)', QueryPlaneHandler),
        (subdirectory + r'/status', StatusHandler),
        (subdirectory + r'/info', ServiceInfoHandler),
        (subdirectory + r'/endpoints', EndpointsHandler),
        (subdirectory + r'/endpoints/([^/]+)?', EndpointHandler),
        (subdirectory + r'/evaluate', EvaluationPlaneHandler,
         dict(executor=executor)),
        (subdirectory + r'/configurations/endpoint_upload_destination',
         UploadDestinationHandler),
        (subdirectory + r'/(.*)', tornado.web.StaticFileHandler,
         dict(path=settings['static_path'], default_filename="index.html")),
    ], debug=False, **settings)

    settings = application.settings

    init_model_evaluator(settings)

    if settings['transfer_protocol'] == 'http':
        application.listen(settings['port'], address=settings['bind_ip'])
    elif settings['transfer_protocol'] == 'https':
        application.listen(settings['port'], address=settings['bind_ip'],
                           ssl_options={
                               'certfile': settings['certificate_file'],
                               'keyfile': settings['key_file']
                           })
    else:
        raise RuntimeError('Unsupported transfer protocol.')

    logger.info('Web service listening on {} port {}'.format(settings['bind_ip'],
                                                             str(settings['port'])))
    tornado.ioloop.IOLoop.instance().start()


if __name__ == '__main__':
    main()
