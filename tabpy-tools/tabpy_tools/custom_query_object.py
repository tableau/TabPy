import types as _types
from .query_object import QueryObject as _QueryObject

import logging as _logging
_logger = _logging.getLogger(__name__)

class CustomQueryObject(_QueryObject):
    def __init__(self, query, description = ''):
        '''Create a new CustomQueryObject.

        Parameters
        -----------

        query : function
            Function that defines a custom query method. The query can have any
            signature, but input and output of the query needs to be JSON serializable.

        description : str
            The description of the custom query object

        '''
        super(CustomQueryObject, self).__init__(description)

        self.custom_query = query


    def query(self, *args, **kwargs):
        '''Query the custom defined query method using the given input.

        Parameters
        ----------
        args : list
            positional arguments to the query

        kwargs : dict
            keyword arguments to the query

        Returns
        -------
        out: object.
            The results depends on the implementation of the query method.
            Typically the return value will be whatever that function returns.

        See Also
        --------
        QueryObject
        '''
        # include the dependent files in sys path so that the query can run correctly

        try:
            ret = self.custom_query(*args, **kwargs)
        except Exception as e:
            _logger.exception('Exception hit when running custom query, error: %s' % e.message)
            raise

        try:
            return self._make_serializable(ret)
        except Exception as e:
            _logger.exception('Cannot properly serialize custom query result, error: %s' % e.message)
            raise

    def get_doc_string(self):
        '''Get doc string from customized query'''
        if self.custom_query.__doc__ is not None:
            return self.custom_query.__doc__
        else:
            return "-- no docstring found in query function --"

    def get_methods(self):
        return [self.get_query_method()]

    def get_query_method(self):
        return {'method': 'query'}
