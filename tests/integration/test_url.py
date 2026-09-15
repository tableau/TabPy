"""
All other misc. URL-related integration tests.
"""

from . import integ_test_base


class TestURL(integ_test_base.IntegTestBase):
    def test_notexistent_url(self):
        # Uncomment the following line to preserve
        # test case output and other files (config, state, ect.)
        # in system temp folder.
        # self.set_delete_temp_folder(False)

        conn = self._get_connection()
        conn.request("GET", "/unicorn")
        res = conn.getresponse()

        self.assertEqual(404, res.status)

    def test_static_page(self):
        conn = self._get_connection()
        conn.request("GET", "/")
        res = conn.getresponse()
        page = res.read()

        self.assertEqual(200, res.status)
        self.assertIn("text/html", res.getheader("Content-Type"))
        self.assertIn(b"<style>", page)
        self.assertIn(b"--canvas", page)
        self.assertIn(b"<script>", page)
        self.assertIn(b"loadSection", page)
        self.assertNotIn(b'href="styles.css"', page)
        self.assertNotIn(b'src="app.js"', page)
        conn.close()
