# Starting TabPy Server

These instructions explain how to start up TabPy Server.

<!-- toc -->

- [Prerequisites](#prerequisites)
- [Windows](#windows)
  * [Command Line Arguments](#command-line-arguments)
- [Mac](#mac)
  * [Command Line Arguments](#command-line-arguments-1)
- [Linux](#linux)
  * [CentOS Specific Steps](#centos-specific-steps)
  * [Command Line Arguments](#command-line-arguments-2)

<!-- tocstop -->

## Prerequisites

To start up TabPy Server from an environment the following prerequisites are required:

- Python 3.6.5
- setuptools (Python module, can be installed from PyPi)

First, select a TabPy version and download its source code from the [releases page](https://github.com/tableau/TabPy/releases). To start up a TabPy server instance, follow the instructions for your OS (found below).

Instructions on how to configure your TabPy server instance can be found in the [TabPy Server Configuration Instructions](server-config.md)

Check [TabPy Known Issue](known-issues.md) page in case of any issues to check if there is a solution for it.

## Windows

1. Open a command prompt.
2. Navigate to the folder in which you downloaded your source code.
    - This folder should contain the file: ```startup.cmd```
3. Run the following command from the command prompt:

    ```batch
    startup.cmd
    ```

### Command Line Arguments

To specify the *config file* with which to configure your server instance, pass it in as a command line argument as follows:

```batch
startup.cmd myconfig.conf
```
Replace ```myconfig.conf``` with the path to your config file relative to ```%TABPY_ROOT%\tabpy-server\tabpy_server\```.

For example, in this case your config file would be located at ```%TABPY_ROOT%\tabpy-server\tabpy_server\myconfig.conf```

## Mac

1. Open a terminal.
2. Navigate to the folder in which you downloaded your source code.
    - This folder should contain the file: ```startup.sh```
3. Run the following command from the terminal:

    ```bash
    ./startup.sh
    ```

### Command Line Arguments

- To specify the *port* on which your server instance listens, set the ```-p``` command line argument as follows:

    ```bash
    ./startup.sh -p 1234
    ```

    Replace ```1234``` with the port of your choice.

- To specify the *config file* with which to configure your server instance, set the ```-c``` command line argument as follows:

    ```bash
    ./startup.sh -c myconfig.conf
    ```
    Replace ```myconfig.conf``` with the path to your config file relative to ```$TABPY_ROOT/tabpy-server/tabpy_server/```.

    For example, in this case your config file would be located at ```$TABPY_ROOT/tabpy-server/tabpy_server/myconfig.conf```.

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

### CentOS Specific Steps

For Python on CentOS you may need to rebuild it with enabling all the features.
Also you'll need `pip` and `setuptools` for TabPy startup script to work.
To install and enable all the required prerequisites follow the steps:

```sh
sudo yum update
sudo yum groupinstall -y "Development tools"
sudo yum install -y zlib-devel bzip2-devel openssl-devel ncurses-devel sqlite-devel readline-devel tk-devel gdbm-devel db4-devel libpcap-devel xz-devel expat-devel
sudo yum install -y wget
wget http://python.org/ftp/python/3.6.5/Python-3.6.5.tar.xz
tar xf Python-3.6.5.tar.xz
cd Python-3.6.5
./configure --prefix=/usr/local --enable-shared LDFLAGS="-Wl,-rpath /usr/local/lib"
```

Edit `./Module/Setup` file uncommenting line 
`#zlib zlibmodule.c -I$(prefix)/include -L$(exec_prefix)/lib -lz` 
(remove pound sign).

Continue the steps:

```sh
make
sudo make altinstall
```

It is highly recommended to use Python virtual enviroment for running TabPy,
check [Running TabPy in Python Virtual Environment](tabpy-virtualenv.md) page
for more details.
    
### Command Line Arguments

- To specify the *port* on which your server instance listens, set the ```-p``` command line argument as follows:

    ```bash
    sudo ./startup.sh -p 1234

    ```

    Replace ```1234``` with the port of your choice.
- To specify the *config file* with which to configure your server instance, set the ```-c``` command line argument as follows:

    ```bash
    sudo ./startup.sh -c myconfig.conf
    ```
    
    Replace ```myconfig.conf``` with the path to your config file relative to ```$TABPY_ROOT/tabpy-server/tabpy_server/```.

    For example, in this case your config file would be located at ```$TABPY_ROOT/tabpy-server/tabpy_server/myconfig.conf```.

The following is an example of how you might set both the port and the config:

```bash
sudo ./startup.sh -p 1234 -c myconfig.conf
```