import integ_test_base
import subprocess
from pathlib import Path


class TestDeployAndEvaluateModel(integ_test_base.IntegTestBase):
    def test_deploy_and_evaluate_model(self):
        # Uncomment the following line to preserve
        # test case output and other files (config, state, ect.)
        # in system temp folder.
        self.set_delete_temp_folder(False)

        self.deploy_models(self._get_username(), self._get_password())

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
