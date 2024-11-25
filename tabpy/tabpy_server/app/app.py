import concurrent.futures
import configparser
import logging
import multiprocessing
import os
import shutil
import signal
import ssl
import sys
import _thread

import tornado
from tornado.http1connection import HTTP1Connection

import tabpy
import tabpy.tabpy_server.app.arrow_server as pa
from tabpy.tabpy import __version__
from tabpy.tabpy_server.app.app_parameters import ConfigParameters, SettingsParameters
from tabpy.tabpy_server.app.util import parse_pwd_file
from tabpy.tabpy_server.handlers.basic_auth_server_middleware_factory import BasicAuthServerMiddlewareFactory
from tabpy.tabpy_server.handlers.no_op_auth_handler import NoOpAuthHandler
from tabpy.tabpy_server.management.state import TabPyState
from tabpy.tabpy_server.management.util import _get_state_from_file
from tabpy.tabpy_server.psws.callbacks import init_model_evaluator, init_ps_server
from tabpy.tabpy_server.psws.python_service import PythonService, PythonServiceHandler
from tabpy.tabpy_server.handlers import (
    EndpointHandler,
    EndpointsHandler,
    EvaluationPlaneHandler,
    EvaluationPlaneDisabledHandler,
    QueryPlaneHandler,
    ServiceInfoHandler,
    StatusHandler,
    UploadDestinationHandler,
)

logger = logging.getLogger(__name__)

def _init_asyncio_patch():
    """
    Select compatible event loop for Tornado 5+.
    As of Python 3.8, the default event loop on Windows is `proactor`,
    however Tornado requires the old default "selector" event loop.
    As Tornado has decided to leave this to users to set, MkDocs needs
    to set it. See https://github.com/tornadoweb/tornado/issues/2608.
    """
    if sys.platform.startswith("win") and sys.version_info >= (3, 8):
        import asyncio
        try:
            from asyncio import WindowsSelectorEventLoopPolicy
        except ImportError:
            pass  # Can't assign a policy which doesn't exist.
        else:
            if not isinstance(asyncio.get_event_loop_policy(), WindowsSelectorEventLoopPolicy):
                asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())


class TabPyApp:
    """
    TabPy application class for keeping context like settings, state, etc.
    """

    settings = {}
    subdirectory = ""
    tabpy_state = None
    python_service = None
    credentials = {}
    arrow_server = None
    max_request_size = None

    def __init__(self, config_file, disable_auth_warning=True):
        self.disable_auth_warning = disable_auth_warning
        if config_file is None:
            config_file = os.path.join(
                os.path.dirname(__file__), os.path.pardir, "common", "default.conf"
            )

        if os.path.isfile(config_file):
            try:
                from logging import config
                config.fileConfig(config_file, disable_existing_loggers=False)
            except KeyError:
                logging.basicConfig(level=logging.DEBUG)

        self._parse_config(config_file)

    def _initialize_ssl_context(self):
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)

        ssl_context.load_cert_chain(
            certfile=self.settings[SettingsParameters.CertificateFile],
            keyfile=self.settings[SettingsParameters.KeyFile]
        )

        min_tls = self.settings[SettingsParameters.MinimumTLSVersion]
        if not hasattr(ssl.TLSVersion, min_tls):
            logger.warning(f"Unrecognized value for TABPY_MINIMUM_TLS_VERSION: {min_tls}")
            min_tls = "TLSv1_2"

        logger.info(f"Setting minimum TLS version to {min_tls}")
        ssl_context.minimum_version = ssl.TLSVersion[min_tls]

        return ssl_context

    def _get_tls_certificates(self, config):
        tls_certificates = []
        cert = config[SettingsParameters.CertificateFile]
        key = config[SettingsParameters.KeyFile]
        with open(cert, "rb") as cert_file:
            tls_cert_chain = cert_file.read()
        with open(key, "rb") as key_file:
            tls_private_key = key_file.read()
        tls_certificates.append((tls_cert_chain, tls_private_key))
        return tls_certificates

    def _get_arrow_server(self, config):
        verify_client = None
        tls_certificates = None
        scheme = "grpc+tcp"
        if config[SettingsParameters.TransferProtocol] == "https":
            scheme = "grpc+tls"
            tls_certificates = self._get_tls_certificates(config)

        host = config.get(SettingsParameters.ArrowFlightBindIp)
        port = config.get(SettingsParameters.ArrowFlightPort)
        location = "{}://{}:{}".format(scheme, host, port)

        auth_middleware = None
        if "authentication" in config[SettingsParameters.ApiVersions]["v1"]["features"]:
            _, creds = parse_pwd_file(config[ConfigParameters.TABPY_PWD_FILE])
            auth_middleware = {
                "basic": BasicAuthServerMiddlewareFactory(creds)
            }

        server = pa.FlightServer(host, location,
                            tls_certificates=tls_certificates,
                            verify_client=verify_client, auth_handler=NoOpAuthHandler(),
                            middleware=auth_middleware)
        return server

    def run(self):
        application = self._create_tornado_web_app()

        init_model_evaluator(self.settings, self.tabpy_state, self.python_service)

        protocol = self.settings[SettingsParameters.TransferProtocol]
        ssl_options = None
        if protocol == "https":
            ssl_options = self._initialize_ssl_context()
        elif protocol != "http":
            msg = f"Unsupported transfer protocol {protocol}."
            logger.critical(msg)
            raise RuntimeError(msg)

        settings = {}
        if self.settings[SettingsParameters.GzipEnabled] is True:
            settings["decompress_request"] = True

        application.listen(
            self.settings[SettingsParameters.Port],
            self.settings[SettingsParameters.BindIp],
            ssl_options=ssl_options,
            max_buffer_size=self.max_request_size,
            max_body_size=self.max_request_size,
            **settings,
        )

        logger.info(
            "Web service listening on "
            f"{str(self.settings[SettingsParameters.BindIp])}:"
            f"{str(self.settings[SettingsParameters.Port])}"
        )

        if self.settings[SettingsParameters.ArrowEnabled]:
            def start_pyarrow():
                self.arrow_server = self._get_arrow_server(self.settings)
                pa.start(self.arrow_server)

            try:
                _thread.start_new_thread(start_pyarrow, ())
            except Exception as e:
                logger.critical(f"Failed to start PyArrow server: {e}")

        tornado.ioloop.IOLoop.instance().start()

    def _create_tornado_web_app(self):
        class TabPyTornadoApp(tornado.web.Application):
            is_closing = False

            def signal_handler(self, signal, _):
                logger.critical(f"Exiting on signal {signal}...")
                self.is_closing = True

            def try_exit(self):
                if self.is_closing:
                    tornado.ioloop.IOLoop.instance().stop()
                    logger.info("Shutting down TabPy...")

        logger.info("Initializing TabPy...")
        tornado.ioloop.IOLoop.instance().run_sync(
            lambda: init_ps_server(self.settings, self.tabpy_state)
        )
        logger.info("Done initializing TabPy.")

        executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=multiprocessing.cpu_count()
        )

        # initialize Tornado application
        _init_asyncio_patch()
        application = TabPyTornadoApp(
            [
                (
                    self.subdirectory + r"/query/([^/]+)",
                    QueryPlaneHandler,
                    dict(app=self),
                ),
                (self.subdirectory + r"/status", StatusHandler, dict(app=self)),
                (self.subdirectory + r"/info", ServiceInfoHandler, dict(app=self)),
                (self.subdirectory + r"/endpoints", EndpointsHandler, dict(app=self)),
                (
                    self.subdirectory + r"/endpoints/([^/]+)?",
                    EndpointHandler,
                    dict(app=self),
                ),
                (
                    self.subdirectory + r"/evaluate",
                    EvaluationPlaneHandler if self.settings[SettingsParameters.EvaluateEnabled]
                    else EvaluationPlaneDisabledHandler,
                    dict(executor=executor, app=self),
                ),
                (
                    self.subdirectory + r"/configurations/endpoint_upload_destination",
                    UploadDestinationHandler,
                    dict(app=self),
                ),
                (
                    self.subdirectory + r"/(.*)",
                    tornado.web.StaticFileHandler,
                    dict(
                        path=self.settings[SettingsParameters.StaticPath],
                        default_filename="index.html",
                    ),
                ),
            ],
            debug=False,
            **self.settings,
        )

        signal.signal(signal.SIGINT, application.signal_handler)
        tornado.ioloop.PeriodicCallback(application.try_exit, 500).start()

        signal.signal(signal.SIGINT, application.signal_handler)
        tornado.ioloop.PeriodicCallback(application.try_exit, 500).start()

        return application

    def _set_parameter(self, parser, settings_key, config_key, default_val, parse_function):
        key_is_set = False

        if (
            config_key is not None
            and parser.has_section("TabPy")
            and parser.has_option("TabPy", config_key)
        ):
            if parse_function is None:
                parse_function = parser.get
            self.settings[settings_key] = parse_function("TabPy", config_key)
            key_is_set = True
            logger.debug(
                f"Parameter {settings_key} set to "
                f'"{self.settings[settings_key]}" '
                "from config file or environment variable"
            )

        if not key_is_set and default_val is not None:
            self.settings[settings_key] = default_val
            key_is_set = True
            logger.debug(
                f"Parameter {settings_key} set to "
                f'"{self.settings[settings_key]}" '
                "from default value"
            )

        if not key_is_set:
            logger.debug(f"Parameter {settings_key} is not set")

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

        pkg_path = os.path.dirname(tabpy.__file__)

        parser = configparser.ConfigParser(os.environ)
        logger.info(f"Parsing config file {config_file}")

        file_exists = False
        if os.path.isfile(config_file):
            try:
                with open(config_file, 'r') as f:
                    parser.read_string(f.read())
                    file_exists = True
            except Exception:
                pass

        if not file_exists:
            logger.warning(
                f"Unable to open config file {config_file}, "
                "using default settings."
            )

        settings_parameters = [
            (SettingsParameters.Port, ConfigParameters.TABPY_PORT, 9004, None),
            (SettingsParameters.BindIp, ConfigParameters.TABPY_BIND_IP, '0.0.0.0', None),
            (SettingsParameters.ServerVersion, None, __version__, None),
            (SettingsParameters.EvaluateEnabled, ConfigParameters.TABPY_EVALUATE_ENABLE,
             True, parser.getboolean),
            (SettingsParameters.EvaluateTimeout, ConfigParameters.TABPY_EVALUATE_TIMEOUT,
             30, parser.getfloat),
            (SettingsParameters.UploadDir, ConfigParameters.TABPY_QUERY_OBJECT_PATH,
             os.path.join(pkg_path, "tmp", "query_objects"), None),
            (SettingsParameters.TransferProtocol, ConfigParameters.TABPY_TRANSFER_PROTOCOL,
             "http", None),
            (SettingsParameters.CertificateFile, ConfigParameters.TABPY_CERTIFICATE_FILE,
             None, None),
            (SettingsParameters.KeyFile, ConfigParameters.TABPY_KEY_FILE, None, None),
            (SettingsParameters.MinimumTLSVersion, ConfigParameters.TABPY_MINIMUM_TLS_VERSION,
             "TLSv1_2", None),
            (SettingsParameters.StateFilePath, ConfigParameters.TABPY_STATE_PATH,
             os.path.join(pkg_path, "tabpy_server"), None),
            (SettingsParameters.StaticPath, ConfigParameters.TABPY_STATIC_PATH,
             os.path.join(pkg_path, "tabpy_server", "static"), None),
            (ConfigParameters.TABPY_PWD_FILE, ConfigParameters.TABPY_PWD_FILE, None, None),
            (SettingsParameters.LogRequestContext, ConfigParameters.TABPY_LOG_DETAILS,
             "false", None),
            (SettingsParameters.MaxRequestSizeInMb, ConfigParameters.TABPY_MAX_REQUEST_SIZE_MB,
             100, None),
            (SettingsParameters.GzipEnabled, ConfigParameters.TABPY_GZIP_ENABLE,
             True, parser.getboolean),
            (SettingsParameters.ArrowEnabled, ConfigParameters.TABPY_ARROW_ENABLE,
             False, parser.getboolean),
            (SettingsParameters.ArrowFlightPort, ConfigParameters.TABPY_ARROWFLIGHT_PORT,
             13622, parser.getint),
            (SettingsParameters.ArrowFlightBindIp, ConfigParameters.TABPY_ARROWFLIGHT_BIND_IP,
             '0.0.0.0', None),
        ]

        for setting, parameter, default_val, parse_function in settings_parameters:
            self._set_parameter(parser, setting, parameter, default_val, parse_function)

        if not os.path.exists(self.settings[SettingsParameters.UploadDir]):
            os.makedirs(self.settings[SettingsParameters.UploadDir])

        # set and validate transfer protocol
        self.settings[SettingsParameters.TransferProtocol] = self.settings[
            SettingsParameters.TransferProtocol
        ].lower()

        self._validate_transfer_protocol_settings()

        # Set max request size in bytes
        self.max_request_size = (
            int(self.settings[SettingsParameters.MaxRequestSizeInMb]) * 1024 * 1024
        )
        logger.info(f"Setting max request size to {self.max_request_size} bytes")

        # if state.ini does not exist try and create it - remove
        # last dependence on batch/shell script
        self.settings[SettingsParameters.StateFilePath] = os.path.realpath(
            os.path.normpath(
                os.path.expanduser(self.settings[SettingsParameters.StateFilePath])
            )
        )
        state_config, self.tabpy_state = self._build_tabpy_state()

        self.python_service = PythonServiceHandler(PythonService())
        self.settings["compress_response"] = True
        self.settings[SettingsParameters.StaticPath] = os.path.abspath(
            self.settings[SettingsParameters.StaticPath]
        )
        logger.debug(
            f"Static pages folder set to "
            f'"{self.settings[SettingsParameters.StaticPath]}"'
        )

        # Set subdirectory from config if applicable
        if state_config.has_option("Service Info", "Subdirectory"):
            self.subdirectory = "/" + state_config.get("Service Info", "Subdirectory")

        # If passwords file specified load credentials
        if ConfigParameters.TABPY_PWD_FILE in self.settings:
            if not self._parse_pwd_file():
                msg = (
                    "Failed to read passwords file "
                    f"{self.settings[ConfigParameters.TABPY_PWD_FILE]}"
                )
                logger.critical(msg)
                raise RuntimeError(msg)
        else:
            self._handle_configuration_without_authentication()

        features = self._get_features()
        self.settings[SettingsParameters.ApiVersions] = {"v1": {"features": features}}

        self.settings[SettingsParameters.LogRequestContext] = (
            self.settings[SettingsParameters.LogRequestContext].lower() != "false"
        )
        call_context_state = (
            "enabled"
            if self.settings[SettingsParameters.LogRequestContext]
            else "disabled"
        )
        logger.info(f"Call context logging is {call_context_state}")

    def _validate_transfer_protocol_settings(self):
        if SettingsParameters.TransferProtocol not in self.settings:
            msg = "Missing transfer protocol information."
            logger.critical(msg)
            raise RuntimeError(msg)

        protocol = self.settings[SettingsParameters.TransferProtocol]

        if protocol == "http":
            return

        if protocol != "https":
            msg = f"Unsupported transfer protocol: {protocol}"
            logger.critical(msg)
            raise RuntimeError(msg)

        self._validate_cert_key_state(
            "The parameter(s) {} must be set.",
            SettingsParameters.CertificateFile in self.settings,
            SettingsParameters.KeyFile in self.settings,
        )
        cert = self.settings[SettingsParameters.CertificateFile]

        self._validate_cert_key_state(
            "The parameter(s) {} must point to " "an existing file.",
            os.path.isfile(cert),
            os.path.isfile(self.settings[SettingsParameters.KeyFile]),
        )
        tabpy.tabpy_server.app.util.validate_cert(cert)

    @staticmethod
    def _validate_cert_key_state(msg, cert_valid, key_valid):
        cert_and_key_param = (
            f"{ConfigParameters.TABPY_CERTIFICATE_FILE} and "
            f"{ConfigParameters.TABPY_KEY_FILE}"
        )
        https_error = "Error using HTTPS: "
        err = None
        if not cert_valid and not key_valid:
            err = https_error + msg.format(cert_and_key_param)
        elif not cert_valid:
            err = https_error + msg.format(ConfigParameters.TABPY_CERTIFICATE_FILE)
        elif not key_valid:
            err = https_error + msg.format(ConfigParameters.TABPY_KEY_FILE)

        if err is not None:
            logger.critical(err)
            raise RuntimeError(err)

    def _parse_pwd_file(self):
        succeeded, self.credentials = parse_pwd_file(
            self.settings[ConfigParameters.TABPY_PWD_FILE]
        )

        if succeeded and len(self.credentials) == 0:
            logger.error("No credentials found")
            succeeded = False

        return succeeded

    def _handle_configuration_without_authentication(self):
        std_no_auth_msg = "Password file is not specified: Authentication is not enabled"

        if self.disable_auth_warning == True:
            logger.info(std_no_auth_msg)
            return

        confirm_no_auth_msg = "\nWARNING: This TabPy server is not currently configured for username/password authentication. "

        if self.settings[SettingsParameters.EvaluateEnabled]:
            confirm_no_auth_msg += (
              "This means that, because the TABPY_EVALUATE_ENABLE feature is enabled, there is "
              "the potential that unauthenticated individuals may be able "
              "to remotely execute code on this machine. "
            )

        confirm_no_auth_msg += ("We strongly advise against proceeding without authentication as it poses a significant security risk.\n\n"
            "Do you wish to proceed without authentication? (y/N): ")

        confirm_no_auth_input = input(confirm_no_auth_msg)

        if confirm_no_auth_input == 'y':
            logger.info(std_no_auth_msg)
        else:
            print("\nAborting start up. To enable authentication for your TabPy server, see "
                "https://github.com/tableau/TabPy/blob/master/docs/server-config.md#authentication.")
            exit()

    def _get_features(self):
        features = {}

        # Check for auth
        if ConfigParameters.TABPY_PWD_FILE in self.settings:
            features["authentication"] = {
                "required": True,
                "methods": {"basic-auth": {}},
            }

        features["evaluate_enabled"] = self.settings[SettingsParameters.EvaluateEnabled]
        features["gzip_enabled"] = self.settings[SettingsParameters.GzipEnabled]
        features["arrow_enabled"] = self.settings[SettingsParameters.ArrowEnabled]
        return features

    def _build_tabpy_state(self):
        pkg_path = os.path.dirname(tabpy.__file__)
        state_file_dir = self.settings[SettingsParameters.StateFilePath]
        state_file_path = os.path.join(state_file_dir, "state.ini")
        if not os.path.isfile(state_file_path):
            state_file_template_path = os.path.join(
                pkg_path, "tabpy_server", "state.ini.template"
            )
            logger.debug(
                f"File {state_file_path} not found, creating from "
                f"template {state_file_template_path}..."
            )
            shutil.copy(state_file_template_path, state_file_path)

        logger.info(f"Loading state from state file {state_file_path}")
        tabpy_state = _get_state_from_file(state_file_dir)
        return tabpy_state, TabPyState(config=tabpy_state, settings=self.settings)


# Override _read_body to allow content with size exceeding max_body_size
# This enables proper handling of 413 errors in base_handler
def _read_body_allow_max_size(self, code, headers, delegate):
    if "Content-Length" in headers:
        content_length = int(headers["Content-Length"])
        if content_length > self._max_body_size:
            return
    return self.original_read_body(code, headers, delegate)

HTTP1Connection.original_read_body = HTTP1Connection._read_body
HTTP1Connection._read_body = _read_body_allow_max_size
