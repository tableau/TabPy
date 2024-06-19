from . import integ_test_base
import os
import requests


class TestMinimumTLSVersionInvalid(integ_test_base.IntegTestBase):
    def _get_log_contents(self):
        with open(self.log_file_path, 'r') as f:
            return f.read()

    def _get_config_file_name(self) -> str:
        config_file = open(os.path.join(self.tmp_dir, "test.conf"), "w+")
        config_file.write(
            "[TabPy]\n"
            "TABPY_PORT = 9005\n"
            "TABPY_TRANSFER_PROTOCOL = https\n"
            "TABPY_CERTIFICATE_FILE = ./tests/integration/resources/2019_04_24_to_3018_08_25.crt\n"
            "TABPY_KEY_FILE = ./tests/integration/resources/2019_04_24_to_3018_08_25.key\n"
            "TABPY_MINIMUM_TLS_VERSION = TLSv-1.3"
        )
        pwd_file = self._get_pwd_file()
        if pwd_file is not None:
            pwd_file = os.path.abspath(pwd_file)
            config_file.write(f"TABPY_PWD_FILE = {pwd_file}\n")

        config_file.close()
        self.delete_config_file = True
        return config_file.name

    def test_minimum_tls_version_invalid(self):
        # Uncomment the following line to preserve
        # test case output and other files (config, state, ect.)
        # in system temp folder.
        # self.set_delete_temp_folder(False)
        log_contents = self._get_log_contents()
        self.assertIn("Unrecognized value for TABPY_MINIMUM_TLS_VERSION", log_contents)
        self.assertIn("Setting minimum TLS version to TLSv1_2", log_contents)
