import os
import socket
import unittest
from tempfile import NamedTemporaryFile
import tabpy
from tabpy.tabpy_server.app.util import validate_cert
from tabpy.tabpy_server.app.app import TabPyApp

from unittest.mock import patch

# The OAuth config tests below all use a fake, non-resolvable
# "idp.example.com" JWKS host. TabPyApp resolves that host to guard
# against JWKS URIs pointing at internal/link-local addresses (SSRF), so
# tests need a fake public resolution result rather than a real DNS lookup.
PUBLIC_JWKS_ADDRINFO = [
    (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443)),
]


class TestConfigEnvironmentCalls(unittest.TestCase):
    def test_config_file_does_not_exist(self):
        app = TabPyApp("/folder_does_not_exit/file_does_not_exist.conf")

        self.assertEqual(app.settings["port"], 9004)
        self.assertEqual(
            app.settings["server_version"], open("tabpy/VERSION").read().strip()
        )
        self.assertEqual(app.settings["transfer_protocol"], "http")
        self.assertTrue("certificate_file" not in app.settings)
        self.assertTrue("key_file" not in app.settings)
        self.assertEqual(app.settings["log_request_context"], False)
        self.assertEqual(app.settings["evaluate_timeout"], 30)

    @patch("tabpy.tabpy_server.app.app.TabPyState")
    @patch("tabpy.tabpy_server.app.app._get_state_from_file")
    @patch("tabpy.tabpy_server.app.app.PythonServiceHandler")
    @patch("tabpy.tabpy_server.app.app.os.path.exists", return_value=True)
    @patch("tabpy.tabpy_server.app.app.os")
    def test_no_config_file(
        self,
        mock_os,
        mock_path_exists,
        mock_psws,
        mock_management_util,
        mock_tabpy_state,
    ):
        pkg_path = os.path.dirname(tabpy.__file__)
        obj_path = os.path.join(pkg_path, "tmp", "query_objects")
        state_path = os.path.join(pkg_path, "tabpy_server")
        mock_os.environ = {
            "TABPY_PORT": "9004",
            "TABPY_QUERY_OBJECT_PATH": obj_path,
            "TABPY_STATE_PATH": state_path,
        }

        TabPyApp(None)

        self.assertEqual(len(mock_psws.mock_calls), 1)
        self.assertEqual(len(mock_tabpy_state.mock_calls), 1)
        self.assertEqual(len(mock_path_exists.mock_calls), 1)
        self.assertTrue(len(mock_management_util.mock_calls) > 0)
        mock_os.makedirs.assert_not_called()

    @patch("tabpy.tabpy_server.app.app.TabPyState")
    @patch("tabpy.tabpy_server.app.app._get_state_from_file")
    @patch("tabpy.tabpy_server.app.app.PythonServiceHandler")
    @patch("tabpy.tabpy_server.app.app.os.path.exists", return_value=False)
    @patch("tabpy.tabpy_server.app.app.os")
    def test_no_state_ini_file_or_state_dir(
        self,
        mock_os,
        mock_path_exists,
        mock_psws,
        mock_management_util,
        mock_tabpy_state,
    ):
        TabPyApp(None)
        self.assertEqual(len(mock_os.makedirs.mock_calls), 1)

    @patch('builtins.input', return_value='y')
    @patch("tabpy.tabpy_server.app.app.os")
    @patch("tabpy.tabpy_server.app.app.os.path.exists", return_value=False)
    @patch("tabpy.tabpy_server.app.app.PythonServiceHandler")
    @patch("tabpy.tabpy_server.app.app._get_state_from_file")
    @patch("tabpy.tabpy_server.app.app.TabPyState")
    def test_handle_configuration_without_authentication(
        self,
        mock_tabpy_state,
        mock_get_state_from_file,
        mock_psws,
        mock_os_path_exists,
        mock_os,
        mock_input,
    ):
        TabPyApp(None)
        mock_input.assert_not_called()

        TabPyApp(None, False)
        mock_input.assert_called()

class TestPartialConfigFile(unittest.TestCase):
    def setUp(self):
        self.config_file = NamedTemporaryFile(delete=False)

    def tearDown(self):
        os.remove(self.config_file.name)
        self.config_file = None

    @patch("tabpy.tabpy_server.app.app.TabPyState")
    @patch("tabpy.tabpy_server.app.app._get_state_from_file")
    @patch("tabpy.tabpy_server.app.app.PythonServiceHandler")
    @patch("tabpy.tabpy_server.app.app.os.path.exists", return_value=True)
    @patch("tabpy.tabpy_server.app.app.os")
    def test_config_file_present(
        self,
        mock_os,
        mock_path_exists,
        mock_psws,
        mock_management_util,
        mock_tabpy_state,
    ):
        self.assertTrue(self.config_file is not None)
        config_file = self.config_file
        config_file.write(
            "[TabPy]\n"
            "TABPY_QUERY_OBJECT_PATH = foo\n"
            "TABPY_STATE_PATH = bar\n".encode()
        )
        config_file.close()

        mock_os.path.realpath.return_value = "bar"
        mock_os.environ = {"TABPY_PORT": "1234"}

        app = TabPyApp(config_file.name)

        self.assertEqual(app.settings["port"], "1234")
        self.assertEqual(
            app.settings["server_version"], open("tabpy/VERSION").read().strip()
        )
        self.assertEqual(app.settings["upload_dir"], "foo")
        self.assertEqual(app.settings["state_file_path"], "bar")
        self.assertEqual(app.settings["transfer_protocol"], "http")
        self.assertTrue("certificate_file" not in app.settings)
        self.assertTrue("key_file" not in app.settings)
        self.assertEqual(app.settings["log_request_context"], False)
        self.assertEqual(app.settings["evaluate_timeout"], 30)

    @patch("tabpy.tabpy_server.app.app.os.path.exists", return_value=True)
    @patch("tabpy.tabpy_server.app.app._get_state_from_file")
    @patch("tabpy.tabpy_server.app.app.TabPyState")
    def test_custom_evaluate_timeout_valid(
        self, mock_state, mock_get_state_from_file, mock_path_exists
    ):
        self.assertTrue(self.config_file is not None)
        config_file = self.config_file
        config_file.write("[TabPy]\n" "TABPY_EVALUATE_TIMEOUT = 1996".encode())
        config_file.close()

        app = TabPyApp(self.config_file.name)
        self.assertEqual(app.settings["evaluate_timeout"], 1996.0)

    @patch("tabpy.tabpy_server.app.app.os.path.exists", return_value=True)
    @patch("tabpy.tabpy_server.app.app._get_state_from_file")
    @patch("tabpy.tabpy_server.app.app.TabPyState")
    def test_custom_evaluate_timeout_invalid(
        self, mock_state, mock_get_state_from_file, mock_path_exists
    ):
        self.assertTrue(self.config_file is not None)
        config_file = self.config_file
        config_file.write(
            "[TabPy]\n" 'TABPY_EVALUATE_TIMEOUT = "im not a float"'.encode()
        )
        config_file.close()

        with self.assertRaises(ValueError):
            TabPyApp(self.config_file.name)

    @patch("tabpy.tabpy_server.app.app.os")
    @patch("tabpy.tabpy_server.app.app.os.path.exists", return_value=True)
    @patch("tabpy.tabpy_server.app.app._get_state_from_file")
    @patch("tabpy.tabpy_server.app.app.TabPyState")
    def test_env_variables_in_config(
        self, mock_state, mock_get_state, mock_path_exists, mock_os
    ):
        mock_os.environ = {"foo": "baz"}
        config_file = self.config_file
        config_file.write("[TabPy]\n" "TABPY_PORT = %(foo)sbar".encode())
        config_file.close()

        app = TabPyApp(self.config_file.name)
        self.assertEqual(app.settings["port"], "bazbar")

    @patch("tabpy.tabpy_server.app.app.os.path.exists", return_value=True)
    @patch("tabpy.tabpy_server.app.app._get_state_from_file")
    @patch("tabpy.tabpy_server.app.app.TabPyState")
    def test_gzip_setting_on_valid(
        self, mock_state, mock_get_state_from_file, mock_path_exists
    ):
        self.assertTrue(self.config_file is not None)
        config_file = self.config_file
        config_file.write("[TabPy]\n" "TABPY_GZIP_ENABLE = true".encode())
        config_file.close()

        app = TabPyApp(self.config_file.name)
        self.assertEqual(app.settings["gzip_enabled"], True)

    @patch("tabpy.tabpy_server.app.app.os.path.exists", return_value=True)
    @patch("tabpy.tabpy_server.app.app._get_state_from_file")
    @patch("tabpy.tabpy_server.app.app.TabPyState")
    def test_gzip_setting_off_valid(
        self, mock_state, mock_get_state_from_file, mock_path_exists
    ):
        self.assertTrue(self.config_file is not None)
        config_file = self.config_file
        config_file.write("[TabPy]\n" "TABPY_GZIP_ENABLE = false".encode())
        config_file.close()

        app = TabPyApp(self.config_file.name)
        self.assertEqual(app.settings["gzip_enabled"], False)

    @patch("tabpy.tabpy_server.app.app.os.path.exists", return_value=True)
    @patch("tabpy.tabpy_server.app.app._get_state_from_file")
    @patch("tabpy.tabpy_server.app.app.TabPyState")
    def test_min_tls_setting_valid(
        self, mock_state, mock_get_state_from_file, mock_path_exists
    ):
        self.assertTrue(self.config_file is not None)
        config_file = self.config_file
        config_file.write("[TabPy]\n" "TABPY_MINIMUM_TLS_VERSION = TLSv1_3".encode())
        config_file.close()

        app = TabPyApp(self.config_file.name)
        self.assertEqual(app.settings["minimum_tls_version"], "TLSv1_3")

class TestTransferProtocolValidation(unittest.TestCase):
    def assertTabPyAppRaisesRuntimeError(self, expected_message):
        with self.assertRaises(RuntimeError) as err:
            TabPyApp(self.fp.name)
        self.assertEqual(err.exception.args[0], expected_message)

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

    def setUp(self):
        self.fp = NamedTemporaryFile(mode="w+t", delete=False)

    def tearDown(self):
        os.remove(self.fp.name)
        self.fp = None

    def test_invalid_protocol(self):
        self.fp.write("[TabPy]\n" "TABPY_TRANSFER_PROTOCOL = gopher")
        self.fp.close()

        self.assertTabPyAppRaisesRuntimeError("Unsupported transfer protocol: gopher")

    def test_http(self):
        self.fp.write("[TabPy]\n" "TABPY_TRANSFER_PROTOCOL = http")
        self.fp.close()

        app = TabPyApp(self.fp.name)
        self.assertEqual(app.settings["transfer_protocol"], "http")

    def test_https_without_cert_and_key(self):
        self.fp.write("[TabPy]\n" "TABPY_TRANSFER_PROTOCOL = https")
        self.fp.close()

        self.assertTabPyAppRaisesRuntimeError(
            "Error using HTTPS: The paramete"
            "r(s) TABPY_CERTIFICATE_FILE and"
            " TABPY_KEY_FILE must be set."
        )

    def test_https_without_cert(self):
        self.fp.write(
            "[TabPy]\n" "TABPY_TRANSFER_PROTOCOL = https\n" "TABPY_KEY_FILE = foo"
        )
        self.fp.close()

        self.assertTabPyAppRaisesRuntimeError(
            "Error using HTTPS: The parameter(s) TABPY_CERTIFICATE_FILE must " "be set."
        )

    def test_https_without_key(self):
        self.fp.write(
            "[TabPy]\n"
            "TABPY_TRANSFER_PROTOCOL = https\n"
            "TABPY_CERTIFICATE_FILE = foo"
        )
        self.fp.close()

        self.assertTabPyAppRaisesRuntimeError(
            "Error using HTTPS: The parameter(s) TABPY_KEY_FILE must be set."
        )

    @patch("tabpy.tabpy_server.app.app.os.path")
    def test_https_cert_and_key_file_not_found(self, mock_path):
        self.fp.write(
            "[TabPy]\n"
            "TABPY_TRANSFER_PROTOCOL = https\n"
            "TABPY_CERTIFICATE_FILE = foo\n"
            "TABPY_KEY_FILE = bar"
        )
        self.fp.close()

        mock_path.isfile.side_effect = lambda x: self.mock_isfile(x, {self.fp.name})

        self.assertTabPyAppRaisesRuntimeError(
            "Error using HTTPS: The parameter(s) TABPY_CERTIFICATE_FILE and "
            "TABPY_KEY_FILE must point to an existing file."
        )

    @patch("tabpy.tabpy_server.app.app.os.path")
    def test_https_cert_file_not_found(self, mock_path):
        self.fp.write(
            "[TabPy]\n"
            "TABPY_TRANSFER_PROTOCOL = https\n"
            "TABPY_CERTIFICATE_FILE = foo\n"
            "TABPY_KEY_FILE = bar"
        )
        self.fp.close()

        mock_path.isfile.side_effect = lambda x: self.mock_isfile(
            x, {self.fp.name, "bar"}
        )

        self.assertTabPyAppRaisesRuntimeError(
            "Error using HTTPS: The parameter(s) TABPY_CERTIFICATE_FILE "
            "must point to an existing file."
        )

    @patch("tabpy.tabpy_server.app.app.os.path")
    def test_https_key_file_not_found(self, mock_path):
        self.fp.write(
            "[TabPy]\n"
            "TABPY_TRANSFER_PROTOCOL = https\n"
            "TABPY_CERTIFICATE_FILE = foo\n"
            "TABPY_KEY_FILE = bar"
        )
        self.fp.close()

        mock_path.isfile.side_effect = lambda x: self.mock_isfile(
            x, {self.fp.name, "foo"}
        )

        self.assertTabPyAppRaisesRuntimeError(
            "Error using HTTPS: The parameter(s) TABPY_KEY_FILE "
            "must point to an existing file."
        )

    @patch("tabpy.tabpy_server.app.app.os.path.isfile", return_value=True)
    @patch("tabpy.tabpy_server.app.util.validate_cert")
    def test_https_success(self, mock_isfile, mock_validate_cert):
        self.fp.write(
            "[TabPy]\n"
            "TABPY_TRANSFER_PROTOCOL = HtTpS\n"
            "TABPY_CERTIFICATE_FILE = foo\n"
            "TABPY_KEY_FILE = bar"
        )
        self.fp.close()

        app = TabPyApp(self.fp.name)

        self.assertEqual(app.settings["transfer_protocol"], "https")
        self.assertEqual(app.settings["certificate_file"], "foo")
        self.assertEqual(app.settings["key_file"], "bar")


class TestCertificateValidation(unittest.TestCase):
    def assertValidateCertRaisesRuntimeError(self, expected_message, path):
        with self.assertRaises(RuntimeError) as err:
            validate_cert(path)
        self.assertEqual(err.exception.args[0], expected_message)

    def __init__(self, *args, **kwargs):
        super(TestCertificateValidation, self).__init__(*args, **kwargs)
        self.resources_path = os.path.join(os.path.dirname(__file__), "resources")

    def test_expired_cert(self):
        path = os.path.join(self.resources_path, "expired.crt")
        message = (
            "Error using HTTPS: The certificate provided expired "
            "on 2018-08-18 19:47:18."
        )
        self.assertValidateCertRaisesRuntimeError(message, path)

    def test_future_cert(self):
        path = os.path.join(self.resources_path, "future.crt")
        message = (
            "Error using HTTPS: The certificate provided is not valid "
            "until 3001-01-01 00:00:00."
        )
        self.assertValidateCertRaisesRuntimeError(message, path)

    def test_valid_cert(self):
        path = os.path.join(self.resources_path, "valid.crt")
        validate_cert(path)


class TestOAuthConfigValidation(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestOAuthConfigValidation, self).__init__(*args, **kwargs)
        self.fp = None

    def setUp(self):
        self.fp = NamedTemporaryFile(mode="w+t", delete=False)

    def tearDown(self):
        os.remove(self.fp.name)
        self.fp = None

    def test_oauth_disabled_by_default(self):
        self.fp.write("[TabPy]\n")
        self.fp.close()

        app = TabPyApp(self.fp.name)
        self.assertFalse(app.settings["oauth_enabled"])
        self.assertNotIn("authentication", app._get_features())

    @patch(
        "tabpy.tabpy_server.app.app.socket.getaddrinfo",
        return_value=PUBLIC_JWKS_ADDRINFO,
    )
    def test_oauth_enabled_with_all_required_settings_succeeds(self, mock_getaddrinfo):
        self.fp.write(
            "[TabPy]\n"
            "TABPY_OAUTH_ENABLED = true\n"
            "TABPY_OAUTH_ISSUER = https://idp.example.com/\n"
            "TABPY_OAUTH_JWKS_URI = https://idp.example.com/.well-known/jwks.json\n"
            "TABPY_OAUTH_AUDIENCE = tabpy\n"
        )
        self.fp.close()

        app = TabPyApp(self.fp.name)
        self.assertTrue(app.settings["oauth_enabled"])
        methods = app._get_features()["authentication"]["methods"]
        self.assertIn("oauth-jwt", methods)

    def test_oauth_enabled_missing_issuer_raises(self):
        self.fp.write(
            "[TabPy]\n"
            "TABPY_OAUTH_ENABLED = true\n"
            "TABPY_OAUTH_JWKS_URI = https://idp.example.com/.well-known/jwks.json\n"
            "TABPY_OAUTH_AUDIENCE = tabpy\n"
        )
        self.fp.close()

        with self.assertRaises(RuntimeError) as err:
            TabPyApp(self.fp.name)
        self.assertIn("TABPY_OAUTH_ISSUER", err.exception.args[0])

    def test_oauth_enabled_missing_jwks_uri_raises(self):
        self.fp.write(
            "[TabPy]\n"
            "TABPY_OAUTH_ENABLED = true\n"
            "TABPY_OAUTH_ISSUER = https://idp.example.com/\n"
            "TABPY_OAUTH_AUDIENCE = tabpy\n"
        )
        self.fp.close()

        with self.assertRaises(RuntimeError) as err:
            TabPyApp(self.fp.name)
        self.assertIn("TABPY_OAUTH_JWKS_URI", err.exception.args[0])

    def test_oauth_enabled_missing_audience_raises(self):
        self.fp.write(
            "[TabPy]\n"
            "TABPY_OAUTH_ENABLED = true\n"
            "TABPY_OAUTH_ISSUER = https://idp.example.com/\n"
            "TABPY_OAUTH_JWKS_URI = https://idp.example.com/.well-known/jwks.json\n"
        )
        self.fp.close()

        with self.assertRaises(RuntimeError) as err:
            TabPyApp(self.fp.name)
        self.assertIn("TABPY_OAUTH_AUDIENCE", err.exception.args[0])

    def test_oauth_enabled_with_http_jwks_uri_raises(self):
        self.fp.write(
            "[TabPy]\n"
            "TABPY_OAUTH_ENABLED = true\n"
            "TABPY_OAUTH_ISSUER = https://idp.example.com/\n"
            "TABPY_OAUTH_JWKS_URI = http://idp.example.com/.well-known/jwks.json\n"
            "TABPY_OAUTH_AUDIENCE = tabpy\n"
        )
        self.fp.close()

        with self.assertRaises(RuntimeError) as err:
            TabPyApp(self.fp.name)
        self.assertIn("TABPY_OAUTH_JWKS_URI", err.exception.args[0])

    def test_oauth_enabled_with_http_issuer_raises(self):
        self.fp.write(
            "[TabPy]\n"
            "TABPY_OAUTH_ENABLED = true\n"
            "TABPY_OAUTH_ISSUER = http://idp.example.com/\n"
            "TABPY_OAUTH_JWKS_URI = https://idp.example.com/.well-known/jwks.json\n"
            "TABPY_OAUTH_AUDIENCE = tabpy\n"
        )
        self.fp.close()

        with self.assertRaises(RuntimeError) as err:
            TabPyApp(self.fp.name)
        self.assertIn("TABPY_OAUTH_ISSUER", err.exception.args[0])

    @patch(
        "tabpy.tabpy_server.app.app.socket.getaddrinfo",
        return_value=PUBLIC_JWKS_ADDRINFO,
    )
    @patch('builtins.input')
    def test_oauth_only_does_not_trigger_no_auth_warning(
        self, mock_input, mock_getaddrinfo
    ):
        self.fp.write(
            "[TabPy]\n"
            "TABPY_OAUTH_ENABLED = true\n"
            "TABPY_OAUTH_ISSUER = https://idp.example.com/\n"
            "TABPY_OAUTH_JWKS_URI = https://idp.example.com/.well-known/jwks.json\n"
            "TABPY_OAUTH_AUDIENCE = tabpy\n"
        )
        self.fp.close()

        TabPyApp(self.fp.name)
        mock_input.assert_not_called()

    def test_oauth_enabled_with_jwks_uri_resolving_to_link_local_address_raises(self):
        """
        TabPy fetches TABPY_OAUTH_JWKS_URI over the network, so a JWKS URI
        that resolves to a link-local address (e.g. a cloud metadata
        endpoint) must be rejected at startup rather than allowed through
        as a server-side request forgery vector.
        """
        self.fp.write(
            "[TabPy]\n"
            "TABPY_OAUTH_ENABLED = true\n"
            "TABPY_OAUTH_ISSUER = https://idp.example.com/\n"
            "TABPY_OAUTH_JWKS_URI = https://idp.example.com/.well-known/jwks.json\n"
            "TABPY_OAUTH_AUDIENCE = tabpy\n"
        )
        self.fp.close()

        with patch(
            "tabpy.tabpy_server.app.app.socket.getaddrinfo",
            return_value=[
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("169.254.169.254", 443)),
            ],
        ):
            with self.assertRaises(RuntimeError) as err:
                TabPyApp(self.fp.name)
        self.assertIn("TABPY_OAUTH_JWKS_URI", err.exception.args[0])

    def test_oauth_enabled_with_unresolvable_jwks_uri_raises(self):
        self.fp.write(
            "[TabPy]\n"
            "TABPY_OAUTH_ENABLED = true\n"
            "TABPY_OAUTH_ISSUER = https://idp.example.com/\n"
            "TABPY_OAUTH_JWKS_URI = https://idp.example.com/.well-known/jwks.json\n"
            "TABPY_OAUTH_AUDIENCE = tabpy\n"
        )
        self.fp.close()

        with patch(
            "tabpy.tabpy_server.app.app.socket.getaddrinfo",
            side_effect=socket.gaierror("Name or service not known"),
        ):
            with self.assertRaises(RuntimeError) as err:
                TabPyApp(self.fp.name)
        self.assertIn("TABPY_OAUTH_JWKS_URI", err.exception.args[0])

    @patch(
        "tabpy.tabpy_server.app.app.socket.getaddrinfo",
        return_value=PUBLIC_JWKS_ADDRINFO,
    )
    def test_oauth_only_with_arrow_enabled_raises(self, mock_getaddrinfo):
        """
        Arrow Flight's auth middleware only supports basic auth (see
        TabPyApp._get_arrow_server), so OAuth-only + Arrow must be
        rejected at startup rather than crashing the Arrow thread with a
        KeyError looking for a password file that was never configured.
        """
        self.fp.write(
            "[TabPy]\n"
            "TABPY_ARROW_ENABLE = true\n"
            "TABPY_OAUTH_ENABLED = true\n"
            "TABPY_OAUTH_ISSUER = https://idp.example.com/\n"
            "TABPY_OAUTH_JWKS_URI = https://idp.example.com/.well-known/jwks.json\n"
            "TABPY_OAUTH_AUDIENCE = tabpy\n"
        )
        self.fp.close()

        with self.assertRaises(RuntimeError) as err:
            TabPyApp(self.fp.name)
        self.assertIn("TABPY_ARROW_ENABLE", err.exception.args[0])

    @patch(
        "tabpy.tabpy_server.app.app.socket.getaddrinfo",
        return_value=PUBLIC_JWKS_ADDRINFO,
    )
    def test_oauth_and_basic_auth_with_arrow_enabled_succeeds(self, mock_getaddrinfo):
        pwd_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "integration", "resources", "pwdfile.txt",
        )
        self.fp.write(
            "[TabPy]\n"
            f"TABPY_PWD_FILE = {pwd_file}\n"
            "TABPY_ARROW_ENABLE = true\n"
            "TABPY_OAUTH_ENABLED = true\n"
            "TABPY_OAUTH_ISSUER = https://idp.example.com/\n"
            "TABPY_OAUTH_JWKS_URI = https://idp.example.com/.well-known/jwks.json\n"
            "TABPY_OAUTH_AUDIENCE = tabpy\n"
        )
        self.fp.close()

        app = TabPyApp(self.fp.name)
        self.assertTrue(app.settings["oauth_enabled"])

    @patch(
        "tabpy.tabpy_server.app.app.socket.getaddrinfo",
        return_value=PUBLIC_JWKS_ADDRINFO,
    )
    def test_basic_auth_and_oauth_both_enabled_advertises_both_methods(
        self, mock_getaddrinfo
    ):
        pwd_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "integration", "resources", "pwdfile.txt",
        )
        self.fp.write(
            "[TabPy]\n"
            f"TABPY_PWD_FILE = {pwd_file}\n"
            "TABPY_OAUTH_ENABLED = true\n"
            "TABPY_OAUTH_ISSUER = https://idp.example.com/\n"
            "TABPY_OAUTH_JWKS_URI = https://idp.example.com/.well-known/jwks.json\n"
            "TABPY_OAUTH_AUDIENCE = tabpy\n"
        )
        self.fp.close()

        app = TabPyApp(self.fp.name)
        methods = app._get_features()["authentication"]["methods"]
        self.assertIn("basic-auth", methods)
        self.assertIn("oauth-jwt", methods)
