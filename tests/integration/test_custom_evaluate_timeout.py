from . import integ_test_base


class TestCustomEvaluateTimeout(integ_test_base.IntegTestBase):
    def _get_evaluate_timeout(self) -> str:
        return "3"

    def test_custom_evaluate_timeout_with_script(self):
        # Uncomment the following line to preserve
        # test case output and other files (config, state, ect.)
        # in system temp folder.
        self.set_delete_temp_folder(False)

        payload = """
            {
                "data": { "_arg1": 1 },
                "script":
                "import time\\ntime.sleep(100)\\nreturn 1"
            }
            """
        headers = {
            "Content-Type": "application/json",
            "TabPy-Client": "Integration test for testing custom evaluate timeouts "
            "with scripts.",
        }

        conn = self._get_connection()
        conn.request("POST", "/evaluate", payload, headers)
        res = conn.getresponse()
        actual_error_message = res.read().decode("utf-8")

        self.assertEqual(408, res.status)
        self.assertEqual(
            '{"message": '
            '"User defined script timed out. Timeout is set to 3.0 s.", '
            '"info": {}}',
            actual_error_message,
        )
