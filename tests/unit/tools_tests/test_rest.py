import json
import requests
from requests.auth import HTTPBasicAuth
from tabpy.tabpy_tools.rest import RequestsNetworkWrapper, ServiceClient
import unittest
from unittest.mock import Mock


class TestRequestsNetworkWrapper(unittest.TestCase):
    def test_init(self):
        RequestsNetworkWrapper()

    def test_init_with_session(self):
        session = {}

        rnw = RequestsNetworkWrapper(session=session)

        self.assertIs(session, rnw.session)

    def mock_response(self, status_code):
        response = Mock(requests.Response)
        response.json.return_value = "json"
        response.status_code = status_code

        return response

    def setUp(self):
        session = Mock(requests.Session)
        session.get.return_value = self.mock_response(200)
        session.post.return_value = self.mock_response(200)
        session.put.return_value = self.mock_response(200)
        session.delete.return_value = self.mock_response(204)

        self.rnw = RequestsNetworkWrapper(session=session)

    def test_GET(self):
        url = "abc"
        data = {"foo": "bar"}
        self.assertEqual(self.rnw.GET(url, data), "json")
        self.rnw.session.get.assert_called_once_with(
            url, params=data, timeout=None, auth=None
        )

    def test_GET_InvalidData(self):
        url = "abc"
        data = {"cat"}
        with self.assertRaises(TypeError):
            self.rnw.session.get.return_value = self.mock_response(404)
            self.rnw.GET(url, data)

    def test_GET_InvalidURL(self):
        url = ""
        data = {"foo": "bar"}
        with self.assertRaises(TypeError):
            self.rnw.session.get.return_value = self.mock_response(404)
            self.rnw.GET(url, data)

    def test_POST(self):
        url = "abc"
        data = {"foo": "bar"}
        self.assertEqual(self.rnw.POST(url, data), "json")
        self.rnw.session.post.assert_called_once_with(
            url,
            data=json.dumps(data),
            headers={"content-type": "application/json"},
            timeout=None,
            auth=None,
        )

    def test_POST_InvalidURL(self):
        url = ""
        data = {"foo": "bar"}
        with self.assertRaises(TypeError):
            self.rnw.session.post.return_value = self.mock_response(404)
            self.rnw.POST(url, data)

    def test_POST_InvalidData(self):
        url = "url"
        data = {"cat"}
        with self.assertRaises(TypeError):
            self.rnw.POST(url, data)

    def test_PUT(self):
        url = "abc"
        data = {"foo": "bar"}
        self.assertEqual(self.rnw.PUT(url, data), "json")
        self.rnw.session.put.assert_called_once_with(
            url,
            data=json.dumps(data),
            headers={"content-type": "application/json"},
            timeout=None,
            auth=None,
        )

    def test_PUT_InvalidData(self):
        url = "url"
        data = {"cat"}
        with self.assertRaises(TypeError):
            self.rnw.PUT(url, data)

    def test_PUT_InvalidURL(self):
        url = ""
        data = {"foo:bar"}
        with self.assertRaises(TypeError):
            self.rnw.PUT(url, data)

    def test_DELETE(self):
        url = "abc"
        data = {"foo": "bar"}
        self.assertIs(self.rnw.DELETE(url, data), None)
        self.rnw.session.delete.assert_called_once_with(
            url, data=json.dumps(data), timeout=None, auth=None
        )

    def test_DELETE_InvalidData(self):
        url = "abc"
        data = {"cat"}
        with self.assertRaises(TypeError):
            self.rnw.DELETE(url, data)

    def test_DELETE_InvalidURL(self):
        url = ""
        data = {"foo:bar"}
        with self.assertRaises(TypeError):
            self.rnw.DELETE(url, data)

    def test_set_credentials(self):
        expected_auth = None
        self.assertEqual(self.rnw.auth, expected_auth)

        username, password = "username", "password"
        expected_auth = HTTPBasicAuth(username, password)
        self.rnw.set_credentials(username, password)
        self.assertEqual(self.rnw.auth, expected_auth)

    def _test_METHOD_with_credentials(
        self,
        http_method_function,
        http_session_method_function,
        headers=None,
        params=False,
        data=False,
        response=None,
    ):
        username, password = "username", "password"
        self.rnw.set_credentials(username, password)

        url = "url"
        _data = {"foo": "bar"}

        self.assertEqual(http_method_function(url, _data), response)

        pargs = {url}
        kwargs = {"timeout": None, "auth": self.rnw.auth}
        if data:
            kwargs["data"] = json.dumps(_data)
        if headers:
            kwargs["headers"] = headers
        if params:
            kwargs["params"] = _data

        http_session_method_function.assert_called_once_with(*pargs, **kwargs)
        self.assertEqual(self.rnw.auth, HTTPBasicAuth(username, password))

    def test_GET_with_credentials(self):
        self._test_METHOD_with_credentials(
            self.rnw.GET, self.rnw.session.get, params=True, response="json"
        )

    def test_POST_with_credentials(self):
        self._test_METHOD_with_credentials(
            self.rnw.POST,
            self.rnw.session.post,
            headers={"content-type": "application/json"},
            data=True,
            response="json",
        )

    def test_PUT_with_credentials(self):
        self._test_METHOD_with_credentials(
            self.rnw.PUT,
            self.rnw.session.put,
            data=True,
            headers={"content-type": "application/json"},
            response="json",
        )

    def test_DELETE_with_credentials(self):
        self._test_METHOD_with_credentials(
            self.rnw.DELETE, self.rnw.session.delete, data=True
        )


class TestServiceClient(unittest.TestCase):
    def setUp(self):
        nw = Mock(RequestsNetworkWrapper())
        nw.GET.return_value = "GET"
        nw.POST.return_value = "POST"
        nw.PUT.return_value = "PUT"
        nw.DELETE.return_value = "DELETE"

        self.sc = ServiceClient("endpoint/", network_wrapper=nw)
        self.scClientDoesNotEndWithSlash = ServiceClient("endpoint", network_wrapper=nw)

    def test_GET(self):
        self.assertEqual(self.sc.GET("test"), "GET")
        self.sc.network_wrapper.GET.assert_called_once_with("endpoint/test", None, None)

    def test_POST(self):
        self.assertEqual(self.sc.POST("test"), "POST")
        self.sc.network_wrapper.POST.assert_called_once_with(
            "endpoint/test", None, None
        )

    def test_PUT(self):
        self.assertEqual(self.sc.PUT("test"), "PUT")
        self.sc.network_wrapper.PUT.assert_called_once_with("endpoint/test", None, None)

    def test_DELETE(self):
        self.assertEqual(self.sc.DELETE("test"), None)
        self.sc.network_wrapper.DELETE.assert_called_once_with(
            "endpoint/test", None, None
        )

    def test_FixEndpoint(self):
        self.assertEqual(self.scClientDoesNotEndWithSlash.GET("test"), "GET")
        self.sc.network_wrapper.GET.assert_called_once_with("endpoint/test", None, None)

    def test_set_credentials(self):
        username, password = "username", "password"
        self.sc.set_credentials(username, password)
        self.sc.network_wrapper.set_credentials.assert_called_once_with(
            username, password
        )
