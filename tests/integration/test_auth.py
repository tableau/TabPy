import base64
from . import integ_test_base


class TestAuth(integ_test_base.IntegTestBase):
    def setUp(self):
        super(TestAuth, self).setUp()
        self.payload = """{
                "data": { "_arg1": [1, 2] },
                "script": "return [x * 2 for x in _arg1]"
            }"""

    def _get_pwd_file(self) -> str:
        return "./tests/integration/resources/pwdfile.txt"

    def test_missing_credentials_fails(self):
        headers = {
            "Content-Type": "application/json",
            "TabPy-Client": "Integration tests for Auth",
        }

        conn = self._get_connection()
        conn.request("POST", "/evaluate", self.payload, headers)
        res = conn.getresponse()

        self.assertEqual(401, res.status)

    def test_invalid_password(self):
        headers = {
            "Content-Type": "application/json",
            "TabPy-Client": "Integration tests for Auth",
            "Authorization": "Basic "
            + base64.b64encode("user1:wrong_password".encode("utf-8")).decode("utf-8"),
        }

        conn = self._get_connection()
        conn.request("POST", "/evaluate", self.payload, headers)
        res = conn.getresponse()

        self.assertEqual(401, res.status)

    def test_invalid_username(self):
        # Uncomment the following line to preserve
        # test case output and other files (config, state, ect.)
        # in system temp folder.
        # self.set_delete_temp_folder(False)

        headers = {
            "Content-Type": "application/json",
            "TabPy-Client": "Integration tests for Auth",
            "Authorization": "Basic "
            + base64.b64encode("wrong_user:P@ssw0rd".encode("utf-8")).decode("utf-8"),
        }

        conn = self._get_connection()
        conn.request("POST", "/evaluate", self.payload, headers)
        res = conn.getresponse()

        self.assertEqual(401, res.status)

    def test_valid_credentials(self):
        headers = {
            "Content-Type": "application/json",
            "TabPy-Client": "Integration tests for Auth",
            "Authorization": "Basic "
            + base64.b64encode("user1:P@ssw0rd".encode("utf-8")).decode("utf-8"),
        }

        conn = self._get_connection()
        conn.request("POST", "/evaluate", self.payload, headers)
        res = conn.getresponse()

        self.assertEqual(200, res.status)
