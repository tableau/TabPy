# TabPy Server Configuration Instructions

<!-- markdownlint-disable MD004 -->
<!-- toc -->

- [Configuring HTTP vs HTTPS](#configuring-http-vs-https)
- [Authentication](#authentication)
  * [Enabling Authentication](#enabling-authentication)
  * [Password File](#password-file)
  * [Adding an Account](#adding-an-account)
  * [Updating an Account](#updating-an-account)
  * [Deleting an Account](#deleting-an-account)

<!-- tocstop -->
<!-- markdownlint-enable MD004 -->

Default settings for TabPy may be viewed in the
tabpy_server/common/default.conf file. This file also contains a
commented example of how to set up your TabPy server to only
serve HTTPS traffic.

Change settings by:

1. Adding environment variables:
   - set the environment variable as required by your Operating System. When
     creating environment variables, use the same name as is in the config file
     as an environment variable. The files startup.sh and startup.cmd in the root
     of the install folder have examples of how to set environment variables in
     both Linux and Windows respectively. Set any desired environment variables
     and then start the application.
2. Modifying default.conf.
3. Specifying your own config file as a command line parameter.
   - i.e. Running the command:
     ```python tabpy.py --config=path\to\my\config```

The default config file is provided to show you the default values but does not
need to be present to run TabPy.

## Configuring HTTP vs HTTPS

By default, TabPy serves only HTTP requests. TabPy can be configured to serve
only HTTPS requests by setting the following parameter in the config file:

```sh
TABPY_TRANSFER_PROTOCOL = https
```

If HTTPS is selected, the absolute paths to the cert and key file need to be
specified in your config file using the following parameters:

```sh
TABPY_CERTIFICATE_FILE = C:/path/to/cert/file.crt
TABPY_KEY_FILE = C:/path/to/key/file.key
```

Note that only PEM-encoded x509 certificates are supported for the secure
connection scenario.

## Authentication

TabPy supports basic access authentication (see
[https://en.wikipedia.org/wiki/Basic_access_authentication](https://en.wikipedia.org/wiki/Basic_access_authentication)
for more details).

### Enabling Authentication

To enable the feature specify `TABPY_PWD_FILE` parameter in TabPy
configuration file with a fully qualified name:

```sh
TABPY_PWD_FILE = c:\path\to\password\file.txt
```

### Password File

Password file is a text file containing usernames and hashed passwords
per line separated by space. For username only ASCII characters
supported.

**It is highly recommended to restrict access to the password file
with hosting OS mechanisms. Ideally the file should only be accessible
for reading with account TabPy runs as and TabPy admin account.**

There is `utils/user_management.py` utility to operate with
accounts in the password file. Run `utils/user_management.py -h` to
see how to use it.

After making any changes to the password file, TabPy needs to be restarted.

### Adding an Account

To add an account run `utils/user_management.py` utility with `add`
command  providing user name, password (optional) and password file:

```sh
python utils/user_management.py add -u <username> -p <password> -f <pwdfile>
```

If `-p` agrument is not provided (recommended) password for the user name
will be generated.

### Updating an Account

To update password for an account run `utils/user_management.py` utility
with `update` command:

```sh
python utils/user_management.py update -u <username> -p <password> -f <pwdfile>
```

If `-p` agrument is not provided (recommended) password for the user name
will be generated.

### Deleting an Account

To delete an account open password file in any text editor and delete the
line with the user name.
