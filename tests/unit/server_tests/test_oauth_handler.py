import base64
import datetime
import json
import os
import socket
import tempfile
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric import rsa
from tornado.testing import AsyncHTTPTestCase

from tabpy.tabpy_server.app.app import TabPyApp
from tests.unit.server_tests.jwt_test_helpers import (
    AUDIENCE,
    ISSUER,
    JWKS_URI,
    make_token,
    patched_jwks_client,
    reset_jwks_state,
)

# The fake "idp.example.com" JWKS host used by these tests doesn't
# resolve. TabPyApp resolves the JWKS host at startup to guard against
# SSRF, so tests need a fake public resolution result in place of a real
# DNS lookup.
_PUBLIC_JWKS_ADDRINFO = [
    (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443)),
]


class BaseTestOAuthHandler(AsyncHTTPTestCase):
    def setUp(self):
        # Each class generates a different signing key but intentionally
        # reuses the same fake JWKS URI. Do not leak a cached key between
        # otherwise-independent HTTP auth tests.
        reset_jwks_state()
        super().setUp()

    def get_app(self):
        with patch(
            "tabpy.tabpy_server.app.app.socket.getaddrinfo",
            return_value=_PUBLIC_JWKS_ADDRINFO,
        ):
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

    def test_401_response_body_is_uniform_across_jwt_failure_reasons(self):
        """
        The specific reason a JWT was rejected (expired, wrong issuer,
        wrong audience, unresolvable signing key, etc.) must never appear
        in the response body -- that would let an unauthenticated caller
        enumerate why a token failed. Every failure reason must produce
        the exact same generic body.
        """
        past = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)
        expired_token = self._make_token(
            {"iat": past - datetime.timedelta(minutes=5), "exp": past}
        )
        wrong_issuer_token = self._make_token({"iss": "https://wrong-idp.example.com/"})
        wrong_audience_token = self._make_token({"aud": "wrong-audience"})

        bodies = []
        for token in (expired_token, wrong_issuer_token, wrong_audience_token):
            headers = {"Authorization": f"Bearer {token}"}
            with self._patched_jwks_client():
                response = self.fetch("/info", headers=headers)
            self.assertEqual(response.code, 401)
            bodies.append(response.body)

        missing_token_response = self.fetch("/info")
        self.assertEqual(missing_token_response.code, 401)
        bodies.append(missing_token_response.body)

        self.assertEqual(len(set(bodies)), 1)

    def test_info_advertises_oauth_jwt_method(self):
        token = self._make_token()
        headers = {"Authorization": f"Bearer {token}"}
        with self._patched_jwks_client():
            response = self.fetch("/info", headers=headers)
        body = json.loads(response.body)
        features = body["versions"]["v1"]["features"]
        oauth = features["authentication"]["methods"]["oauth-jwt"]
        self.assertEqual(oauth["scopes"], ["tabpy:query", "tabpy:evaluate", "tabpy:deploy"])
        self.assertFalse(oauth["endpoint_scopes_enforced"])

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


_EVALUATE_SCRIPT = (
    '{"data":{"_arg1":[2,3],"_arg2":[3,-1]},'
    '"script":"res=[]\\nfor i in range(len(_arg1)):\\n  '
    'res.append(_arg1[i] * _arg2[i])\\nreturn res"}'
)


class TestEndpointScopesDefaultOff(BaseTestOAuthHandler):
    @classmethod
    def setUpClass(cls):
        cls.prefix = "__TestEndpointScopesDefaultOff_"
        cls.tabpy_config = [
            "TABPY_OAUTH_ENABLED = true\n",
            f"TABPY_OAUTH_ISSUER = {ISSUER}\n",
            f"TABPY_OAUTH_JWKS_URI = {JWKS_URI}\n",
            f"TABPY_OAUTH_AUDIENCE = {AUDIENCE}\n",
        ]
        super().setUpClass()

    def test_query_without_scope_claim_is_not_forbidden(self):
        token = self._make_token()
        headers = {"Authorization": f"Bearer {token}"}
        with self._patched_jwks_client():
            response = self.fetch("/query/missing", headers=headers)
        self.assertNotEqual(response.code, 403)
        self.assertNotEqual(response.code, 401)

    def test_evaluate_without_scope_claim_is_accepted(self):
        token = self._make_token()
        headers = {"Authorization": f"Bearer {token}"}
        with self._patched_jwks_client():
            response = self.fetch(
                "/evaluate", method="POST", body=_EVALUATE_SCRIPT, headers=headers
            )
        self.assertEqual(response.code, 200)


class TestEndpointScopesEnforced(BaseTestOAuthHandler):
    @classmethod
    def setUpClass(cls):
        cls.prefix = "__TestEndpointScopesEnforced_"
        cls.tabpy_config = [
            "TABPY_OAUTH_ENABLED = true\n",
            f"TABPY_OAUTH_ISSUER = {ISSUER}\n",
            f"TABPY_OAUTH_JWKS_URI = {JWKS_URI}\n",
            f"TABPY_OAUTH_AUDIENCE = {AUDIENCE}\n",
            "TABPY_OAUTH_ENFORCE_ENDPOINT_SCOPES = true\n",
        ]
        super().setUpClass()

    def _bearer(self, claims_override=None):
        token = self._make_token(claims_override)
        return {"Authorization": f"Bearer {token}"}

    def test_query_without_tabpy_query_returns_403(self):
        headers = self._bearer({"scope": "tabpy:evaluate"})
        with self._patched_jwks_client():
            response = self.fetch(
                "/query/missing", method="POST", body="{}", headers=headers
            )
        self.assertEqual(response.code, 403)
        self.assertIn(
            'error="insufficient_scope"', response.headers.get("WWW-Authenticate", "")
        )

    def test_query_with_tabpy_query_is_authorized(self):
        headers = self._bearer({"scope": "tabpy:query"})
        with self._patched_jwks_client():
            response = self.fetch(
                "/query/missing", method="POST", body="{}", headers=headers
            )
        self.assertNotEqual(response.code, 401)
        self.assertNotEqual(response.code, 403)

    def test_evaluate_without_tabpy_evaluate_returns_403(self):
        headers = self._bearer({"scope": "tabpy:query"})
        with self._patched_jwks_client():
            response = self.fetch(
                "/evaluate", method="POST", body=_EVALUATE_SCRIPT, headers=headers
            )
        self.assertEqual(response.code, 403)
        self.assertIn(
            'error="insufficient_scope"', response.headers.get("WWW-Authenticate", "")
        )

    def test_evaluate_with_tabpy_evaluate_is_accepted(self):
        headers = self._bearer({"scope": "tabpy:evaluate"})
        with self._patched_jwks_client():
            response = self.fetch(
                "/evaluate", method="POST", body=_EVALUATE_SCRIPT, headers=headers
            )
        self.assertEqual(response.code, 200)

    def test_get_endpoints_is_not_gated(self):
        headers = self._bearer()
        with self._patched_jwks_client():
            info = self.fetch("/info", headers=headers)
            status = self.fetch("/status", headers=headers)
            endpoints = self.fetch("/endpoints", headers=headers)
        self.assertEqual(info.code, 200)
        self.assertEqual(status.code, 200)
        self.assertEqual(endpoints.code, 200)
        oauth = json.loads(info.body)["versions"]["v1"]["features"][
            "authentication"
        ]["methods"]["oauth-jwt"]
        self.assertTrue(oauth["endpoint_scopes_enforced"])
        self.assertEqual(
            oauth["scopes"], ["tabpy:query", "tabpy:evaluate", "tabpy:deploy"]
        )

    def _assert_management_forbidden(self, headers, method, url, **kwargs):
        with self._patched_jwks_client():
            response = self.fetch(url, method=method, headers=headers, **kwargs)
        self.assertEqual(response.code, 403)
        self.assertIn(
            'error="insufficient_scope"', response.headers.get("WWW-Authenticate", "")
        )

    def test_query_only_token_cannot_mutate_endpoints(self):
        headers = self._bearer({"scope": "tabpy:query"})
        self._assert_management_forbidden(
            headers, "POST", "/endpoints", body="{}"
        )
        self._assert_management_forbidden(
            headers, "PUT", "/endpoints/production-model", body="{}"
        )
        self._assert_management_forbidden(
            headers,
            "DELETE",
            "/endpoints/production-model",
            allow_nonstandard_methods=True,
        )
        self._assert_management_forbidden(
            headers, "GET", "/configurations/endpoint_upload_destination"
        )

    def test_evaluate_only_token_cannot_mutate_endpoints(self):
        headers = self._bearer({"scope": "tabpy:evaluate"})
        self._assert_management_forbidden(
            headers, "POST", "/endpoints", body="{}"
        )
        self._assert_management_forbidden(
            headers, "DELETE", "/endpoints/production-model",
            allow_nonstandard_methods=True,
        )

    def test_scopeless_token_cannot_mutate_endpoints(self):
        headers = self._bearer()
        self._assert_management_forbidden(
            headers, "POST", "/endpoints", body="{}"
        )
        self._assert_management_forbidden(
            headers, "PUT", "/endpoints/production-model", body="{}"
        )
        self._assert_management_forbidden(
            headers,
            "DELETE",
            "/endpoints/production-model",
            allow_nonstandard_methods=True,
        )

    def test_deploy_scope_is_authorized_for_management(self):
        headers = self._bearer({"scope": "tabpy:deploy"})
        with self._patched_jwks_client():
            upload = self.fetch(
                "/configurations/endpoint_upload_destination", headers=headers
            )
            create = self.fetch("/endpoints", method="POST", body="{}", headers=headers)
            delete = self.fetch(
                "/endpoints/production-model",
                method="DELETE",
                headers=headers,
                allow_nonstandard_methods=True,
            )
        self.assertEqual(upload.code, 200)
        self.assertNotEqual(create.code, 401)
        self.assertNotEqual(create.code, 403)
        self.assertNotEqual(delete.code, 401)
        self.assertNotEqual(delete.code, 403)

    def test_evaluate_only_token_fails_inner_query(self):
        """RestrictedTabPy forwards the original JWT to nested /query."""
        headers = self._bearer({"scope": "tabpy:evaluate"})
        with self._patched_jwks_client():
            response = self.fetch(
                "/query/missing", method="POST", body="{}", headers=headers
            )
        self.assertEqual(response.code, 403)

    def test_query_options_does_not_require_endpoint_scope(self):
        headers = self._bearer({"scope": "tabpy:evaluate"})
        with self._patched_jwks_client():
            response = self.fetch(
                "/query/missing",
                method="OPTIONS",
                headers=headers,
                allow_nonstandard_methods=True,
            )
        self.assertNotEqual(response.code, 403)


class TestEndpointScopesWithGlobalRequired(BaseTestOAuthHandler):
    @classmethod
    def setUpClass(cls):
        cls.prefix = "__TestEndpointScopesWithGlobalRequired_"
        cls.tabpy_config = [
            "TABPY_OAUTH_ENABLED = true\n",
            f"TABPY_OAUTH_ISSUER = {ISSUER}\n",
            f"TABPY_OAUTH_JWKS_URI = {JWKS_URI}\n",
            f"TABPY_OAUTH_AUDIENCE = {AUDIENCE}\n",
            "TABPY_OAUTH_REQUIRED_SCOPES = tabpy\n",
            "TABPY_OAUTH_ENFORCE_ENDPOINT_SCOPES = true\n",
        ]
        super().setUpClass()

    def test_missing_global_scope_is_401_on_info(self):
        token = self._make_token({"scope": "tabpy:query"})
        headers = {"Authorization": f"Bearer {token}"}
        with self._patched_jwks_client():
            response = self.fetch("/info", headers=headers)
        self.assertEqual(response.code, 401)

    def test_global_scope_without_query_scope_forbids_query_only(self):
        token = self._make_token({"scope": "tabpy"})
        headers = {"Authorization": f"Bearer {token}"}
        with self._patched_jwks_client():
            info = self.fetch("/info", headers=headers)
            query = self.fetch(
                "/query/missing", method="POST", body="{}", headers=headers
            )
        self.assertEqual(info.code, 200)
        self.assertEqual(query.code, 403)


class TestEndpointScopesBasicAuthUnaffected(BaseTestOAuthHandler):
    @classmethod
    def setUpClass(cls):
        cls.prefix = "__TestEndpointScopesBasicAuthUnaffected_"
        cls.tabpy_config = [
            "TABPY_PWD_FILE = ./tests/integration/resources/pwdfile.txt\n",
            "TABPY_OAUTH_ENABLED = true\n",
            f"TABPY_OAUTH_ISSUER = {ISSUER}\n",
            f"TABPY_OAUTH_JWKS_URI = {JWKS_URI}\n",
            f"TABPY_OAUTH_AUDIENCE = {AUDIENCE}\n",
            "TABPY_OAUTH_ENFORCE_ENDPOINT_SCOPES = true\n",
        ]
        super().setUpClass()

    def test_basic_auth_evaluate_still_works(self):
        headers = {
            "Authorization": "Basic "
            + base64.b64encode(b"user1:P@ssw0rd").decode("utf-8"),
        }
        response = self.fetch(
            "/evaluate", method="POST", body=_EVALUATE_SCRIPT, headers=headers
        )
        self.assertEqual(response.code, 200)

    def test_basic_auth_query_is_not_forbidden(self):
        headers = {
            "Authorization": "Basic "
            + base64.b64encode(b"user1:P@ssw0rd").decode("utf-8"),
        }
        response = self.fetch(
            "/query/missing", method="POST", body="{}", headers=headers
        )
        self.assertNotEqual(response.code, 403)
        self.assertNotEqual(response.code, 401)


if __name__ == "__main__":
    unittest.main()
