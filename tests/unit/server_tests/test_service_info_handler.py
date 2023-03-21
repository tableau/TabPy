import base64
import json
import os
from tabpy.tabpy_server.app.app import TabPyApp
from tabpy.tabpy_server.app.app_parameters import SettingsParameters
import tempfile
from tornado.testing import AsyncHTTPTestCase


def _create_expected_info_response(settings, tabpy_state):
    return {
        "description": tabpy_state.get_description(),
        "creation_time": tabpy_state.creation_time,
        "state_path": settings["state_file_path"],
        "server_version": settings[SettingsParameters.ServerVersion],
        "name": tabpy_state.name,
        "versions": settings["versions"]
    }


class BaseTestServiceInfoHandler(AsyncHTTPTestCase):
    def get_app(self):
        if hasattr(self, 'config_file') and hasattr(self.config_file, 'name'):
            self.app = TabPyApp(self.config_file.name)
        else:
            self.app = TabPyApp()
        return self.app._create_tornado_web_app()

    @classmethod
    def tearDownClass(cls):
        os.remove(cls.state_file.name)
        os.remove(cls.config_file.name)
        os.rmdir(cls.state_dir)

    @classmethod
    def setUpClass(cls):
        # create state.ini dir and file
        cls.state_dir = tempfile.mkdtemp(prefix=cls.prefix)
        with open(os.path.join(cls.state_dir, "state.ini"), "w+") as cls.state_file:
            cls.state_file.write(
                "[Service Info]\n"
                "Name = TabPy Serve\n"
                "Description = \n"
                "Creation Time = 0\n"
                "Access-Control-Allow-Origin = \n"
                "Access-Control-Allow-Headers = \n"
                "Access-Control-Allow-Methods = \n"
                "\n"
                "[Query Objects Service Versions]\n"
                "\n"
                "[Query Objects Docstrings]\n"
                "\n"
                "[Meta]\n"
                "Revision Number = 1\n"
            )
        cls.state_file.close()

        # create config file
        cls.config_file = tempfile.NamedTemporaryFile(
            prefix=cls.prefix, suffix=".conf", delete=False, mode='w'
        )
        cls.config_file.write("[TabPy]\n")
        if hasattr(cls, 'tabpy_config'):
            for k in cls.tabpy_config:
                cls.config_file.write(k)
        cls.config_file.close()


class TestServiceInfoHandlerWithAuth(BaseTestServiceInfoHandler):
    @classmethod
    def setUpClass(cls):
        cls.prefix = "__TestServiceInfoHandlerWithAuth_"
        cls.tabpy_config = ["TABPY_PWD_FILE = ./tests/integration/resources/pwdfile.txt\n"]
        super(TestServiceInfoHandlerWithAuth, cls).setUpClass()

    def test_given_server_with_auth_expect_error_info_response(self):
        response = self.fetch("/info")
        self.assertEqual(response.code, 401)

    def test_given_server_with_auth_expect_correct_info_response(self):
        header = {
            "Content-Type": "application/json",
            "TabPy-Client": "Integration test for deploying models with auth",
            "Authorization": "Basic " +
            base64.b64encode("user1:P@ssw0rd".encode("utf-8")).decode("utf-8"),
        }

        response = self.fetch("/info", headers=header)
        self.assertEqual(response.code, 200)
        actual_response = json.loads(response.body)
        expected_response = _create_expected_info_response(
            self.app.settings, self.app.tabpy_state
        )

        self.assertDictEqual(actual_response, expected_response)
        self.assertTrue("versions" in actual_response)
        versions = actual_response["versions"]
        self.assertTrue("v1" in versions)
        v1 = versions["v1"]
        self.assertTrue("features" in v1)
        features = v1["features"]
        self.assertDictEqual(
            {"authentication": {"methods": {"basic-auth": {}}, "required": True},
                'evaluate_enabled': True, 'gzip_enabled': True},
                features,
        )


class TestServiceInfoHandlerWithoutAuth(BaseTestServiceInfoHandler):
    @classmethod
    def setUpClass(cls):
        cls.prefix = "__TestServiceInfoHandlerWithoutAuth_"
        super(TestServiceInfoHandlerWithoutAuth, cls).setUpClass()

    def test_server_with_no_auth_expect_correct_info_response(self):
        response = self.fetch("/info")
        self.assertEqual(response.code, 200)
        actual_response = json.loads(response.body)
        expected_response = _create_expected_info_response(
            self.app.settings, self.app.tabpy_state
        )

        self.assertDictEqual(actual_response, expected_response)
        self.assertTrue("versions" in actual_response)
        versions = actual_response["versions"]
        self.assertTrue("v1" in versions)
        v1 = versions["v1"]
        self.assertTrue("features" in v1)
        features = v1["features"]
        self.assertDictEqual({'evaluate_enabled': True, 'gzip_enabled': True}, features)

    def test_given_server_with_no_auth_and_password_expect_correct_info_response(self):
        header = {
            "Content-Type": "application/json",
            "TabPy-Client": "Integration test for deploying models with auth",
            "Authorization": "Basic " +
            base64.b64encode("user1:P@ssw0rd".encode("utf-8")).decode("utf-8"),
        }

        response = self.fetch("/info", headers=header)
        self.assertEqual(response.code, 406)
