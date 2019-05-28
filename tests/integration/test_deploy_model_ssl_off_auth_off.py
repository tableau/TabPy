import integ_test_base
import subprocess
from pathlib import Path


class TestDeployModelSSLOffAuthOff(integ_test_base.IntegTestBase):
    def test_deploy_ssl_off_auth_off(self):
        path = str(Path('models', 'setup.py'))
        subprocess.call([self.py, path, self._get_config_file_name()])

        payload = (
            '''{
                "data": { "_arg1": ["happy", "sad", "neutral"] },
                "script":
                "return tabpy.query('Sentiment Analysis',_arg1)['response']"
            }''')

        conn = self._get_connection()
        conn.request("POST", "/evaluate", payload)
        SentimentAnalysis_eval = conn.getresponse()
        self.assertEqual(200, SentimentAnalysis_eval.status)
        SentimentAnalysis_eval.read()
