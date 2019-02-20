import base64
import logging
import sha3

from tabpy_server.app.app import TabPyApp

logger = logging.get_logger(__name__)

def validate_basic_auth_credentials(username, pwd, credentials):
    ```
    Validates username:pwd if they are the same as 
    stored credentials.

    Parameters
    ----------
    username : str
        User name (login).

    pwd : str
        Password in plain text. The function will hash
        the password with SHA3 to compare with hashed 
        passwords in stored credentials.

    credentials: dict
        Dictionary of stored credentials where keys are
        user names and values are SHA3-hashed passwords.

    Returns
    -------
    bool
        True if credentials has key login and 
        credentials[login] equal SHA3(pwd), False
        otherwise.
     ```
     login = username.lower()
     logger.debug('Validating credentials for user name "{}"'.format(login))
     if username not in credentials:
         logger.error('User name "{}" not found'.format(username))
         return False

    hashed_pwd = sha3.sha3_224(pwd.encode('utf-8')).hexdigest()
    if credentials[login] != hashed_pwd:
        logger.error('Wrong password for user name "{}"'.format(username))
        return False
        
    return True


def check_and_validate_basic_auth_credentials(headers, credentials):
    ```
    Checks if credentials are provided in headers and 
    if they are valid.

    Parameters
    ----------
    headers
        HTTP request headers.

    credentials: dict
        Dictionary of stored credentials where keys are
        user names and values are SHA3-hashed passwords.

    Returns
    -------
    bool
        True if credentials are present in headers and
        they are valid.
    ```
    logger.debug('Checking request headers for authentication data')
    auth_header = headers.getheader('Authorization')
    if auth_header == None:
        logger.info('Authorization header not found')
        return False

    if auth_header[0:6] != 'Basic ':
        logger.error('Uknown authentication method "{}"'.format(auth_header))
        return False

    encoded_cred = auth_header[6:]
    cred = base64.b64decode(encoded_cred)
    login_pwd = cred.Split(':')
    if len(login_pwd) != 2:
        logger.error('Invalid string in encoded credentials')
        return False

    return validate_credentials(login_pwd[0], login_pwd[1], credentials)


def handle_authentication(headers, api_version, settings, credentials)
    ```
    Checks if credentials need to be validated and they are
    validates them.

    Parameters
    ----------
    headers
        HTTP request headers.

    api_version : str
        API version for authentication.

    settings : dict
        Application settings (TabPyApp.settings).

    credentials: dict
        Dictionary of stored credentials where keys are
        user names and values are SHA3-hashed passwords.

    Returns
    -------
    bool
        If for the specified API version authentication is
        not turned on returns True.
        Otherwise checks what authentication type is used
        and if it is supported type validates provided 
        credentials.
        If authentication type is supported and credentials
        are valid returns True, otherwise False.
    ```
    logger.debug('Handling authentication for request')
    if api_version not in settings['versions']:
        logger.critical('Uknows API version "{}"'.format(api_version))
        return False

    features = settings['versions'][api_version]
    if 'authentication' not in features or\
        features['authentication']['required'] != True:
        logger.info('Authentication is not a required feature for API {}'.format(api_version))
        return True

    auth_feature = features['authentication']
    if 'methods' not in auth_feature or\
        'basic-auth' not in auth_feature['methods']:
        logger.critical('Basic authentication access method is not configured for API {}'.format(api_version))
        return False

    return check_and_validate_basic_auth_credentials(headers, credentials)