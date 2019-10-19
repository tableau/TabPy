import coverage
import os
import platform
import signal
import subprocess
import tabpy
import tempfile
import unittest

class TestApp(unittest.TestCase):
    def setUp(self):
        prefix = 'TabPy_UnitTest_' + __name__ + '_'
        self.tmp_dir = tempfile.mkdtemp(prefix=prefix)

        # create temporary state.ini
        orig_state_file_name = os.path.abspath(
            self._get_state_file_path() + '/state.ini')
        self.state_file_name = os.path.abspath(self.tmp_dir + '/state.ini')
        if orig_state_file_name != self.state_file_name:
            shutil.copyfile(orig_state_file_name, self.state_file_name)

        # create config file
        orig_config_file_name = os.path.abspath(self._get_config_file_name())
        self.config_file_name = os.path.abspath(
            self.tmp_dir + '/' +
            os.path.basename(orig_config_file_name))
        if orig_config_file_name != self.config_file_name:
            shutil.copyfile(orig_config_file_name, self.config_file_name)

        self.outfile = open(self.tmp_dir + '/output.txt', 'w')

    def tearDown(self):
        # stop TabPy
        if self.process is not None:
            if platform.system() == 'Windows':
                subprocess.call(['taskkill', '/F', '/T', '/PID',
                                 str(self.process.pid)])
            else:
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            self.process.kill()

            # after shutting down TabPy and before we start it again
            # for next test give it some time to terminate.
            time.sleep(5)

        # remove temporary files
        os.remove(self.state_file_name)
        os.remove(self.config_file_name)
        shutil.rmtree(self.tmp_dir)

    def test_ctrl_c(self):
        cmd = ['tabpy']
        preexec_fn = None

        py = 'python'
        preexec_fn = None
        if platform.system() != 'Windows':
            self.py = 'python3'
            preexec_fn = os.setsid

        coverage.process_startup()
        self.process = subprocess.Popen(
            cmd,
            preexec_fn=preexec_fn,
            stdout=outfile,
            stderr=outfile)

        # give the app some time to start up...
        time.sleep(5)

        process.send_signal(signal.SIGINT)

        # stop TabPy
        self.assertEqual(None, self.process)


