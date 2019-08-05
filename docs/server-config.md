# TabPy Server Configuration Instructions

<!-- markdownlint-disable MD004 -->

<!-- toc -->

- [Custom Settings](#custom-settings)
  * [Configuration File Content](#configuration-file-content)
  * [Configuration File Example](#configuration-file-example)
- [Configuring HTTP vs HTTPS](#configuring-http-vs-https)
- [Authentication](#authentication)
  * [Enabling Authentication](#enabling-authentication)
  * [Password File](#password-file)
  * [Adding an Account](#adding-an-account)
  * [Updating an Account](#updating-an-account)
  * [Deleting an Account](#deleting-an-account)
- [Logging](#logging)
  * [Request Context Logging](#request-context-logging)

<!-- tocstop -->

<!-- markdownlint-enable MD004 -->

## Custom Settings

TabPy starts with set of default settings unless settings are provided via
environment variables or with a config files.

Configuration parameters can be updated with:

1. Adding environment variables - set the environment variable as required by
   your Operating System. When creating environment variables, use the same
   name as is in the config file as an environment variable.
2. Specifying a parameter in a config file (enviroment variable value overwrites
   configuration setting).

Configuration file with custom settings is specified as a command line parameter:

```sh
tabpy --config=path/to/my/config/file.conf
```

The default config file is provided to show you the default values but does not
need to be present to run TabPy.

### Configuration File Content

Configuration file consists of settings for TabPy itself and Python logger
settings. It is possible to only set parameters which value should be different
from default.

TabPy parameters explained below and for the logger documentation
can be found at [`logging.config` documentation page](https://docs.python.org/3.6/library/logging.config.html).

`[TabPy]` parameters:

- `TABPY_PORT` - port for TabPy to listen on. Default value - `9004`.
- `TABPY_QUERY_OBJECT_PATH` - query objects location. Used with models, see
  [TabPy Tools documentation](tabpy-tools.md) for details. Default value -
  `/tmp/query_objects`.
- `TABPY_STATE_PATH` - state location for Tornado web server. Default
   value - `tabpy/tabpy_server` subfolder in TabPy package folder.
- `TABPY_STATIC_PATH` - location of static files (index.html page) for
  TabPy instance. Default value - `tabpy/tabpy_server/static` subfolder in
  TabPy package folder.
- `TABPY_PWD_FILE` - path to password file. Setting up this parameter
  makes TabPy require credentials with HTTP(S) requests. More details about
  authentication can be found in [Authentication](#authentication)
  section. Default value - not set.
- `TABPY_TRANSFER_PROTOCOL` - transfer protocol. Default value - `http`. If
  set to `http` two additional parameters have to be specified:
  `TABPY_CERTIFICATE_FILE` and `TABPY_KEY_FILE`. More details for how to
  configure TabPy for HTTPS are at [Configuring HTTP vs HTTPS]
  (#configuring-http-vs-https) section.
- `TABPY_CERTIFICATE_FILE` to certificate file to run TabPy with. Only used
  with `TABPY_TRANSFER_PROTOCOL` set to `https`. Default value - not set.
- `TABPY_KEY_FILE` to private key file to run TabPy with. Only used
  with `TABPY_TRANSFER_PROTOCOL` set to `https`. Default value - not set.
- `TABPY_LOG_DETAILS` - when set to `true` additional call information
  (caller IP, URL, client info, etc.) is logged. Default value - `false`.
- `TABPY_EVALUATE_TIMEOUT` - script evaluation timeout in seconds. Default
  value - `30`.

### Configuration File Example

```toml
[TabPy]
# TABPY_QUERY_OBJECT_PATH = /tmp/query_objects
# TABPY_PORT = 9004
# TABPY_STATE_PATH = ./tabpy/tabpy_server

# Where static pages live
# TABPY_STATIC_PATH = ./tabpy/tabpy_server/static

# For how to configure TabPy authentication read
# docs/server-config.md.
# TABPY_PWD_FILE = /path/to/password/file.txt

# To set up secure TabPy uncomment and modify the following lines.
# Note only PEM-encoded x509 certificates are supported.
# TABPY_TRANSFER_PROTOCOL = https
# TABPY_CERTIFICATE_FILE = path/to/certificate/file.crt
# TABPY_KEY_FILE = path/to/key/file.key

# Log additional request details including caller IP, full URL, client
# end user info if provided.
# TABPY_LOG_DETAILS = true

# Configure how long a custom script provided to the /evaluate method
# will run before throwing a TimeoutError.
# The value should be a float representing the timeout time in seconds.
#TABPY_EVALUATE_TIMEOUT = 30

[loggers]
keys=root

[handlers]
keys=rootHandler,rotatingFileHandler

[formatters]
keys=rootFormatter

[logger_root]
level=DEBUG
handlers=rootHandler,rotatingFileHandler
qualname=root
propagete=0

[handler_rootHandler]
class=StreamHandler
level=DEBUG
formatter=rootFormatter
args=(sys.stdout,)

[handler_rotatingFileHandler]
class=handlers.RotatingFileHandler
level=DEBUG
formatter=rootFormatter
args=('tabpy_log.log', 'a', 1000000, 5)

[formatter_rootFormatter]
format=%(asctime)s [%(levelname)s] (%(filename)s:%(module)s:%(lineno)d): %(message)s
datefmt=%Y-%m-%d,%H:%M:%S

```

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

To enable the feature specify the `TABPY_PWD_FILE` parameter in the
TabPy configuration file with a fully qualified name:

```sh
TABPY_PWD_FILE = c:\path\to\password\file.txt
```

### Password File

Password file is a text file containing usernames and hashed passwords
per line separated by single space. For username only ASCII characters
are supported. Usernames are case-insensitive.

Passwords in the password file are hashed with PBKDF2. [See source code
for implementation details](../tabpy-server/tabpy_server/handlers/util.py).

**It is highly recommended to restrict access to the password file
with hosting OS mechanisms. Ideally the file should only be accessible
for reading with the account under which TabPy runs and TabPy admin account.**

There is a `utils/user_management.py` utility to operate with
accounts in the password file. Run `utils/user_management.py -h` to
see how to use it.

After making any changes to the password file, TabPy needs to be restarted.

### Adding an Account

To add an account run `utils/user_management.py` utility with `add`
command  providing user name, password (optional) and password file:

```sh
python utils/user_management.py add -u <username> -p <password> -f <pwdfile>
```

If the (recommended) `-p` argument is not provided a password for the user name
will be generated and displayed in the command line.

### Updating an Account

To update the password for an account run `utils/user_management.py` utility
with `update` command:

```sh
python utils/user_management.py update -u <username> -p <password> -f <pwdfile>
```

If the (recommended) `-p` agrument is not provided a password for the user name
will be generated and displayed in the command line.

### Deleting an Account

To delete an account open password file in any text editor and delete the
line with the user name.

## Logging

Logging for TabPy is implemented with Python's standard logger and can be configured
as explained in Python documentation at
[Logging Configuration page](https://docs.python.org/3.6/library/logging.config.html).

A default config provided with TabPy is at
[`tabpy-server/tabpy_server/common/default.conf`](tabpy-server/tabpy_server/common/default.conf)
and has a configuration for console and file loggers. Changing the config file
allows the user to modify the log level, format of the logged messages and
add or remove loggers.

### Request Context Logging

For extended logging (e.g. for auditing purposes) additional logging can be turned
on with setting `TABPY_LOG_DETAILS` configuration file parameter to `true`.

With the feature on additional information is logged for HTTP requests: caller ip,
URL, client infomation (Tableau Desktop\Server), Tableau user name (for Tableau Server)
and TabPy user name as shown in the example below:

<!-- markdownlint-disable MD013 -->
<!-- markdownlint-disable MD040 -->

```
2019-05-02,13:50:08 [INFO] (base_handler.py:base_handler:90): Call ID: 934073bd-0d29-46d3-b693-b1e4b1efa9e4, Caller: ::1, Method: POST, Resource: http://localhost:9004/evaluate, Client: Postman for manual testing, Tableau user: ogolovatyi
2019-05-02,13:50:08 [DEBUG] (base_handler.py:base_handler:120): Checking if need to handle authentication, <<
call ID: 934073bd-0d29-46d3-b693-b1e4b1efa9e4>>
2019-05-02,13:50:08 [DEBUG] (base_handler.py:base_handler:120): Handling authentication, <<call ID: 934073bd-
0d29-46d3-b693-b1e4b1efa9e4>>
2019-05-02,13:50:08 [DEBUG] (base_handler.py:base_handler:120): Checking request headers for authentication d
ata, <<call ID: 934073bd-0d29-46d3-b693-b1e4b1efa9e4>>
2019-05-02,13:50:08 [DEBUG] (base_handler.py:base_handler:120): Validating credentials for user name "user1",
 <<call ID: 934073bd-0d29-46d3-b693-b1e4b1efa9e4>>
2019-05-02,13:50:08 [DEBUG] (state.py:state:484): Collecting Access-Control-Allow-Origin from state file...  
2019-05-02,13:50:08 [INFO] (base_handler.py:base_handler:120): function to evaluate=def _user_script(tabpy, _
arg1, _arg2):
 res = []
 for i in range(len(_arg1)):
   res.append(_arg1[i] * _arg2[i])
 return res
, <<call ID: 934073bd-0d29-46d3-b693-b1e4b1efa9e4>>
```

<!-- markdownlint-enable MD040 -->
<!-- markdownlint-enable MD013 -->

No passwords are logged.

NOTE the request context details are logged with INFO level.
