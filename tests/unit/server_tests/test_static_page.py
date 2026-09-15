import base64
import hashlib
import json
import os
import re
import tempfile

from tabpy.tabpy_server.app.app import TabPyApp
from tornado.testing import AsyncHTTPTestCase


class TestStaticPageWithSubdirectory(AsyncHTTPTestCase):
    @classmethod
    def setUpClass(cls):
        cls.state_dir = tempfile.mkdtemp(prefix="TabPyStaticPage_")
        cls.state_file = os.path.join(cls.state_dir, "state.ini")
        with open(cls.state_file, "w") as state_file:
            state_file.write(
                "[Service Info]\n"
                "Name = Subdirectory TabPy\n"
                "Description = Static page test\n"
                "Creation Time = 0\n"
                "Subdirectory = analytics\n"
                "Access-Control-Allow-Origin = \n"
                "Access-Control-Allow-Headers = \n"
                "Access-Control-Allow-Methods = \n"
                "\n"
                "[Query Objects Service Versions]\n"
                "\n"
                "[Query Objects Docstrings]\n"
                "\n"
                "[Meta]\n"
                "Revision Number = 1\n"
            )

        cls.config_file = tempfile.NamedTemporaryFile(
            prefix="TabPyStaticPage_", suffix=".conf", delete=False, mode="w"
        )
        cls.config_file.write(
            "[TabPy]\n"
            f"TABPY_STATE_PATH = {cls.state_dir}\n"
        )
        cls.config_file.close()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        os.remove(cls.state_file)
        os.remove(cls.config_file.name)
        os.rmdir(cls.state_dir)
        super().tearDownClass()

    def get_app(self):
        self.tabpy_app = TabPyApp(self.config_file.name)
        return self.tabpy_app._create_tornado_web_app()

    def test_assets_and_api_routes_use_configured_subdirectory(self):
        page = self.fetch("/analytics/")
        self.assertEqual(200, page.code)
        self.assertIn("text/html", page.headers["Content-Type"])
        self.assertIn(b"<style>", page.body)
        self.assertIn(b"<script>", page.body)

        info = self.fetch("/analytics/info")
        endpoints = self.fetch("/analytics/endpoints")
        self.assertEqual("Subdirectory TabPy", json.loads(info.body)["name"])
        self.assertDictEqual({}, json.loads(endpoints.body))

    def test_default_page_keeps_remote_content_out_of_executable_html(self):
        page = self.fetch("/analytics/").body

        self.assertIn(b"Content-Security-Policy", page)
        self.assertIn(b"default-src 'self'", page)
        self.assertIn(b"sha256-", page)
        favicon_match = re.search(
            rb'href="data:image/x-icon;base64,([^"]+)"',
            page,
        )
        self.assertIsNotNone(favicon_match)
        favicon = base64.b64decode(favicon_match.group(1))
        self.assertEqual(10134, len(favicon))
        self.assertEqual(
            "26e7546a015a3299fb76d46030ee9202f6f428ba3505d25734858a279c3b2c54",
            hashlib.sha256(favicon).hexdigest(),
        )
        self.assertNotIn(
            b"https://www.tableau.com/themes/custom/tableau_www/favicon.ico",
            page,
        )
        self.assertIn(b"textContent", page)
        self.assertIn(b"if (depth >= 2)", page)
        self.assertIn(b"is-depth-stacked", page)
        self.assertIn(b"await response.text()", page)
        self.assertIn(b"failedResponse.rawText", page)
        self.assertNotIn(b"innerHTML", page)
        self.assertNotIn(b"insertAdjacentHTML", page)
        self.assertNotIn(b'href="styles.css"', page)
        self.assertNotIn(b'src="app.js"', page)
