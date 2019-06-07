import integ_test_base
import base64
import subprocess
from pathlib import Path


class TestDeployModelSSLOffAuthOn(integ_test_base.IntegTestBase):
    def _get_pwd_file(self) -> str:
        return './tests/integration/resources/pwdfile.txt'

    def test_deploy_ssl_off_auth_on(self):
        models = ['PCA', 'Sentiment%20Analysis', "ttest"]
        path = str(Path('models', 'setup.py'))
        p = subprocess.run([self.py, path, self._get_config_file_name()],
                           input=b'user1\nP@ssw0rd\n')

        headers = {
            'Content-Type': "application/json",
            'TabPy-Client': "Integration test for deploying models with auth",
            'Authorization':
                'Basic ' +
                base64.b64encode('user1:P@ssw0rd'.
                                 encode('utf-8')).decode('utf-8')
        }

        conn = self._get_connection()
        for m in models:
            conn.request("GET", f'/endpoints/{m}', headers=headers)
            m_request = conn.getresponse()
            self.assertEqual(200, m_request.status)
            m_request.read()
