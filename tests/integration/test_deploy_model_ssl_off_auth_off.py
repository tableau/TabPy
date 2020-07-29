from . import integ_test_base


class TestDeployModelSSLOffAuthOff(integ_test_base.IntegTestBase):
    def test_deploy_ssl_off_auth_off(self):
        # Uncomment the following line to preserve
        # test case output and other files (config, state, ect.)
        # in system temp folder.
        # self.set_delete_temp_folder(False)

        self.deploy_models(self._get_username(), self._get_password())

        conn = self._get_connection()

        models = ["PCA", "Sentiment%20Analysis", "ttest", "anova"]
        for m in models:
            conn.request("GET", f"/endpoints/{m}")
            m_request = conn.getresponse()
            self.assertEqual(200, m_request.status)
            m_request.read()
