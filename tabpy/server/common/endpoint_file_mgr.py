"""
This module provides functionality required for managing endpoint objects in
TabPy. It provides a way to download endpoint files from remote
and then properly cleanup local the endpoint files on update/remove of endpoint
objects.

The local temporary files for TabPy will by default located at
    /tmp/query_objects

"""
import logging
import os
import shutil
from re import compile as _compile


_name_checker = _compile(r"^[a-zA-Z0-9-_\s]+$")


def _check_endpoint_name(name, logger=logging.getLogger(__name__)):
    """Checks that the endpoint name is valid by comparing it with an RE and
    checking that it is not reserved."""
    if not isinstance(name, str):
        msg = "Endpoint name must be a string"
        logger.log(logging.CRITICAL, msg)
        raise TypeError(msg)

    if name == "":
        msg = "Endpoint name cannot be empty"
        logger.log(logging.CRITICAL, msg)
        raise ValueError(msg)

    if not _name_checker.match(name):
        msg = (
            "Endpoint name can only contain: a-z, A-Z, 0-9,"
            " underscore, hyphens and spaces."
        )
        logger.log(logging.CRITICAL, msg)
        raise ValueError(msg)


def grab_files(directory):
    """
    Generator that returns all files in a directory.
    """
    if not os.path.isdir(directory):
        return
    else:
        for name in os.listdir(directory):
            full_path = os.path.join(directory, name)
            if os.path.isdir(full_path):
                for entry in grab_files(full_path):
                    yield entry
            elif os.path.isfile(full_path):
                yield full_path


def cleanup_endpoint_files(
    name, query_path, logger=logging.getLogger(__name__), retain_versions=None
):
    """
    Cleanup the disk space a certain endpiont uses.

    Parameters
    ----------
    name : str
        The endpoint name

    retain_version : int, optional
        If given, then all files for this endpoint are removed except the
        folder for the given version, otherwise, all files for that endpoint
        are removed.
    """
    _check_endpoint_name(name, logger=logger)
    local_dir = os.path.join(query_path, name)

    # nothing to clean, this is true for state file path where we load
    # Query Object directly from the state path instead of downloading
    # to temporary location
    if not os.path.exists(local_dir):
        return

    if not retain_versions:
        shutil.rmtree(local_dir)
    else:
        retain_folders = [
            os.path.join(local_dir, str(version)) for version in retain_versions
        ]
        logger.log(logging.INFO, f"Retain folders: {retain_folders}")

        for file_or_dir in os.listdir(local_dir):
            candidate_dir = os.path.join(local_dir, file_or_dir)
            if os.path.isdir(candidate_dir) and (candidate_dir not in retain_folders):
                shutil.rmtree(candidate_dir)
