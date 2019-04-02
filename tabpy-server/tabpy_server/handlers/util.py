import base64
import binascii
from hashlib import pbkdf2_hmac
import logging

logger = logging.getLogger(__name__)


def hash_password(username, pwd):
    '''
    Hashes password using PKDBF2 method:
    hash = PKDBF2('sha512', pwd, salt=username, 10000)

    Parameters
    ----------
    username : str
        User name (login). Used as salt for hashing.
        User name is lowercased befor being used in hashing.
        Salt is formatted as '_$salt@tabpy:<username>$_' to
        guarantee there's at least 16 characters.

    pwd : str
        Password to hash.

    Returns
    -------
    str
        Sting representation (hexidecimal) for PBKDF2 hash
        for the password.
    '''
    salt = '_$salt@tabpy:%s$_' % username.lower()

    hash = pbkdf2_hmac(hash_name='sha512',
                       password=pwd.encode(),
                       salt=salt.encode(),
                       iterations=10000)
    return binascii.hexlify(hash).decode()


def validate_basic_auth_credentials(username, pwd, credentials):
    '''
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
    '''
    login = username.lower()
    logger.debug('Validating credentials for user name "{}"'.format(login))
    if login not in credentials:
        logger.error('User name "{}" not found'.format(username))
        return False

    hashed_pwd = hash_password(username, pwd)
    if credentials[login].lower() != hashed_pwd.lower():
        logger.error('Wrong password for user name "{}"'.format(username))
        return False

    return True


def check_and_validate_basic_auth_credentials(headers, credentials):
    '''
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
    '''
    logger.debug('Checking request headers for authentication data')
    if 'Authorization' not in headers:
        logger.info('Authorization header not found')
        return False

    auth_header = headers['Authorization']
    auth_header_list = headers['Authorization'].split(' ')
    if len(auth_header_list) != 2 or\
            auth_header_list[0] != 'Basic':
        logger.error('Unknown authentication method "{}"'.format(auth_header))
        return False

    try:
        cred = base64.b64decode(auth_header_list[1]).decode('utf-8')
    except (binascii.Error, UnicodeDecodeError) as ex:
        logger.critical('Cannot decode credentials: {}'.format(str(ex)))
        return False

    login_pwd = cred.split(':')
    if len(login_pwd) != 2:
        logger.error('Invalid string in encoded credentials')
        return False

    return validate_basic_auth_credentials(login_pwd[0],
                                           login_pwd[1],
                                           credentials)


def handle_basic_authentication(headers, api_version, settings, credentials):
    '''
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
    '''
    logger.debug('Handling authentication for request')
    if api_version not in settings['versions']:
        logger.critical('Unknown API version "{}"'.format(api_version))
        return False

    version_settings = settings['versions'][api_version]
    if 'features' not in version_settings:
        logger.info('No features configured for API {}'.format(api_version))
        return True

    features = version_settings['features']
    if 'authentication' not in features or\
            not features['authentication']['required']:
        logger.info(
            'Authentication is not a required feature for API '
            '{}'.format(api_version))
        return True

    auth_feature = features['authentication']
    if 'methods' not in auth_feature or\
            'basic-auth' not in auth_feature['methods']:
        logger.critical(
            'Basic authentication access method is not configured '
            'for API {}'.format(api_version))
        return False

    return check_and_validate_basic_auth_credentials(headers, credentials)
