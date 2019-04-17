import base64
import binascii
import concurrent
import tornado.web
import json
import logging

from tabpy_server.app.SettingsParameters import SettingsParameters
from tabpy_server.handlers.util import hash_password

logger = logging.getLogger(__name__)
STAGING_THREAD = concurrent.futures.ThreadPoolExecutor(max_workers=3)


class BaseHandler(tornado.web.RequestHandler):
    KEYS_TO_SANITIZE = ("api key", "api_key", "admin key", "admin_key")

    def initialize(self, app):
        self.tabpy_state = app.tabpy_state
        # set content type to application/json
        self.set_header("Content-Type", "application/json")
        self.port = self.settings[SettingsParameters.Port]
        self.python_service = app.python_service
        self.credentials = app.credentials
        self.log_request_context =\
            app.settings[SettingsParameters.LogRequestContext]
        self.username = None

    def error_out(self, code, log_message, info=None):
        self.set_status(code)
        self.write(json.dumps(
            {'message': log_message, 'info': info or {}}))

        # We want to duplicate error message in console for
        # loggers are misconfigured or causing the failure
        # themselves
        print(info)
        logger.error(
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
            logger.debug(self.append_request_context(
                "Access-Control-Allow-Origin:{}".format(origin)))

        headers = self.tabpy_state.get_access_control_allow_headers()
        if len(headers) > 0:
            self.set_header("Access-Control-Allow-Headers", headers)
            logger.debug(self.append_request_context(
                "Access-Control-Allow-Headers:{}".format(headers)))

        methods = self.tabpy_state.get_access_control_allow_methods()
        if len(methods) > 0:
            self.set_header("Access-Control-Allow-Methods", methods)
            logger.debug(self.append_request_context(
                "Access-Control-Allow-Methods:{}".format(methods)))

    def _sanitize_request_data(self, data, keys=KEYS_TO_SANITIZE):
        """Remove keys so that we can log safely"""
        for key in keys:
            data.pop(key, None)

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
        '''
        if api_version not in self.settings[SettingsParameters.ApiVersions]:
            logger.critical(f'Unknown API version "{api_version}"')
            return False, ''

        version_settings =\
            self.settings[SettingsParameters.ApiVersions][api_version]
        if 'features' not in version_settings:
            logger.info(f'No features configured for API "{api_version}"')
            return True, ''

        features = version_settings['features']
        if 'authentication' not in features or\
                not features['authentication']['required']:
            logger.info(
                f'Authentication is not a required feature for API '
                '"{api_version}"')
            return True, ''

        auth_feature = features['authentication']
        if 'methods' not in auth_feature:
            logger.critical(
                f'Authentication method is not configured for API '
                '"{api_version}"')

        methods = auth_feature['methods']
        if 'basic-auth' in auth_feature['methods']:
            return True, 'basic-auth'
        # Add new methods here...

        # No known methods were found
        logger.critical(
            f'Unknown authentication method(s) "{methods}" are configured '
            'for API "{api_version}"')
        return False, ''

    def _get_basic_auth_credentials(self) -> bool:
        '''
        Find credentials for basic access authentication method. Credentials if
        found stored in self.username and self.password.

        Returns
        -------
        bool
            True if valid credentials were found.
            False otherwise.
        '''
        logger.debug('Checking request headers for authentication data')
        if 'Authorization' not in self.request.headers:
            logger.info('Authorization header not found')
            return False

        auth_header = self.request.headers['Authorization']
        auth_header_list = auth_header.split(' ')
        if len(auth_header_list) != 2 or\
                auth_header_list[0] != 'Basic':
            logger.error(f'Unknown authentication method "{auth_header}"')
            return False

        try:
            cred = base64.b64decode(auth_header_list[1]).decode('utf-8')
        except (binascii.Error, UnicodeDecodeError) as ex:
            logger.critical(f'Cannot decode credentials: {str(ex)}')
            return False

        login_pwd = cred.split(':')
        if len(login_pwd) != 2:
            logger.error('Invalid string in encoded credentials')
            return False

        self.username = login_pwd[0]
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
        logger.critical(
            f'Unknown authentication method(s) "{method}" are configured '
            'for API "{api_version}"')
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
        logger.debug(f'Validating credentials for user name "{login}"')
        if login not in self.credentials:
            logger.error(f'User name "{self.username}" not found')
            return False

        hashed_pwd = hash_password(self.username, self.password)
        if self.credentials[login].lower() != hashed_pwd.lower():
            logger.error(f'Wrong password for user name "{self.username}"')
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
        logger.critical(
            f'Unknown authentication method(s) "{method}" are configured '
            'for API "{api_version}"')
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
        logger.debug('Handling authentication')
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
        logger.debug(self.append_request_context(
            'Checking if need to handle authentication'))
        return not self.handle_authentication("v1")

    def fail_with_not_authorized(self):
        '''
        Prepares server 401 response.
        '''
        logger.error(self.append_request_context(
            'Failing with 401 for unauthorized request'))
        self.set_status(401)
        self.set_header('WWW-Authenticate',
                        'Basic realm="{}"'.format(self.tabpy_state.name))
        self.error_out(
            401,
            info="Unauthorized request.",
            log_message="Invalid credentials provided.")

    def append_request_context(self, msg) -> str:
        '''
        Adds request context (caller info) to logged messages.
        '''
        context = ''
        if self.log_request_context:
            # log request details
            context = (f'{self.request.remote_ip} calls '
                       '{self.request.method} {self.request.full_url()}')
            if 'TabPy-Client' in self.request.headers:
                context += f', Client: {self.request.headers["TabPy-Client"]}'
            if 'TabPy-User' in self.request.headers:
                context +=\
                    f', Tableau user: {self.request.headers["TabPy-User"]}'
            if self.username is not None and self.username != '':
                context += f', TabPy user: {self.username}'
            context += '\n'

        return context + msg
