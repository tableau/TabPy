import concurrent.futures
import configparser
import logging
import multiprocessing
import os
import time
import tornado

from argparse import ArgumentParser

import tabpy_server
from tabpy_server import __version__
from tabpy_server.app.ConfigParameters import ConfigParameters
from tabpy_server.app.util import (log_and_raise, validate_cert)
from tabpy_server.management.state import TabPyState
from tabpy_server.management.util import _get_state_from_file
from tabpy_server.psws.callbacks import (init_model_evaluator, init_ps_server,
                                         on_state_change)
from tabpy_server.psws.python_service import (PythonService,
                                              PythonServiceHandler)
from tabpy_server.handlers import (EndpointHandler, EndpointsHandler, EvaluationPlaneHandler, QueryPlaneHandler,
                                   ServiceInfoHandler, StatusHandler, UploadDestinationHandler)

from tornado_json.constants import TORNADO_MAJOR


logger = logging.getLogger(__name__)


class TabPyApp:
    '''
    TabPy application class for keeping context like settings, state, etc.
    '''

    settings = {}
    subdirectory = ""
    tabpy_state = None
    python_service = None

    def __init__(self, config_file=None):
        if config_file is None:
            cli_args = self._parse_cli_arguments()
            config_file = cli_args.config if cli_args.config is not None else os.path.join(os.path.dirname(__file__),
                                                                                           os.path.pardir, 'common',
                                                                                           'default.conf')

        if os.path.isfile(config_file):
            try:
                logging.config.fileConfig(
                    config_file, disable_existing_loggers=False)
            except:
                logging.basicConfig(level=logging.DEBUG)

        self._parse_config(config_file)

    def run(self):
        logger.info('Initializing TabPy...')
        tornado.ioloop.IOLoop.instance().run_sync(
            lambda: init_ps_server(self.settings, self.tabpy_state))
        logger.info('Done initializing TabPy.')

        executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=multiprocessing.cpu_count())

        # initialize Tornado application
        application = tornado.web.Application([
            # skip MainHandler to use StaticFileHandler .* page requests and
            # default to index.html
            # (r"/", MainHandler),
            (self.subdirectory + r'/query/([^/]+)', QueryPlaneHandler, dict(
                tabpy_state=self.tabpy_state, python_service=self.python_service)),
            (self.subdirectory + r'/status', StatusHandler,
             dict(tabpy_state=self.tabpy_state, python_service=self.python_service)),
            (self.subdirectory + r'/info', ServiceInfoHandler,
             dict(tabpy_state=self.tabpy_state, python_service=self.python_service)),
            (self.subdirectory + r'/endpoints', EndpointsHandler,
             dict(tabpy_state=self.tabpy_state, python_service=self.python_service)),
            (self.subdirectory + r'/endpoints/([^/]+)?', EndpointHandler, dict(
                tabpy_state=self.tabpy_state, python_service=self.python_service)),
            (self.subdirectory + r'/evaluate', EvaluationPlaneHandler,
             dict(executor=executor, tabpy_state=self.tabpy_state, python_service=self.python_service)),
            (self.subdirectory + r'/configurations/endpoint_upload_destination',
             UploadDestinationHandler, dict(tabpy_state=self.tabpy_state, python_service=self.python_service)),
            (self.subdirectory + r'/(.*)', tornado.web.StaticFileHandler,
             dict(path=self.settings['static_path'], default_filename="index.html", tabpy_state=self.tabpy_state, python_service=self.python_service)),
        ], debug=False, **self.settings)

        init_model_evaluator(self.settings, self.tabpy_state, self.python_service)

        if self.settings['transfer_protocol'] == 'http':
            application.listen(self.settings['port'])
        elif self.settings['transfer_protocol'] == 'https':
            application.listen(self.settings['port'],
                               ssl_options={
                'certfile': self.settings['certificate_file'],
                'keyfile': self.settings['key_file']
            })
        else:
            log_and_raise('Unsupported transfer protocol.', RuntimeError)

        logger.info('Web service listening on port {}'.format(str(self.settings['port'])))
        tornado.ioloop.IOLoop.instance().start()

    def _parse_cli_arguments(self):
        '''
        Parse command line arguments. Expected arguments:
        * --config: string
        '''
        parser = ArgumentParser(description='Run TabPy Server.')
        parser.add_argument('--config', help='Path to a config file.')
        return parser.parse_args()

    def _parse_config(self, config_file):
        """Provide consistent mechanism for pulling in configuration.

        Attempt to retain backward compatibility for existing implementations by
        grabbing port setting from CLI first.

        Take settings in the following order:

        1. CLI arguments if present
        2. config file
        3. OS environment variables (for ease of setting defaults if not present)
        4. current defaults if a setting is not present in any location

        Additionally provide similar configuration capabilities in between
        config filw and environment variables.
        For consistency use the same variable name in the config file as in the os
        environment.
        For naming standards use all capitals and start with 'TABPY_'
        """
        self.settings = {}
        self.subdirectory = ""
        self.tabpy_state = None
        self.python_service = None

        parser = configparser.ConfigParser()

        if os.path.isfile(config_file):
            with open(config_file) as f:
                parser.read_string(f.read())
        else:
            logger.warning(
                "Unable to find config file at '{}', using default settings.".format(config_file))

        def set_parameter(settings_key, config_key, default_val=None, check_env_var=False):
            if config_key is not None and parser.has_option('TabPy', config_key):
                self.settings[settings_key] = parser.get('TabPy', config_key)
            elif check_env_var:
                self.settings[settings_key] = os.getenv(
                    config_key, default_val)
            elif default_val is not None:
                self.settings[settings_key] = default_val

        set_parameter('port', ConfigParameters.TABPY_PORT,
                      default_val=9004, check_env_var=True)
        set_parameter('server_version', None, default_val=__version__)

        set_parameter('upload_dir', ConfigParameters.TABPY_QUERY_OBJECT_PATH,
                      default_val='/tmp/query_objects', check_env_var=True)
        if not os.path.exists(self.settings['upload_dir']):
            os.makedirs(self.settings['upload_dir'])

        # set and validate transfer protocol
        set_parameter('transfer_protocol',
                      ConfigParameters.TABPY_TRANSFER_PROTOCOL, default_val='http')
        self.settings['transfer_protocol'] = self.settings['transfer_protocol'].lower()

        set_parameter('certificate_file',
                      ConfigParameters.TABPY_CERTIFICATE_FILE)
        set_parameter('key_file', ConfigParameters.TABPY_KEY_FILE)
        self._validate_transfer_protocol_settings()

        # if state.ini does not exist try and create it - remove last dependence
        # on batch/shell script
        set_parameter('state_file_path', ConfigParameters.TABPY_STATE_PATH,
                      default_val='./', check_env_var=True)
        self.settings['state_file_path'] = os.path.realpath(
            os.path.normpath(
                os.path.expanduser(self.settings['state_file_path'])))
        state_file_path = self.settings['state_file_path']
        logger.info("Loading state from state file %s" %
                    os.path.join(state_file_path, "state.ini"))
        tabpy_state = _get_state_from_file(state_file_path)
        self.tabpy_state = TabPyState(
            config=tabpy_state, settings=self.settings)

        self.python_service = PythonServiceHandler(PythonService())
        self.settings['compress_response'] = True if TORNADO_MAJOR >= 4 else "gzip"
        self.settings['static_path'] = os.path.join(
            os.path.dirname(__file__), "static")

        # parse passwords file
        if not self._parse_pwd_file():
            msg = 'Failed to read passwords file %s' % ConfigParameters.TABPY_PWD_FILE
            logger.critical(msg)
            raise RuntimeError(msg)

        # Set subdirectory from config if applicable
        if tabpy_state.has_option("Service Info", "Subdirectory"):
            self.subdirectory = "/" + \
                tabpy_state.get("Service Info", "Subdirectory")

    def _validate_transfer_protocol_settings(self):
        if 'transfer_protocol' not in self.settings:
            log_and_raise(
                'Missing transfer protocol information.', RuntimeError)

        protocol = self.settings['transfer_protocol']

        if protocol == 'http':
            return

        if protocol != 'https':
            log_and_raise('Unsupported transfer protocol: {}.'.format(
                protocol), RuntimeError)

        self._validate_cert_key_state('The parameter(s) {} must be set.',
                                      'certificate_file' in self.settings, 'key_file' in self.settings)
        cert = self.settings['certificate_file']

        self._validate_cert_key_state('The parameter(s) {} must point to an existing file.', os.path.isfile(cert),
                                      os.path.isfile(self.settings['key_file']))
        tabpy_server.app.util.validate_cert(cert)

    def _validate_cert_key_state(self, msg, cert_valid, key_valid):
        cert_and_key_param = '{} and {}'.format(
            ConfigParameters.TABPY_CERTIFICATE_FILE, ConfigParameters.TABPY_KEY_FILE)
        https_error = 'Error using HTTPS: '
        err = None
        if not cert_valid and not key_valid:
            err = https_error + msg.format(cert_and_key_param)
        elif not cert_valid:
            err = https_error + \
                msg.format(ConfigParameters.TABPY_CERTIFICATE_FILE)
        elif not key_valid:
            err = https_error + msg.format(ConfigParameters.TABPY_KEY_FILE)

        if err is not None:
            log_and_raise(err, RuntimeError)

    def _parse_pwd_file(self):
        if not ConfigParameters.TABPY_PWD_FILE in self.settings:
            return True

        logger.info('Parsing password file %s' %
                    self.settings[ConfigParameters.TABPY_PWD_FILE])

        return True
