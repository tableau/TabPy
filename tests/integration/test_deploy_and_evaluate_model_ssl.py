import integ_test_base
import requests
import subprocess
from pathlib import Path


class TestDeployAndEvaluateModelSSL(integ_test_base.IntegTestBase):
    def _get_port(self):
        return '9005'

    def _get_transfer_protocol(self) -> str:
        return 'https'

    def _get_certificate_file_name(self) -> str:
        return './tests/integration/resources/2019_04_24_to_3018_08_25.crt'

    def _get_key_file_name(self) -> str:
        return './tests/integration/resources/2019_04_24_to_3018_08_25.key'

    def test_deploy_and_evaluate_model_ssl(self):
        path = str(Path('models', 'setup.py'))
        subprocess.call([self.py, path, self._get_config_file_name()])

        payload = (
            '''{
                "data": { "_arg1": ["happy", "sad", "neutral"] },
                "script":
                "return tabpy.query('Sentiment%20Analysis',_arg1)['response']"
            }''')

        session = requests.Session()
        # Do not verify servers' cert to be signed by trusted CA
        session.verify = False
        # Do not warn about insecure request
        requests.packages.urllib3.disable_warnings()
        response = session.post(
            f'{self._get_transfer_protocol()}://'
            f'localhost:{self._get_port()}/evaluate',
            data=payload)

        self.assertEqual(200, response.status_code)
