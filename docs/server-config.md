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
environment variables or with a config file.

Configuration parameters can be updated with:

1. Adding environment variables - set the environment variable as required by
   your Operating System. When creating environment variables, use the same
   name for your environment variable as specified in the config file.
2. Specifying a parameter in a config file (environment variable value overwrites
   configuration setting).

Configuration file with custom settings is specified as a command line parameter:

```sh
tabpy --config=path/to/my/config/file.conf
```

The default config file is provided to show you the default values but does not
need to be present to run TabPy.

### Configuration File Content

Configuration file consists of settings for TabPy itself and Python logger
settings. You should only set parameters if you need different values than
the defaults.

Environment variables can be used in the config file. Any instances of
`%(ENV_VAR)s` will be replaced by the value of the environment variable `ENV_VAR`.

TabPy parameters explained below, the logger documentation can be found
at [`logging.config` documentation page](https://docs.python.org/3.6/library/logging.config.html).

`[TabPy]` parameters:

- `TABPY_PORT` - port for TabPy to listen on. Default value - `9004`.
- `TABPY_BIND_IP` - ip address to bind to for TabPy to listen on. Default value - `0.0.0.0`.
- `TABPY_QUERY_OBJECT_PATH` - query objects location. Used with models, see
  [TabPy Tools documentation](tabpy-tools.md) for details. Default value -
  `/tmp/query_objects`.
- `TABPY_STATE_PATH` - state folder location (absolute path) for Tornado web
   server. Default value - `tabpy/tabpy_server` subfolder in TabPy package
   folder.
- `TABPY_STATIC_PATH` - absolute path for location of static files (index.html
  page) for TabPy instance. Default value - `tabpy/tabpy_server/static`
  subfolder in TabPy package folder.
- `TABPY_PWD_FILE` - absolute path to password file. Setting up this parameter
  makes TabPy require credentials with HTTP(S) requests. More details about
  authentication can be found in [Authentication](#authentication)
  section. Default value - not set.
- `TABPY_TRANSFER_PROTOCOL` - transfer protocol. Default value - `http`. If
  set to `https` two additional parameters have to be specified:
  `TABPY_CERTIFICATE_FILE` and `TABPY_KEY_FILE`.
  Details are in the [Configuring HTTP vs HTTPS](#configuring-http-vs-https)
  section.
- `TABPY_CERTIFICATE_FILE` - absolute path to the certificate file to run
  TabPy with. Only used with `TABPY_TRANSFER_PROTOCOL` set to `https`.
  Default value - not set.
- `TABPY_KEY_FILE` - absolute path to private key file to run TabPy with.
  Only used with `TABPY_TRANSFER_PROTOCOL` set to `https`. Default value -
  not set.
- `TABPY_MINIMUM_TLS_VERSION` - set the minimum TLS version that the server
  will accept for secure connections (`TLSv1_2`, `TLSv1_3`, etc). Refer to
  [docs.python.org](https://docs.python.org/3/library/ssl.html#ssl.TLSVersion.MINIMUM_SUPPORTED)
  for acceptable values. Default value - `TLSv1_2`.
- `TABPY_LOG_DETAILS` - when set to `true` additional call information
  (caller IP, URL, client info, etc.) is logged. Default value - `false`.
- `TABPY_MAX_REQUEST_SIZE_MB` - maximal request size supported by TabPy server
  in Megabytes. All requests of exceeding size are rejected. Default value is
  100 Mb.
- `TABPY_EVALUATE_ENABLE` - enable evaluate api to execute ad-hoc Python scripts
  Default value - `true`.
- `TABPY_EVALUATE_TIMEOUT` - script evaluation timeout in seconds. Default
  value - `30`. This timeout does not apply when evaluating models either
  through the `/query` method, or using the `tabpy.query(...)` syntax with
  the `/evaluate` method.
- `TABPY_GZIP_ENABLE` - Enable Gzip support for requests. Enabled by default.
- `TABPY_ARROW_ENABLE` - Enable Arrow connection for data streaming. Default
  value is False.
- `TABPY_ARROWFLIGHT_PORT` - port for
  [Arrow Flight](https://arrow.apache.org/docs/format/Flight.html)
  connection used in streaming mode. Default value is 13622.
- `TABPY_ARROWFLIGHT_BIND_IP` - ip address to bind to for Arrow Flight to listen on. Default value is `0.0.0.0`.

### Configuration File Example

**Note:** _Always use absolute paths for the configuration paths
settings._

```ini
[TabPy]
# TABPY_QUERY_OBJECT_PATH = /tmp/query_objects
# TABPY_PORT = 9004
# TABPY_BIND_IP = 0.0.0.0
# TABPY_STATE_PATH = <package-path>/tabpy/tabpy_server

# Where static pages live
# TABPY_STATIC_PATH = <package-path>/tabpy/tabpy_server/static

# For how to configure TabPy authentication read
# docs/server-config.md.
# TABPY_PWD_FILE = /path/to/password/file.txt

# To set up secure TabPy uncomment and modify the following lines.
# Note only PEM-encoded x509 certificates are supported.
# TABPY_TRANSFER_PROTOCOL = https
# TABPY_CERTIFICATE_FILE = /path/to/certificate/file.crt
# TABPY_KEY_FILE = /path/to/key/file.key
# TABPY_MINIMUM_TLS_VERSION = TLSv1_2

# Log additional request details including caller IP, full URL, client
# end user info if provided.
# TABPY_LOG_DETAILS = true

# Limit request size (in Mb) - any request which size exceeds
# specified amount will be rejected by TabPy.
# Default value is 100 Mb.
# TABPY_MAX_REQUEST_SIZE_MB = 100

# Enable evaluate api to execute ad-hoc Python scripts
# Enabled by default. Disabling it will result in 404 error.
# TABPY_EVALUATE_ENABLE = true

# Configure how long a custom script provided to the /evaluate method
# will run before throwing a TimeoutError.
# The value should be a float representing the timeout time in seconds.
# TABPY_EVALUATE_TIMEOUT = 30

# Configure TabPy to support streaming data via Arrow Flight.
# This will cause an Arrow Flight server start up. The Arrow
# Flight port defaults to 13622 if not set here.
# TABPY_ARROW_ENABLE = True
# TABPY_ARROWFLIGHT_PORT = 13622
# TABPY_ARROWFLIGHT_BIND_IP = 0.0.0.0


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

Passwords in the password file are hashed with PBKDF2.

**It is highly recommended to restrict access to the password file
with hosting OS mechanisms. Ideally the file should only be accessible
for reading with the account under which TabPy runs and TabPy admin account.**

There is a `tabpy-user` command provided with `tabpy` package to
operate with accounts in the password file. Run `tabpy-user -h`
to see how to use it.

After making any changes to the password file, TabPy needs to be restarted.

### Adding an Account

To add an account run `tabpy-user add`
command  providing user name, password (optional) and password file:

```sh
tabpy-user add -u <username> -p <password> -f <pwdfile>
```

If the (recommended) `-p` argument is not provided a password for the user name
will be generated and displayed in the command line.

### Updating an Account

To update the password for an account run `tabpy-user update`
command:

```sh
tabpy-user update -u <username> -p <password> -f <pwdfile>
```

If the (recommended) `-p` agrument is not provided a password for the user name
will be generated and displayed in the command line.

### Deleting an Account

To delete an account open password file in any text editor and delete the
line with the user name.

### Endpoint Security

All endpoints require authentication if it is enabled for the server.

## Arrow Flight

TabPy can be configured to enable Arrow Flight. This will cause a Flight
server to start up alongside the HTTP server and will allow for handling
incoming streamed data in the Arrow columnar format.

**As of May 2023, the Arrow Flight feature can only be used by compatible
versions of Tableau Prep. The Arrow Flight feature is not used by Tableau
Desktop, Tableau Server, or Tableau Cloud, regardless of the
`TABPY_ARROW_ENABLE` setting. In other words, those products will continue
to send the data in a single payload when Arrow Flight is both enabled
and disabled.**

To leverage the Flight server, use an existing Flight Client API. There
are implementations available in C++, Java, and Python. To begin streaming
data to the server, a Flight Descriptor (data path) must be generated.
One can be obtained via the TabPy Flight server by using the client to
submit a `getUniquePath` Action to the server or it can be randomly generated
locally. The client's `do_put` interface can then be used to begin sending
data to the server.

Structure the data payload in Arrow format according to the client's API
requirements. Continue using the client to append the data path with the
data stream.

The mechanism for sending the Python script to the server does not change.

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
URL, client infomation (Tableau Desktop\Server) and TabPy user name as shown in
the example below:

<!-- markdownlint-disable MD013 -->
<!-- markdownlint-disable MD040 -->

```
2019-05-02,13:50:08 [INFO] (base_handler.py:base_handler:90): Call ID: 934073bd-0d29-46d3-b693-b1e4b1efa9e4, Caller: ::1, Method: POST, Resource: http://localhost:9004/evaluate, Client: Postman for manual testing
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
