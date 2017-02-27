from re import compile as _compile
import time as _time
import sys

import requests

from .rest import (
    RequestsNetworkWrapper as _RequestsNetworkWrapper,
    ServiceClient as _ServiceClient,
)

from .rest_client import (
    RESTServiceClient as _RESTServiceClient,
    Endpoint as _Endpoint,
    AliasEndpoint as _AliasEndpoint,
)

from .custom_query_object import CustomQueryObject as \
    _CustomQueryObject

import os as _os


import logging as _logging
_logger = _logging.getLogger(__name__)


_name_checker = _compile('^[a-zA-Z0-9-_\ ]+$')

if sys.version_info.major == 3:
    unicode = str


def _check_endpoint_name(name):
    """Checks that the endpoint name is valid by comparing it with an RE and
    checking that it is not reserved."""
    if not isinstance(name, (str,unicode)):
        raise TypeError("Endpoint name must be a string or unicode")

    if name == '':
        raise ValueError("Endpoint name cannot be empty")

    if not _name_checker.match(name):
        raise ValueError('endpoint name %r can only contain: a-z, A-Z, 0-9,'
            ' underscore, hyphens and spaces.' % name)


class Client(object):

    def __init__(self,
            endpoint,
            query_timeout=None,
            verify_certificate=True):
        """
        Connects to a running server.

        The class constructor takes a server address which is then used to connect
        for all subsequent member APIs.

        Parameters
        ----------

        endpoint : str, optional

            The server URL.

        query_timeout : float, optional

            The timeout for query operations.

        verify_certificate : bool, optional

            Whether to check the certificate for SSL connections. Defaults to
            True.

        """
        self._endpoint = endpoint
        self._verify_certificate = verify_certificate

        session = requests.session()
        session.verify = self._verify_certificate

        # Setup the communications layer.
        network_wrapper = _RequestsNetworkWrapper(session)
        service_client = _ServiceClient(self._endpoint, network_wrapper)

        self._service =  _RESTServiceClient(service_client)
        if query_timeout is not None and query_timeout > 0:
            self.query_timeout = query_timeout
        else:
            self.query_timeout = 0.0

    def __repr__(self):
        return (
            "<"+self.__class__.__name__+
                ' object at '+hex(id(self))+
                ' connected to '+repr(self._endpoint)+">")

    def get_info(self):
        """Returns a dict containing information about the service.

        Returns
        -------
        dict
            Keys are:

            * name: The name of the service
            * creation_time: The creation time in seconds since 1970-01-01
            * description: Description of the service
            * server_version: The version of the service used
            * state_path: Where the state file is stored.
        """
        return self._service.get_info()


    def get_status(self):
        '''
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

        '''
        return self._service.get_status()


    #
    # Query
    #

    @property
    def query_timeout(self):
        """The timeout for queries in seconds."""
        return self._service.query_timeout

    @query_timeout.setter
    def query_timeout(self, value):
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
               "target": null},
            "add": {
              "description": "",
              "docstring": "-- no docstring found in query function --",
              "creation_time": 1469505967,
              "version": 1,
              "dependencies": [],
              "last_modified_time": 1469505967,
              "type": "model",
              "target": null}
            }
        """
        return self._service.get_endpoints(type)

    def _get_endpoint_upload_destination(self):
        """Returns the endpoint upload destination."""
        return self._service.get_endpoint_upload_destination()['path']

    def alias(self, alias, existing_endpoint_name, description = None):
        '''
        Create a new endpoint to redirect to an existing endpoint, or update an
        existing alias to point to a different existing endpoint.

        Parameters
        ----------
        alias : str
            The new endpoint name or an existing alias endpoint name.

        existing_endpoint_name : str
            A name of an existing endpoint to redirect the alias to.

        description : str, optional
            A description for the alias.
        '''
        # check for invalid PO names
        _check_endpoint_name(alias)

        if not description:
            description = 'Alias for %s' % existing_endpoint_name

        if existing_endpoint_name not in self.get_endpoints():
            raise ValueError("Endpoint '%s' does not exist." % existing_endpoint_name)

        # Can only overwrite existing alias
        existing_endpoint = self.get_endpoints().get(alias)
        endpoint = _AliasEndpoint(
                name          = alias,
                type          = 'alias',
                description   = description,
                target        = existing_endpoint_name,
                cache_state   = 'disabled',
                version       = 1,
                )

        if existing_endpoint:
            if existing_endpoint.type != 'alias':
                raise RuntimeError('Name "%s" is already in use by another endpoint.' % alias)

            endpoint.version = existing_endpoint.version + 1

            self._service.set_endpoint(endpoint)
        else:
            self._service.add_endpoint(endpoint)

        self._wait_for_endpoint_deployment(alias, endpoint.version)


    def deploy(self,
        name, obj, description='', schema=None,
        override=False):
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
            output parameters, and respective examples. Providing a schema for a
            deployed function lets other users of the service discover how to
            use it. Refer to schema.generate_schema for more information on
            how to generate the schema.

        override : bool
            Whether to override (update) an existing endpoint. If False and
            there is already an endpoint with that name, it will raise a
            RuntimeError. If True and there is already an endpoint with that
            name, it will deploy a new version on top of it.

        See Also
        --------
        remove, get_endpoints

        """
        endpoint = self.get_endpoints().get(name)
        if endpoint:
            if not override:
                raise RuntimeError("An endpoint with that name (%r) already"
                    " exists. Use 'override = True' to force update "
                    "an existing endpoint." % name)

            version = endpoint.version + 1
        else:
            version = 1

        obj = self._gen_endpoint(name, obj, description, version, schema)

        self._upload_endpoint(obj)

        if version == 1:
            self._service.add_endpoint(_Endpoint(**obj))
        else:
            self._service.set_endpoint(_Endpoint(**obj))

        self._wait_for_endpoint_deployment(obj['name'], obj['version'])

    def _gen_endpoint(self, name, obj, description, version=1, schema=[]):
        '''Generates an endpoint dict.

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
        '''
        # check for invalid PO names
        _check_endpoint_name(name)

        if description is None:
            if isinstance(obj.__doc__, str):
                # extract doc string
                description = obj.__doc__.strip() or ''
            else:
                description = ''

        endpoint_object = _CustomQueryObject(
                query=obj,
                description=description,
                )

        return {
            'name'          : name,
            'version'       : version,
            'description'   : description,
            'type'          : 'model',
            'endpoint_obj'  : endpoint_object,
            'dependencies'  : endpoint_object.get_dependencies(),
            'methods'       : endpoint_object.get_methods(),
            'required_files': [],
            'required_packages': [],
            'schema': schema
        }

    def _upload_endpoint(self, obj):
        """Sends the endpoint across the wire."""
        endpoint_obj = obj['endpoint_obj']

        dest_path = self._get_endpoint_upload_destination()

        # Upload the endpoint
        obj['src_path'] = _os.path.join(
            dest_path,
            'endpoints',
            obj['name'],
            str(obj['version']))

        endpoint_obj.save(obj['src_path'])



    def _wait_for_endpoint_deployment(self,
            endpoint_name,
            version=1,
            interval=1.0,
        ):
        """
        Waits for the endpoint to be deployed by calling get_status() and
        checking the versions deployed of the endpoint against the expected
        version. If all the versions are equal to or greater than the version
        expected, then it will return. Uses time.sleep().
        """
        _logger.info("Waiting for endpoint %r to deploy to version %r",
            endpoint_name,
            version)
        start = _time.time()
        while True:
            ep_status = self.get_status()
            try:
                ep = ep_status[endpoint_name]
            except KeyError:
                _logger.info("Endpoint %r doesn't exist in endpoints yet",
                    endpoint_name)
            else:
                _logger.info("ep=%r", ep)

                if ep['status']  == 'LoadFailed':
                    raise RuntimeError("LoadFailed: %r" % (
                        ep['last_error'],
                    ))

                elif ep['status'] == 'LoadSuccessful':
                    if ep['version'] >= version:
                        _logger.info("LoadSuccessful")
                        break
                    else:
                        _logger.info("LoadSuccessful but wrong version")



            if _time.time() - start > 10:
                raise RuntimeError("Waited more then 10s for deployment")

            _logger.info("Sleeping %r", interval)
            _time.sleep(interval)

    def remove(self, name):
        '''
        Remove the endpoint that has the specified name.

        Parameters
        ----------
        name : str
            The name of the endpoint to be removed.

        Notes
        -----
        This could fail if the endpoint does not exist, or if the endpoint is
        in use by an alias. To check all endpoints
        that are depending on this endpoint, use `get_endpoint_dependencies`.

        See Also
        --------
        deploy, get_endpoint_dependencies
        '''
        self._service.remove_endpoint(name)

        # Wait for the endpoint to be removed
        while name in self.get_endpoints():
            _time.sleep(1.0)

    def get_endpoint_dependencies(self, endpoint_name = None):
        '''
        Get all endpoints that depend on the given endpoint. The only
        dependency that is recorded is aliases on the endpoint they refer to.
        This will not return internal dependencies, as when you have an
        endpoint that calls another endpoint from within its code body.

        Parameters
        ----------
        endpoint_name : str, optional
            The name of the endpoint to find dependent endpoints. If not given,
            find all dependent endpoints for all endpoints.

        Returns
        -------
        dependent endpoints : dict
            if endpoint_name is given, returns a list of endpoint names that depend
            on the given endpoint.

            If endpoint_name is not given, returns a dictionary where key is the
            endpoint name and value is a set of endpoints that depend on the
            endpoint specified by the key.

        '''
        endpoints = self.get_endpoints()

        def get_dependencies(endpoint):
            result = set()
            for d in endpoints[endpoint].dependencies:
                result.update([d])
                result.update(get_dependencies(d))
            return result

        if endpoint_name:
            return get_dependencies(endpoint_name)

        else:
            return {
                endpoint : get_dependencies(endpoint)
                for endpoint in endpoints
            }
