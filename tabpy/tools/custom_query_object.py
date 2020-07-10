import logging
from .query_object import QueryObject as _QueryObject


logger = logging.getLogger(__name__)


class CustomQueryObject(_QueryObject):
    def __init__(self, query, description=""):
        """Create a new CustomQueryObject.

        Parameters
        -----------

        query : function
            Function that defines a custom query method. The query can have any
            signature, but input and output of the query needs to be JSON
            serializable.

        description : str
            The description of the custom query object

        """
        super().__init__(description)

        self.custom_query = query

    def query(self, *args, **kwargs):
        """Query the custom defined query method using the given input.

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
        """
        # include the dependent files in sys path so that the query can run
        # correctly

        try:
            logger.debug(
                "Running custom query with arguments " f"({args}, {kwargs})..."
            )
            ret = self.custom_query(*args, **kwargs)
        except Exception as e:
            logger.exception(
                "Exception hit when running custom query, error: " f"{str(e)}"
            )
            raise

        logger.debug(f"Received response {ret}")
        try:
            return self._make_serializable(ret)
        except Exception as e:
            logger.exception(
                "Cannot properly serialize custom query result, " f"error: {str(e)}"
            )
            raise

    def get_doc_string(self):
        """Get doc string from customized query"""
        if self.custom_query.__doc__ is not None:
            return self.custom_query.__doc__
        else:
            return "-- no docstring found in query function --"

    def get_methods(self):
        return [self.get_query_method()]

    def get_query_method(self):
        return {"method": "query"}
