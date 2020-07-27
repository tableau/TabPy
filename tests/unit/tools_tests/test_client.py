import unittest
from unittest.mock import Mock

from tabpy.tabpy_tools.client import Client
from tabpy.tabpy_tools.client import _check_endpoint_name


class TestClient(unittest.TestCase):
    def setUp(self):
        self.client = Client("http://example.com/")
        self.client._service = Mock()  # TODO: should spec this

    def test_init(self):
        client = Client("http://example.com:9004")

        self.assertEqual(client._endpoint, "http://example.com:9004")

        client = Client("http://example.com/", 10.0)

        self.assertEqual(client._endpoint, "http://example.com/")

        client = Client(endpoint="https://example.com/", query_timeout=-10.0)

        self.assertEqual(client._endpoint, "https://example.com/")
        self.assertEqual(client.query_timeout, 0.0)

        # valid name tests
        with self.assertRaises(ValueError):
            Client("")
        with self.assertRaises(TypeError):
            Client(1.0)
        with self.assertRaises(ValueError):
            Client("*#")
        with self.assertRaises(TypeError):
            Client()
        with self.assertRaises(ValueError):
            Client("http:/www.example.com/")
        with self.assertRaises(ValueError):
            Client("httpx://www.example.com:9004")

    def test_get_status(self):
        self.client._service.get_status.return_value = "asdf"
        self.assertEqual(self.client.get_status(), "asdf")

    def test_query_timeout(self):
        self.client.query_timeout = 5.0
        self.assertEqual(self.client.query_timeout, 5.0)
        self.assertEqual(self.client._service.query_timeout, 5.0)

    def test_query(self):
        self.client._service.query.return_value = "ok"

        self.assertEqual(self.client.query("foo", 1, 2, 3), "ok")

        self.client._service.query.assert_called_once_with("foo", 1, 2, 3)

        self.client._service.query.reset_mock()

        self.assertEqual(self.client.query("foo", a=1, b=2, c=3), "ok")

        self.client._service.query.assert_called_once_with("foo", a=1, b=2, c=3)

    def test_get_endpoints(self):
        self.client._service.get_endpoints.return_value = "foo"

        self.assertEqual(self.client.get_endpoints("foo"), "foo")

        self.client._service.get_endpoints.assert_called_once_with("foo")

    def test_get_endpoint_upload_destination(self):
        self.client._service.get_endpoint_upload_destination.return_value = {
            "path": "foo"
        }

        self.assertEqual(self.client._get_endpoint_upload_destination(), "foo")

    def test_set_credentials(self):
        username, password = "username", "password"
        self.client.set_credentials(username, password)

        self.client._service.set_credentials.assert_called_once_with(username, password)

    def test_check_invalid_endpoint_name(self):
        endpoint_name = "Invalid:model:@name"
        with self.assertRaises(ValueError) as err:
            _check_endpoint_name(endpoint_name)

        self.assertEqual(
            err.exception.args[0],
            f"endpoint name {endpoint_name } can only contain: "
            "a-z, A-Z, 0-9, underscore, hyphens and spaces.",
        )
