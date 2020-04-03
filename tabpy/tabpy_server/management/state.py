try:
    from ConfigParser import ConfigParser
except ImportError:
    from configparser import ConfigParser
import logging


_SERVICE_INFO_SECTION_NAME = "Service Info"
logger = logging.getLogger(__name__)


def _get_root_path(state_path):
    if state_path[-1] != "/":
        return state_path + "/"
    else:
        return state_path


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

    def __init__(self, settings, models, config=None):
        self.settings = settings
        self.models = models
        self.set_config(config)

    def set_config(self, config, logger=logging.getLogger(__name__)):
        """
        Set the local ConfigParser manually.
        This new ConfigParser will be used as current state.
        """
        if not isinstance(config, ConfigParser):
            raise ValueError("Invalid config")
        self.config = config

    def get_endpoints(self):
        return self.models.keys()

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
