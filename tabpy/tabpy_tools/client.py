import copy
import inspect
from re import compile
import time
import requests

from .rest import RequestsNetworkWrapper, ServiceClient

from .rest_client import RESTServiceClient, Endpoint

from .custom_query_object import CustomQueryObject
import os
import logging

logger = logging.getLogger(__name__)

_name_checker = compile(r"^[\w -]+$")


def _check_endpoint_type(name):
    if not isinstance(name, str):
        raise TypeError("Endpoint name must be a string")

    if name == "":
        raise ValueError("Endpoint name cannot be empty")


def _check_hostname(name):
    _check_endpoint_type(name)
    hostname_checker = compile(r"^^http(s)?://[\w.-]+(/)?(:\d+)?(/)?$")

    if not hostname_checker.match(name):
        raise ValueError(
            f"endpoint name {name} should be in http(s)://<hostname>"
            "[:<port>] and hostname may consist only of: "
            "a-z, A-Z, 0-9, underscore and hyphens."
        )


def _check_endpoint_name(name):
    """Checks that the endpoint name is valid by comparing it with an RE and
    checking that it is not reserved."""
    _check_endpoint_type(name)

    if not _name_checker.match(name):
        raise ValueError(
            f"endpoint name {name} can only contain: a-z, A-Z, 0-9,"
            " underscore, hyphens and spaces."
        )


class Client:
    def __init__(
        self, endpoint, query_timeout=1000, remote_server=False, localhost_endpoint=None
    ):
        """
        Connects to a running server.

        The class constructor takes a server address which is then used to
        connect for all subsequent member APIs.

        Parameters
        ----------
        endpoint : str, optional
            The server URL.

        query_timeout : float, optional
            The timeout for query operations.

        remote_server : bool, optional
            Whether client is a remote TabPy server.

        localhost_endpoint : str, optional
            The localhost endpoint with potentially different protocol and
            port compared to the main endpoint parameter.
        """
        _check_hostname(endpoint)

        self._endpoint = endpoint
        self._remote_server = remote_server
        self._localhost_endpoint = localhost_endpoint

        session = requests.session()
        session.verify = False
        requests.packages.urllib3.disable_warnings()

        # Setup the communications layer.
        network_wrapper = RequestsNetworkWrapper(session)
        service_client = ServiceClient(self._endpoint, network_wrapper)

        self._service = RESTServiceClient(service_client)
        if not type(query_timeout) in (int, float) or query_timeout <= 0:
            query_timeout = 0.0
        self._service.query_timeout = query_timeout

    def __repr__(self):
        return (
            "<"
            + self.__class__.__name__
            + " object at "
            + hex(id(self))
            + " connected to "
            + repr(self._endpoint)
            + ">"
        )

    def get_status(self):
        """
        Gets the status of the deployed endpoints.

        Returns
        -------
        dict
            Keys are endpoints and values are dicts describing the state of
            the endpoint.

        Examples
        --------
        .. sourcecode:: python
            {
                u'foo': {
                    u'status': u'LoadFailed',
                    u'last_error': u'error mesasge',
                    u'version': 1,
                    u'type': u'model',
                },
            }
        """
        return self._service.get_status()

    #
    # Query
    #

    @property
    def query_timeout(self):
        """The timeout for queries in milliseconds."""
        return self._service.query_timeout

    @query_timeout.setter
    def query_timeout(self, value):
        if type(value) in (int, float) and value > 0:
            self._service.query_timeout = value

    def query(self, name, *args, **kwargs):
        """Query an endpoint.

        Parameters
        ----------
        name : str
            The name of the endpoint.

        *args : list of anything
            Ordered parameters to the endpoint.

        **kwargs : dict of anything
            Named parameters to the endpoint.

        Returns
        -------
        dict
            Keys are:
                model: the name of the endpoint
                version: the version used.
                response: the response to the query.
                uuid : a unique id for the request.
        """
        return self._service.query(name, *args, **kwargs)

    #
    # Endpoints
    #

    def get_endpoints(self, type=None):
        """Returns all deployed endpoints.

        Examples
        --------
        .. sourcecode:: python
            {"clustering":
              {"description": "",
               "docstring": "-- no docstring found in query function --",
               "creation_time": 1469511182,
               "version": 1,
               "dependencies": [],
               "last_modified_time": 1469511182,
               "type": "model",
               "target": null,
               "is_public": True}
            "add": {
              "description": "",
              "docstring": "-- no docstring found in query function --",
              "creation_time": 1469505967,
              "version": 1,
              "dependencies": [],
              "last_modified_time": 1469505967,
              "type": "model",
              "target": null,
              "is_public": False}
            }
        """
        return self._service.get_endpoints(type)

    def _get_endpoint_upload_destination(self):
        """Returns the endpoint upload destination."""
        return self._service.get_endpoint_upload_destination()["path"]

    def deploy(self, name, obj, description="", schema=None, override=False, is_public=False):
        """Deploys a Python function as an endpoint in the server.

        Parameters
        ----------
        name : str
            A unique identifier for the endpoint.

        obj :  function
            Refers to a user-defined function with any signature. However both
            input and output of the function need to be JSON serializable.

        description : str, optional
            The description for the endpoint. This string will be returned by
            the ``endpoints`` API.

        schema : dict, optional
            The schema of the function, containing information about input and
            output parameters, and respective examples. Providing a schema for
            a deployed function lets other users of the service discover how to
            use it. Refer to schema.generate_schema for more information on
            how to generate the schema.

        override : bool
            Whether to override (update) an existing endpoint. If False and
            there is already an endpoint with that name, it will raise a
            RuntimeError. If True and there is already an endpoint with that
            name, it will deploy a new version on top of it.

        is_public : bool, optional
            Whether a function should be public for viewing from within tableau. If
            False, function will not appear in the custom functions explorer within
            Tableau. If True, function will be visible ta anyone on a site with this
            analytics extension configured

        See Also
        --------
        remove, get_endpoints
        """
        if self._remote_server:
            self._remote_deploy(
                name, obj,
                description=description, schema=schema, override=override, is_public=is_public
            )
            return

        endpoint = self.get_endpoints().get(name)
        version = 1
        if endpoint:
            if not override:
                raise RuntimeError(
                    f"An endpoint with that name ({name}) already"
                    ' exists. Use "override = True" to force update '
                    "an existing endpoint."
                )

            version = endpoint.version + 1

        obj = self._gen_endpoint(name, obj, description, version, schema, is_public)

        self._upload_endpoint(obj)

        if version == 1:
            self._service.add_endpoint(Endpoint(**obj))
        else:
            self._service.set_endpoint(Endpoint(**obj), should_update_version=True)

        self._wait_for_endpoint_deployment(obj["name"], obj["version"])

    def remove(self, name):
        '''Removes an endpoint dict.

        Parameters
        ----------
        name : str
            Endpoint name to remove'''
        self._service.remove_endpoint(name)

    def update_endpoint_info(self, name, description=None, schema=None, is_public=None):
        '''Updates description, schema, or is public for an existing endpoint

        Parameters
        ----------
        name : str
            Name of the endpoint that to be updated. If endpoint does not exist
            runtime error will be thrown

        description : str, optional
            The description for the endpoint. This string will be returned by
            the ``endpoints`` API.

        schema : dict, optional
            The schema of the function, containing information about input and
            output parameters, and respective examples. Providing a schema for
            a deployed function lets other users of the service discover how to
            use it. Refer to schema.generate_schema for more information on
            how to generate the schema.

        is_public : bool, optional
            Whether a function should be public for viewing from within tableau. If
            False, function will not appear in the custom functions explorer within
            Tableau. If True, function will be visible to anyone on a site with this
            analytics extension configured
        '''

        endpoint = self.get_endpoints().get(name)

        if not endpoint:
            raise RuntimeError(
                f"No endpoint with that name ({name}) exists"
                " Please select an existing endpoint to update"
            )

        if description is not None:
            if type(description) is not str:
                raise RuntimeError(
                    f"Type of description must be string"
                )
            endpoint.description = description
        if schema is not None:
            if type(schema) is not dict:
                raise RuntimeError(
                    f"Type of schema must be dictionary"
                )
            endpoint.schema = schema
        if is_public is not None:
            if type(is_public) is not bool:
                raise RuntimeError(
                    f"Type of is_public must be bool"
                )
            endpoint.is_public = is_public

        dest_path = self._get_endpoint_upload_destination()

        endpoint.src_path = os.path.join(
            dest_path, "endpoints", endpoint.name, str(endpoint.version)
        )
        self._service.set_endpoint(endpoint, should_update_version=False)

    def _gen_endpoint(self, name, obj, description, version=1, schema=None, is_public=False):
        """Generates an endpoint dict.

        Parameters
        ----------
        name : str
            Endpoint name to add or update

        obj :  func
            Object that backs the endpoint. See add() for a complete
            description.

        description : str
            Description of the endpoint

        version : int
            The version. Defaults to 1.

        is_public : bool
            True if function should be visible in the custom functions explorer
            within Tableau

        Returns
        -------
        dict
            Keys:
                name : str
                    The name provided.

                version : int
                    The version provided.

                description : str
                    The provided description.

                type : str
                    The type of the endpoint.

                endpoint_obj : object
                    The wrapper around the obj provided that can be used to
                    generate the code and dependencies for the endpoint.

        Raises
        ------
        TypeError
            When obj is not one of the expected types.
        """
        # check for invalid PO names
        _check_endpoint_name(name)

        if description is None:
            description = obj.__doc__.strip() or "" if isinstance(obj.__doc__, str) else ""

        endpoint_object = CustomQueryObject(query=obj, description=description,)
        docstring = inspect.getdoc(obj) or "-- no docstring found in query function --"

        return {
            "name": name,
            "version": version,
            "description": description,
            "type": "model",
            "endpoint_obj": endpoint_object,
            "dependencies": endpoint_object.get_dependencies(),
            "methods": endpoint_object.get_methods(),
            "required_files": [],
            "required_packages": [],
            "docstring": docstring,
            "schema": copy.copy(schema),
            "is_public": is_public,
        }

    def _upload_endpoint(self, obj):
        """Sends the endpoint across the wire."""
        endpoint_obj = obj["endpoint_obj"]

        dest_path = self._get_endpoint_upload_destination()

        # Upload the endpoint
        obj["src_path"] = os.path.join(
            dest_path, "endpoints", obj["name"], str(obj["version"])
        )

        endpoint_obj.save(obj["src_path"])

    def _wait_for_endpoint_deployment(
        self, endpoint_name, version=1, interval=1.0,
    ):
        """
        Waits for the endpoint to be deployed by calling get_status() and
        checking the versions deployed of the endpoint against the expected
        version. If all the versions are equal to or greater than the version
        expected, then it will return. Uses time.sleep().
        """
        logger.info(
            f"Waiting for endpoint {endpoint_name} to deploy to " f"version {version}"
        )
        time.sleep(interval)
        start = time.time()
        while True:
            ep_status = self.get_status()
            try:
                ep = ep_status[endpoint_name]
            except KeyError:
                logger.info(
                    f"Endpoint {endpoint_name} doesn't " "exist in endpoints yet"
                )
            else:
                logger.info(f"ep={ep}")

                if ep["status"] == "LoadFailed":
                    raise RuntimeError(f'LoadFailed: {ep["last_error"]}')

                elif ep["status"] == "LoadSuccessful":
                    if ep["version"] >= version:
                        logger.info("LoadSuccessful")
                        break
                    else:
                        logger.info("LoadSuccessful but wrong version")

            if time.time() - start > 10:
                raise RuntimeError("Waited more then 10s for deployment")

            logger.info(f"Sleeping {interval}...")
            time.sleep(interval)

    def _remote_deploy(
        self, name, obj, description="", schema=None, override=False, is_public=False
    ):
        """
        Remotely deploy a Python function using the /evaluate endpoint. Takes the same inputs
        as deploy.
        """
        remote_script = self._gen_remote_script()
        remote_script += f"{inspect.getsource(obj)}\n"

        remote_script += (
            f"client.deploy("
            f"'{name}', {obj.__name__}, '{description}', "
            f"override={override}, is_public={is_public}, schema={schema}"
            f")"
        )

        self._evaluate_remote_script(remote_script)

    def _gen_remote_script(self):
        """
        Generates a remote script for TabPy client connection with credential handling.

        Returns:
            str: A Python script to establish a TabPy client connection
        """
        remote_script = [
            "from tabpy.tabpy_tools.client import Client",
            f"client = Client('{self._localhost_endpoint or self._endpoint}')"
        ]

        remote_script.append(
            f"client.set_credentials('{auth.username}', '{auth.password}')"
        ) if (auth := self._service.service_client.network_wrapper.auth) else None

        return "\n".join(remote_script) + "\n"

    def _evaluate_remote_script(self, remote_script):
        """
        Uses TabPy /evaluate endpoint to execute a remote TabPy client script.

        Parameters
        ----------
        remote_script : str
            The script to execute remotely.
        """
        print(f"Remote script:\n{remote_script}")
        url = f"{self._endpoint}evaluate"
        headers = {"Content-Type": "application/json"}
        payload = {"data": {}, "script": remote_script}

        response = requests.post(
            url,
            headers=headers,
            auth=self._service.service_client.network_wrapper.auth,
            json=payload
        )

        msg = response.text.replace('null', 'success')
        if "Ad-hoc scripts have been disabled" in msg:
            msg += "\n[Remote TabPy client not allowed.]"
        print(f"\n{response.status_code} - {msg}\n")

    def set_credentials(self, username, password):
        """
        Set credentials for all the TabPy client-server communication
        where client is tabpy-tools and server is tabpy-server.

        Parameters
        ----------
        username : str
            User name (login). Username is case insensitive.

        password : str
            Password in plain text.
        """
        self._service.set_credentials(username, password)
