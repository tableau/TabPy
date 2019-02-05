import logging
import os
try:
    from ConfigParser import ConfigParser as _ConfigParser
except ImportError:
    from configparser import ConfigParser as _ConfigParser
try:
    from StringIO import StringIO as _StringIO
except ImportError:
    from io import StringIO as _StringIO
from dateutil import parser
from datetime import datetime, timedelta, tzinfo
from time import mktime


logger = logging.getLogger(__name__)


def write_state_config(state, settings):
    if 'state_file_path' in settings:
        state_path = settings['state_file_path']
    else:
        raise ValueError('TABPY_STATE_PATH is not set')
    
    logger.debug("State path is {}".format(state_path))
    state_key = os.path.join(state_path, 'state.ini')
    tmp_state_file = state_key

    with open(tmp_state_file, 'w') as f:
        state.write(f)



def _get_state_from_file(state_path):
    state_key = os.path.join(state_path, 'state.ini')
    tmp_state_file = state_key

    if not os.path.exists(tmp_state_file):
        raise ValueError("Missing config file at %r" % (tmp_state_file,))

    config = _ConfigParser(allow_no_value=True)
    config.optionxform = str
    config.read(tmp_state_file)

    if not config.has_section('Service Info'):
        raise ValueError("Config error: Expected 'Service Info' section in %s" % (tmp_state_file,))

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
        raise ValueError('Only local time and UTC time is supported')


