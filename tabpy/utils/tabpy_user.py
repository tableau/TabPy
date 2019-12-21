"""
Utility for managing user names and passwords for TabPy.
For more information about how to configure and use authentication for
TabPy read the documentation at https://github.com/tableau/TabPy.

Usage:
  tabpy-user add (-u NAME | --user <NAME>) [-p PWD | --password PWD] (-f FILE | --pwdfile FILE)
  tabpy-user update (-u NAME | --user <NAME>) [-p PWD | --password PWD] (-f FILE | --pwdfile FILE)
  tabpy-user -h | --help

Options:
  -h --help                Show this screen.
  -u NAME --username NAME  Username to add to password file.
  -p PWD --password PWD    Password for the username. If not specified a
                             password will be generated.
  -f FILE --pwdfile FILE   Fully qualified path to passwords file.
"""

import docopt
import logging
import secrets
from tabpy.tabpy_server.app.util import parse_pwd_file
from tabpy.tabpy_server.handlers.util import hash_password

logger = logging.getLogger(__name__)


def generate_password(pwd_len=16):
    # List of characters to generate password from.
    # We want to avoid to use similarly looking pairs like
    # (O, 0), (1, l), etc.
    lower_case_letters = "abcdefghijkmnpqrstuvwxyz"
    upper_case_letters = "ABCDEFGHIJKLMPQRSTUVWXYZ"
    digits = "23456789"

    # and for punctuation we want to exclude some characters
    # like inverted comma which can be hard to find and/or
    # type
    # change this string if you are supporting an
    # international keyboard with differing keys available
    punctuation = "!#$%&()*+,-./:;<=>?@[\\]^_{|}~"

    # we also want to try to have more letters and digits in
    # generated password than punctuation marks
    password_chars = (
        lower_case_letters
        + lower_case_letters
        + upper_case_letters
        + upper_case_letters
        + digits
        + digits
        + punctuation
    )
    pwd = "".join(secrets.choice(password_chars) for i in range(pwd_len))
    logger.info(f'Generated password: "{pwd}"')
    return pwd


def store_passwords_file(pwdfile, credentials):
    with open(pwdfile, "wt") as f:
        for username, pwd in credentials.items():
            f.write(f"{username} {pwd}\n")
    return True


def add_user(args, credentials):
    username = args["--username"].lower()
    logger.info(f'Adding username "{username}"')

    if username in credentials:
        logger.error(
            f"Can't add username {username} as it is already present"
            " in passwords file. Do you want to run the "
            '"update" command instead?'
        )
        return False

    password = args["--password"]
    logger.info(f'Adding username "{username}" with password "{password}"...')
    credentials[username] = hash_password(username, password)

    if store_passwords_file(args["--pwdfile"], credentials):
        logger.info(f'Added username "{username}" with password "{password}"')
    else:
        logger.info(
            f'Could not add username "{username}" , ' f'password "{password}" to file'
        )


def update_user(args, credentials):
    username = args["--username"].lower()
    logger.info(f'Updating username "{username}"')

    if username not in credentials:
        logger.error(
            f'Username "{username}" not found in passwords file. '
            'Do you want to run "add" command instead?'
        )
        return False

    password = args["--password"]
    logger.info(f'Updating username "{username}" password  to "{password}"')
    credentials[username] = hash_password(username, password)
    return store_passwords_file(args["--pwdfile"], credentials)


def process_command(args, credentials):
    if args["add"]:
        return add_user(args, credentials)
    elif args["update"]:
        return update_user(args, credentials)
    else:
        logger.error(f'Unknown command "{args.command}"')
        return False


def main():
    logging.basicConfig(level=logging.DEBUG, format="%(message)s")

    args = docopt.docopt(__doc__)

    succeeded, credentials = parse_pwd_file(args["--pwdfile"])
    if not succeeded and not args["add"]:
        return

    if args["--password"] is None:
        args["--password"] = generate_password()

    process_command(args, credentials)
    return


if __name__ == "__main__":
    main()
