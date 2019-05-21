import integ_test_base
from tabpy_tools.client import Client


class TestCustomEvaluateTimeout(integ_test_base.IntegTestBase):
    def __init__(self, *args, **kwargs):
        super(TestCustomEvaluateTimeout, self).__init__(*args, **kwargs)
        self.headers = {
            'Content-Type': "application/json",
            'TabPy-Client': "Integration test for testing custom evaluate timeouts."
        }

    def _get_evaluate_timeout(self) -> str:
        return '5'

    def test_custom_evaluate_timeout_with_script(self):
        payload = (
            '''
            {
                "data": { "_arg1": 1 },
                "script": "import time\\nwhile True:\\n    time.sleep(1)\\nreturn 1"
            }
            ''')

        self._run_test(payload)

    def test_custom_evaluate_timeout_with_model(self):
        # deploy spin
        def spin():
            import time
            while True:
                time.sleep(1)
            return 1

        client = Client(f'http://localhost:{self._get_port()}/')
        client.deploy('spin', spin, 'Spins indefinitely for testing purposes.')

        payload = (
            '''
            {
                "data": {"_arg1": 1},
                "script": "return tabpy.query('spin')"
                
            }
            ''')

        self._run_test(payload)

    def _run_test(self, payload):
        conn = self._get_connection()
        conn.request('POST', '/evaluate', payload, self.headers)
        res = conn.getresponse()
        res_bytes = res.read().decode('utf-8')

        self.assertEqual(500, res.status)
        print('res_bytes: ' + res_bytes)
        self.assertTrue('TimeoutError' in res_bytes)
