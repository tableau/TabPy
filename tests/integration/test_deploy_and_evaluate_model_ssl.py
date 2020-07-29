from . import integ_test_base
import requests


class TestDeployAndEvaluateModelSSL(integ_test_base.IntegTestBase):
    def _get_port(self):
        return "9005"

    def _get_transfer_protocol(self) -> str:
        return "https"

    def _get_certificate_file_name(self) -> str:
        return "./tests/integration/resources/2019_04_24_to_3018_08_25.crt"

    def _get_key_file_name(self) -> str:
        return "./tests/integration/resources/2019_04_24_to_3018_08_25.key"

    def test_deploy_and_evaluate_model_ssl(self):
        # Uncomment the following line to preserve
        # test case output and other files (config, state, ect.)
        # in system temp folder.
        # self.set_delete_temp_folder(False)

        self.deploy_models(self._get_username(), self._get_password())

        payload = """{
                "data": { "_arg1": ["happy", "sad", "neutral"] },
                "script":
                "return tabpy.query('Sentiment%20Analysis',_arg1)['response']"
            }"""

        session = requests.Session()
        # Do not verify servers' cert to be signed by trusted CA
        session.verify = False
        # Do not warn about insecure request
        requests.packages.urllib3.disable_warnings()
        response = session.post(
            f"{self._get_transfer_protocol()}://"
            f"localhost:{self._get_port()}/evaluate",
            data=payload,
        )

        self.assertEqual(200, response.status_code)
