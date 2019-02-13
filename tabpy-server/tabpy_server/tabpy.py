from argparse import ArgumentParser
import concurrent.futures
import configparser
from datetime import datetime
import logging.config
import multiprocessing
from OpenSSL import crypto
import os
import shutil
import sys
from tabpy_server import __version__
from tabpy_server.handlers import (EndpointHandler, EndpointsHandler, EvaluationPlaneHandler, QueryPlaneHandler,
                                   ServiceInfoHandler, StatusHandler, UploadDestinationHandler)
from tabpy_server.psws.python_service import PythonService
from tabpy_server.psws.python_service import PythonServiceHandler
from tabpy_server.psws.callbacks import init_ps_server, init_model_evaluator
from tabpy_server.management.util import _get_state_from_file
from tabpy_server.management.state import TabPyState
import tornado
import tornado.options
import tornado.web
import tornado.ioloop
from tornado_json.constants import TORNADO_MAJOR


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
