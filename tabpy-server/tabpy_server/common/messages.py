import simplejson
import abc
from abc import ABCMeta
from collections import namedtuple

class Msg(object):
    """
    An abstract base class for all messages used for communicating between
    the WebServices.

    The minimal functionality is the ability to instantiate a Msg from JSON
    and to write a Msg instance to JSON.

    We use namedtuples because they are lightweight and immutable. The splat
    operator (*) that we inherit from namedtuple is also convenient. We empty
    __slots__ to avoid unnecessary overhead.
    """
    __metaclass__ = ABCMeta

    @abc.abstractmethod
    def for_json(self):
        d = self._asdict()
        type_str = self.__class__.__name__
        d.update({'type': type_str})
        return d

    @abc.abstractmethod
    def to_json(self):
        return simplejson.dumps(self.for_json())

    @staticmethod
    def from_json(str):
        d = simplejson.loads(str)
        type_str = d['type']
        del d['type']
        return eval(type_str)(**d)


class LoadSuccessful(namedtuple(
    'LoadSuccessful', ['uri', 'path', 'version', 'is_update', 'endpoint_type']), Msg):
    __slots__ = ()

class LoadFailed(namedtuple('LoadFailed', ['uri', 'version', 'error_msg']), Msg):
    __slots__ = ()

class LoadInProgress(namedtuple(
    'LoadInProgress', ['uri', 'path', 'version', 'is_update', 'endpoint_type']), Msg):
    __slots__ = ()

class Query(namedtuple('Query', ['uri', 'params']), Msg):
    __slots__ = ()

class QuerySuccessful(namedtuple(
        'QuerySuccessful', ['uri', 'version', 'response']), Msg):
    __slots__ = ()

class LoadObject(namedtuple(
        'LoadObject', ['uri', 'url', 'version', 'is_update', 'endpoint_type']), Msg):
    __slots__ = ()

class DeleteObjects(namedtuple('DeleteObjects', ['uris']), Msg):
    __slots__ = ()

# Used for testing to flush out objects
class FlushObjects(namedtuple('FlushObjects', []), Msg):
    __slots__ = ()

class ObjectsDeleted(namedtuple('ObjectsDeleted', ['uris']), Msg):
    __slots__ = ()

class ObjectsFlushed(namedtuple(
        'ObjectsFlushed', ['n_before', 'n_after']), Msg):
    __slots__ = ()

class CountObjects(namedtuple('CountObjects', []), Msg):
    __slots__ = ()

class ObjectCount(namedtuple('ObjectCount', ['count']), Msg):
    __slots__ = ()

class ListObjects(namedtuple('ListObjects', []), Msg):
    __slots__ = ()

class ObjectList(namedtuple('ObjectList', ['objects']), Msg):
    __slots__ = ()

class UnknownURI(namedtuple('UnknownURI', ['uri']), Msg):
    __slots__ = ()

class UnknownMessage(namedtuple('UnknownMessage', ['msg']), Msg):
    __slots__ = ()

class DownloadSkipped(namedtuple('DownloadSkipped', ['uri', 'version', 'msg','host']),
                      Msg):
    __slots__ = ()

class QueryFailed(namedtuple('QueryFailed', ['uri', 'error']), Msg):
    __slots__ = ()

class QueryError(namedtuple('QueryError', ['uri', 'error']), Msg):
    __slots__ = ()

class CheckHealth(namedtuple('CheckHealth', []), Msg):
    __slots__ = ()

class Healthy(namedtuple('Healthy', []), Msg):
    __slots__ = ()

class Unhealthy(namedtuple('Unhealthy', []), Msg):
    __slots__ = ()

class Ping(namedtuple('Ping', ['id']), Msg):
    __slots__ = ()

class Pong(namedtuple('Pong', ['id']), Msg):
    __slots__ = ()

class Listening(namedtuple('Listening', []), Msg):
    __slots__ = ()

class EngineFailure(namedtuple('EngineFailure', ['error']), Msg):
    __slots__ = ()

class FlushLogs(namedtuple('FlushLogs', []), Msg):
    __slots__ = ()

class LogsFlushed(namedtuple('LogsFlushed', []), Msg):
    __slots__ = ()

class ServiceError(namedtuple(
        'ServiceError', ['error']), Msg):
    __slots__ = ()

