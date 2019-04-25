'''
All other misc. URL-related integration tests.
'''

import integ_test_base


class TestURL(integ_test_base.IntegTestBase):
    def test_notexistent_url(self):
        conn = self._get_connection()
        conn.request("GET", "/unicorn")
        res = conn.getresponse()

        self.assertEqual(404, res.status)
