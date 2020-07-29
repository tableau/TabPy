"""
Script evaluation tests.
"""

from . import integ_test_base
import json


class TestEvaluate(integ_test_base.IntegTestBase):
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
        }

        conn = self._get_connection()
        conn.request("POST", "/evaluate", payload, headers)
        response = conn.getresponse()
        result = response.read().decode("utf-8")

        self.assertEqual(200, response.status)
        self.assertEqual("42", result)

    def test_collection_returned(self):
        payload = """
            {
                "data": { "_arg1": [2, 3], "_arg2": [40, 0.1415926] },
                "script":
                "return [x + y for x, y in zip(_arg1, _arg2)]"
            }
            """
        headers = {
            "Content-Type": "application/json",
        }

        conn = self._get_connection()
        conn.request("POST", "/evaluate", payload, headers)
        response = conn.getresponse()
        result = response.read().decode("utf-8")

        self.assertEqual(200, response.status)
        self.assertEqual("[42, 3.1415926]", result)

    def test_none_returned(self):
        payload = """
            {
                "data": { "_arg1": 2, "_arg2": 40 },
                "script":
                "return None"
            }
            """
        headers = {
            "Content-Type": "application/json",
        }

        conn = self._get_connection()
        conn.request("POST", "/evaluate", payload, headers)
        response = conn.getresponse()
        result = response.read().decode("utf-8")

        self.assertEqual(200, response.status)
        self.assertEqual("null", result)

    def test_nothing_returned(self):
        payload = """
            {
                "data": { "_arg1": [2], "_arg2": [40] },
                "script":
                "res = [x + y for x, y in zip(_arg1, _arg2)]"
            }
            """
        headers = {
            "Content-Type": "application/json",
        }

        conn = self._get_connection()
        conn.request("POST", "/evaluate", payload, headers)
        response = conn.getresponse()
        result = response.read().decode("utf-8")

        self.assertEqual(200, response.status)
        self.assertEqual("null", result)

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
        }

        conn = self._get_connection()
        conn.request("POST", "/evaluate", payload, headers)
        response = conn.getresponse()
        result = json.loads(response.read().decode("utf-8"))

        self.assertEqual(500, response.status)
        self.assertEqual("Error processing script", result["message"])
        self.assertTrue(result["info"].startswith("SyntaxError"))
