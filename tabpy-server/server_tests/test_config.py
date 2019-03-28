import os
import unittest
<<<<<<< HEAD
from argparse import Namespace
from tempfile import NamedTemporaryFile

from tabpy_server.app.util import validate_cert
from tabpy_server.app.app import TabPyApp
=======
>>>>>>> fab86dd... Merge pull request #206 from WillAyd/server-linting

from unittest.mock import patch, call



def assert_raises_runtime_error(message, fn, args={}):
    try:
        fn(*args)
        assert False
    except RuntimeError as err:
        assert err.args[0] == message


<<<<<<< HEAD
class TestConfigEnvironmentCalls(unittest.TestCase):
    @patch('tabpy_server.app.app.TabPyApp._parse_cli_arguments',
           return_value=Namespace(config=None))
    @patch('tabpy_server.app.app.TabPyState')
    @patch('tabpy_server.app.app._get_state_from_file')
    @patch('tabpy_server.app.app.PythonServiceHandler')
    @patch('tabpy_server.app.app.os.path.exists', return_value=True)
    @patch('tabpy_server.app.app.os.path.isfile', return_value=False)
    @patch('tabpy_server.app.app.os')
    def test_no_config_file(self, mock_os, mock_file_exists,
                            mock_path_exists, mock_psws,
                            mock_management_util, mock_tabpy_state,
                            mock_parse_arguments):
        TabPyApp(None)
=======
def append_logger_settings_to_config_file(config_file):
    config_file.write("[loggers]\n"
                      "keys=root\n"
                      "[handlers]\n"
                      "keys=rotatingFileHandler\n"
                      "[formatters]\n"
                      "keys=rootFormatter\n"
                      "[logger_root]\n"
                      "level=ERROR\n"
                      "handlers=rotatingFileHandler\n"
                      "qualname=root\n"
                      "propagete=0\n"
                      "[handler_rotatingFileHandler]\n"
                      "class=handlers.RotatingFileHandler\n"
                      "level=ERROR\n"
                      "formatter=rootFormatter\n"
                      "args=('tabpy_server_tests_log.log', 'w', 1000000, 5)\n"
                      "[formatter_rootFormatter]\n"
                      "format=%(asctime)s [%(levelname)s] (%(filename)s:"
                      "%(module)s:%(lineno)d): %(message)s\n"
                      "datefmt=%Y-%m-%d,%H:%M:%S\n".encode())


class TestConfigEnvironmentCalls(unittest.TestCase):

    @patch('tabpy_server.tabpy.TabPyState')
    @patch('tabpy_server.tabpy._get_state_from_file')
    @patch('tabpy_server.tabpy.shutil')
    @patch('tabpy_server.tabpy.PythonServiceHandler')
    @patch('tabpy_server.tabpy.os.path.exists', return_value=True)
    @patch('tabpy_server.tabpy.os.path.isfile', return_value=False)
    @patch('tabpy_server.tabpy.os')
    def test_no_config_file(self, mock_os, mock_file_exists, mock_path_exists,
                            mock_psws, mock_shutil, mock_management_util,
                            mock_tabpy_state):
        get_config(None)
>>>>>>> fab86dd... Merge pull request #206 from WillAyd/server-linting

        getenv_calls = [call('TABPY_PORT', 9004),
                        call('TABPY_QUERY_OBJECT_PATH', '/tmp/query_objects'),
                        call('TABPY_STATE_PATH', './')]
        mock_os.getenv.assert_has_calls(getenv_calls, any_order=True)
        self.assertEqual(len(mock_file_exists.mock_calls), 2)
        self.assertEqual(len(mock_psws.mock_calls), 1)
        self.assertEqual(len(mock_tabpy_state.mock_calls), 1)
        self.assertEqual(len(mock_path_exists.mock_calls), 1)
        self.assertTrue(len(mock_management_util.mock_calls) > 0)
        mock_os.makedirs.assert_not_called()

<<<<<<< HEAD
    @patch('tabpy_server.app.app.TabPyApp._parse_cli_arguments',
           return_value=Namespace(config=None))
    @patch('tabpy_server.app.app.TabPyState')
    @patch('tabpy_server.app.app._get_state_from_file')
    @patch('tabpy_server.app.app.PythonServiceHandler')
    @patch('tabpy_server.app.app.os.path.exists', return_value=False)
    @patch('tabpy_server.app.app.os.path.isfile', return_value=False)
    @patch('tabpy_server.app.app.os')
    def test_no_state_ini_file_or_state_dir(self, mock_os, mock_file_exists,
                                            mock_path_exists, mock_psws,
                                            mock_management_util,
                                            mock_tabpy_state,
                                            mock_parse_arguments):
        TabPyApp(None)
=======
    @patch('tabpy_server.tabpy.TabPyState')
    @patch('tabpy_server.tabpy._get_state_from_file')
    @patch('tabpy_server.tabpy.shutil')
    @patch('tabpy_server.tabpy.PythonServiceHandler')
    @patch('tabpy_server.tabpy.os.path.exists', return_value=False)
    @patch('tabpy_server.tabpy.os.path.isfile', return_value=False)
    @patch('tabpy_server.tabpy.os')
    def test_no_state_ini_file_or_state_dir(self, mock_os, mock_file_exists,
                                            mock_path_exists, mock_psws,
                                            mock_shutil, mock_management_util,
                                            mock_tabpy_state):
        get_config(None)
>>>>>>> fab86dd... Merge pull request #206 from WillAyd/server-linting
        self.assertEqual(len(mock_os.makedirs.mock_calls), 1)


class TestPartialConfigFile(unittest.TestCase):
<<<<<<< HEAD
    @patch('tabpy_server.app.app.TabPyApp._parse_cli_arguments')
    @patch('tabpy_server.app.app.TabPyState')
    @patch('tabpy_server.app.app._get_state_from_file')
    @patch('tabpy_server.app.app.PythonServiceHandler')
    @patch('tabpy_server.app.app.os.path.exists', return_value=True)
    @patch('tabpy_server.app.app.os')
    def test_config_file_present(self, mock_os, mock_path_exists,
                                 mock_psws, mock_management_util,
=======

    @patch('tabpy_server.tabpy.parse_arguments')
    @patch('tabpy_server.tabpy.TabPyState')
    @patch('tabpy_server.tabpy._get_state_from_file')
    @patch('tabpy_server.tabpy.shutil')
    @patch('tabpy_server.tabpy.PythonServiceHandler')
    @patch('tabpy_server.tabpy.os.path.exists', return_value=True)
    @patch('tabpy_server.tabpy.os')
    def test_config_file_present(self, mock_os, mock_path_exists, mock_psws,
                                 mock_shutil, mock_management_util,
>>>>>>> fab86dd... Merge pull request #206 from WillAyd/server-linting
                                 mock_tabpy_state, mock_parse_arguments):
        config_file = NamedTemporaryFile(delete=False)

        config_file.write("[TabPy]\n"
                          "TABPY_QUERY_OBJECT_PATH = foo\n"
                          "TABPY_STATE_PATH = bar\n".encode())
        config_file.close()

<<<<<<< HEAD
        mock_parse_arguments.return_value = Namespace(config=config_file.name)
=======
        mock_parse_arguments.return_value = Namespace(
            config=config_file.name, port=None)
>>>>>>> fab86dd... Merge pull request #206 from WillAyd/server-linting

        mock_os.getenv.side_effect = [1234]
        mock_os.path.realpath.return_value = 'bar'

        app = TabPyApp(config_file.name)
        getenv_calls = [call('TABPY_PORT', 9004)]

        mock_os.getenv.assert_has_calls(getenv_calls, any_order=True)
<<<<<<< HEAD
        self.assertEqual(app.settings['port'], 1234)
        self.assertEqual(app.settings['server_version'], open(
            'VERSION').read().strip())
        self.assertEqual(app.settings['upload_dir'], 'foo')
        self.assertEqual(app.settings['state_file_path'], 'bar')
        self.assertEqual(app.settings['transfer_protocol'], 'http')
        self.assertTrue('certificate_file' not in app.settings)
        self.assertTrue('key_file' not in app.settings)
=======
        self.assertEqual(settings['port'], 1234)
        self.assertEqual(settings['server_version'],
                         open('VERSION').read().strip())
        self.assertEquals(settings['bind_ip'], '0.0.0.0')
        self.assertEquals(settings['upload_dir'], 'foo')
        self.assertEquals(settings['state_file_path'], 'bar')
        self.assertEqual(settings['transfer_protocol'], 'http')
        self.assertTrue('certificate_file' not in settings)
        self.assertTrue('key_file' not in settings)
>>>>>>> fab86dd... Merge pull request #206 from WillAyd/server-linting

        os.remove(config_file.name)


class TestTransferProtocolValidation(unittest.TestCase):
    @staticmethod
    def mock_isfile(target_file, existing_files):
        if target_file in existing_files:
            return True
        return False

    @staticmethod
    def raise_attribute_error():
        raise AttributeError()

    def __init__(self, *args, **kwargs):
        super(TestTransferProtocolValidation, self).__init__(*args, **kwargs)
        self.fp = None
        self.cwd = os.getcwd()
        self.tabpy_cwd = os.path.join(self.cwd, 'tabpy-server', 'tabpy_server')

    def setUp(self):
        os.chdir(self.tabpy_cwd)
<<<<<<< HEAD
        self.fp = NamedTemporaryFile(mode='w+t', delete=False)
=======
        self.fp = NamedTemporaryFile(delete=False)
        self.config_name = self.fp.name
        append_logger_settings_to_config_file(self.fp)

        patcher = patch('tabpy_server.tabpy.parse_arguments',
                        return_value=Namespace(config=self.fp.name, port=None))
        patcher.start()
        self.addCleanup(patcher.stop)
>>>>>>> fab86dd... Merge pull request #206 from WillAyd/server-linting

    def tearDown(self):
        os.chdir(self.cwd)
        os.remove(self.fp.name)
        self.fp = None

    def test_http(self):
        self.fp.write("[TabPy]\n"
                      "TABPY_TRANSFER_PROTOCOL = http")
        self.fp.close()

        app = TabPyApp(self.fp.name)
        self.assertEqual(app.settings['transfer_protocol'], 'http')

    def test_https_without_cert_and_key(self):
        self.fp.write("[TabPy]\n"
                      "TABPY_TRANSFER_PROTOCOL = https")
        self.fp.close()

        assert_raises_runtime_error(
            'Error using HTTPS: The parameter(s) TABPY_CERTIFICATE_FILE '
<<<<<<< HEAD
            'and TABPY_KEY_FILE must be set.',
            TabPyApp, {self.fp.name})
=======
            'and TABPY_KEY_FILE must be set.', get_config, {self.config_name})
>>>>>>> fab86dd... Merge pull request #206 from WillAyd/server-linting

    def test_https_without_cert(self):
        self.fp.write(
            "[TabPy]\n"
            "TABPY_TRANSFER_PROTOCOL = https\n"
            "TABPY_KEY_FILE = foo")
        self.fp.close()

        assert_raises_runtime_error('Error using HTTPS: The parameter(s) '
                                    'TABPY_CERTIFICATE_FILE must be set.',
<<<<<<< HEAD
                                    TabPyApp, {self.fp.name})
=======
                                    get_config, [self.config_name])
>>>>>>> fab86dd... Merge pull request #206 from WillAyd/server-linting

    def test_https_without_key(self):
        self.fp.write("[TabPy]\n"
                      "TABPY_TRANSFER_PROTOCOL = https\n"
                      "TABPY_CERTIFICATE_FILE = foo")
        self.fp.close()

        assert_raises_runtime_error('Error using HTTPS: The parameter(s) '
                                    'TABPY_KEY_FILE must be set.',
<<<<<<< HEAD
                                    TabPyApp, {self.fp.name})
=======
                                    get_config, [self.config_name])
>>>>>>> fab86dd... Merge pull request #206 from WillAyd/server-linting

    @patch('tabpy_server.app.app.os.path')
    def test_https_cert_and_key_file_not_found(self, mock_path):
        self.fp.write("[TabPy]\n"
                      "TABPY_TRANSFER_PROTOCOL = https\n"
                      "TABPY_CERTIFICATE_FILE = foo\n"
                      "TABPY_KEY_FILE = bar")
        self.fp.close()

<<<<<<< HEAD
        mock_path.isfile.side_effect =\
            lambda x: self.mock_isfile(x, {self.fp.name})

        assert_raises_runtime_error(
            'Error using HTTPS: The parameter(s) TABPY_CERTIFICATE_FILE '
            'and TABPY_KEY_FILE must point to an existing file.',
            TabPyApp, {self.fp.name})
=======
        mock_path.isfile.side_effect = lambda x: self.mock_isfile(
            x, {self.fp.name})

        assert_raises_runtime_error(
            'Error using HTTPS: The parameter(s) TABPY_CERTIFICATE_FILE and '
            'TABPY_KEY_FILE must point to an existing file.',
            get_config, {self.config_name})
>>>>>>> fab86dd... Merge pull request #206 from WillAyd/server-linting

    @patch('tabpy_server.app.app.os.path')
    def test_https_cert_file_not_found(self, mock_path):
        self.fp.write("[TabPy]\n"
                      "TABPY_TRANSFER_PROTOCOL = https\n"
                      "TABPY_CERTIFICATE_FILE = foo\n"
                      "TABPY_KEY_FILE = bar")
        self.fp.close()

        mock_path.isfile.side_effect = lambda x: self.mock_isfile(
            x, {self.fp.name, 'bar'})

        assert_raises_runtime_error(
<<<<<<< HEAD
            'Error using HTTPS: The parameter(s) TABPY_CERTIFICATE_FILE '
            'must point to an existing file.',
            TabPyApp, {self.fp.name})
=======
            'Error using HTTPS: The parameter(s) TABPY_CERTIFICATE_FILE must '
            'point to an existing file.', get_config, {self.config_name})
>>>>>>> fab86dd... Merge pull request #206 from WillAyd/server-linting

    @patch('tabpy_server.app.app.os.path')
    def test_https_key_file_not_found(self, mock_path):
        self.fp.write("[TabPy]\n"
                      "TABPY_TRANSFER_PROTOCOL = https\n"
                      "TABPY_CERTIFICATE_FILE = foo\n"
                      "TABPY_KEY_FILE = bar")
        self.fp.close()

        mock_path.isfile.side_effect = lambda x: self.mock_isfile(
            x, {self.fp.name, 'foo'})

        assert_raises_runtime_error(
<<<<<<< HEAD
            'Error using HTTPS: The parameter(s) TABPY_KEY_FILE must '
            'point to an existing file.', TabPyApp, {self.fp.name})
=======
            'Error using HTTPS: The parameter(s) TABPY_KEY_FILE must point to '
            'an existing file.', get_config, {self.config_name})
>>>>>>> fab86dd... Merge pull request #206 from WillAyd/server-linting

    @patch('tabpy_server.app.app.os.path.isfile', return_value=True)
    @patch('tabpy_server.app.util.validate_cert')
    def test_https_success(self, mock_isfile, mock_validate_cert):
        self.fp.write("[TabPy]\n"
                      "TABPY_TRANSFER_PROTOCOL = HtTpS\n"
                      "TABPY_CERTIFICATE_FILE = foo\n"
                      "TABPY_KEY_FILE = bar")
        self.fp.close()

        app = TabPyApp(self.fp.name)

        self.assertEqual(app.settings['transfer_protocol'], 'https')
        self.assertEqual(app.settings['certificate_file'], 'foo')
        self.assertEqual(app.settings['key_file'], 'bar')


class TestCertificateValidation(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(TestCertificateValidation, self).__init__(*args, **kwargs)
        self.resources_path = os.path.join(
            os.path.dirname(__file__), 'resources')

    def test_expired_cert(self):
        path = os.path.join(self.resources_path, 'expired.crt')
<<<<<<< HEAD
        message = 'Error using HTTPS: The certificate provided expired '\
            'on 2018-08-18 19:47:18.'
=======
        message = ('Error using HTTPS: The certificate provided expired '
                   'on 2018-08-18 19:47:18.')
>>>>>>> fab86dd... Merge pull request #206 from WillAyd/server-linting
        assert_raises_runtime_error(message, validate_cert, {path})

    def test_future_cert(self):
        path = os.path.join(self.resources_path, 'future.crt')
<<<<<<< HEAD
        message = 'Error using HTTPS: The certificate provided is not '\
            'valid until 3001-01-01 00:00:00.'
=======
        message = ('Error using HTTPS: The certificate provided is not valid '
                   'until 3001-01-01 00:00:00.')
>>>>>>> fab86dd... Merge pull request #206 from WillAyd/server-linting
        assert_raises_runtime_error(message, validate_cert, {path})

    def test_valid_cert(self):
        path = os.path.join(self.resources_path, 'valid.crt')
        validate_cert(path)
