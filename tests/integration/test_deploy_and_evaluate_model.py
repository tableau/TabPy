from . import integ_test_base


class TestDeployAndEvaluateModel(integ_test_base.IntegTestBase):
    def _get_config_file_name(self) -> str:
        return "./tests/integration/resources/deploy_and_evaluate_model.conf"

    def _get_port(self) -> str:
        return "9008"

    def test_deploy_and_evaluate_model(self):
        # Uncomment the following line to preserve
        # test case output and other files (config, state, ect.)
        # in system temp folder.
        # self.set_delete_temp_folder(False)

        self.deploy_models(self._get_username(), self._get_password())

        payload = """{
                "data": { "_arg1": ["happy", "sad", "neutral"] },
                "script":
                "return tabpy.query('Sentiment Analysis',_arg1)['response']"
            }"""

        conn = self._get_connection()
        conn.request("POST", "/evaluate", payload)
        SentimentAnalysis_eval = conn.getresponse()
        self.assertEqual(200, SentimentAnalysis_eval.status)
        SentimentAnalysis_eval.read()
