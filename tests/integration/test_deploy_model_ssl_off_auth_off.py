import integ_test_base
import subprocess
from pathlib import Path


class TestDeployModelSSLOffAuthOff(integ_test_base.IntegTestBase):
    def test_deploy_ssl_off_auth_off(self):
        models = ['PCA', 'Sentiment%20Analysis', "ttest"]
        path = str(Path('models', 'setup.py'))
        subprocess.call([self.py, path, self._get_config_file_name()])

        conn = self._get_connection()
        for m in models:
            conn.request("GET", f'/endpoints/{m}')
            m_request = conn.getresponse()
            self.assertEqual(200, m_request.status)
            m_request.read()
