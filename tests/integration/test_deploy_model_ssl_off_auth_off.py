import integ_test_base
import subprocess
from pathlib import Path


class TestDeployModelSSLOffAuthOff(integ_test_base.IntegTestBase):
    def test_deploy_ssl_off_auth_off(self):
        path = str(Path('models', 'setup.py'))
        subprocess.call([self.py, path, self._get_config_file_name()])

        conn = self._get_connection()
        conn.request("GET", "/endpoints/PCA")
        PCA_request = conn.getresponse()
        self.assertEqual(200, PCA_request.status)
        PCA_request.read()

        conn.request("GET", "/endpoints/Sentiment%20Analysis")
        SentimentAnalysis_request = conn.getresponse()
        self.assertEqual(200, SentimentAnalysis_request.status)
        SentimentAnalysis_request.read()

        conn.request("GET", "/endpoints/ttest")
        ttest_request = conn.getresponse()
        self.assertEqual(200, ttest_request.status)
        ttest_request.read()
