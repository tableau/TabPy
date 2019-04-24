'''
All other misc. URL-related integration tests for
when SSL is turned on for TabPy.
'''

import integ_test_base


class TestURL_SSL(integ_test_base.IntegTestBase):
    def _get_port(self) -> str:
        return '9005'

    def _get_transfer_protocol(self) -> str:
        return 'https'

    def _get_certificate_file_name(self) -> str:
        return './tests/integration/resources/2019_04_24_to_3018_08_25.crt'

    def _get_key_file_name(self) -> str:
        return './tests/integration/resources/2019_04_24_to_3018_08_25.key'

    def test_notexistant_url(self):
        self.set_delete_temp_folder(False)
        conn = self._get_connection()
        conn.request("GET", "/unicorn")
        res = conn.getresponse()

        self.assertEqual(404, res.status)
