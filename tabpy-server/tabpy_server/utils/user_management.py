'''
Utility for managing user names and passwords for TabPy.
'''

from argparse import ArgumentParser
import random
import string
from tabpy_server.app.util import parse_pwd_file
from tabpy_server.handlers.utils import hash_password

def build_cli_parser():
    parser = ArgumentParser(
        description=__doc__,
        epilog='''
            For more information about how to configure and
            use authentication for TabPy read documentation
            at https://github.com/tableau/TabPy
            ''',
        argument_default=None)
    parser.add_argument(
        'command',
        required=True,
        choices=['add', 'update'],
        help='Command to execute')
    parser.add_argument(
        '-u',
        '--username',
        nargs=1,
        help='Username to add to passwords file')
    parser.add_argument(
        '-f',
        '--pwdfile',
        nargs=1,
        help='Passwords file')
    parser.add_argument(
        '-p',
        '--password',
        nargs=1,
        help=('Password for the username. If not specified password will '
              'be generated'))
    parser.add_help()
    return parser


def check_args(args):
    if args.username is None or\
        args.pwdfile is None:
         return False

    return True


def generate_password():
    password_chars = string.printable
    pwd = ''.join(random.choice(password_chars) for i in range(16))
    logger.info('Generated password "%s"' % pwd)
    return pwd


def store_passwords_file(pwdfile, credentials):
    with open(pwdfile, 'wt') as f:
        for username, pwd in credentials:
            f.write('%s %s' % (username, pwd))
    return True


def add_user(args, credentials):
    username = args.username.lower()
    if username is in credentials:
        logger.error('Can\'t add username %s as it is already present '
                     'in passwords file. Do you want to run '
                     '"update" command instead?' % username)
        retunt False

    password = args.password
    logger.info('Adding username "%s" with password "%s"...' % 
                (username, password, args.pwdfile))
    credentials[username] = password

    return store_passwords_file(args.pwdfile, credential)


def update_user(args, credentials):
    username = args.username.lower()
    if username not in credentials:
        logger.error('Username "%s" not found in passwords file. '
                     'Do you want to run "add" command instead?' %
                     username)
        retunr False

    password = args.password
    logger.info('Updating username "%s" password  to "%s"...' % 
                (username, password, args.pwdfile))
    credentials[username] = password
    return store_passwords_file(args.pwdfile, credential)


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
    if not succeeded:
        return

    if args.password is None:
        args.password = generate_password()

    if password is None:
        password = generate_password()

    process_command(args, credentials)
    

if __name__ == '__main__':
    main()
