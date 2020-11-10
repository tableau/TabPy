from . import integ_test_base
import base64
import requests


class TestDeployModelSSLOnAuthOn(integ_test_base.IntegTestBase):
    def _get_transfer_protocol(self) -> str:
        return "https"

    def _get_certificate_file_name(self) -> str:
        return "./tests/integration/resources/2019_04_24_to_3018_08_25.crt"

    def _get_key_file_name(self) -> str:
        return "./tests/integration/resources/2019_04_24_to_3018_08_25.key"

    def _get_pwd_file(self) -> str:
        return "./tests/integration/resources/pwdfile.txt"

    def test_deploy_ssl_on_auth_on(self):
        # Uncomment the following line to preserve
        # test case output and other files (config, state, ect.)
        # in system temp folder.
        # self.set_delete_temp_folder(False)

        self.deploy_models(self._get_username(), self._get_password())

        headers = {
            "Content-Type": "application/json",
            "TabPy-Client": "Integration test for deploying models with auth",
            "Authorization": "Basic "
            + base64.b64encode("user1:P@ssw0rd".encode("utf-8")).decode("utf-8"),
        }

        session = requests.Session()
        # Do not verify servers' cert to be signed by trusted CA
        session.verify = False
        # Do not warn about insecure request
        requests.packages.urllib3.disable_warnings()

        models = ["PCA", "Sentiment%20Analysis", "ttest", "anova"]
        for m in models:
            m_response = session.get(
                url=f"{self._get_transfer_protocol()}://"
                f"localhost:9004/endpoints/{m}",
                headers=headers,
            )
            self.assertEqual(200, m_response.status_code)

    def test_override_model_ssl_on_auth_on(self):
        # Uncomment the following line to preserve
        # test case output and other files (config, state, ect.)
        # in system temp folder.
        # self.set_delete_temp_folder(False)

        self.deploy_models(self._get_username(), self._get_password())

        # Override models
        self.deploy_models(self._get_username(), self._get_password())

        headers = {
            "Content-Type": "application/json",
            "TabPy-Client": "Integration test for deploying models with auth",
            "Authorization": "Basic "
            + base64.b64encode("user1:P@ssw0rd".encode("utf-8")).decode("utf-8"),
        }

        session = requests.Session()
        # Do not verify servers' cert to be signed by trusted CA
        session.verify = False
        # Do not warn about insecure request
        requests.packages.urllib3.disable_warnings()

        models = ["PCA", "Sentiment%20Analysis", "ttest", "anova"]
        for m in models:
            m_response = session.get(
                url=f"{self._get_transfer_protocol()}://"
                f"localhost:9004/endpoints/{m}",
                headers=headers,
            )
            self.assertEqual(200, m_response.status_code)
