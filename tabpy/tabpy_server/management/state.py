try:
    from ConfigParser import ConfigParser
except ImportError:
    from configparser import ConfigParser
import json
import logging
from tabpy.tabpy_server.management.util import write_state_config
from threading import Lock
from time import time


logger = logging.getLogger(__name__)

# State File Config Section Names
_DEPLOYMENT_SECTION_NAME = "Query Objects Service Versions"
_QUERY_OBJECT_DOCSTRING = "Query Objects Docstrings"
_SERVICE_INFO_SECTION_NAME = "Service Info"
_META_SECTION_NAME = "Meta"

# Directory Names
_QUERY_OBJECT_DIR = "query_objects"

"""
Lock to change the TabPy State.
"""
_PS_STATE_LOCK = Lock()


def state_lock(func):
    """
    Mutex for changing PS state
    """

    def wrapper(self, *args, **kwargs):
        try:
            _PS_STATE_LOCK.acquire()
            return func(self, *args, **kwargs)
        finally:
            # ALWAYS RELEASE LOCK
            _PS_STATE_LOCK.release()

    return wrapper


def _get_root_path(state_path):
    if state_path[-1] != "/":
        return state_path + "/"
    else:
        return state_path


def get_query_object_path(state_file_path, name, version):
    """
    Returns the query object path

    If the version is None, a path without the version will be returned.
    """
    root_path = _get_root_path(state_file_path)
    if version is not None:
        full_path = root_path + "/".join([_QUERY_OBJECT_DIR, name, str(version)])
    else:
        full_path = root_path + "/".join([_QUERY_OBJECT_DIR, name])
    return full_path


class TabPyState:
    """
    The TabPy state object that stores attributes
    about this TabPy and perform GET/SET on these
    attributes.

    Attributes:
        - name
        - description
        - endpoints (name, description, docstring, version, target)
        - revision number

    When the state object is initialized, the state is saved as a ConfigParser.
    There is a config to any attribute.

    """

    def __init__(self, settings, config=None):
        self.settings = settings
        self.set_config(config, _update=False)

    @state_lock
    def set_config(self, config, logger=logging.getLogger(__name__), _update=True):
        """
        Set the local ConfigParser manually.
        This new ConfigParser will be used as current state.
        """
        if not isinstance(config, ConfigParser):
            raise ValueError("Invalid config")
        self.config = config
        if _update:
            self._write_state(logger)

    def get_endpoints(self, name=None):
        """
        Return a dictionary of endpoints

        Parameters
        ----------
        name : str
            The name of the endpoint.
            If "name" is specified, only the information about that endpoint
            will be returned.

        Returns
        -------
        endpoints : dict
            The dictionary containing information about each endpoint.
            The keys are the endpoint names.
            The values for each include:
                - description
                - doc string
                - type
                - target

        """
        endpoints = {}
        try:
            endpoint_names = self._get_config_value(_DEPLOYMENT_SECTION_NAME, name)
        except Exception as e:
            logger.error(f"error in get_endpoints: {str(e)}")
            return {}

        if name:
            endpoint_info = json.loads(endpoint_names)
            docstring = self._get_config_value(_QUERY_OBJECT_DOCSTRING, name)
            endpoint_info["docstring"] = str(
                bytes(docstring, "utf-8").decode("unicode_escape")
            )
            endpoints = {name: endpoint_info}
        else:
            for endpoint_name in endpoint_names:
                endpoint_info = json.loads(
                    self._get_config_value(_DEPLOYMENT_SECTION_NAME, endpoint_name)
                )
                docstring = self._get_config_value(
                    _QUERY_OBJECT_DOCSTRING, endpoint_name, True, ""
                )
                endpoint_info["docstring"] = str(
                    bytes(docstring, "utf-8").decode("unicode_escape")
                )
                endpoints[endpoint_name] = endpoint_info
        logger.debug(f"Collected endpoints: {endpoints}")
        return endpoints

    @state_lock
    def add_endpoint(
        self,
        name,
        description=None,
        docstring=None,
        endpoint_type=None,
        methods=None,
        target=None,
        dependencies=None,
        schema=None,
    ):
        """
        Add a new endpoint to the TabPy.

        Parameters
        ----------
        name : str
            Name of the endpoint
        description : str, optional
            Description of this endpoint
        doc_string : str, optional
            The doc string for this endpoint, if needed.
        endpoint_type : str
            The endpoint type (model, alias)
        target : str, optional
            The target endpoint name for the alias to be added.

        Note:
        The version of this endpoint will be set to 1 since it is a new
        endpoint.

        """
        try:
            endpoints = self.get_endpoints()
            if name is None or not isinstance(name, str) or len(name) == 0:
                raise ValueError("name of the endpoint must be a valid string.")
            elif name in endpoints:
                raise ValueError(f"endpoint {name} already exists.")
            if description and not isinstance(description, str):
                raise ValueError("description must be a string.")
            elif not description:
                description = ""
            if docstring and not isinstance(docstring, str):
                raise ValueError("docstring must be a string.")
            elif not docstring:
                docstring = "-- no docstring found in query function --"
            if not endpoint_type or not isinstance(endpoint_type, str):
                raise ValueError("endpoint type must be a string.")
            if dependencies and not isinstance(dependencies, list):
                raise ValueError("dependencies must be a list.")
            elif not dependencies:
                dependencies = []
            if target and not isinstance(target, str):
                raise ValueError("target must be a string.")
            elif target and target not in endpoints:
                raise ValueError("target endpoint is not valid.")

            endpoint_info = {
                "description": description,
                "docstring": docstring,
                "type": endpoint_type,
                "version": 1,
                "dependencies": dependencies,
                "target": target,
                "creation_time": int(time()),
                "last_modified_time": int(time()),
                "schema": schema,
            }

            endpoints[name] = endpoint_info
            self._add_update_endpoints_config(endpoints)
        except Exception as e:
            logger.error(f"Error in add_endpoint: {e}")
            raise

    def _add_update_endpoints_config(self, endpoints):
        # save the endpoint info to config
        dstring = ""
        for endpoint_name in endpoints:
            try:
                info = endpoints[endpoint_name]
                dstring = str(
                    bytes(info["docstring"], "utf-8").decode("unicode_escape")
                )
                self._set_config_value(
                    _QUERY_OBJECT_DOCSTRING,
                    endpoint_name,
                    dstring,
                    _update_revision=False,
                )
                del info["docstring"]
                self._set_config_value(
                    _DEPLOYMENT_SECTION_NAME, endpoint_name, json.dumps(info)
                )
            except Exception as e:
                logger.error(f"Unable to write endpoints config: {e}")
                raise

    @state_lock
    def update_endpoint(
        self,
        name,
        description=None,
        docstring=None,
        endpoint_type=None,
        version=None,
        methods=None,
        target=None,
        dependencies=None,
        schema=None,
    ):
        """
        Update an existing endpoint on the TabPy.

        Parameters
        ----------
        name : str
            Name of the endpoint
        description : str, optional
            Description of this endpoint
        doc_string : str, optional
            The doc string for this endpoint, if needed.
        endpoint_type : str, optional
            The endpoint type (model, alias)
        version : str, optional
            The version of this endpoint
        dependencies=[]
            List of dependent endpoints for this existing endpoint
        target : str, optional
            The target endpoint name for the alias.

        Note:
        For those parameters that are not specified, those values will not
        get changed.

        """
        try:
            endpoints = self.get_endpoints()
            if not name or not isinstance(name, str):
                raise ValueError("name of the endpoint must be string.")
            elif name not in endpoints:
                raise ValueError(f"endpoint {name} does not exist.")

            endpoint_info = endpoints[name]

            if description and not isinstance(description, str):
                raise ValueError("description must be a string.")
            elif not description:
                description = endpoint_info["description"]
            if docstring and not isinstance(docstring, str):
                raise ValueError("docstring must be a string.")
            elif not docstring:
                docstring = endpoint_info["docstring"]
            if endpoint_type and not isinstance(endpoint_type, str):
                raise ValueError("endpoint type must be a string.")
            elif not endpoint_type:
                endpoint_type = endpoint_info["type"]
            if version and not isinstance(version, int):
                raise ValueError("version must be an int.")
            elif not version:
                version = endpoint_info["version"]
            if dependencies and not isinstance(dependencies, list):
                raise ValueError("dependencies must be a list.")
            elif not dependencies:
                if "dependencies" in endpoint_info:
                    dependencies = endpoint_info["dependencies"]
                else:
                    dependencies = []
            if target and not isinstance(target, str):
                raise ValueError("target must be a string.")
            elif target and target not in endpoints:
                raise ValueError("target endpoint is not valid.")
            elif not target:
                target = endpoint_info["target"]
            endpoint_info = {
                "description": description,
                "docstring": docstring,
                "type": endpoint_type,
                "version": version,
                "dependencies": dependencies,
                "target": target,
                "creation_time": endpoint_info["creation_time"],
                "last_modified_time": int(time()),
                "schema": schema,
            }

            endpoints[name] = endpoint_info
            self._add_update_endpoints_config(endpoints)
        except Exception as e:
            logger.error(f"Error in update_endpoint: {e}")
            raise

    @state_lock
    def delete_endpoint(self, name):
        """
        Delete an existing endpoint on the TabPy

        Parameters
        ----------
        name : str
            The name of the endpoint to be deleted.

        Returns
        -------
        deleted endpoint object

        Note:
        Cannot delete this endpoint if other endpoints are currently
        depending on this endpoint.

        """
        if not name or name == "":
            raise ValueError("Name of the endpoint must be a valid string.")
        endpoints = self.get_endpoints()
        if name not in endpoints:
            raise ValueError(f"Endpoint {name} does not exist.")

        endpoint_to_delete = endpoints[name]

        # get dependencies and target
        deps = set()
        for endpoint_name in endpoints:
            if endpoint_name != name:
                deps_list = endpoints[endpoint_name].get("dependencies", [])
                if name in deps_list:
                    deps.add(endpoint_name)

        # check if other endpoints are depending on this endpoint
        if len(deps) > 0:
            raise ValueError(
                f"Cannot remove endpoint {name}, it is currently "
                f"used by {list(deps)} endpoints."
            )

        del endpoints[name]

        # delete the endpoint from state
        try:
            self._remove_config_option(
                _QUERY_OBJECT_DOCSTRING, name, _update_revision=False
            )
            self._remove_config_option(_DEPLOYMENT_SECTION_NAME, name)

            return endpoint_to_delete
        except Exception as e:
            logger.error(f"Unable to delete endpoint {e}")
            raise ValueError(f"Unable to delete endpoint: {e}")

    @property
    def name(self):
        """
        Returns the name of the TabPy service.
        """
        name = None
        try:
            name = self._get_config_value(_SERVICE_INFO_SECTION_NAME, "Name")
        except Exception as e:
            logger.error(f"Unable to get name: {e}")
        return name

    @property
    def creation_time(self):
        """
        Returns the creation time of the TabPy service.
        """
        creation_time = 0
        try:
            creation_time = self._get_config_value(
                _SERVICE_INFO_SECTION_NAME, "Creation Time"
            )
        except Exception as e:
            logger.error(f"Unable to get name: {e}")
        return creation_time

    @state_lock
    def set_name(self, name):
        """
        Set the name of this TabPy service.

        Parameters
        ----------
        name : str
            Name of TabPy service.
        """
        if not isinstance(name, str):
            raise ValueError("name must be a string.")
        try:
            self._set_config_value(_SERVICE_INFO_SECTION_NAME, "Name", name)
        except Exception as e:
            logger.error(f"Unable to set name: {e}")

    def get_description(self):
        """
        Returns the description of the TabPy service.
        """
        description = None
        try:
            description = self._get_config_value(
                _SERVICE_INFO_SECTION_NAME, "Description"
            )
        except Exception as e:
            logger.error(f"Unable to get description: {e}")
        return description

    @state_lock
    def set_description(self, description):
        """
        Set the description of this TabPy service.

        Parameters
        ----------
        description : str
            Description of TabPy service.
        """
        if not isinstance(description, str):
            raise ValueError("Description must be a string.")
        try:
            self._set_config_value(
                _SERVICE_INFO_SECTION_NAME, "Description", description
            )
        except Exception as e:
            logger.error(f"Unable to set description: {e}")

    def get_revision_number(self):
        """
        Returns the revision number of this TabPy service.
        """
        rev = -1
        try:
            rev = int(self._get_config_value(_META_SECTION_NAME, "Revision Number"))
        except Exception as e:
            logger.error(f"Unable to get revision number: {e}")
        return rev

    def get_access_control_allow_origin(self):
        """
        Returns Access-Control-Allow-Origin of this TabPy service.
        """
        _cors_origin = ""
        try:
            logger.debug("Collecting Access-Control-Allow-Origin from state file ...")
            _cors_origin = self._get_config_value(
                "Service Info", "Access-Control-Allow-Origin"
            )
        except Exception as e:
            logger.error(e)
        return _cors_origin

    def get_access_control_allow_headers(self):
        """
        Returns Access-Control-Allow-Headers of this TabPy service.
        """
        _cors_headers = ""
        try:
            _cors_headers = self._get_config_value(
                "Service Info", "Access-Control-Allow-Headers"
            )
        except Exception:
            pass
        return _cors_headers

    def get_access_control_allow_methods(self):
        """
        Returns Access-Control-Allow-Methods of this TabPy service.
        """
        _cors_methods = ""
        try:
            _cors_methods = self._get_config_value(
                "Service Info", "Access-Control-Allow-Methods"
            )
        except Exception:
            pass
        return _cors_methods

    def _set_revision_number(self, revision_number):
        """
        Set the revision number of this TabPy service.
        """
        if not isinstance(revision_number, int):
            raise ValueError("revision number must be an int.")
        try:
            self._set_config_value(
                _META_SECTION_NAME, "Revision Number", revision_number
            )
        except Exception as e:
            logger.error(f"Unable to set revision number: {e}")

    def _remove_config_option(
        self,
        section_name,
        option_name,
        logger=logging.getLogger(__name__),
        _update_revision=True,
    ):
        if not self.config:
            raise ValueError("State configuration not yet loaded.")
        self.config.remove_option(section_name, option_name)
        # update revision number
        if _update_revision:
            self._increase_revision_number()
        self._write_state(logger=logger)

    def _has_config_value(self, section_name, option_name):
        if not self.config:
            raise ValueError("State configuration not yet loaded.")
        return self.config.has_option(section_name, option_name)

    def _increase_revision_number(self):
        if not self.config:
            raise ValueError("State configuration not yet loaded.")
        cur_rev = int(self.config.get(_META_SECTION_NAME, "Revision Number"))
        self.config.set(_META_SECTION_NAME, "Revision Number", str(cur_rev + 1))

    def _set_config_value(
        self,
        section_name,
        option_name,
        option_value,
        logger=logging.getLogger(__name__),
        _update_revision=True,
    ):
        if not self.config:
            raise ValueError("State configuration not yet loaded.")

        if not self.config.has_section(section_name):
            logger.log(logging.DEBUG, f"Adding config section {section_name}")
            self.config.add_section(section_name)

        self.config.set(section_name, option_name, option_value)
        # update revision number
        if _update_revision:
            self._increase_revision_number()
        self._write_state(logger=logger)

    def _get_config_items(self, section_name):
        if not self.config:
            raise ValueError("State configuration not yet loaded.")
        return self.config.items(section_name)

    def _get_config_value(
        self, section_name, option_name, optional=False, default_value=None
    ):
        logger.log(
            logging.DEBUG,
            f"Loading option '{option_name}' from section [{section_name}]...")

        if not self.config:
            msg = "State configuration not yet loaded."
            logging.log(msg)
            raise ValueError(msg)

        res = None
        if not option_name:
            res = self.config.options(section_name)
        elif self.config.has_option(section_name, option_name):
            res = self.config.get(section_name, option_name)
        elif optional:
            res = default_value
        else:
            raise ValueError(
                f"Cannot find option name {option_name} "
                f"under section {section_name}"
            )

        logger.log(logging.DEBUG, f"Returning value '{res}'")
        return res

    def _write_state(self, logger=logging.getLogger(__name__)):
        """
        Write state (ConfigParser) to Consul
        """
        logger.log(logging.INFO, "Writing state to config")
        write_state_config(self.config, self.settings, logger=logger)
