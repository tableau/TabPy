# TabPy Server Configuration Instructions

Default settings for TabPy may be viewed in the tabpy_server/common/default.conf file. This file also contains a commented example of how to set up your TabPy server to only serve HTTPS traffic.

Change settings by:

1. Adding environment variables:
   - set the environment variable as required by your Operating System. When creating environment variables, use the same name as is in the config file as an environment variable. The files tabpy_server/startup.sh and startup.bat have examples of how to set environment variables in both Linux and Windows respectively.  Set any desired environment variables beforehand and then start the application.
2. Modifying default.conf.
3. Specifying your own config file as a command line parameter.
   - i.e. Running the command:
     ```python tabpy.py --config=path\to\my\config```

The default config file is provided to show you the default values but does not need to be present to run TabPy.

## Configuring HTTP vs HTTPS

By default, TabPy serves only HTTP requests. TabPy can be configured to serve only HTTPS requests by setting the following parameter in the config file:

```sh
TABPY_TRANSFER_PROTOCOL = https
```

If HTTPS is selected, the absolute paths to the cert and key file need to be specified in your config file using the following parameters:

```sh
TABPY_CERTIFICATE_FILE = C:/path/to/cert/file.crt
TABPY_KEY_FILE = C:/path/to/key/file.key
```

Note that only PEM-encoded x509 certificates are supported for the secure connection scenario.

