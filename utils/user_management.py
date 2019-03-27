'''
Utility for managing user names and passwords for TabPy.
'''

from argparse import ArgumentParser
import logging
import os
import random
import sys
from tabpy_server.app.util import parse_pwd_file
from tabpy_server.handlers.util import hash_password

logger = logging.getLogger(__name__)


def build_cli_parser():
    parser = ArgumentParser(
        description=__doc__,
        epilog='''
            For more information about how to configure and
            use authentication for TabPy read documentation
            at https://github.com/tableau/TabPy
            ''',
        argument_default=None,
        add_help=True)
    parser.add_argument(
        'command',
        choices=['add', 'update'],
        help='Command to execute')
    parser.add_argument(
        '-u',
        '--username',
        help='Username to add to passwords file')
    parser.add_argument(
        '-f',
        '--pwdfile',
        help='Passwords file')
    parser.add_argument(
        '-p',
        '--password',
        help=('Password for the username. If not specified password will '
              'be generated'))
    return parser


def check_args(args):
    if (args.username is None) or (args.pwdfile is None):
        return False

    return True


def generate_password(pwd_len=16):
    # List of characters to generate password from.
    # We want to avoid to use similarly looking pairs like
    # (O, 0), (1, l), etc.
    lower_case_letters = 'abcdefghijkmnpqrstuvwxyz'
    upper_case_letters = 'ABCDEFGHIJKLMPQRSTUVWXYZ'
    digits = '23456789'

    # and for punctuation we want to exclude some characters
    # like inverted coma which can be hard to find and/or
    # type
    punctuation = '!#$%&()*+,-./:;<=>?@[\\]^_{|}~'

    # we also want to have more letters and digits in
    # generated password then punctuations
    password_chars =\
        lower_case_letters + lower_case_letters +\
        upper_case_letters + upper_case_letters +\
        digits + digits +\
        punctuation
    pwd = ''.join(random.choice(password_chars) for i in range(pwd_len))
    logger.info('Generated password: "{}"'.format(pwd))
    return pwd


def store_passwords_file(pwdfile, credentials):
    with open(pwdfile, 'wt') as f:
        for username, pwd in credentials.items():
            f.write('{} {}\n'.format(username, pwd))
    return True


def add_user(args, credentials):
    username = args.username.lower()
    logger.info('Adding username "{}"'.format(username))

    if username in credentials:
        logger.error('Can\'t add username {} as it is already present '
                     'in passwords file. Do you want to run '
                     '"update" command instead?'.format(username))
        return False

    password = args.password
    logger.info('Adding username "{}" with password "{}"...'.format(
                (username, password)))
    credentials[username] = hash_password(username, password)

    return store_passwords_file(args.pwdfile, credentials)


def update_user(args, credentials):
    username = args.username.lower()
    logger.info('Updating username "{}"'.format(username))

    if username not in credentials:
        logger.error('Username "{}" not found in passwords file. '
                     'Do you want to run "add" command instead?'.
                     format(username))
        return False

    password = args.password
    logger.info('Updating username "{}" password  to "{}"...'.format(
                (username, password)))
    credentials[username] = hash_password(username, password)
    return store_passwords_file(args.pwdfile, credentials)


def process_command(args, credentials):
    if args.command == 'add':
        return add_user(args, credentials)
    elif args.command == 'update':
        return update_user(args, credentials)
    else:
        logger.error('Uknown command "%s"' % args.command)
        return False


def main():
    parser = build_cli_parser()
    args = parser.parse_args()
    if not check_args(args):
        parser.print_help()
        return

    succeeded, credentials = parse_pwd_file(args.pwdfile)
    if not succeeded and args.command != 'add':
        return

    if args.password is None:
        args.password = generate_password()

    process_command(args, credentials)
    return


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format="%(message)s")

    # add tabpy-tools and tabpy-server folders to
    # PYTHONPATH so code from there can be found when
    # modules are imported
    for dir_ in {'tabpy-tools', 'tabpy-server'}:
        sys.path.insert(0, os.path.join(
            os.path.abspath(os.path.dirname(__file__)), dir_))

    main()
