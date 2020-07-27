import unittest
from tabpy.tabpy_server.common.endpoint_file_mgr import _check_endpoint_name


class TestEndpointFileManager(unittest.TestCase):
    def test_endpoint_name_not_str(self):
        self.assertRaises(TypeError, _check_endpoint_name, 2)

    def test_endpoint_name_empty_str(self):
        self.assertRaises(ValueError, _check_endpoint_name, "")

    def test_endpoint_name_wrong_regex(self):
        self.assertRaises(ValueError, _check_endpoint_name, "****")
