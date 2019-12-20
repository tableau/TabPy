import logging
from tabpy.tabpy_server.app.SettingsParameters import SettingsParameters
from tabpy.tabpy_server.common.messages import (
    LoadObject,
    DeleteObjects,
    ListObjects,
    ObjectList,
)
from tabpy.tabpy_server.common.endpoint_file_mgr import cleanup_endpoint_files
from tabpy.tabpy_server.common.util import format_exception
from tabpy.tabpy_server.management.state import TabPyState, get_query_object_path
from tabpy.tabpy_server.management import util
from time import sleep
from tornado import gen


logger = logging.getLogger(__name__)


def wait_for_endpoint_loaded(python_service, object_uri):
    """
    This method waits for the object to be loaded.
    """
    logger.info("Waiting for object to be loaded...")
    while True:
        msg = ListObjects()
        list_object_msg = python_service.manage_request(msg)
        if not isinstance(list_object_msg, ObjectList):
            logger.error(f"Error loading endpoint {object_uri}: {list_object_msg}")
            return

        for (uri, info) in list_object_msg.objects.items():
            if uri == object_uri:
                if info["status"] != "LoadInProgress":
                    logger.info(f'Object load status: {info["status"]}')
                    return

        sleep(0.1)


@gen.coroutine
def init_ps_server(settings, tabpy_state):
    logger.info("Initializing TabPy Server...")
    existing_pos = tabpy_state.get_endpoints()
    for (object_name, obj_info) in existing_pos.items():
        try:
            object_version = obj_info["version"]
            get_query_object_path(
                settings[SettingsParameters.StateFilePath], object_name, object_version
            )
        except Exception as e:
            logger.error(
                f"Exception encounted when downloading object: {object_name}"
                f", error: {e}"
            )


@gen.coroutine
def init_model_evaluator(settings, tabpy_state, python_service):
    """
    This will go through all models that the service currently have and
    initialize them.
    """
    logger.info("Initializing models...")

    existing_pos = tabpy_state.get_endpoints()

    for (object_name, obj_info) in existing_pos.items():
        object_version = obj_info["version"]
        object_type = obj_info["type"]
        object_path = get_query_object_path(
            settings[SettingsParameters.StateFilePath], object_name, object_version
        )

        logger.info(
            f"Load endpoint: {object_name}, "
            f"version: {object_version}, "
            f"type: {object_type}"
        )
        if object_type == "alias":
            msg = LoadObject(
                object_name, obj_info["target"], object_version, False, "alias"
            )
        else:
            local_path = object_path
            msg = LoadObject(
                object_name, local_path, object_version, False, object_type
            )
        python_service.manage_request(msg)


def _get_latest_service_state(settings, tabpy_state, new_ps_state, python_service):
    """
    Update the endpoints from the latest remote state file.

    Returns
    --------
    (has_changes, endpoint_diff):
        has_changes: True or False
        endpoint_diff: Summary of what has changed, one entry for each changes
    """
    # Shortcut when nothing is changed
    changes = {"endpoints": {}}

    # update endpoints
    new_endpoints = new_ps_state.get_endpoints()
    diff = {}
    current_endpoints = python_service.ps.query_objects
    for (endpoint_name, endpoint_info) in new_endpoints.items():
        existing_endpoint = current_endpoints.get(endpoint_name)
        if (existing_endpoint is None) or endpoint_info["version"] != existing_endpoint[
            "version"
        ]:
            # Either a new endpoint or new endpoint version
            path_to_new_version = get_query_object_path(
                settings[SettingsParameters.StateFilePath],
                endpoint_name,
                endpoint_info["version"],
            )
            endpoint_type = endpoint_info.get("type", "model")
            diff[endpoint_name] = (
                endpoint_type,
                endpoint_info["version"],
                path_to_new_version,
            )

    # add removed models too
    for (endpoint_name, endpoint_info) in current_endpoints.items():
        if endpoint_name not in new_endpoints.keys():
            endpoint_type = current_endpoints[endpoint_name].get("type", "model")
            diff[endpoint_name] = (endpoint_type, None, None)

    if diff:
        changes["endpoints"] = diff

    return (True, changes)


@gen.coroutine
def on_state_change(
    settings, tabpy_state, python_service, logger=logging.getLogger(__name__)
):
    try:
        logger.log(logging.INFO, "Loading state from state file")
        config = util._get_state_from_file(
            settings[SettingsParameters.StateFilePath], logger=logger
        )
        new_ps_state = TabPyState(config=config, settings=settings)

        (has_changes, changes) = _get_latest_service_state(
            settings, tabpy_state, new_ps_state, python_service
        )
        if not has_changes:
            logger.info("Nothing changed, return.")
            return

        new_endpoints = new_ps_state.get_endpoints()
        for object_name in changes["endpoints"]:
            (object_type, object_version, object_path) = changes["endpoints"][
                object_name
            ]

            if not object_path and not object_version:  # removal
                logger.info(f"Removing object: URI={object_name}")

                python_service.manage_request(DeleteObjects([object_name]))

                cleanup_endpoint_files(
                    object_name, settings[SettingsParameters.UploadDir], logger=logger
                )

            else:
                endpoint_info = new_endpoints[object_name]
                is_update = object_version > 1
                if object_type == "alias":
                    msg = LoadObject(
                        object_name,
                        endpoint_info["target"],
                        object_version,
                        is_update,
                        "alias",
                    )
                else:
                    local_path = object_path
                    msg = LoadObject(
                        object_name, local_path, object_version, is_update, object_type
                    )

                python_service.manage_request(msg)
                wait_for_endpoint_loaded(python_service, object_name)

                # cleanup old version of endpoint files
                if object_version > 2:
                    cleanup_endpoint_files(
                        object_name,
                        settings[SettingsParameters.UploadDir],
                        logger=logger,
                        retain_versions=[object_version, object_version - 1],
                    )

    except Exception as e:
        err_msg = format_exception(e, "on_state_change")
        logger.log(
            logging.ERROR, f"Error submitting update model request: error={err_msg}"
        )
