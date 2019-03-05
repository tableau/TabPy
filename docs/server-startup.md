# Starting TabPy Server

These instructions explain how to start up TabPy Server.

<!-- markdownlint-disable MD004 -->
<!-- toc -->

- [Prerequisites](#prerequisites)
- [Windows](#windows)
  * [Command Line Arguments](#command-line-arguments)
- [Mac](#mac)
  * [Command Line Arguments](#command-line-arguments-1)
- [Linux](#linux)
  * [Command Line Arguments](#command-line-arguments-2)

<!-- tocstop -->
<!-- markdownlint-enable MD004 -->

## Prerequisites

To start up TabPy Server from an environment the following prerequisites are required:

- Python 3.6.5
- setuptools (Python module, can be installed from PyPi)

First, select a TabPy version and download its source code from the
[releases page](https://github.com/tableau/TabPy/releases). To start up
a TabPy server instance, follow the instructions for your OS (found below).

Instructions on how to configure your TabPy server instance can be found in the
[TabPy Server Configuration Instructions](server-config.md)

It is highly recommended to use Python virtual enviroment for running TabPy.
Check the [Running TabPy in Python Virtual Environment](tabpy-virtualenv.md) page
for more details.
If you are installing a newer version of TabPy in the same environment as a
previous install, delete the previous TabPy version folder in your Python directory.

## Windows

1. Open a command prompt.
2. Navigate to the folder in which you downloaded your source code.
    - This folder should contain the file: ```startup.cmd```
3. Run the following command from the command prompt:

    ```batch
    startup.cmd
    ```

### Command Line Arguments for Windows

To specify the *config file* with which to configure your server instance, pass
it in as a command line argument as follows:

```batch
startup.cmd myconfig.conf
```

Replace `myconfig.conf` with the path to your config file relative to
`%TABPY_ROOT%\tabpy-server\tabpy_server\`.

For example, in this case your config file would be located at
`%TABPY_ROOT%\tabpy-server\tabpy_server\myconfig.conf`.

## Mac

1. Open a terminal.
2. Navigate to the folder in which you downloaded your source code.
    - This folder should contain the file: ```startup.sh```
3. Run the following command from the terminal:

    ```bash
    ./startup.sh
    ```

### Command Line Arguments for Mac

- To specify the *port* on which your server instance listens, set the `-p`
  command line argument as follows:

    ```bash
    ./startup.sh -p 1234
    ```

    Replace `1234` with the port of your choice.

- To specify the *config file* with which to configure your server instance,
  set the `-c` command line argument as follows:

    ```bash
    ./startup.sh -c myconfig.conf
    ```

    Replace `myconfig.conf` with the path to your config file relative to
   `$TABPY_ROOT/tabpy-server/tabpy_server/`.

    For example, in this case your config file would be located at
    `$TABPY_ROOT/tabpy-server/tabpy_server/myconfig.conf`.

The following is an example of how you might set both the port and the config:

```bash
./startup.sh -p 1234 -c myconfig.conf
```

## Linux

1. Open a terminal.
2. Navigate to the folder in which you downloaded your source code.
    - This folder should contain the file: ```startup.sh```
3. Run the following command from the terminal:

    ```bash
    sudo ./startup.sh
    ```

### Command Line Arguments for Linux

- To specify the *port* on which your server instance listens, set the `-p`
  command line argument as follows:

    ```bash
    sudo ./startup.sh -p 1234

    ```

    Replace `1234` with the port of your choice.

- To specify the *config file* with which to configure your server instance,
  set the `-c` command line argument as follows:

    ```bash
    sudo ./startup.sh -c myconfig.conf
    ```

    Replace `myconfig.conf` with the path to your config file relative to
    `$TABPY_ROOT/tabpy-server/tabpy_server/`.

    For example, in this case your config file would be located at
    `$TABPY_ROOT/tabpy-server/tabpy_server/myconfig.conf`.

The following is an example of how you might set both the port and the config:

```bash
sudo ./startup.sh -p 1234 -c myconfig.conf
```
