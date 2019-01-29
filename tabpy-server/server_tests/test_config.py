import os
import unittest
import logging
import tabpy_server

try:
    from unittest.mock import patch, call
except ImportError:
    from mock import patch, call

from tempfile import NamedTemporaryFile
from tabpy_server.tabpy import get_config, validate_cert
from argparse import Namespace


def assert_raises_runtime_error(message, fn, args={}):
    try:
        fn(*args)
        assert False
    except RuntimeError as err:
        assert err.args[0] == message


class TestConfigEnvironmentCalls(unittest.TestCase):

    @patch('tabpy_server.tabpy.TabPyState')
    @patch('tabpy_server.tabpy._get_state_from_file')
    @patch('tabpy_server.tabpy.shutil')
    @patch('tabpy_server.tabpy.PythonServiceHandler')
    @patch('tabpy_server.tabpy.os.path.exists', return_value=True)
    @patch('tabpy_server.tabpy.os.path.isfile', return_value=False)
    @patch('tabpy_server.tabpy.os')
    def test_no_config_file(self, mock_os, mock_file_exists, mock_path_exists, mock_psws, mock_shutil,
                            mock_management_util, mock_tabpy_state):
        get_config()

        getenv_calls = [call('TABPY_PORT', 9004),
                        call('TABPY_QUERY_OBJECT_PATH', '/tmp/query_objects'), call('TABPY_STATE_PATH', './')]
        mock_os.getenv.assert_has_calls(getenv_calls, any_order=True)
        mock_shutil.assert_not_called()
        self.assertEqual(len(mock_file_exists.mock_calls), 1)
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
    def test_no_state_ini_file_or_state_dir(self, mock_os, mock_file_exists, mock_path_exists, mock_psws, mock_shutil,
                                            mock_management_util, mock_tabpy_state):
        get_config()
        self.assertEqual(len(mock_os.makedirs.mock_calls), 1)


class TestPartialConfigFile(unittest.TestCase):

    @patch('tabpy_server.tabpy.parse_arguments')
    @patch('tabpy_server.tabpy.TabPyState')
    @patch('tabpy_server.tabpy._get_state_from_file')
    @patch('tabpy_server.tabpy.shutil')
    @patch('tabpy_server.tabpy.PythonServiceHandler')
    @patch('tabpy_server.tabpy.os.path.exists', return_value=True)
    @patch('tabpy_server.tabpy.os')
    def test_config_file_present(self, mock_os, mock_path_exists, mock_psws, mock_shutil, mock_management_util,
                                 mock_tabpy_state, mock_parse_arguments):
        config_file = NamedTemporaryFile(delete=False)
        config_file.write(b'TABPY_BIND_IP = 0.0.0.0\n'
                          b'TABPY_QUERY_OBJECT_PATH = foo\n'
                          b'TABPY_STATE_PATH = bar\n'
                          b'TABPY_LOG_LEVEL = warning')
        config_file.close()

        mock_parse_arguments.return_value = Namespace(config=config_file.name, port=None)

        mock_os.getenv.side_effect = [1234]
        mock_os.path.realpath.return_value = 'bar'

        settings, _ = get_config()
        getenv_calls = [call('TABPY_PORT', 9004)]

        mock_os.getenv.assert_has_calls(getenv_calls, any_order=True)
        self.assertEqual(settings['log_level'], 'WARNING')
        self.assertEqual(settings['port'], 1234)
        self.assertEquals(settings['bind_ip'], '0.0.0.0')
        self.assertEquals(settings['upload_dir'], 'foo')
        self.assertEquals(settings['state_file_path'], 'bar')
        self.assertEqual(settings['transfer_protocol'], 'http')
        self.assertTrue('certificate_file' not in settings)
        self.assertTrue('key_file' not in settings)

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
        self.fp = NamedTemporaryFile(delete=False)

        patcher = patch('tabpy_server.tabpy.parse_arguments', return_value=Namespace(config=self.fp.name, port=None))
        patcher.start()
        self.addCleanup(patcher.stop)

        self.addCleanup(os.remove, self.fp.name)
        self.addCleanup(os.chdir, self.cwd)

    def test_http(self):
        self.fp.write(b'TABPY_TRANSFER_PROTOCOL = http')
        self.fp.close()

        settings, _ = get_config()
        self.assertEqual(settings['transfer_protocol'], 'http')

    def test_https_without_cert_and_key(self):
        self.fp.write(b'TABPY_TRANSFER_PROTOCOL = https')
        self.fp.close()

        assert_raises_runtime_error(
            'Error using HTTPS: The parameter(s) TABPY_CERTIFICATE_FILE and TABPY_KEY_FILE must be set.', get_config)

    def test_https_without_cert(self):
        self.fp.write(b'TABPY_TRANSFER_PROTOCOL = https\n'
                      b'TABPY_KEY_FILE = foo')
        self.fp.close()

        assert_raises_runtime_error('Error using HTTPS: The parameter(s) TABPY_CERTIFICATE_FILE must be set.',
                                    get_config)

    def test_https_without_key(self):
        self.fp.write(b'TABPY_TRANSFER_PROTOCOL = https\n'
                      b'TABPY_CERTIFICATE_FILE = foo')
        self.fp.close()

        assert_raises_runtime_error('Error using HTTPS: The parameter(s) TABPY_KEY_FILE must be set.',
                                    get_config)

    @patch('tabpy_server.tabpy.os.path')
    def test_https_cert_and_key_file_not_found(self, mock_path):
        self.fp.write(b'TABPY_TRANSFER_PROTOCOL = https\n'
                      b'TABPY_CERTIFICATE_FILE = foo\n'
                      b'TABPY_KEY_FILE = bar')
        self.fp.close()

        mock_path.isfile.side_effect = lambda x: self.mock_isfile(x, {self.fp.name})

        assert_raises_runtime_error(
            'Error using HTTPS: The parameter(s) TABPY_CERTIFICATE_FILE and TABPY_KEY_FILE must point to an existing file.',
            get_config)

    @patch('tabpy_server.tabpy.os.path')
    def test_https_cert_file_not_found(self, mock_path):
        self.fp.write(b'TABPY_TRANSFER_PROTOCOL = https\n'
                      b'TABPY_CERTIFICATE_FILE = foo\n'
                      b'TABPY_KEY_FILE = bar')
        self.fp.close()

        mock_path.isfile.side_effect = lambda x: self.mock_isfile(x, {self.fp.name, 'bar'})

        assert_raises_runtime_error(
            'Error using HTTPS: The parameter(s) TABPY_CERTIFICATE_FILE must point to an existing file.', get_config)

    @patch('tabpy_server.tabpy.os.path')
    def test_https_key_file_not_found(self, mock_path):
        self.fp.write(b'TABPY_TRANSFER_PROTOCOL = https\n'
                      b'TABPY_CERTIFICATE_FILE = foo\n'
                      b'TABPY_KEY_FILE = bar')
        self.fp.close()

        mock_path.isfile.side_effect = lambda x: self.mock_isfile(x, {self.fp.name, 'foo'})

        assert_raises_runtime_error(
            'Error using HTTPS: The parameter(s) TABPY_KEY_FILE must point to an existing file.', get_config)

    @patch('tabpy_server.tabpy.os.path.isfile', return_value=True)
    @patch('tabpy_server.tabpy.validate_cert', return_value=True)
    def test_https_success(self, mock_validate_cert, mock_isfile):
        self.fp.write(b'TABPY_TRANSFER_PROTOCOL = HtTpS\n'
                      b'TABPY_CERTIFICATE_FILE = foo\n'
                      b'TABPY_KEY_FILE = bar')
        self.fp.close()

        settings, _ = get_config()

        self.assertEqual(settings['transfer_protocol'], 'https')
        self.assertEqual(settings['certificate_file'], 'foo')
        self.assertEqual(settings['key_file'], 'bar')


class TestLogLevelValidation(unittest.TestCase):

    def setUp(self):
        os.chdir(os.path.join(os.getcwd(), 'tabpy-server', 'tabpy_server'))
        self.addCleanup(os.chdir, os.path.join(os.getcwd(), '..', '..'))

    def test_valid_log_level(self):
        valid_levels = {'inFO', 'WARNING', 'error', 'CriTiCal'}
        for level in valid_levels:
            fp = NamedTemporaryFile(delete=False)
            fp.write(b'TABPY_LOG_LEVEL = ' + bytes(level, 'utf-8'))
            fp.close()

            patcher = patch('tabpy_server.tabpy.parse_arguments',
                            return_value=Namespace(config=fp.name, port=None))
            patcher.start()

            settings, _ = get_config()
            self.assertEqual(settings['log_level'], level.upper())

            os.remove(fp.name)

    @patch('tabpy_server.tabpy.parse_arguments')
    def test_invalid_log_level(self, mock_parse_arguments):
        fp = NamedTemporaryFile(delete=False)
        fp.write(b'TABPY_LOG_LEVEL = foo')
        fp.close()

        mock_parse_arguments.return_value = Namespace(config=fp.name, port=None)

        settings, _ = get_config()
        self.assertEqual(settings['log_level'], 'INFO')

        os.remove(fp.name)

    @patch('tabpy_server.tabpy.os.path.isfile', side_effect={False, True})
    def test_default_log_level(self, mock_isfile):
        settings, _ = get_config()
        self.assertEqual(settings['log_level'], 'INFO')


class TestCertificateValidation(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(TestCertificateValidation, self).__init__(*args, **kwargs)
        self.resources_path = os.path.join(os.path.dirname(__file__), 'resources')

    def test_expired_cert(self):
        path = os.path.join(self.resources_path, 'expired.crt')
        message = 'Error using HTTPS: The certificate provided expired on 2018-08-18 19:47:18.'
        assert_raises_runtime_error(message, validate_cert, {path})

    def test_future_cert(self):
        path = os.path.join(self.resources_path, 'future.crt')
        message = 'Error using HTTPS: The certificate provided is not valid until 3001-01-01 00:00:00.'
        assert_raises_runtime_error(message, validate_cert, {path})

    def test_valid_cert(self):
        path = os.path.join(self.resources_path, 'valid.crt')
        validate_cert(path)
