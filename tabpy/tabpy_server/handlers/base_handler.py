import base64
import binascii
import concurrent
import json
import logging
import tornado.web
from tabpy.tabpy_server.app.SettingsParameters import SettingsParameters
from tabpy.tabpy_server.handlers.util import hash_password
import uuid


STAGING_THREAD = concurrent.futures.ThreadPoolExecutor(max_workers=3)


class ContextLoggerWrapper(object):
    '''
    This class appends request context to logged messages.
    '''
    @staticmethod
    def _generate_call_id():
        return str(uuid.uuid4())

    def __init__(self, request: tornado.httputil.HTTPServerRequest):
        self.call_id = self._generate_call_id()
        self.set_request(request)

        self.tabpy_username = None
        self.log_request_context = False
        self.request_context_logged = False

    def set_request(self, request: tornado.httputil.HTTPServerRequest):
        '''
        Set HTTP(S) request for logger. Headers will be used to
        append request data as client information, Tableau user name, etc.
        '''
        self.remote_ip = request.remote_ip
        self.method = request.method
        self.url = request.full_url()

        if 'TabPy-Client' in request.headers:
            self.client = request.headers['TabPy-Client']
        else:
            self.client = None

        if 'TabPy-User' in request.headers:
            self.tableau_username = request.headers['TabPy-User']
        else:
            self.tableau_username = None

    def set_tabpy_username(self, tabpy_username: str):
        self.tabpy_username = tabpy_username

    def enable_context_logging(self, enable: bool):
        '''
        Enable/disable request context information logging.

        Parameters
        ----------
        enable: bool
            If True request context information will be logged and
            every log entry for a request handler will have call ID
            with it.
        '''
        self.log_request_context = enable

    def _log_context_info(self):
        if not self.log_request_context:
            return

        context = f'Call ID: {self.call_id}'

        if self.remote_ip is not None:
            context += f', Caller: {self.remote_ip}'

        if self.method is not None:
            context += f', Method: {self.method}'

        if self.url is not None:
            context += f', URL: {self.url}'

        if self.client is not None:
            context += f', Client: {self.client}'

        if self.tableau_username is not None:
            context += f', Tableau user: {self.tableau_username}'

        if self.tabpy_username is not None:
            context += f', TabPy user: {self.tabpy_username}'

        logging.getLogger(__name__).log(logging.INFO, context)
        self.request_context_logged = True

    def log(self, level: int, msg: str):
        '''
        Log message with or without call ID. If call context is logged and
        call ID added to any log entry is specified by if context logging
        is enabled (see CallContext.enable_context_logging for more details).

        Parameters
        ----------
        level: int
            Log level: logging.CRITICAL, ERROR, WARNING, INFO, DEBUG, NOTSET.

        msg: str
            Message format string.

        args
            Same as args in Logger.debug().

        kwargs
            Same as kwargs in Logger.debug().
        '''
        extended_msg = msg
        if self.log_request_context:
            if not self.request_context_logged:
                self._log_context_info()

            extended_msg += f', <<call ID: {self.call_id}>>'

        logging.getLogger(__name__).log(level, extended_msg)


class BaseHandler(tornado.web.RequestHandler):
    def initialize(self, app):
        self.tabpy_state = app.tabpy_state
        # set content type to application/json
        self.set_header("Content-Type", "application/json")
        self.protocol = self.settings[SettingsParameters.TransferProtocol]
        self.port = self.settings[SettingsParameters.Port]
        self.python_service = app.python_service
        self.credentials = app.credentials
        self.username = None
        self.password = None
        self.eval_timeout = self.settings[SettingsParameters.EvaluateTimeout]

        self.logger = ContextLoggerWrapper(self.request)
        self.logger.enable_context_logging(
            app.settings[SettingsParameters.LogRequestContext])
        self.logger.log(
            logging.DEBUG,
            'Checking if need to handle authentication')
        self.not_authorized = not self.handle_authentication("v1")

    def error_out(self, code, log_message, info=None):
        self.set_status(code)
        self.write(json.dumps(
            {'message': log_message, 'info': info or {}}))

        # We want to duplicate error message in console for
        # loggers are misconfigured or causing the failure
        # themselves
        print(info)
        self.logger.log(
            logging.ERROR,
            'Responding with status={}, message="{}", info="{}"'.
            format(code, log_message, info))
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
        origin = self.tabpy_state.get_access_control_allow_origin()
        if len(origin) > 0:
            self.set_header("Access-Control-Allow-Origin", origin)
            self.logger.log(logging.DEBUG,
                            f'Access-Control-Allow-Origin:{origin}')

        headers = self.tabpy_state.get_access_control_allow_headers()
        if len(headers) > 0:
            self.set_header("Access-Control-Allow-Headers", headers)
            self.logger.log(logging.DEBUG,
                            f'Access-Control-Allow-Headers:{headers}')

        methods = self.tabpy_state.get_access_control_allow_methods()
        if len(methods) > 0:
            self.set_header("Access-Control-Allow-Methods", methods)
            self.logger.log(logging.DEBUG,
                            f'Access-Control-Allow-Methods:{methods}')

    def _get_auth_method(self, api_version) -> (bool, str):
        '''
        Finds authentication method if provided.

        Parameters
        ----------
        api_version : str
            API version for authentication.

        Returns
        -------
        bool
            True if known authentication method is found.
            False otherwise.

        str
            Name of authentication method used by client.
            If empty no authentication required.

        (True, '') as result of this function means authentication
        is not needed.
        '''
        if api_version not in self.settings[SettingsParameters.ApiVersions]:
            self.logger.log(logging.CRITICAL,
                            f'Unknown API version "{api_version}"')
            return False, ''

        version_settings =\
            self.settings[SettingsParameters.ApiVersions][api_version]
        if 'features' not in version_settings:
            self.logger.log(logging.INFO,
                            f'No features configured for API "{api_version}"')
            return True, ''

        features = version_settings['features']
        if 'authentication' not in features or\
                not features['authentication']['required']:
            self.logger.log(
                logging.INFO,
                'Authentication is not a required feature for API '
                f'"{api_version}"')
            return True, ''

        auth_feature = features['authentication']
        if 'methods' not in auth_feature:
            self.logger.log(
                logging.INFO,
                'Authentication method is not configured for API '
                f'"{api_version}"')

        methods = auth_feature['methods']
        if 'basic-auth' in auth_feature['methods']:
            return True, 'basic-auth'
        # Add new methods here...

        # No known methods were found
        self.logger.log(
            logging.CRITICAL,
            f'Unknown authentication method(s) "{methods}" are configured '
            f'for API "{api_version}"')
        return False, ''

    def _get_basic_auth_credentials(self) -> bool:
        '''
        Find credentials for basic access authentication method. Credentials if
        found stored in Credentials.username and Credentials.password.

        Returns
        -------
        bool
            True if valid credentials were found.
            False otherwise.
        '''
        self.logger.log(logging.DEBUG,
                        'Checking request headers for authentication data')
        if 'Authorization' not in self.request.headers:
            self.logger.log(logging.INFO, 'Authorization header not found')
            return False

        auth_header = self.request.headers['Authorization']
        auth_header_list = auth_header.split(' ')
        if len(auth_header_list) != 2 or\
                auth_header_list[0] != 'Basic':
            self.logger.log(logging.ERROR,
                            f'Unknown authentication method "{auth_header}"')
            return False

        try:
            cred = base64.b64decode(auth_header_list[1]).decode('utf-8')
        except (binascii.Error, UnicodeDecodeError) as ex:
            self.logger.log(logging.CRITICAL,
                            f'Cannot decode credentials: {str(ex)}')
            return False

        login_pwd = cred.split(':')
        if len(login_pwd) != 2:
            self.logger.log(logging.ERROR,
                            'Invalid string in encoded credentials')
            return False

        self.username = login_pwd[0]
        self.logger.set_tabpy_username(self.username)
        self.password = login_pwd[1]
        return True

    def _get_credentials(self, method) -> bool:
        '''
        Find credentials for specified authentication method. Credentials if
        found stored in self.username and self.password.

        Parameters
        ----------
        method: str
            Authentication method name.

        Returns
        -------
        bool
            True if valid credentials were found.
            False otherwise.
        '''
        if method == 'basic-auth':
            return self._get_basic_auth_credentials()
        # Add new methods here...

        # No known methods were found
        self.logger.log(
            logging.CRITICAL,
            f'Unknown authentication method(s) "{method}" are configured '
            f'for API "{api_version}"')
        return False

    def _validate_basic_auth_credentials(self) -> bool:
        '''
        Validates username:pwd if they are the same as
        stored credentials.

        Returns
        -------
        bool
            True if credentials has key login and
            credentials[login] equal SHA3(pwd), False
            otherwise.
        '''
        login = self.username.lower()
        self.logger.log(logging.DEBUG,
                        f'Validating credentials for user name "{login}"')
        if login not in self.credentials:
            self.logger.log(logging.ERROR,
                            f'User name "{self.username}" not found')
            return False

        hashed_pwd = hash_password(login, self.password)
        if self.credentials[login].lower() != hashed_pwd.lower():
            self.logger.log(logging.ERROR,
                            f'Wrong password for user name "{self.username}"')
            return False

        return True

    def _validate_credentials(self, method) -> bool:
        '''
        Validates credentials according to specified methods if they
        are what expected.

        Parameters
        ----------
        method: str
            Authentication method name.

        Returns
        -------
        bool
            True if credentials are valid.
            False otherwise.
        '''
        if method == 'basic-auth':
            return self._validate_basic_auth_credentials()
        # Add new methods here...

        # No known methods were found
        self.logger.log(
            logging.CRITICAL,
            f'Unknown authentication method(s) "{method}" are configured '
            f'for API "{api_version}"')
        return False

    def handle_authentication(self, api_version) -> bool:
        '''
        If authentication feature is configured checks provided
        credentials.

        Parameters
        ----------
        api_version : str
            API version for authentication.

        Returns
        -------
        bool
            True if authentication is not required.
            True if authentication is required and valid
            credentials provided.
            False otherwise.
        '''
        self.logger.log(logging.DEBUG, 'Handling authentication')
        found, method = self._get_auth_method(api_version)
        if not found:
            return False

        if method == '':
            # Do not validate credentials
            return True

        if not self._get_credentials(method):
            return False

        return self._validate_credentials(method)

    def should_fail_with_not_authorized(self):
        '''
        Checks if authentication is required:
        - if it is not returns false, None
        - if it is required validates provided credentials

        Returns
        -------
        bool
            False if authentication is not required or is
            required and validation for credentials passes.
            True if validation for credentials failed.
        '''
        return self.not_authorized

    def fail_with_not_authorized(self):
        '''
        Prepares server 401 response.
        '''
        self.logger.log(
            logging.ERROR,
            'Failing with 401 for unauthorized request')
        self.set_status(401)
        self.set_header('WWW-Authenticate',
                        f'Basic realm="{self.tabpy_state.name}"')
        self.error_out(
            401,
            info="Unauthorized request.",
            log_message="Invalid credentials provided.")
