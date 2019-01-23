# TabPy Contributing Guide

<!-- toc -->

- [Environment Setup](#environment-setup)
- [Prerequisites](#prerequisites)
- [Windows Specific Steps](#windows-specific-steps)
- [Mac Specific Steps](#mac-specific-steps)
- [Documentation Updates](#documentation-updates)
- [Versioning](#versioning)
- [TabPy with Swagger](#tabpy-with-swagger)

<!-- tocstop -->

## Environment Setup

The purpose of this guide is to enable developers of Tabpy to install the project
and run it locally.

## Prerequisites

These are prerequisites for an environment required for a contributor to
be able to work on TabPy changes:

- Python 3.x
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

## Linux and Mac Specific Steps

If you have downloaded Tabpy and would like to manually install Tabpy Server
not using pip then follow the steps below [to run TabPy in Python virtual environment](docs/tabpy-virtualenv.md).


## Documentation Updates

For any process, scripts or API changes documentation needs to be updated accordingly.
Please use markdown validation tools like web-based[markdownlint](https://dlaa.me/markdownlint/)
or npm [markdownlint-cli](https://github.com/igorshubovych/markdownlint-cli).

TOC for markdown file is built with [markdonw-toc](https://www.npmjs.com/package/markdown-toc).

## Versioning

TabPy is versioned with [Versioneer tool](https://github.com/warner/python-versioneer) and uses the github release
tag as a version. In case you need to update version for TabPy use `git tag` command. Example below
shows how to update TabPy version to `v3.14-gamma`:

```sh
git tag v3.14-gamma
git push
git push --tag
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
