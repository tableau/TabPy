import integ_test_base
import base64
import requests
import subprocess


class TestDeployModelSSLOnAuthOn(integ_test_base.IntegTestBase):
    def _get_transfer_protocol(self) -> str:
        return 'https'

    def _get_certificate_file_name(self) -> str:
        return './tests/integration/resources/2019_04_24_to_3018_08_25.crt'

    def _get_key_file_name(self) -> str:
        return './tests/integration/resources/2019_04_24_to_3018_08_25.key'

    def _get_pwd_file(self) -> str:
        return './tests/integration/resources/pwdfile.txt'

    def test_deploy_ssl_on_auth_on(self):
        self.set_delete_temp_folder(False)
        self.deploy_models(self._get_username(), self._get_password())

        headers = {
            'Content-Type': "application/json",
            'TabPy-Client': "Integration test for deploying models with auth",
            'Authorization': 'Basic ' +
            base64.b64encode('user1:P@ssw0rd'.encode('utf-8')).decode('utf-8')
        }

        session = requests.Session()
        # Do not verify servers' cert to be signed by trusted CA
        session.verify = False
        # Do not warn about insecure request
        requests.packages.urllib3.disable_warnings()

        models = ['PCA', 'Sentiment%20Analysis', "ttest"]
        for m in models:
            m_response = session.get(url=f'{self._get_transfer_protocol()}://'
                                     f'localhost:9004/endpoints/{m}',
                                     headers=headers)
            self.assertEqual(200, m_response.status_code)
