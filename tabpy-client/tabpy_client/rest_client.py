from .rest import (
    RESTObject,
    RESTProperty,
    enum,
)

from datetime import datetime


def from_epoch(value):
    if isinstance(value, datetime):
        return value
    else:
        return datetime.utcfromtimestamp(value)

def to_epoch(value):
    return (value - datetime(1970, 1, 1)).total_seconds()


class Endpoint(RESTObject):
    """Represents an endpoint.

    Note that not every attribute is returned as part of the GET.

    Attributes
    ----------

    name : str

        The name of the endpoint. Valid names include ``[a-zA-Z0-9_\- ]+``

    type : str

        The type of endpoint. The types include "alias", "model".

    version : int

        The version of this endpoint. Initial versions have version on 1. New
        versions increment this by 1.

    description : str

        A human-readable description of the endpoint.

    dependencies: list

        A list of endpoints that this endpoint depends on.

    methods : list

        ???

    """
    name = RESTProperty(str)
    type = RESTProperty(str)
    version = RESTProperty(int)
    description = RESTProperty(str)
    dependencies = RESTProperty(list)
    methods = RESTProperty(list)
    creation_time = RESTProperty(datetime, from_epoch, to_epoch)
    last_modified_time = RESTProperty(datetime, from_epoch, to_epoch)
    evaluator = RESTProperty(str)
    schema_version = RESTProperty(int)
    schema = RESTProperty(str)

    def __new__(cls, **kwargs):
        """Dispatch to the appropriate class."""
        cls = {
            'alias': AliasEndpoint,
            'model': ModelEndpoint,
        }[kwargs['type']]

        """return object.__new__(cls, **kwargs)"""
        """ modified for Python 3"""
        return object.__new__(cls)

    def __eq__(self, other):
        return self.name == other.name and \
            self.type == other.type and \
            self.version == other.version and \
            self.description == other.description and \
            self.dependencies == other.dependencies and \
            self.methods == other.methods and \
            self.evaluator == other.evaluator and \
            self.schema_version == other.schema_version and \
            self.schema == other.schema

class ModelEndpoint(Endpoint):
    """Represents a model endpoint.

    src_path : str

        The local file path to the source of this object.

    required_files : str

        The local file path to the directory containing the
        required files.

    required_packages : str

        The local file path to the directory containing the
        required packages.

    """
    src_path = RESTProperty(str)
    required_files = RESTProperty(list)
    required_packages = RESTProperty(list)
    required_packages_dst_path = RESTProperty(str)

    def __init__(self, **kwargs):
        super(ModelEndpoint, self).__init__(**kwargs)
        self.type = 'model'

    def __eq__(self, other):
        return super(ModelEndpoint, self).__eq__(other) and \
            self.required_files==other.required_files and \
            self.required_packages == other.required_packages

class AliasEndpoint(Endpoint):
    """Represents an alias Endpoint.

    target : str

        The endpoint that this is an alias for.

    """
    target = RESTProperty(str)

    def __init__(self, **kwargs):
        super(AliasEndpoint, self).__init__(**kwargs)
        self.type = 'alias'

class RESTServiceClient(object):
    """A thin client for the REST Service."""

    def __init__(self, service_client):
        self.service_client = service_client
        self.query_timeout = None

    def get_info(self):
        """Returns the /info"""
        return self.service_client.GET('info')

    def query(self, name, *args, **kwargs):
        """Performs a query. Either specify *args or **kwargs, not both.
        Respects query_timeout."""
        if args and kwargs:
            raise ValueError('Mixing of keyword arguments and positional arguments '
                                'when querying an endpoint is not supported.')
        return self.service_client.POST('query/'+name,
            data={'data':args or kwargs},
            timeout=self.query_timeout)


    def get_endpoint_upload_destination(self):
        """Returns a dict representing where endpoint data should be uploaded.

        Returns
        -------

        dict

            Keys include:

            * path: a local file path.

        Note: In the future, other paths and parameters may be supported.

        Note: At this time, the response should not change over time.
        """
        return self.service_client.GET(
            'configurations/endpoint_upload_destination')

    def get_endpoints(self, type=None):
        """Returns endpoints from the management API.

        Parameters
        ----------

        type : str

            The type of endpoint to return. None will include all endpoints.
            Other options are 'model' and 'alias'.
        """
        result = {}
        for name, attrs in self.service_client.GET(
                'endpoints',
                {'type':type}).items():
            endpoint = Endpoint.from_json(attrs)
            endpoint.name = name
            result[name] = endpoint
        return result

    def get_endpoint(self, endpoint_name):
        """Returns an endpoints from the management API given its name.

        Parameters
        ----------

        endpoint_name : str

            The name of the endpoint.
        """
        ((name, attrs),) = self.service_client.GET('endpoints/'+endpoint_name).items()
        endpoint = Endpoint.from_json(attrs)
        endpoint.name = name
        return endpoint

    def add_endpoint(self, endpoint):
        """Adds an endpoint through the management API.

        Parameters
        ----------

        endpoint : Endpoint
        """
        return self.service_client.POST('endpoints',
                endpoint.to_json()
            )

    def set_endpoint(self, endpoint):
        """Updates an endpoint through the management API.

        Parameters
        ----------

        endpoint : Endpoint

            The endpoint to update.
        """
        return self.service_client.PUT('endpoints/'+endpoint.name,
                endpoint.to_json())

    def remove_endpoint(self, endpoint_name):
        """Deletes an endpoint through the management API.

        Parameters
        ----------

        endpoint_name : str

            The endpoint to delete.
        """
        self.service_client.DELETE('endpoints/'+endpoint_name)


    def get_status(self):
        """Returns the status of the server.

        Returns
        -------

        dict
        """
        return self.service_client.GET('status')
