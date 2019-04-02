import logging
import os
try:
    from ConfigParser import ConfigParser as _ConfigParser
except ImportError:
    from configparser import ConfigParser as _ConfigParser
from datetime import datetime, timedelta, tzinfo
from tabpy_server.app.ConfigParameters import ConfigParameters
from tabpy_server.app.util import log_and_raise
from time import mktime

logger = logging.getLogger(__name__)


def write_state_config(state, settings):
    if 'state_file_path' in settings:
        state_path = settings['state_file_path']
    else:
        log_and_raise(
            '{} is not set'.format(
                ConfigParameters.TABPY_STATE_PATH),
            ValueError)

    logger.debug("State path is {}".format(state_path))
    state_key = os.path.join(state_path, 'state.ini')
    tmp_state_file = state_key

    with open(tmp_state_file, 'w') as f:
        state.write(f)


def _get_state_from_file(state_path):
    state_key = os.path.join(state_path, 'state.ini')
    tmp_state_file = state_key

    if not os.path.exists(tmp_state_file):
        log_and_raise(
            "Missing config file at %r" %
            (tmp_state_file,), ValueError)

    config = _ConfigParser(allow_no_value=True)
    config.optionxform = str
    config.read(tmp_state_file)

    if not config.has_section('Service Info'):
        log_and_raise(
            "Config error: Expected 'Service Info' section in %s" %
            (tmp_state_file,), ValueError)

    return config


_ZERO = timedelta(0)


class _UTC(tzinfo):
    """
    A UTC datetime.tzinfo class modeled after the pytz library. It includes a
    __reduce__ method for pickling,
    """

    def fromutc(self, dt):
        if dt.tzinfo is None:
            return self.localize(dt)
        return super(_UTC, self).fromutc(dt)

    def utcoffset(self, dt):
        return _ZERO

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return _ZERO

    def __reduce__(self):
        return _UTC, ()

    def __repr__(self):
        return "<UTC>"

    def __str__(self):
        return "UTC"


_utc = _UTC()


def _dt_to_utc_timestamp(t):
    if t.tzname() == 'UTC':
        return (t - datetime(1970, 1, 1, tzinfo=_utc)).total_seconds()
    elif not t.tzinfo:
        return mktime(t.timetuple())
    else:
        log_and_raise('Only local time and UTC time is supported', ValueError)
