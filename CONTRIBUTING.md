# TabPy Contributing Guide

<!-- markdownlint-disable MD004 -->

<!-- toc -->

- [Environment Setup](#environment-setup)
- [Prerequisites](#prerequisites)
- [Cloning TabPy Repository](#cloning-tabpy-repository)
- [Tests](#tests)
  * [Unit Tests](#unit-tests)
  * [Integration Tests](#integration-tests)
- [Code Coverage](#code-coverage)
- [TabPy in Python Virtual Environment](#tabpy-in-python-virtual-environment)
- [Documentation Updates](#documentation-updates)
- [TabPy with Swagger](#tabpy-with-swagger)
- [Code styling](#code-styling)
- [Publishing TabPy Package](#publishing-tabpy-package)

<!-- tocstop -->

<!-- markdownlint-enable MD004 -->

## Environment Setup

The purpose of this guide is to enable developers of Tabpy to install the project
and run it locally.

## Prerequisites

These are prerequisites for an environment required for a contributor to
be able to work on TabPy changes:

- Python 3.6.5:
  - To see which version of Python you have installed, run `python --version`.
- git
- TabPy repo:
  - Get the latest TabPy repository with
    `git clone https://github.com/tableau/TabPy.git`.
  - Create a new branch for your changes.
  - When changes are ready push them on github and create merge request.
- PIP packages - install all with
  `pip install pytest pycodestyle autopep8 twine coverage --upgrade` command
- Node.js for npm packages - install from <https://nodejs.org>.
- NPM packages - install all with
  `npm install markdown-toc markdownlint` command.

## Cloning TabPy Repository

1. Open your OS shell.
2. Navigate to the folder in which you would like to save
   your local TabPy repository.
3. In the command prompt, enter the following commands:

    ```sh
    git clone https://github.com/tableau/TabPy.git
    cd TabPy
    ```

4. Register TabPy repo as a pip package:

    ```sh
    pip install -e .
    ```

5. Install all dependencies:

   ```sh
   python setup.py install
   ```

## Tests

To run the whole test suite execute the following command:

```sh
pytest
```

### Unit Tests

Unit tests suite can be executed with the following command:

```sh
pytest tests/unit
```

### Integration Tests

Integration tests can be executed with the next command:

```sh
pytest tests/integration
```

## Code Coverage

You can run unit tests to collect code coverage data. To do so run `pytest`
either for server or tools test, or even combined:

```sh
pytest tests --cov=tabpy-server/tabpy_server --cov=tabpy-tools/tabpy_tools --cov-append
```

## TabPy in Python Virtual Environment

It is possible (and recommended) to run TabPy in a virtual environment. More
details are on
[TabPy in Python virtual environment](docs/tabpy-virtualenv.md) page.

## Documentation Updates

For any process, scripts or API changes documentation needs to be updated accordingly.
Please use markdown validation tools like web-based [markdownlint](https://dlaa.me/markdownlint/)
or npm [markdownlint-cli](https://github.com/igorshubovych/markdownlint-cli).

TOC for markdown file is built with [markdown-toc](https://www.npmjs.com/package/markdown-toc):

```sh
markdown-toc -i docs/server-startup.md
```

To check markdown style for all the documentation use `markdownlint`:

```sh
markdownlint .
```

These checks will run as part of the build if you submit a pull request.

## TabPy with Swagger

You can invoke the TabPy Server API against a running TabPy instance with Swagger.

- Make CORS related changes in TabPy configuration file: update `tabpy/tabpy-server/state.ini`
  file in your local repository to have the next settings:

```config
[Service Info]
Access-Control-Allow-Origin = *
Access-Control-Allow-Headers = Origin, X-Requested-with, Content-Type
Access-Control-Allow-Methods = GET, OPTIONS, POST
```

- Start a local instance of TabPy server following [TabPy Server Startup Guide](docs/server-startup.md).
- Run a local copy of Swagger editor with steps provided at
  [https://github.com/swagger-api/swagger-editor](https://github.com/swagger-api/swagger-editor).
- Open `misc/TabPy.yml` in Swagger editor.
- In case your TabPy server does not run on `localhost:9004` update
  `host` value in `TabPy.yml` accordingly.

## Code styling

`pycodestyle` is used to check Python code against our style conventions:

```sh
pycodestyle .
```

For reported errors and warnings either fix them manually or auto-format files with
`autopep8`.

Run the tool for a file. In the example below `-i`
option tells `autopep8` to update the file. Without the option it
outputs formatted code to the console.

```sh
autopep8 -i tabpy-server/server_tests/test_pwd_file.py
```

## Publishing TabPy Package

Execute the following commands to build and publish a new version of
TabPy package:

```sh
python setup.py sdist bdist_wheel
python -m twine upload dist/*
```

To publish test version of the package use the following command:

```sh
python -m twine upload --repository-url https://test.pypi.org/legacy/ dist/*
```

To install package from TestPyPi use the command:

```sh
pip install -i https://test.pypi.org/simple/ tabpy
```
