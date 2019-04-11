# TabPy Contributing Guide

<!-- toc -->

- [Environment Setup](#environment-setup)
- [Prerequisites](#prerequisites)
- [Windows Specific Steps](#windows-specific-steps)
- [Linux and Mac Specific Steps](#linux-and-mac-specific-steps)
- [Documentation Updates](#documentation-updates)
- [TabPy with Swagger](#tabpy-with-swagger)
- [Code styling](#code-styling)

<!-- tocstop -->

## Environment Setup

The purpose of this guide is to enable developers of Tabpy to install the project
and run it locally.

## Prerequisites

These are prerequisites for an environment required for a contributor to
be able to work on TabPy changes:

- Python 3.6.5:
  - To see which version of Python you have installed, run ```python --version```.
- git
- TabPy repo:
  - Get the latest TabPy repository with `git clone https://github.com/tableau/TabPy.git`
  - Create a new branch for your changes.
  - When changes are ready push them on github and create merge request.

## Windows Specific Steps

1. Open a windows command prompt.
2. In the command prompt, navigate to the folder in which you would like to save
   your local TabPy repository.
3. In the command prompt, enter the following commands:

    ```sh
    git clone https://github.com/tableau/TabPy.git
    cd TabPy
    ```

To start a local TabPy instance:

```sh
startup.cmd
```

To run the unit test suite:

```sh
python tests\runtests.py
```

Alternatively you can run unit tests to collect code coverage data. First
install `pytest`:

```sh
pip install pytest
```

And then run `pytest` either for server, tools, or integrations tests, or even combined:

```sh
pytest tabpy-server/server_tests/ --cov=tabpy-server/tabpy_server
pytest tabpy-tools/tools_tests/ --cov=tabpy-tools/tabpy_tools --cov-append
pytest tabpy-tools/tests/integration_tests/ --cov=models --cov-append
```

It should be noted that running the integration tests will install the following
packages on to the machine if it does not already have them: `sklearn, nltk,
textblob, pandas, & numpy`

## Linux and Mac Specific Steps

If you have downloaded Tabpy and would like to manually install Tabpy Server
not using pip then follow the steps below [to run TabPy in Python virtual environment](docs/tabpy-virtualenv.md).

## Documentation Updates

For any process, scripts or API changes documentation needs to be updated accordingly.
Please use markdown validation tools like web-based[markdownlint](https://dlaa.me/markdownlint/)
or npm [markdownlint-cli](https://github.com/igorshubovych/markdownlint-cli).

TOC for markdown file is built with [markdown-toc](https://www.npmjs.com/package/markdown-toc):

```sh
markdown-toc -i docs/server-startup.md
```

## TabPy with Swagger

You can invoke TabPy Server API against running TabPy instance with Swagger:

- Make CORS related changes in TabPy configuration file: update `tabpy-server\state.ini`
  file in your local repository to have the next settings:

```config
[Service Info]
Access-Control-Allow-Origin = *
Access-Control-Allow-Headers = Origin, X-Requested-with, Content-Type
Access-Control-Allow-Methods = GET, OPTIONS, POST
```

- Start local instance of TabPy server following [TabPy Server Startup Guide](docs/server-startup.md).
- Run local copy of Swagger editor with steps provided at
  [https://github.com/swagger-api/swagger-editor](https://github.com/swagger-api/swagger-editor).
- Open `misc/TabPy.yml` in Swagger editor.
- In case your TabPy server runs not on `localhost:9004` update
  `host` value in `TabPy.yml` accordingly.

## Code styling

On github repo for merge request `pycodestyle` is used to check Python code
against our style conventions. You can run install it and run locally for
file where modifications were made:

```sh
pip install pycodestyle
```

And then run it for file where modifications were made, e.g.:

```sh
pycodestyle tabpy-server/server_tests/test_pwd_file.py
```

For reported errors and warnings either fix them manually or auto-format files with
`autopep8`.

To install `autopep8` run the next command:

```sh
pip install autopep8
```

And then you can run the tool for a file. In the example below `-i`
option tells `autopep8` to update the file. Without the option it
outputs formated code to console.

```sh
autopep8 -i tabpy-server/server_tests/test_pwd_file.py
```
