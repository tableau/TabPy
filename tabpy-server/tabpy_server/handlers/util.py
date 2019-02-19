import logging
import sha3

from tabpy_server.app.app import TabPyApp

logger = logging.get_logger(__name__)

def validate_credentials(username, pwd, credentials):
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
