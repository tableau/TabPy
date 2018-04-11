from tornado import testing, web
import tabpy


class TestWhitelistNotEnabled(testing.AsyncHTTPTestCase):

    def get_app(self):
        settings = {
            "compress_response": True,
            "tabpy": "",
            "py_handler": "",
            "port": 9004,
            "state_file_path": "",
            "static_path": "",
            "disable_evaluate": False,
            "enable_safelist": False
        }
        application = web.Application([
            (r'/', tabpy.EvaluationPlaneHandler, dict(executor=None))], **settings)
        return application

    def test_whitelist_checking_not_enabled(self):
        # There is no py_handler defined expect 500 errors, not 403 since there are no restrictions on imported modules

        body = b'{"data": {"_arg1": 13, "_arg2": 3}, "script": "import os, numpy\\nreturn _arg1 * _arg2"}'
        response = self.fetch('/', method='POST', body=body)
        self.assertEqual(response.code, 500)

        body = b'{"data": {"_arg1": 13, "_arg2": 3}, "script": "from os import path\\nimport numpy\\nreturn _arg1 * _arg2"}'
        response = self.fetch('/', method='POST', body=body)
        self.assertEqual(response.code, 500)

        body = b'{"data": {"_arg1": 13, "_arg2": 3}, "script": "from os\\\\\\nimport path\\nimport numpy\\nreturn _arg1 * _arg2"}'
        response = self.fetch('/', method='POST', body=body)
        self.assertEqual(response.code, 500)

        body = b'{"data": {"_arg1": 13, "_arg2": 3}, "script": "from os\\\\\\nimport path\\nimport numpy as np\\nreturn _arg1 * _arg2"}'
        response = self.fetch('/', method='POST', body=body)
        self.assertEqual(response.code, 500)


class TestWhitelistEmptyList(testing.AsyncHTTPTestCase):

    def get_app(self):
        settings = {
            "compress_response": True,
            "tabpy": "",
            "py_handler": "",
            "port": 9004,
            "state_file_path": "",
            "static_path": "",
            "disable_evaluate": False,
            "enable_safelist": True,
            "module_safelist": []
        }
        application = web.Application([
            (r'/', tabpy.EvaluationPlaneHandler, dict(executor=None))], **settings)
        return application

    def test_whitelist_empty_list(self):
        whitelist_error_message = b'The following modules are not allowed:'

        body = b'{"data": {"_arg1": 13, "_arg2": 3}, "script": "import os, numpy\\nreturn _arg1 * _arg2"}'
        response = self.fetch('/', method='POST', body=body)
        self.assertEqual(response.code, 403)
        self.assertIn(whitelist_error_message, response.body)
        self.assertIn(b'os', response.body)
        self.assertIn(b'numpy', response.body)

        body = b'{"data": {"_arg1": 13, "_arg2": 3}, "script": "from os import path\\nimport numpy\\nreturn _arg1 * _arg2"}'
        response = self.fetch('/', method='POST', body=body)
        self.assertEqual(response.code, 403)
        self.assertIn(whitelist_error_message, response.body)
        self.assertIn(b'os', response.body)
        self.assertIn(b'numpy', response.body)

        body = b'{"data": {"_arg1": 13, "_arg2": 3}, "script": "from os\\\\\\nimport path\\nimport numpy\\nreturn _arg1 * _arg2"}'
        response = self.fetch('/', method='POST', body=body)
        self.assertEqual(response.code, 403)
        self.assertIn(whitelist_error_message, response.body)
        self.assertIn(b'os', response.body)
        self.assertIn(b'numpy', response.body)

        body = b'{"data": {"_arg1": 13, "_arg2": 3}, "script": "from os\\\\\\nimport path\\nimport numpy as np\\nreturn _arg1 * _arg2"}'
        response = self.fetch('/', method='POST', body=body)
        self.assertEqual(response.code, 403)
        self.assertIn(whitelist_error_message, response.body)
        self.assertIn(b'os', response.body)
        self.assertIn(b'numpy', response.body)
        self.assertNotIn(b'as', response.body)
        self.assertNotIn(b'np', response.body)


class TestPopulatedWhitelist(testing.AsyncHTTPTestCase):

    def get_app(self):
        settings = {
            "compress_response": True,
            "tabpy": "",
            "py_handler": "",
            "port": 9004,
            "state_file_path": "",
            "static_path": "",
            "disable_evaluate": False,
            "enable_safelist": True,
            "module_safelist": ["numpy", "scipy", "sklearn"]
        }
        application = web.Application([
            (r'/', tabpy.EvaluationPlaneHandler, dict(executor=None))], **settings)
        return application

    def test_whitelist(self):
        whitelist_error_message = b'The following modules are not allowed:'

        body = b'{"data": {"_arg1": 13, "_arg2": 3}, "script": "import scipy, numpy\\nreturn _arg1 * _arg2"}'
        response = self.fetch('/', method='POST', body=body)
        self.assertEqual(response.code, 500)

        body = b'{"data": {"_arg1": 13, "_arg2": 3}, "script": "import scipy, shutil, numpy\\nreturn _arg1 * _arg2"}'
        response = self.fetch('/', method='POST', body=body)
        self.assertEqual(response.code, 403)
        self.assertIn(whitelist_error_message, response.body)
        self.assertIn(b'shutil', response.body)
        self.assertNotIn(b'numpy', response.body)
        self.assertNotIn(b'scipy', response.body)

        body = b'{"data": {"_arg1": 13, "_arg2": 3}, "script": "from os import path\\nimport numpy\\nreturn _arg1 * _arg2"}'
        response = self.fetch('/', method='POST', body=body)
        self.assertEqual(response.code, 403)
        self.assertIn(whitelist_error_message, response.body)
        self.assertIn(b'os', response.body)
        self.assertNotIn(b'numpy', response.body)

        body = b'{"data": {"_arg1": 13, "_arg2": 3}, "script": "from os\\\\\\nimport path\\nimport numpy as np\\nreturn _arg1 * _arg2"}'
        response = self.fetch('/', method='POST', body=body)
        self.assertEqual(response.code, 403)
        self.assertIn(whitelist_error_message, response.body)
        self.assertIn(b'os', response.body)
        self.assertNotIn(b'numpy', response.body)
        self.assertNotIn(b'as', response.body)
        self.assertNotIn(b'np', response.body)

        body = b'{"data": {"_arg1": 13, "_arg2": 3}, "script": "__import__(\'os\').system(\'touch testfile\')"}'
        response = self.fetch('/', method='POST', body=body)
        self.assertEqual(response.code, 403)
        self.assertIn(whitelist_error_message, response.body)
        self.assertIn(b'os', response.body)
