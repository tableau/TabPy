# TabPy Installation Instructions

These instructions explain how to install and start up TabPy Server.

<!-- markdownlint-disable MD004 -->

<!-- toc -->

- [TabPy Installation](#tabpy-installation)
- [Starting TabPy](#starting-tabpy)

<!-- tocstop -->

<!-- markdownlint-enable MD004 -->

## TabPy Installation

To install TabPy on to an environment `pip` needs to be installed and
updated first:

```sh
python -m pip install --upgrade pip
```

Now TabPy can be install as a package:

```sh
pip install tabpy
```

## Starting TabPy

To start TabPy with default setting run the following command:

```sh
tabpy
```

To run TabPy with custom settings create config file with parameters
explained in [TabPy Server Configuration Instructions](server-config.md)
and specify it in command line:

```sh
tabpy --config=path/to/my/config/file.conf
```

It is highly recommended to use Python virtual environment for running TabPy.
Check the [Running TabPy in Python Virtual Environment](tabpy-virtualenv.md) page
for more details.

## Starting a Local TabPy Project

To create a version of TabPy that incorporates locally-made changes,
use pip to create a package from your local TabPy project
and install it within that directory (preferably a virtual environment):

```sh
pip install -e .
```

Then start TabPy just like it was mentioned earlier

```sh
tabpy
```
