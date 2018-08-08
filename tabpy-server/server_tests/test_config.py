import os
import unittest
try:
    from unittest.mock import patch, call
except ImportError:
    from mock import patch, call

from os.path import isfile
from sys import version_info

from tabpy_server.tabpy import get_config


class TestConfigEnvironmentCalls(unittest.TestCase):

    def file_exists(fn):  # Hmm - reinventing the wheel here?
        if fn == './common/config.py':
            return False
        return True

    @patch('tabpy_server.tabpy.TabPyState')
    @patch('tabpy_server.tabpy._get_state_from_file')
    @patch('tabpy_server.tabpy.shutil')
    @patch('tabpy_server.tabpy.PythonServiceHandler')
    @patch('tabpy_server.tabpy.os.path.exists', return_value=True)
    @patch('tabpy_server.tabpy.os.path.isfile', side_effect=file_exists)
    @patch('tabpy_server.tabpy.os')
    def test_no_config_file(self, mock_os, mock_file_exists, mock_path_exists, mock_psws, mock_shutil, mock_management_util, mock_tabpy_state):

        get_config()

        getenv_calls = [call('TABPY_PORT', 9004), call('TABPY_SERVER_VERSION', 'Alpha'),
                        call('TABPY_QUERY_OBJECT_PATH', '/tmp/query_objects'), call('TABPY_STATE_PATH', './')]
        mock_os.getenv.assert_has_calls(getenv_calls, any_order=True)
        mock_file_exists.assert_called_once()
        mock_shutil.assert_not_called()
        self.assertEqual(len(mock_psws.mock_calls), 1)
        self.assertEqual(len(mock_tabpy_state.mock_calls), 1)
        self.assertEqual(len(mock_path_exists.mock_calls), 1)
        self.assertTrue(len(mock_management_util.mock_calls) > 0)
        mock_os.makedirs.assert_not_called()

    @patch('tabpy_server.tabpy.TabPyState')
    @patch('tabpy_server.tabpy._get_state_from_file')
    @patch('tabpy_server.tabpy.shutil')
    @patch('tabpy_server.tabpy.PythonServiceHandler')
    @patch('tabpy_server.tabpy.os.path.exists', return_value=False)
    @patch('tabpy_server.tabpy.os.path.isfile', return_value=False)
    @patch('tabpy_server.tabpy.os')
    def test_no_state_ini_file_or_state_dir(self, mock_os, mock_file_exists, mock_path_exists, mock_psws, mock_shutil, mock_management_util, mock_tabpy_state):

        get_config()
        self.assertEqual(len(mock_shutil.mock_calls), 1)
        self.assertEqual(len(mock_os.makedirs.mock_calls), 1)


class TestPartialConfigFile(unittest.TestCase):

    def setUp(self):
        config_file = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                   'tabpy_server', 'common', 'config.py')
        if not isfile(config_file):
            with open(config_file, "w") as fh:
                fh.write("TABPY_QUERY_OBJECT_PATH = '/tmp/query_objects'\nTABPY_STATE_PATH = './'")
            self.addCleanup(os.remove, config_file)

    @patch('tabpy_server.tabpy.TabPyState')
    @patch('tabpy_server.tabpy._get_state_from_file')
    @patch('tabpy_server.tabpy.shutil')
    @patch('tabpy_server.tabpy.PythonServiceHandler')
    @patch('tabpy_server.tabpy.os.path.exists', return_value=True)
    @patch('tabpy_server.tabpy.os')
    def test_config_file_present(self, mock_os, mock_path_exists, mock_psws, mock_shutil, mock_management_util, mock_tabpy_state):

        settings, _ = get_config()

        getenv_calls = [call('TABPY_PORT', 9004), call('TABPY_SERVER_VERSION', 'Alpha')]
        mock_os.getenv.assert_has_calls(getenv_calls, any_order=True)
        self.assertEqual(settings['upload_dir'], '/tmp/query_objects')
