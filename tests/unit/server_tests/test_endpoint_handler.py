import base64
import os
import sys
import tempfile

from tabpy.tabpy_server.app.app import TabPyApp
from tabpy.tabpy_server.app.app import _init_asyncio_patch
from tabpy.tabpy_server.handlers.util import hash_password
from tornado.testing import AsyncHTTPTestCase


class TestEndpointHandlerWithAuth(AsyncHTTPTestCase):
    @classmethod
    def setUpClass(cls):
        _init_asyncio_patch()
        prefix = "__TestEndpointHandlerWithAuth_"
        # create password file
        cls.pwd_file = tempfile.NamedTemporaryFile(
            mode="w+t", prefix=prefix, suffix=".txt", delete=False
        )
        username = "username"
        password = "password"
        cls.pwd_file.write(f"{username} {hash_password(username, password)}")
        cls.pwd_file.close()

        # create state.ini dir and file
        cls.state_dir = tempfile.mkdtemp(prefix=prefix)
        cls.state_file = open(os.path.join(cls.state_dir, "state.ini"), "w+")
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
            mode="w+t", prefix=prefix, suffix=".conf", delete=False
        )
        cls.config_file.write(
            "[TabPy]\n"
            f"TABPY_PWD_FILE = {cls.pwd_file.name}\n"
            f"TABPY_STATE_PATH = {cls.state_dir}"
        )
        cls.config_file.close()

    @classmethod
    def tearDownClass(cls):
        os.remove(cls.pwd_file.name)
        os.remove(cls.state_file.name)
        os.remove(cls.config_file.name)
        os.rmdir(cls.state_dir)

    def get_app(self):
        self.app = TabPyApp(self.config_file.name)
        return self.app._create_tornado_web_app()

    def test_no_creds_required_auth_fails(self):
        response = self.fetch("/endpoints/anything")
        self.assertEqual(401, response.code)

    def test_invalid_creds_fails(self):
        response = self.fetch(
            "/endpoints/anything",
            method="GET",
            headers={
                "Authorization": "Basic {}".format(
                    base64.b64encode("user:wrong_password".encode("utf-8")).decode(
                        "utf-8"
                    )
                )
            },
        )
        self.assertEqual(401, response.code)

    def test_valid_creds_pass(self):
        response = self.fetch(
            "/endpoints/",
            method="GET",
            headers={
                "Authorization": "Basic {}".format(
                    base64.b64encode("username:password".encode("utf-8")).decode(
                        "utf-8"
                    )
                )
            },
        )
        self.assertEqual(200, response.code)

    def test_valid_creds_unknown_endpoint_fails(self):
        response = self.fetch(
            "/endpoints/unknown_endpoint",
            method="GET",
            headers={
                "Authorization": "Basic {}".format(
                    base64.b64encode("username:password".encode("utf-8")).decode(
                        "utf-8"
                    )
                )
            },
        )
        self.assertEqual(404, response.code)


class TestEndpointHandlerWithoutAuth(AsyncHTTPTestCase):
    @classmethod
    def setUpClass(cls):
        _init_asyncio_patch()
        prefix = "__TestEndpointHandlerWithoutAuth_"

        # create state.ini dir and file
        cls.state_dir = tempfile.mkdtemp(prefix=prefix)
        cls.state_file = open(os.path.join(cls.state_dir, "state.ini"), "w+")
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

    @classmethod
    def tearDownClass(cls):
        os.remove(cls.state_file.name)
        os.rmdir(cls.state_dir)

    def get_app(self):
        self.app = TabPyApp(None)
        return self.app._create_tornado_web_app()

    def test_creds_no_auth_fails(self):
        response = self.fetch(
            "/endpoints/",
            method="GET",
            headers={
                "Authorization": "Basic {}".format(
                    base64.b64encode("username:password".encode("utf-8")).decode(
                        "utf-8"
                    )
                )
            },
        )
        self.assertEqual(400, response.code)
