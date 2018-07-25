# Contributing Guide

## Environment Setup

TabPy suggests using [Pipenv](https://docs.pipenv.org) to configure and manage your development environment and provides facilities to enable this out of the box. To start, clone the source code and from the project root run:

```sh
pipenv install --dev
```

This will create a dedicated virtual environment containing all of the required packages.

## Starting the Server

From the project root, activate the virtual environment you created above via:

```sh
pipenv shell
```

Thereafter, simply navigate to tabpy-server/tabpy-server and run:

```sh
python tabpy.py
```
