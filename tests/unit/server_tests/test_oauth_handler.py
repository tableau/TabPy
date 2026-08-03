import base64
import datetime
import json
import os
import tempfile
import unittest

from cryptography.hazmat.primitives.asymmetric import rsa
from tornado.testing import AsyncHTTPTestCase

from tabpy.tabpy_server.app.app import TabPyApp
from tests.unit.server_tests.jwt_test_helpers import (
    AUDIENCE,
    ISSUER,
    JWKS_URI,
    make_token,
    patched_jwks_client,
)


class BaseTestOAuthHandler(AsyncHTTPTestCase):
    def get_app(self):
        self.app = TabPyApp(self.config_file.name)
        return self.app._create_tornado_web_app()

    @classmethod
    def tearDownClass(cls):
        os.remove(cls.state_file.name)
        os.remove(cls.config_file.name)
        os.rmdir(cls.state_dir)

    @classmethod
    def setUpClass(cls):
        cls.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

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

        cls.config_file = tempfile.NamedTemporaryFile(
            prefix=cls.prefix, suffix=".conf", delete=False, mode="w"
        )
        cls.config_file.write("[TabPy]\n")
        for line in cls.tabpy_config:
            cls.config_file.write(line)
        cls.config_file.close()

    def _make_token(self, claims_override=None):
        return make_token(self.private_key, claims_override=claims_override)

    def _patched_jwks_client(self):
        return patched_jwks_client(self.private_key)


class TestOAuthOnlyHandler(BaseTestOAuthHandler):
    @classmethod
    def setUpClass(cls):
        cls.prefix = "__TestOAuthOnlyHandler_"
        cls.tabpy_config = [
            "TABPY_OAUTH_ENABLED = true\n",
            f"TABPY_OAUTH_ISSUER = {ISSUER}\n",
            f"TABPY_OAUTH_JWKS_URI = {JWKS_URI}\n",
            f"TABPY_OAUTH_AUDIENCE = {AUDIENCE}\n",
        ]
        super().setUpClass()

    def test_missing_token_returns_401(self):
        response = self.fetch("/info")
        self.assertEqual(response.code, 401)

    def test_valid_jwt_is_accepted(self):
        token = self._make_token()
        headers = {"Authorization": f"Bearer {token}"}
        with self._patched_jwks_client():
            response = self.fetch("/info", headers=headers)
        self.assertEqual(response.code, 200)

    def test_expired_jwt_returns_401(self):
        past = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)
        token = self._make_token({"iat": past - datetime.timedelta(minutes=5), "exp": past})
        headers = {"Authorization": f"Bearer {token}"}
        with self._patched_jwks_client():
            response = self.fetch("/info", headers=headers)
        self.assertEqual(response.code, 401)

    def test_info_advertises_oauth_jwt_method(self):
        token = self._make_token()
        headers = {"Authorization": f"Bearer {token}"}
        with self._patched_jwks_client():
            response = self.fetch("/info", headers=headers)
        body = json.loads(response.body)
        features = body["versions"]["v1"]["features"]
        self.assertIn("oauth-jwt", features["authentication"]["methods"])

    def test_malformed_bearer_header_is_rejected_without_logging_the_token(self):
        """
        A Bearer header that fails to parse into the expected two-part
        "Bearer <token>" form (e.g. extra whitespace) still carries a
        credential-bearing value. It must never be logged in full.
        """
        token = self._make_token()
        headers = {"Authorization": f"Bearer  {token}"}
        with self.assertLogs(
            "tabpy.tabpy_server.handlers.base_handler", level="ERROR"
        ) as log_ctx:
            response = self.fetch("/info", headers=headers)
        self.assertEqual(response.code, 401)
        logged_text = " ".join(log_ctx.output)
        self.assertNotIn(token, logged_text)


class TestOAuthAndBasicAuthCoexist(BaseTestOAuthHandler):
    @classmethod
    def setUpClass(cls):
        cls.prefix = "__TestOAuthAndBasicAuthCoexist_"
        cls.tabpy_config = [
            "TABPY_PWD_FILE = ./tests/integration/resources/pwdfile.txt\n",
            "TABPY_OAUTH_ENABLED = true\n",
            f"TABPY_OAUTH_ISSUER = {ISSUER}\n",
            f"TABPY_OAUTH_JWKS_URI = {JWKS_URI}\n",
            f"TABPY_OAUTH_AUDIENCE = {AUDIENCE}\n",
        ]
        super().setUpClass()

    def test_basic_auth_still_works_when_oauth_also_enabled(self):
        headers = {
            "Authorization": "Basic "
            + base64.b64encode(b"user1:P@ssw0rd").decode("utf-8"),
        }
        response = self.fetch("/info", headers=headers)
        self.assertEqual(response.code, 200)

    def test_bearer_token_also_works_when_basic_auth_also_enabled(self):
        token = self._make_token()
        headers = {"Authorization": f"Bearer {token}"}
        with self._patched_jwks_client():
            response = self.fetch("/info", headers=headers)
        self.assertEqual(response.code, 200)

    def test_invalid_basic_auth_credentials_still_rejected(self):
        headers = {
            "Authorization": "Basic "
            + base64.b64encode(b"user1:wrong_password").decode("utf-8"),
        }
        response = self.fetch("/info", headers=headers)
        self.assertEqual(response.code, 401)


class TestOAuthLogUserEnabled(BaseTestOAuthHandler):
    @classmethod
    def setUpClass(cls):
        cls.prefix = "__TestOAuthLogUserEnabled_"
        cls.tabpy_config = [
            "TABPY_OAUTH_ENABLED = true\n",
            f"TABPY_OAUTH_ISSUER = {ISSUER}\n",
            f"TABPY_OAUTH_JWKS_URI = {JWKS_URI}\n",
            f"TABPY_OAUTH_AUDIENCE = {AUDIENCE}\n",
            "TABPY_OAUTH_LOG_USER = true\n",
            "TABPY_LOG_DETAILS = true\n",
        ]
        super().setUpClass()

    def test_subject_is_logged_in_request_context_line(self):
        """
        Regression test: the request-context line is built once per
        request the first time something is logged, which (before a fix)
        happened before auth had resolved -- so the subject was always
        missing from it despite TABPY_OAUTH_LOG_USER being enabled.
        """
        token = self._make_token({"sub": "user1"})
        headers = {"Authorization": f"Bearer {token}"}
        with self._patched_jwks_client():
            with self.assertLogs(
                "tabpy.tabpy_server.handlers.base_handler", level="INFO"
            ) as log_ctx:
                response = self.fetch("/info", headers=headers)
        self.assertEqual(response.code, 200)
        logged_text = " ".join(log_ctx.output)
        self.assertIn("TabPy user: user1", logged_text)


class TestOAuthLogUserDisabled(BaseTestOAuthHandler):
    @classmethod
    def setUpClass(cls):
        cls.prefix = "__TestOAuthLogUserDisabled_"
        cls.tabpy_config = [
            "TABPY_OAUTH_ENABLED = true\n",
            f"TABPY_OAUTH_ISSUER = {ISSUER}\n",
            f"TABPY_OAUTH_JWKS_URI = {JWKS_URI}\n",
            f"TABPY_OAUTH_AUDIENCE = {AUDIENCE}\n",
            "TABPY_OAUTH_LOG_USER = false\n",
            "TABPY_LOG_DETAILS = true\n",
        ]
        super().setUpClass()

    def test_subject_is_not_logged_when_oauth_log_user_disabled(self):
        token = self._make_token({"sub": "should-not-be-logged"})
        headers = {"Authorization": f"Bearer {token}"}
        with self._patched_jwks_client():
            with self.assertLogs(
                "tabpy.tabpy_server.handlers.base_handler", level="INFO"
            ) as log_ctx:
                response = self.fetch("/info", headers=headers)
        self.assertEqual(response.code, 200)
        logged_text = " ".join(log_ctx.output)
        self.assertNotIn("should-not-be-logged", logged_text)


class TestOAuthLogUserDefault(BaseTestOAuthHandler):
    @classmethod
    def setUpClass(cls):
        cls.prefix = "__TestOAuthLogUserDefault_"
        cls.tabpy_config = [
            "TABPY_OAUTH_ENABLED = true\n",
            f"TABPY_OAUTH_ISSUER = {ISSUER}\n",
            f"TABPY_OAUTH_JWKS_URI = {JWKS_URI}\n",
            f"TABPY_OAUTH_AUDIENCE = {AUDIENCE}\n",
            "TABPY_LOG_DETAILS = true\n",
        ]
        super().setUpClass()

    def test_subject_is_not_logged_by_default(self):
        """
        TABPY_OAUTH_LOG_USER defaults to disabled: the `sub` claim is
        often a user's email or SSO ID, so it must not be written to logs
        unless an operator explicitly opts in.
        """
        token = self._make_token({"sub": "should-not-be-logged"})
        headers = {"Authorization": f"Bearer {token}"}
        with self._patched_jwks_client():
            with self.assertLogs(
                "tabpy.tabpy_server.handlers.base_handler", level="INFO"
            ) as log_ctx:
                response = self.fetch("/info", headers=headers)
        self.assertEqual(response.code, 200)
        logged_text = " ".join(log_ctx.output)
        self.assertNotIn("should-not-be-logged", logged_text)


if __name__ == "__main__":
    unittest.main()
