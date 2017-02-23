import os
import sys
import simplejson
import multiprocessing
import time
from time import sleep
from uuid import uuid4 as random_uuid
import shutil
from re import compile as _compile

import uuid
import urllib
import functools
import requests
import tornado
import tornado.options
import tornado.web
import tornado.ioloop
from tornado import gen
from tornado_json.constants import TORNADO_MAJOR

from hashlib import md5
from argparse import ArgumentParser

from psws.python_service import PythonService
from psws.python_service import PythonServiceHandler

from common.util import format_exception
from common.config import (DEFAULT_TABPY_PORT, TABPY_QUERY_OBJECT_PATH, SERVER_VERSION)
from common.tabpy_logging import PYLogging, log_error, log_info, log_debug
from common.messages import *
from psws.callbacks import (init_ps_server, init_model_evaluator, on_state_change)

from management.util import _get_state_from_file
from management.state import TabPyState, get_query_object_path
import concurrent.futures


import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
PYLogging.initialize(logger)

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
    parser.add_argument('--port', type=int, help='Listening port for this service.')
    return parser.parse_args()

def copy_from_local(localpath, remotepath, is_dir = False):
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
                    full_remote_path = os.path.join(remotepath,
                                                        file_name)
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
        return {"data":data.get("data"), "method":data.get("method")}
    elif "data" in data:
        return data.get("data")
    else:
        raise RuntimeError("Expect input data is a dictionary with at least a key called 'data'")

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
        print(info)
        self.write(simplejson.dumps({'message': log_message, 'info': info or {}}))
        log_error(log_message, info = info)
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
        if len(self.tabpy.get_cors_origin()) > 0:
            self.set_header("Access-Control-Allow-Origin",
                            self.tabpy.get_cors_origin())
            self.set_header("Access-Control-Allow-Headers",
                            "Origin, X-Requested-With, Content-Type, Accept, Authorization")
            self.set_header("Access-Control-Allow-Methods",
                            "OPTIONS, POST, GET")

    def _sanitize_request_data(self, data, keys = KEYS_TO_SANITIZE):
        """Remove keys so that we can log safely"""
        for key in keys:
            data.pop(key, None)

class MainHandler(BaseHandler):
    def initialize(self):
        super(MainHandler, self).initialize()

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
        _name_checker = _compile('^[a-zA-Z0-9-_\ ]+$')
        if not isinstance(name, (str,unicode)):
            raise TypeError("Endpoint name must be a string or unicode")

        if not _name_checker.match(name):
            raise gen.Return('endpoint name can only contain: a-z, A-Z, 0-9,'
            ' underscore, hyphens and spaces.')

        if self.settings.get('add_or_updating_endpoint'):
            raise RuntimeError("Another endpoint update is already in progress, "
                                "please wait a while and try again")

        request_uuid = random_uuid()
        self.settings['add_or_updating_endpoint'] = request_uuid
        try:
            description = request_data['description'] if 'description' in request_data else None
            if 'docstring' in request_data:
                if sys.version_info > (3, 0):
                    docstring = str(bytes(request_data['docstring'], "utf-8").decode('unicode_escape'))
                else:
                    docstring = request_data['docstring'].decode('string_escape')
            else:
                docstring=None
            endpoint_type = request_data['type'] if 'type' in request_data else None
            methods = request_data['methods'] if 'methods' in request_data else []
            dependencies = request_data['dependencies'] if 'dependencies' in request_data else None
            target = request_data['target'] if 'target' in request_data else None
            schema = request_data['schema'] if 'schema' in request_data else None

            src_path = request_data['src_path'] if 'src_path' in request_data else None
            target_path = get_query_object_path(self.settings['state_file_path'], name, version)
            _path_checker = _compile('^[\\a-zA-Z0-9-_\ /]+$')
            # copy from staging
            if src_path:
                if not isinstance(request_data['src_path'], (str,unicode)):
                    raise gen.Return("src_path must be a string.")
                if not _path_checker.match(src_path):
                    raise gen.Return('Endpoint name can only contain: a-z, A-Z, 0-9,underscore, hyphens and spaces.')

                yield self._copy_po_future(src_path, target_path)
            elif endpoint_type != 'alias':
                    raise gen.Return("src_path is required to add/update an endpoint.")

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
        future = STAGING_THREAD.submit(copy_from_local, src_path, target_path, is_dir=True)
        ret = yield future
        raise gen.Return(ret)


class ServiceInfoHandler(ManagementHandler):
    def initialize(self):
        super(ServiceInfoHandler, self).initialize()

    def get(self):
        info = {}
        info['state_path'] = self.settings['state_file_path']
        info['name'] = self.tabpy.name
        info['description'] = self.tabpy.get_description()
        info['server_version'] = SERVER_VERSION
        info['creation_time'] = self.tabpy.creation_time
        self.write(simplejson.dumps(info))

class StatusHandler(BaseHandler):
    def initialize(self):
        super(StatusHandler, self).initialize()

    def get(self):
        self._add_CORS_header()
        status_dict = {}
        for k, v in self.py_handler.ps.query_objects.items():
            status_dict[k] = {'version':v['version'], 'type':v['type'], 'status':v['status'], 'last_error':v['last_error']}
        self.write(simplejson.dumps(status_dict))

class UploadDestinationHandler(ManagementHandler):
    def initialize(self):
        super(UploadDestinationHandler, self).initialize()

    def get(self):
        path = self.settings['state_file_path']
        path = os.path.join(path, _QUERY_OBJECT_STAGING_FOLDER)
        self.write({"path": path})


class EndpointsHandler(ManagementHandler):
    def initialize(self):
        super(EndpointsHandler, self).initialize()

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
                request_data = simplejson.loads(self.request.body.decode('utf-8'))
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

            err_msg = yield self._add_or_update_endpoint('add', name, 1, request_data)
            if err_msg:
                self.error_out(400, err_msg)
            else:
                self.set_status(201)
                self.write(self.tabpy.get_endpoints(name))
                self.finish()

        except Exception as e:
            err_msg = format_exception(e, '/add_endpoint')
            self.error_out(500, "error adding endpoint", err_msg)
            self.finish()
            return

class EndpointHandler(ManagementHandler):
    def initialize(self):
        super(EndpointHandler, self).initialize()

    def get(self, endpoint_name):
        self._add_CORS_header()
        if not endpoint_name:
            self.write(simplejson.dumps(self.tabpy.get_endpoints()))
        else:
            if endpoint_name in self.tabpy.get_endpoints():
                self.write(simplejson.dumps(self.tabpy.get_endpoints()[endpoint_name]))
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
                request_data = simplejson.loads(self.request.body.decode('utf-8'))
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
            log_info('Endpoint info: %s' % request_data)
            err_msg = yield self._add_or_update_endpoint('update', name, new_version, request_data)
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
                delete_path = get_query_object_path(self.settings['state_file_path'], name, None)
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
                    self.error_out(400, 'Script parameters need to be provided as a dictionary.')
                    return
                else:
                    arguments_expected = []
                    for i in range(1, len(arguments.keys())+1):
                        arguments_expected.append('_arg'+str(i))
                    if sorted(arguments_expected)==sorted(arguments.keys()):
                        arguments_str = ', ' + ', '.join(arguments.keys())
                    else:
                        self.error_out(400, 'Variables names should follow the format _arg1, _arg2, _argN')
                        return


            function_to_evaluate = 'def _user_script(tabpy' + arguments_str + '):\n'
            for u in user_code.splitlines():
                function_to_evaluate += ' ' + u + '\n'

            log_info("function to evaluate=%s" % function_to_evaluate)


            result = yield self.call_subprocess(function_to_evaluate, arguments)
            if result is None:
                self.error_out(400, 'Error running script. No return value')
            else:
                self.write(simplejson.dumps(result))
                self.finish()

        except Exception as e:
            err_msg = "%s : " % e.__class__.__name__
            err_msg += "%s" % str(e)
            if err_msg!="KeyError : 'response'":
                err_msg = format_exception(e, 'POST /evaluate')
                self.error_out(500, 'Error processing script', info = err_msg)
            else:
                self.error_out(404, 'Error processing script',
                       info="The endpoint you're trying to query did not respond. Please make sure the endpoint exists and the correct set of arguments are provided.")


    @gen.coroutine
    def call_subprocess(self, function_to_evaluate, arguments):
        restricted_tabpy = RestrictedTabPy(self.port)
        # Exec does not run the function, so it does not block.
        if sys.version_info > (3, 0):
            exec(function_to_evaluate,globals())
        else:
            exec(function_to_evaluate)

        if arguments is None:
            future = self.executor.submit(_user_script, restricted_tabpy)
        else:
            future = self.executor.submit(_user_script, restricted_tabpy, **arguments)
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
        response = requests.post(url = url, data=data, headers=headers,\
                                timeout=30)

        return response.json()

class QueryPlaneHandler(BaseHandler):
    def initialize(self):
        super(QueryPlaneHandler, self).initialize()

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
            self.set_header("Etag", '"%s"' % md5(response_json.encode('utf-8')).hexdigest())
            return (QuerySuccessful, response.for_json(), gls_time)
        else:
            log_error("Failed query", response=response)
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
                               info="No query object has been registered" \
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
            (po_name, all_endpoint_names) = self._get_actual_model(endpoint_name)

            ## po_name is None if self.py_handler.ps.query_objects.get(endpoint_name) is None
            if not po_name:
                log_error("UnknownURI", endpoint_name = endpoint_name)
                self.error_out(404, 'UnknownURI', info="Endpoint '%s' does not exist" % endpoint_name)
                return

            po_obj = self.py_handler.ps.query_objects.get(po_name)

            if not po_obj:
                log_error("UnknownURI", endpoint_name = po_name)
                self.error_out(404, 'UnknownURI',info="Endpoint '%s' does not exist" % po_name)
                return

            if po_name != endpoint_name:
                log_info("Querying actual model", po_name = po_name)

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
            self.error_out(500, 'Error processing query', info = err_msg)
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
                       info="Endpoint type '%s' does not exist" % endpoint_type)
                return

        return (endpoint_name, all_endpoint_names)


    @tornado.web.asynchronous
    def get(self, endpoint_name):
        start = time.time()
        if sys.version_info > (3, 0):
            endpoint_name = urllib.parse.unquote(endpoint_name)
        else:
            endpoint_name = urllib.unquote(endpoint_name)
        log_debug("GET /query", endpoint_name=endpoint_name)
        self._process_query(endpoint_name, start)

    @tornado.web.asynchronous
    def post(self, endpoint_name):
        start = time.time()
        if sys.version_info > (3, 0):
            endpoint_name = urllib.parse.unquote(endpoint_name)
        else:
            endpoint_name = urllib.unquote(endpoint_name)
        log_debug("POST /query", endpoint_name=endpoint_name)
        self._process_query(endpoint_name, start)

def main():
    args = parse_arguments()
    port = args.port
    if not port:
        port = DEFAULT_TABPY_PORT
    log_info("Loading state from state file")
    state_file_path = os.environ['TABPY_STATE_PATH']
    config = _get_state_from_file(state_file_path)
    tabpy = TabPyState(config=config)

    python_service_handler = PythonServiceHandler(PythonService())

    state_file_path = os.path.realpath(
        os.path.normpath(
            os.path.expanduser(
                os.environ.get('TABPY_STATE_PATH', './state'))))

    # initialize settings for application handlers
    settings = {
        "compress_response" if TORNADO_MAJOR >= 4 else "gzip": True,
        "tabpy": tabpy,
        "py_handler": python_service_handler,
        "port": port,
        "state_file_path": state_file_path,
        "static_path": os.path.join(os.path.dirname(__file__), "static")}

    print('Initializing TabPy...')
    tornado.ioloop.IOLoop.instance().run_sync(lambda: init_ps_server(settings))
    print('Done initializing TabPy.')

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=multiprocessing.cpu_count())

    # Set subdirectory from config if applicable
    subdirectory = ""
    if config.has_option("Service Info", "Subdirectory"):
        subdirectory = "/" + config.get("Service Info", "Subdirectory")

    # initialize Tornado application
    application = tornado.web.Application([
        # skip MainHandler to use StaticFileHandler .* page requests and default to index.html
        # (r"/", MainHandler),
        (subdirectory + r'/query/([^/]+)', QueryPlaneHandler),
        (subdirectory + r'/status', StatusHandler),
        (subdirectory + r'/info', ServiceInfoHandler),
        (subdirectory + r'/endpoints', EndpointsHandler),
        (subdirectory + r'/endpoints/([^/]+)?', EndpointHandler),
        (subdirectory + r'/evaluate', EvaluationPlaneHandler, dict(executor=executor)),
        (subdirectory + r'/configurations/endpoint_upload_destination', UploadDestinationHandler),
        (subdirectory + r'/(.*)', tornado.web.StaticFileHandler,dict(path=settings['static_path'],default_filename="index.html")),
    ], debug=False, **settings)

    settings = application.settings

    init_model_evaluator(settings)

    application.listen(port)
    print('Web service listening on port ' + str(port))
    tornado.ioloop.IOLoop.instance().start()

if __name__ == '__main__':
    main()
