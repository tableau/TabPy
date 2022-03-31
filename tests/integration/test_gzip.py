"""
Script evaluation tests.
"""

from . import integ_test_base
import json
import gzip
import os
import requests


class TestEvaluate(integ_test_base.IntegTestBase):
    def _get_config_file_name(self) -> str:
        """
        Generates config file. Overwrite this function for tests to
        run against not default state file.

        Returns
        -------
        str
            Absolute path to config file.
        """
        config_file = open(os.path.join(self.tmp_dir, "test.conf"), "w+")
        config_file.write(
            "[TabPy]\n"
            f"TABPY_QUERY_OBJECT_PATH = {self.tmp_dir}/query_objects\n"
            f"TABPY_PORT = {self._get_port()}\n"
            f"TABPY_GZIP_ENABLE = TRUE\n"
            f"TABPY_STATE_PATH = {self.tmp_dir}\n"
        )

        pwd_file = self._get_pwd_file()
        if pwd_file is not None:
            pwd_file = os.path.abspath(pwd_file)
            config_file.write(f"TABPY_PWD_FILE = {pwd_file}\n")

        transfer_protocol = self._get_transfer_protocol()
        if transfer_protocol is not None:
            config_file.write(f"TABPY_TRANSFER_PROTOCOL = {transfer_protocol}\n")

        cert_file_name = self._get_certificate_file_name()
        if cert_file_name is not None:
            cert_file_name = os.path.abspath(cert_file_name)
            config_file.write(f"TABPY_CERTIFICATE_FILE = {cert_file_name}\n")

        key_file_name = self._get_key_file_name()
        if key_file_name is not None:
            key_file_name = os.path.abspath(key_file_name)
            config_file.write(f"TABPY_KEY_FILE = {key_file_name}\n")

        evaluate_timeout = self._get_evaluate_timeout()
        if evaluate_timeout is not None:
            config_file.write(f"TABPY_EVALUATE_TIMEOUT = {evaluate_timeout}\n")

        config_file.close()

        self.delete_config_file = True
        return config_file.name

    def test_single_value_returned(self):
        payload = """
            {
                "data": { "_arg1": 2, "_arg2": 40 },
                "script":
                "return _arg1 + _arg2"
            }
            """
        headers = {
            "Content-Type": "application/json",
            "Content-Encoding": "gzip",
        }

        url = self._get_url() + "/evaluate"
        response = requests.request("POST", url, data=gzip.compress(payload.encode('utf-8')),
            headers=headers)
        result = json.loads(response.text)

        self.assertEqual(200, response.status_code)
        self.assertEqual(42, result)

    def test_syntax_error(self):
        payload = """
            {
                "data": { "_arg1": [2], "_arg2": [40] },
                "script":
                "% ^ !! return Nothing"
            }
            """
        headers = {
            "Content-Type": "application/json",
            "Content-Encoding": "gzip",
        }

        url = self._get_url() + "/evaluate"
        response = requests.request("POST", url, data=gzip.compress(payload.encode('utf-8')),
            headers=headers)
        result = json.loads(response.text)

        self.assertEqual(500, response.status_code)
        self.assertEqual("Error processing script", result["message"])
        self.assertTrue(result["info"].startswith("SyntaxError"))
