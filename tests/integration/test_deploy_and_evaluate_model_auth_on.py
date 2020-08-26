from . import integ_test_base


class TestDeployAndEvaluateModelAuthOn(integ_test_base.IntegTestBase):
    def _get_config_file_name(self) -> str:
        return "./tests/integration/resources/deploy_and_evaluate_model_auth.conf"

    def _get_port(self) -> str:
        return "9009"

    def test_deploy_and_evaluate_model(self):
        # Uncomment the following line to preserve
        # test case output and other files (config, state, ect.)
        # in system temp folder.
        # self.set_delete_temp_folder(False)

        self.deploy_models(self._get_username(), self._get_password())

        headers = {
            "Content-Type": "application/json",
            "Authorization": "Basic dXNlcjE6UEBzc3cwcmQ=",
            "Host": "localhost:9009",
        }
        payload = """{
                "data": { "_arg1": ["happy", "sad", "neutral"] },
                "script":
                "return tabpy.query('Sentiment Analysis',_arg1)['response']"
            }"""

        conn = self._get_connection()
        conn.request("POST", "/evaluate", payload, headers)
        SentimentAnalysis_eval = conn.getresponse()
        self.assertEqual(200, SentimentAnalysis_eval.status)
        SentimentAnalysis_eval.read()
