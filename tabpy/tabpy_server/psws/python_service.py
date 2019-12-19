import concurrent.futures
import logging
from tabpy.tabpy_tools.query_object import QueryObject
from tabpy.tabpy_server.common.util import format_exception
from tabpy.tabpy_server.common.messages import (
    LoadObject,
    DeleteObjects,
    FlushObjects,
    CountObjects,
    ListObjects,
    UnknownMessage,
    LoadFailed,
    ObjectsDeleted,
    ObjectsFlushed,
    QueryFailed,
    QuerySuccessful,
    UnknownURI,
    DownloadSkipped,
    LoadInProgress,
    ObjectCount,
    ObjectList,
)


logger = logging.getLogger(__name__)


class PythonServiceHandler:
    """
    A wrapper around PythonService object that receives requests and calls the
    corresponding methods.
    """

    def __init__(self, ps):
        self.ps = ps

    def manage_request(self, msg):
        try:
            logger.debug(f"Received request {type(msg).__name__}")
            if isinstance(msg, LoadObject):
                response = self.ps.load_object(*msg)
            elif isinstance(msg, DeleteObjects):
                response = self.ps.delete_objects(msg.uris)
            elif isinstance(msg, FlushObjects):
                response = self.ps.flush_objects()
            elif isinstance(msg, CountObjects):
                response = self.ps.count_objects()
            elif isinstance(msg, ListObjects):
                response = self.ps.list_objects()
            else:
                response = UnknownMessage(msg)

            logger.debug(f"Returning response {response}")
            return response
        except Exception as e:
            logger.exception(e)
            msg = e
            if hasattr(e, "message"):
                msg = e.message
            logger.error(f"Error processing request: {msg}")
            return UnknownMessage(msg)


class PythonService:
    """
    This class is a simple wrapper maintaining loaded query objects from
    the current TabPy instance. `query_objects` is a dictionary that
    maps query object URI to query objects

    The query_objects schema is as follow:

    {'version': <current-successfuly-loaded-version>,
     'last_error':<your-recent-error-to-load-model>,
     'endpoint_obj':<loaded_query_objects>,
     'type':<object-type>,
     'status':<LoadSuccessful-or-LoadFailed-or-LoadInProgress>}

    """

    def __init__(self, query_objects=None):

        self.EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.query_objects = query_objects or {}

    def _load_object(
        self, object_uri, object_url, object_version, is_update, object_type
    ):
        try:
            logger.info(
                f"Loading object:, URI={object_uri}, "
                f"URL={object_url}, version={object_version}, "
                f"is_updated={is_update}"
            )
            if object_type == "model":
                po = QueryObject.load(object_url)
            elif object_type == "alias":
                po = object_url
            else:
                raise RuntimeError(f"Unknown object type: {object_type}")

            self.query_objects[object_uri] = {
                "version": object_version,
                "type": object_type,
                "endpoint_obj": po,
                "status": "LoadSuccessful",
                "last_error": None,
            }
        except Exception as e:
            logger.exception(e)
            logger.error(
                f"Unable to load QueryObject: path={object_url}, " f"error={str(e)}"
            )

            self.query_objects[object_uri] = {
                "version": object_version,
                "type": object_type,
                "endpoint_obj": None,
                "status": "LoadFailed",
                "last_error": f"Load failed: {str(e)}",
            }

    def load_object(
        self, object_uri, object_url, object_version, is_update, object_type
    ):
        try:
            obj_info = self.query_objects.get(object_uri)
            if (
                obj_info
                and obj_info["endpoint_obj"]
                and (obj_info["version"] >= object_version)
            ):
                logger.info("Received load message for object already loaded")

                return DownloadSkipped(
                    object_uri,
                    obj_info["version"],
                    "Object with greater " "or equal version already loaded",
                )
            else:
                if object_uri not in self.query_objects:
                    self.query_objects[object_uri] = {
                        "version": object_version,
                        "type": object_type,
                        "endpoint_obj": None,
                        "status": "LoadInProgress",
                        "last_error": None,
                    }
                else:
                    self.query_objects[object_uri]["status"] = "LoadInProgress"

                self.EXECUTOR.submit(
                    self._load_object,
                    object_uri,
                    object_url,
                    object_version,
                    is_update,
                    object_type,
                )

                return LoadInProgress(
                    object_uri, object_url, object_version, is_update, object_type
                )
        except Exception as e:
            logger.exception(e)
            logger.error(
                f"Unable to load QueryObject: path={object_url}, " f"error={str(e)}"
            )

            self.query_objects[object_uri] = {
                "version": object_version,
                "type": object_type,
                "endpoint_obj": None,
                "status": "LoadFailed",
                "last_error": str(e),
            }

            return LoadFailed(object_uri, object_version, str(e))

    def delete_objects(self, object_uris):
        """Delete one or more objects from the query_objects map"""
        if isinstance(object_uris, list):
            deleted = []
            for uri in object_uris:
                deleted.extend(self.delete_objects(uri).uris)
            return ObjectsDeleted(deleted)
        elif isinstance(object_uris, str):
            deleted_obj = self.query_objects.pop(object_uris, None)
            if deleted_obj:
                return ObjectsDeleted([object_uris])
            else:
                logger.warning(
                    f"Received message to delete query object "
                    f"that doesn't exist: "
                    f"object_uris={object_uris}"
                )
                return ObjectsDeleted([])
        else:
            logger.error(
                f"Unexpected input to delete objects: input={object_uris}, "
                f'info="Input should be list or str. '
                f'Type: {type(object_uris)}"'
            )
            return ObjectsDeleted([])

    def flush_objects(self):
        """Flush objects from the query_objects map"""
        logger.debug("Flushing query objects")
        n = len(self.query_objects)
        self.query_objects.clear()
        return ObjectsFlushed(n, 0)

    def count_objects(self):
        """Count the number of Loaded QueryObjects stored in memory"""
        count = 0
        for uri, po in self.query_objects.items():
            if po["endpoint_obj"] is not None:
                count += 1
        return ObjectCount(count)

    def list_objects(self):
        """List the objects as (URI, version) pairs"""

        objects = {}
        for (uri, obj_info) in self.query_objects.items():
            objects[uri] = {
                "version": obj_info["version"],
                "type": obj_info["type"],
                "status": obj_info["status"],
                "reason": obj_info["last_error"],
            }

        return ObjectList(objects)

    def query(self, object_uri, params, uid):
        """Execute a QueryObject query"""
        logger.debug(f"Querying Python service {object_uri}...")
        try:
            if not isinstance(params, dict) and not isinstance(params, list):
                return QueryFailed(
                    uri=object_uri,
                    error=(
                        "Query parameter needs to be a dictionary or a list"
                        f". Given value is of type {type(params)}"
                    ),
                )

            obj_info = self.query_objects.get(object_uri)
            logger.debug(f"Found object {obj_info}")
            if obj_info:
                pred_obj = obj_info["endpoint_obj"]
                version = obj_info["version"]

                if not pred_obj:
                    return QueryFailed(
                        uri=object_uri,
                        error=(
                            "There is no query object associated to the "
                            f"endpoint: {object_uri}"
                        ),
                    )

                logger.debug(f"Querying endpoint with params ({params})...")
                if isinstance(params, dict):
                    result = pred_obj.query(**params)
                else:
                    result = pred_obj.query(*params)

                return QuerySuccessful(object_uri, version, result)
            else:
                return UnknownURI(object_uri)
        except Exception as e:
            logger.exception(e)
            err_msg = format_exception(e, "/query")
            logger.error(err_msg)
            return QueryFailed(uri=object_uri, error=err_msg)
