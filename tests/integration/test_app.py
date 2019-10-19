import integ_test_base
import os
import signal
import unittest

class TestApp(integ_test_base.IntegTestBase):
    def test_ctrl_c(self):
        # Uncomment the following line to preserve
        # test case output and other files (config, state, ect.)
        # in system temp folder.
        # self.set_delete_temp_folder(False)

        process = self._get_process()
        os.kill(process.pid, signal.SIGINT)


