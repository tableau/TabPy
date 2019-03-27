'''
Utility for managing user names and passwords for TabPy.
'''

from argparse import ArgumentParser
import logging
import random
import string
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


def generate_password():
    password_chars =\
        string.ascii_letters +\
        string.digits +\
        string.punctuation
    pwd = ''.join(random.choice(password_chars) for i in range(16))
    logger.info('Generated password "%s"' % pwd)
    return pwd


def store_passwords_file(pwdfile, credentials):
    with open(pwdfile, 'wt') as f:
        for username, pwd in credentials.items():
            f.write('%s %s\n' % (username, pwd))
    return True


def add_user(args, credentials):
    username = args.username.lower()
    if username in credentials:
        logger.error('Can\'t add username %s as it is already present '
                     'in passwords file. Do you want to run '
                     '"update" command instead?' % username)
        return False

    password = args.password
    logger.info('Adding username "%s" with password "%s"...' % 
                (username, password))
    credentials[username] = hash_password(username, password)

    return store_passwords_file(args.pwdfile, credentials)


def update_user(args, credentials):
    username = args.username.lower()
    if username not in credentials:
        logger.error('Username "%s" not found in passwords file. '
                     'Do you want to run "add" command instead?' %
                     username)
        return False

    password = args.password
    logger.info('Updating username "%s" password  to "%s"...' % 
                (username, password))
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
    

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format="%(message)s")
    main()
