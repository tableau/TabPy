"""
All other misc. URL-related integration tests for
when SSL is turned on for TabPy.
"""

from . import integ_test_base
import requests


class TestURL_SSL(integ_test_base.IntegTestBase):
    def _get_port(self):
        return "9005"

    def _get_transfer_protocol(self) -> str:
        return "https"

    def _get_certificate_file_name(self) -> str:
        return "./tests/integration/resources/2019_04_24_to_3018_08_25.crt"

    def _get_key_file_name(self) -> str:
        return "./tests/integration/resources/2019_04_24_to_3018_08_25.key"

    def test_notexistent_url(self):
        session = requests.Session()
        # Do not verify servers' cert to be signed by trusted CA
        session.verify = False
        # Do not warn about insecure request
        requests.packages.urllib3.disable_warnings()
        response = session.get(url=f"https://localhost:{self._get_port()}/unicorn")

        self.assertEqual(404, response.status_code)
