import os
import unittest
from tempfile import NamedTemporaryFile

from tabpy.tabpy_server.app.app import TabPyApp


class TestPasswordFile(unittest.TestCase):
    def setUp(self):
        self.config_file = NamedTemporaryFile(mode="w", delete=False)
        self.config_file.close()
        self.pwd_file = NamedTemporaryFile(mode="w", delete=False)
        self.pwd_file.close()

    def tearDown(self):
        os.remove(self.config_file.name)
        self.config_file = None
        os.remove(self.pwd_file.name)
        self.pwd_file = None

    def _set_file(self, file_name, value):
        with open(file_name, "w") as f:
            f.write(value)

    def test_given_no_pwd_file_expect_empty_credentials_list(self):
        self._set_file(
            self.config_file.name, "[TabPy]\n" "TABPY_TRANSFER_PROTOCOL = http"
        )

        app = TabPyApp(self.config_file.name)
        self.assertDictEqual(
            app.credentials,
            {},
            "Expected no credentials with no password file provided",
        )

    def test_given_empty_pwd_file_expect_app_fails(self):
        self._set_file(
            self.config_file.name, "[TabPy]\n" f"TABPY_PWD_FILE = {self.pwd_file.name}"
        )

        self._set_file(self.pwd_file.name, "# just a comment")

        with self.assertRaises(RuntimeError) as cm:
            TabPyApp(self.config_file.name)
            ex = cm.exception
            self.assertEqual(
                f"Failed to read password file {self.pwd_file.name}", ex.args[0]
            )

    def test_given_missing_pwd_file_expect_app_fails(self):
        self._set_file(self.config_file.name, "[TabPy]\n" "TABPY_PWD_FILE = foo")

        with self.assertRaises(RuntimeError) as cm:
            TabPyApp(self.config_file.name)
            ex = cm.exception
            self.assertEqual(
                f"Failed to read password file {self.pwd_file.name}", ex.args[0]
            )

    def test_given_one_password_in_pwd_file_expect_one_credentials_entry(self):
        self._set_file(
            self.config_file.name, "[TabPy]\n" f"TABPY_PWD_FILE = {self.pwd_file.name}"
        )

        login = "user_name_123"
        pwd = "someting@something_else"
        self._set_file(self.pwd_file.name, "# passwords\n" "\n" f"{login} {pwd}")

        app = TabPyApp(self.config_file.name)

        self.assertEqual(len(app.credentials), 1)
        self.assertIn(login, app.credentials)
        self.assertEqual(app.credentials[login], pwd)

    def test_given_username_but_no_password_expect_parsing_fails(self):
        self._set_file(
            self.config_file.name, "[TabPy]\n" f"TABPY_PWD_FILE = {self.pwd_file.name}"
        )

        login = "user_name_123"
        pwd = ""
        self._set_file(self.pwd_file.name, "# passwords\n" "\n" f"{login} {pwd}")

        with self.assertRaises(RuntimeError) as cm:
            TabPyApp(self.config_file.name)
            ex = cm.exception
            self.assertEqual(
                f"Failed to read password file {self.pwd_file.name}", ex.args[0]
            )

    def test_given_duplicate_usernames_expect_parsing_fails(self):
        self._set_file(
            self.config_file.name, "[TabPy]\n" f"TABPY_PWD_FILE = {self.pwd_file.name}"
        )

        login = "user_name_123"
        pwd = "hashedpw"
        self._set_file(
            self.pwd_file.name, "# passwords\n" "\n" f"{login} {pwd}\n{login} {pwd}"
        )

        with self.assertRaises(RuntimeError) as cm:
            TabPyApp(self.config_file.name)
            ex = cm.exception
            self.assertEqual(
                f"Failed to read password file {self.pwd_file.name}", ex.args[0]
            )

    def test_given_one_line_with_too_many_params_expect_app_fails(self):
        self._set_file(
            self.config_file.name, "[TabPy]\n" f"TABPY_PWD_FILE = {self.pwd_file.name}"
        )

        self._set_file(
            self.pwd_file.name,
            "# passwords\n" "user1 pwd1\n" "user_2 pwd#2" "user1 pwd@3",
        )

        with self.assertRaises(RuntimeError) as cm:
            TabPyApp(self.config_file.name)
            ex = cm.exception
            self.assertEqual(
                f"Failed to read password file {self.pwd_file.name}", ex.args[0]
            )

    def test_given_different_cases_in_pwd_file_expect_app_fails(self):
        self._set_file(
            self.config_file.name, "[TabPy]\n" f"TABPY_PWD_FILE = {self.pwd_file.name}"
        )

        self._set_file(
            self.pwd_file.name,
            "# passwords\n" "user1 pwd1\n" "user_2 pwd#2" "UseR1 pwd@3",
        )

        with self.assertRaises(RuntimeError) as cm:
            TabPyApp(self.config_file.name)
            ex = cm.exception
            self.assertEqual(
                f"Failed to read password file {self.pwd_file.name}", ex.args[0]
            )

    def test_given_multiple_credentials_expect_all_parsed(self):
        self._set_file(
            self.config_file.name, "[TabPy]\n" f"TABPY_PWD_FILE = {self.pwd_file.name}"
        )
        creds = {"user_1": "pwd_1", "user@2": "pwd@2", "user#3": "pwd#3"}

        pwd_file_context = ""
        for login in creds:
            pwd_file_context += f"{login} {creds[login]}\n"

        self._set_file(self.pwd_file.name, pwd_file_context)
        app = TabPyApp(self.config_file.name)

        self.assertCountEqual(creds, app.credentials)
        for login in creds:
            self.assertIn(login, app.credentials)
            self.assertEqual(creds[login], app.credentials[login])
