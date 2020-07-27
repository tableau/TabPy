import abc
import logging
import os
import json
import shutil

import cloudpickle as _cloudpickle


logger = logging.getLogger(__name__)


class QueryObject(abc.ABC):
    """
    Derived class needs to implement the following interface:
      * query() -- given input, return query result
      * get_doc_string() -- returns documentation for the Query Object
    """

    def __init__(self, description=""):
        self.description = description

    def get_dependencies(self):
        """All endpoints this endpoint depends on"""
        return []

    @abc.abstractmethod
    def query(self, input):
        """execute query on the provided input"""
        pass

    @abc.abstractmethod
    def get_doc_string(self):
        """Returns documentation for the query object

        By default, this method returns the docstring for 'query' method
        Derived class may overwrite this method to dynamically create docstring
        """
        pass

    def save(self, path):
        """ Save query object to the given local path

        Parameters
        ----------
        path : str
          The location to save the query object to
        """
        if os.path.exists(path):
            logger.warning(
                f'Overwriting existing file "{path}" when saving query object'
            )
            rm_fn = os.remove if os.path.isfile(path) else shutil.rmtree
            rm_fn(path)
        self._save_local(path)

    def _save_local(self, path):
        """Save current query object to local path
        """
        try:
            os.makedirs(path)
        except OSError as e:
            import errno

            if e.errno == errno.EEXIST and os.path.isdir(path):
                pass
            else:
                raise

        with open(os.path.join(path, "pickle_archive"), "wb") as f:
            _cloudpickle.dump(self, f)

    @classmethod
    def load(cls, path):
        """ Load query object from given path
        """
        new_po = None
        new_po = cls._load_local(path)

        logger.info(f'Loaded query object "{type(new_po).__name__}" successfully')

        return new_po

    @classmethod
    def _load_local(cls, path):
        path = os.path.abspath(os.path.expanduser(path))
        with open(os.path.join(path, "pickle_archive"), "rb") as f:
            return _cloudpickle.load(f)

    @classmethod
    def _make_serializable(cls, result):
        """Convert a result from object query to python data structure that can
        easily serialize over network
        """
        try:
            json.dumps(result)
        except TypeError:
            raise TypeError(
                "Result from object query is not json serializable: " f"{result}"
            )

        return result

    # Returns an array of dictionary that contains the methods and their
    # corresponding schema information.
    @abc.abstractmethod
    def get_methods(self):
        return None
