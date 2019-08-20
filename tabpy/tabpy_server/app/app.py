from argparse import ArgumentParser
import concurrent.futures
import configparser
import logging
from logging import config
import multiprocessing
import os
import shutil
import tabpy.tabpy_server
from tabpy.tabpy import __version__
from tabpy.tabpy_server.app.ConfigParameters import ConfigParameters
from tabpy.tabpy_server.app.SettingsParameters import SettingsParameters
from tabpy.tabpy_server.app.util import parse_pwd_file
from tabpy.tabpy_server.management.state import TabPyState
from tabpy.tabpy_server.management.util import _get_state_from_file
from tabpy.tabpy_server.psws.callbacks\
    import (init_model_evaluator, init_ps_server)
from tabpy.tabpy_server.psws.python_service\
    import (PythonService, PythonServiceHandler)
from tabpy.tabpy_server.handlers\
    import (EndpointHandler, EndpointsHandler,
            EvaluationPlaneHandler, QueryPlaneHandler,
            ServiceInfoHandler, StatusHandler,
            UploadDestinationHandler)
import tornado


logger = logging.getLogger(__name__)


class TabPyApp:
    '''
    TabPy application class for keeping context like settings, state, etc.
    '''

    settings = {}
    subdirectory = ""
    tabpy_state = None
    python_service = None
    credentials = {}

    def __init__(self, config_file=None):
        if config_file is None:
            cli_args = self._parse_cli_arguments()
            if cli_args.config is not None:
                config_file = cli_args.config
            else:
                config_file = os.path.join(os.path.dirname(__file__),
                                           os.path.pardir, 'common',
                                           'default.conf')

        if os.path.isfile(config_file):
            try:
                logging.config.fileConfig(
                    config_file, disable_existing_loggers=False)
            except KeyError:
                logging.basicConfig(level=logging.DEBUG)

        self._parse_config(config_file)

    def run(self):
        application = self._create_tornado_web_app()

        init_model_evaluator(
            self.settings,
            self.tabpy_state,
            self.python_service)

        protocol = self.settings[SettingsParameters.TransferProtocol]
        if protocol == 'http':
            application.listen(self.settings[SettingsParameters.Port])
        elif protocol == 'https':
            application.listen(self.settings[SettingsParameters.Port],
                               ssl_options={
                'certfile': self.settings[SettingsParameters.CertificateFile],
                'keyfile': self.settings[SettingsParameters.KeyFile]
            })
        else:
            msg = f'Unsupported transfer protocol {protocol}.'
            logger.critical(msg)
            raise RuntimeError(msg)

        logger.info(
            'Web service listening on port '
            f'{str(self.settings[SettingsParameters.Port])}')
        tornado.ioloop.IOLoop.instance().start()

    def _create_tornado_web_app(self):
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
            (self.subdirectory + r'/query/([^/]+)', QueryPlaneHandler,
             dict(app=self)),
            (self.subdirectory + r'/status', StatusHandler,
             dict(app=self)),
            (self.subdirectory + r'/info', ServiceInfoHandler,
             dict(app=self)),
            (self.subdirectory + r'/endpoints', EndpointsHandler,
             dict(app=self)),
            (self.subdirectory + r'/endpoints/([^/]+)?', EndpointHandler,
             dict(app=self)),
            (self.subdirectory + r'/evaluate', EvaluationPlaneHandler,
             dict(executor=executor,
                  app=self)),
            (self.subdirectory +
             r'/configurations/endpoint_upload_destination',
             UploadDestinationHandler,
             dict(app=self)),
            (self.subdirectory + r'/(.*)', tornado.web.StaticFileHandler,
             dict(path=self.settings[SettingsParameters.StaticPath],
                  default_filename="index.html")),
        ], debug=False, **self.settings)

        return application

    @staticmethod
    def _parse_cli_arguments():
        '''
        Parse command line arguments. Expected arguments:
        * --config: string
        '''
        parser = ArgumentParser(description='Run TabPy Server.')
        parser.add_argument('--config', help='Path to a config file.')
        return parser.parse_args()

    def _parse_config(self, config_file):
        """Provide consistent mechanism for pulling in configuration.

        Attempt to retain backward compatibility for
        existing implementations by grabbing port
        setting from CLI first.

        Take settings in the following order:

        1. CLI arguments if present
        2. config file
        3. OS environment variables (for ease of
           setting defaults if not present)
        4. current defaults if a setting is not present in any location

        Additionally provide similar configuration capabilities in between
        config file and environment variables.
        For consistency use the same variable name in the config file as
        in the os environment.
        For naming standards use all capitals and start with 'TABPY_'
        """
        self.settings = {}
        self.subdirectory = ""
        self.tabpy_state = None
        self.python_service = None
        self.credentials = {}

        parser = configparser.ConfigParser()

        if os.path.isfile(config_file):
            with open(config_file) as f:
                parser.read_string(f.read())
        else:
            logger.warning(
                f'Unable to find config file at {config_file}, '
                'using default settings.')

        def set_parameter(settings_key,
                          config_key,
                          default_val=None,
                          check_env_var=False):
            key_is_set = False

            if config_key is not None and\
               parser.has_section('TabPy') and\
               parser.has_option('TabPy', config_key):
                self.settings[settings_key] = parser.get('TabPy', config_key)
                key_is_set = True
                logger.debug(
                    f'Parameter {settings_key} set to '
                    f'"{self.settings[settings_key]}" '
                    'from config file')

            if not key_is_set and check_env_var:
                val = os.getenv(config_key)
                if val is not None:
                    self.settings[settings_key] = val
                    key_is_set = True
                    logger.debug(
                        f'Parameter {settings_key} set to '
                        f'"{self.settings[settings_key]}" '
                        'from environment variable')

            if not key_is_set and default_val is not None:
                self.settings[settings_key] = default_val
                key_is_set = True
                logger.debug(
                    f'Parameter {settings_key} set to '
                    f'"{self.settings[settings_key]}" '
                    'from default value')

            if not key_is_set:
                logger.debug(
                    f'Parameter {settings_key} is not set')

        set_parameter(SettingsParameters.Port, ConfigParameters.TABPY_PORT,
                      default_val=9004, check_env_var=True)
        set_parameter(SettingsParameters.ServerVersion, None,
                      default_val=__version__)

        set_parameter(SettingsParameters.EvaluateTimeout,
                      ConfigParameters.TABPY_EVALUATE_TIMEOUT,
                      default_val=30)
        try:
            self.settings[SettingsParameters.EvaluateTimeout] = float(
                self.settings[SettingsParameters.EvaluateTimeout])
        except ValueError:
            logger.warning(
                'Evaluate timeout must be a float type. Defaulting '
                'to evaluate timeout of 30 seconds.')
            self.settings[SettingsParameters.EvaluateTimeout] = 30

        pkg_path = os.path.dirname(tabpy.__file__)
        set_parameter(SettingsParameters.UploadDir,
                      ConfigParameters.TABPY_QUERY_OBJECT_PATH,
                      default_val=os.path.join(pkg_path,
                                               'tmp', 'query_objects'),
                      check_env_var=True)
        if not os.path.exists(self.settings[SettingsParameters.UploadDir]):
            os.makedirs(self.settings[SettingsParameters.UploadDir])

        # set and validate transfer protocol
        set_parameter(SettingsParameters.TransferProtocol,
                      ConfigParameters.TABPY_TRANSFER_PROTOCOL,
                      default_val='http')
        self.settings[SettingsParameters.TransferProtocol] =\
            self.settings[SettingsParameters.TransferProtocol].lower()

        set_parameter(SettingsParameters.CertificateFile,
                      ConfigParameters.TABPY_CERTIFICATE_FILE)
        set_parameter(SettingsParameters.KeyFile,
                      ConfigParameters.TABPY_KEY_FILE)
        self._validate_transfer_protocol_settings()

        # if state.ini does not exist try and create it - remove
        # last dependence on batch/shell script
        set_parameter(SettingsParameters.StateFilePath,
                      ConfigParameters.TABPY_STATE_PATH,
                      default_val=os.path.join(pkg_path, 'tabpy_server'),
                      check_env_var=True)
        self.settings[SettingsParameters.StateFilePath] = os.path.realpath(
            os.path.normpath(
                os.path.expanduser(
                    self.settings[SettingsParameters.StateFilePath])))
        state_file_dir = self.settings[SettingsParameters.StateFilePath]
        state_file_path = os.path.join(state_file_dir, 'state.ini')
        if not os.path.isfile(state_file_path):
            state_file_template_path = os.path.join(
                pkg_path, 'tabpy_server', 'state.ini.template')
            logger.debug(f'File {state_file_path} not found, creating from '
                         f'template {state_file_template_path}...')
            shutil.copy(state_file_template_path, state_file_path)

        logger.info(f'Loading state from state file {state_file_path}')
        tabpy_state = _get_state_from_file(state_file_dir)
        self.tabpy_state = TabPyState(
            config=tabpy_state, settings=self.settings)

        self.python_service = PythonServiceHandler(PythonService())
        self.settings['compress_response'] = True
        set_parameter(SettingsParameters.StaticPath,
                      ConfigParameters.TABPY_STATIC_PATH,
                      default_val='./')
        self.settings[SettingsParameters.StaticPath] =\
            os.path.abspath(self.settings[SettingsParameters.StaticPath])
        logger.debug(f'Static pages folder set to '
                     f'"{self.settings[SettingsParameters.StaticPath]}"')

        # Set subdirectory from config if applicable
        if tabpy_state.has_option("Service Info", "Subdirectory"):
            self.subdirectory = "/" + \
                tabpy_state.get("Service Info", "Subdirectory")

        # If passwords file specified load credentials
        set_parameter(ConfigParameters.TABPY_PWD_FILE,
                      ConfigParameters.TABPY_PWD_FILE)
        if ConfigParameters.TABPY_PWD_FILE in self.settings:
            if not self._parse_pwd_file():
                msg = ('Failed to read passwords file '
                       f'{self.settings[ConfigParameters.TABPY_PWD_FILE]}')
                logger.critical(msg)
                raise RuntimeError(msg)
        else:
            logger.info(
                "Password file is not specified: "
                "Authentication is not enabled")

        features = self._get_features()
        self.settings[SettingsParameters.ApiVersions] =\
            {'v1': {'features': features}}

        set_parameter(SettingsParameters.LogRequestContext,
                      ConfigParameters.TABPY_LOG_DETAILS,
                      default_val='false')
        self.settings[SettingsParameters.LogRequestContext] = (
            self.settings[SettingsParameters.LogRequestContext].lower() !=
            'false')
        call_context_state =\
            'enabled' if self.settings[SettingsParameters.LogRequestContext]\
            else 'disabled'
        logger.info(f'Call context logging is {call_context_state}')

    def _validate_transfer_protocol_settings(self):
        if SettingsParameters.TransferProtocol not in self.settings:
            msg = 'Missing transfer protocol information.'
            logger.critical(msg)
            raise RuntimeError(msg)

        protocol = self.settings[SettingsParameters.TransferProtocol]

        if protocol == 'http':
            return

        if protocol != 'https':
            msg = f'Unsupported transfer protocol: {protocol}'
            logger.critical(msg)
            raise RuntimeError(msg)

        self._validate_cert_key_state(
            'The parameter(s) {} must be set.',
            SettingsParameters.CertificateFile in self.settings,
            SettingsParameters.KeyFile in self.settings)
        cert = self.settings[SettingsParameters.CertificateFile]

        self._validate_cert_key_state(
            'The parameter(s) {} must point to '
            'an existing file.',
            os.path.isfile(cert),
            os.path.isfile(self.settings[SettingsParameters.KeyFile]))
        tabpy.tabpy_server.app.util.validate_cert(cert)

    @staticmethod
    def _validate_cert_key_state(msg, cert_valid, key_valid):
        cert_and_key_param = (
            f'{ConfigParameters.TABPY_CERTIFICATE_FILE} and '
            f'{ConfigParameters.TABPY_KEY_FILE}')
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
            logger.critical(err)
            raise RuntimeError(err)

    def _parse_pwd_file(self):
        succeeded, self.credentials = parse_pwd_file(
            self.settings[ConfigParameters.TABPY_PWD_FILE])

        if succeeded and len(self.credentials) == 0:
            logger.error('No credentials found')
            succeeded = False

        return succeeded

    def _get_features(self):
        features = {}

        # Check for auth
        if ConfigParameters.TABPY_PWD_FILE in self.settings:
            features['authentication'] = {
                'required': True, 'methods': {
                    'basic-auth': {}}}

        return features
