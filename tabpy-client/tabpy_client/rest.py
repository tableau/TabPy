import logging as _logging
from future.utils import with_metaclass
import requests
_logger = _logging.getLogger(__name__)

from collections import MutableMapping as _MutableMapping

import json as json

class ResponseError(Exception):
    """Raised when we get an unexpected response."""

    def __init__(self, response):
        super(ResponseError, self).__init__("Unexpected server response")
        self.response = response
        self.status_code = response.status_code

        try:
            r = response.json()
            self.info = r['info']
            self.message = response.json()['message']
        except:
            self.info = None
            self.message = response.text

    def __str__(self):
        return "(%s) %s %r" % (
            self.status_code,
            self.message,
            self.info)

class RequestsNetworkWrapper(object):
    """The NetworkWrapper wraps the underlying network connection to simplify
    the interface a bit. This can be replaced with something that can be built
    on some other type of network connection, such as PyCURL.

    This version requires you to instantiate a requests session object to your
    liking. It will create a generic session for you if you don't specify it,
    which you can modify later.

    For authentication, use::

        session.auth = (username, password)

    For modifying SSL behavior::

        session.verify = False # Ignore SSL warnings

    """

    def __init__(self, session=None):
        # Set .verify and .auth as appropriate.
        if session is None:
            session = requests.session()

        self.session = session

    def raise_error(self, response):
        _logger.error("Error with server response. code=%s; text=%s",
            response.status_code,
            response.text)

        raise ResponseError(response)

    def _remove_nones(self, data):
        if isinstance(data, dict):
            for k in [k for k,v in data.items() if v is None]:
                del data[k]

    def _encode_request(self, data):
        self._remove_nones(data)

        if data is not None:
            return json.dumps(data)
        else:
            return None

    def GET(self, url, data, timeout=None):
        """Issues a GET request to the URL with the data specified. Returns an
        object that is parsed from the response JSON."""
        self._remove_nones(data)

        _logger.info("GET %s with %r", url, data)

        response = self.session.get(url, params=data, timeout=timeout)
        if response.status_code != 200:
            self.raise_error(response)
        _logger.info("response=%r", response.text)

        if response.text == '':
            return dict()
        else:
            return response.json()

    def POST(self, url, data, timeout=None):
        """Issues a POST request to the URL with the data specified. Returns an
        object that is parsed from the response JSON."""
        data = self._encode_request(data)

        _logger.info("POST %s with %r", url, data)
        response = self.session.post(url,
                data=data,
                headers={
                    'content-type': 'application/json',
                },
                timeout=timeout)
        if response.status_code not in (200, 201):
            self.raise_error(response)

        return response.json()

    def PUT(self, url, data, timeout=None):
        """Issues a PUT request to the URL with the data specified. Returns an
        object that is parsed from the response JSON."""
        data = self._encode_request(data)

        _logger.info("PUT %s with %r", url, data)

        response = self.session.put(url,
                data=data,
                headers={
                    'content-type': 'application/json',
                },
                timeout=timeout)
        if response.status_code != 200:
            self.raise_error(response)

        return response.json()

    def DELETE(self, url, data, timeout=None):
        """Issues a DELETE request to the URL with the data specified. Returns an
        object that is parsed from the response JSON."""
        if data is not None:
            data = json.dumps(data)

        _logger.info("DELETE %s with %r", url, data)

        response = self.session.delete(url, data=data, timeout=timeout)

        if response.status_code <= 499 and response.status_code >= 400:
            raise RuntimeError(response.text)

        if response.status_code not in (200, 201, 204):
            raise RuntimeError("Error with server response code: %s", response.status_code)

class ServiceClient(object):
    """A generic service client.

    This will take an endpoint URL and a network_wrapper. You can use the
    RequestsNetworkWrapper if you want to use the requests module. The
    endpoint URL is prepended to all the requests and forwarded to the network
    wrapper."""

    def __init__(self, endpoint, network_wrapper=None):
        if network_wrapper is None:
            network_wrapper = RequestsNetworkWrapper(session=requests.session())

        self.network_wrapper = network_wrapper

        if not endpoint.endswith('/'):
            _logger.warning("endpoint %s does not end with '/': appending.", endpoint)
            endpoint = endpoint + '/'

        self.endpoint = endpoint

    def GET(self, url, data=None, timeout=None):
        """Prepends self.endpoint to the url and issues a GET request."""
        return self.network_wrapper.GET(self.endpoint + url, data, timeout)

    def POST(self, url, data=None, timeout=None):
        """Prepends self.endpoint to the url and issues a POST request."""
        return self.network_wrapper.POST(self.endpoint + url, data, timeout)

    def PUT(self, url, data=None, timeout=None):
        """Prepends self.endpoint to the url and issues a PUT request."""
        return self.network_wrapper.PUT(self.endpoint + url, data, timeout)

    def DELETE(self, url, data=None, timeout=None):
        """Prepends self.endpoint to the url and issues a DELETE request."""
        self.network_wrapper.DELETE(self.endpoint + url, data, timeout)


class RESTProperty(object):
    """A descriptor that will control the type of value stored."""
    def __init__(self, type, from_json=lambda x: x, to_json=lambda x: x,
            doc=None):
        self.__doc__ = doc
        self.type = type
        self.from_json = from_json
        self.to_json = to_json

    def __get__(self, instance, owner):
        if instance:
            try:
                return getattr(instance,
                    self.name)
            except AttributeError:
                raise AttributeError("%s has not been set yet." % (
                    self.name))
        else:
            return self

    def __set__(self, instance, value):
        if value is not None and not isinstance(value, self.type):
            value = self.type(value)

        setattr(instance, self.name, value)

    def __delete__(self, instance):
        delattr(instance, self.name)


class _RESTMetaclass(type(_MutableMapping)):
    """The metaclass for RESTObjects.

    This will look into the attributes for the class. If they are a
    RESTProperty, then it will add it to the __rest__ set and give it its
    name.

    If the bases have __rest__, then it will add them to the __rest__ set as
    well.
    """
    def __init__(self, name, bases, dict):
        super(_RESTMetaclass, self).__init__(name, bases, dict)

        self.__rest__ = set()
        for base in bases:
            self.__rest__.update(getattr(base, '__rest__', set()))


        for k,v in dict.items():
            if isinstance(v, RESTProperty):
                v.__dict__['name'] = '_'+k
                self.__rest__.add(k)


class RESTObject(with_metaclass(_RESTMetaclass,_MutableMapping)):
    """A base class that has methods generally useful for interacting with
    REST objects. The attributes are accessible either as dict keys or as
    attributes. The object also behaves like a dict, even replicating the
    repr() functionality.

    Attributes
    ----------

    __rest__ : set of str
        A set of all the rest attribute names. This is generated automatically
        and should include all of the base classes' __rest__ as well as any
        addition RESTProperty.

    """
    """ __metaclass__ = _RESTMetaclass"""

    def __init__(self, **kwargs):
        """Creates a new instance of the RESTObject.

        Parameters
        ----------

        The parameters depend on __rest__. Each item in __rest__ is searched
        for. If found, it is assigned to the instance. Additional parameters
        are ignored.

        """
        _logger.info("Initializing %s from %r",
            self.__class__.__name__,
            kwargs)
        for attr in self.__rest__:
            if attr in kwargs:
                setattr(self, attr, kwargs.pop(attr))

    def __repr__(self):
        return (
            "{"+
                ", ".join([
                    repr(k) + ": " + repr(v)
                    for k,v in self.items()
                ])+
            "}"
        )

    @classmethod
    def from_json(cls, data):
        """Returns a new class object with data populated from json.loads()."""
        attrs = {}
        for attr in cls.__rest__:
            try:
                value = data[attr]
            except KeyError:
                pass
            else:
                prop = cls.__dict__[attr]
                attrs[attr] = prop.from_json(value)
        return cls(**attrs)


    def to_json(self):
        """Returns a dict representing this object. This dict will be sent to
        json.dumps().

        The keys are the items in __rest__ and the values are the current
        values. If missing, it is not included.
        """
        result = {}
        for attr in self.__rest__:
            prop = getattr(self.__class__, attr)
            try:
                result[attr] = prop.to_json(getattr(self, attr))
            except AttributeError:
                pass

        return result

    def __eq__(self, other):
        return (
            type(self) == type(self)
            and all((
                getattr(self, a) == getattr(other, a)
                for a in self.__rest__
            )))

    def __len__(self):
        return len([a for a in self.__rest__ if hasattr(self, '_'+a)])

    def __iter__(self):
        return iter([a for a in self.__rest__ if hasattr(self, '_'+a)])


    def __getitem__(self, item):
        if item not in self.__rest__:
            raise KeyError(item)
        try:
            return getattr(self, item)
        except AttributeError:
            raise KeyError(item)

    def __setitem__(self, item, value):
        if item not in self.__rest__:
            raise KeyError(item)
        setattr(self, item, value)

    def __delitem__(self, item):
        if item not in self.__rest__:
            raise KeyError(item)
        try:
            delattr(self, '_'+item)
        except AttributeError:
            raise KeyError(item)

    def __contains__(self, item):
        return item in self.__rest__


def enum(*values, **kwargs):
    """Generates an enum function that only accepts particular values. Other
    values will raise a ValueError.

    Parameters
    ----------

    values : list
        These are the acceptable values.

    type : type
        The acceptable types of values. Values will be converted before being
        checked against the allowed values. If not specified, no conversion
        will be performed.

    Example
    -------

    >>> my_enum = enum(1, 2, 3, 4, 5, type=int)
    >>> a = my_enum(1)
    >>> b = my_enum(2)
    >>> c = mu_enum(6) # Raises ValueError

    """
    if len(values) < 1:
        raise ValueError("At least one value is required.")
    enum_type = kwargs.pop('type', str)
    if kwargs:
        raise TypeError("Unexpected parameters: %s" % (
            ", ".join(kwargs.keys())))

    def __new__(cls, value):
        if value not in cls.values:
            raise ValueError(
                "%r is an unexpected value. Expected one of %r" % (
                    value,
                    cls.values))

        return super(enum, cls).__new__(cls, value)

    enum = type(
        'Enum',
        (enum_type,),
        {
            'values':values,
            '__new__':__new__,
        })

    return enum
