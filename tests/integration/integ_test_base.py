import http.client
import os
import platform
import shutil
import signal
import subprocess
import tempfile
import time
import unittest


class IntegTestBase(unittest.TestCase):
    '''
    Base class for integration tests.
    '''
    def __init__(self, methodName="runTest"):
        super(IntegTestBase, self).__init__(methodName)
        self.process = None

    def setUp(self):
        super(IntegTestBase, self).setUp()
        prefix = 'TabPyIntegTest'
        self.tmp_dir = tempfile.mkdtemp(prefix=prefix)

        # create temporary state.ini
        self.state_file = open(os.path.join(self.tmp_dir, 'state.ini'), 'w+')
        self.state_file.write(
            '[Service Info]\n'
            'Name = TabPy Serve\n'
            'Description = \n'
            'Creation Time = 0\n'
            'Access-Control-Allow-Origin = \n'
            'Access-Control-Allow-Headers = \n'
            'Access-Control-Allow-Methods = \n'
            '\n'
            '[Query Objects Service Versions]\n'
            '\n'
            '[Query Objects Docstrings]\n'
            '\n'
            '[Meta]\n'
            'Revision Number = 1\n')
        self.state_file.close()

        # create config file
        self.config_file = open(os.path.join(self.tmp_dir, 'auth.conf'), 'w+')
        self.config_file.write(
            '[TabPy]\n'
            'TABPY_PORT=9004\n'
            'TABPY_PWD_FILE=./tests/integration/resources/pwdfile.txt\n'
            f'TABPY_STATE_PATH = {self.tmp_dir}')
        self.config_file.close()

        # Platform specific - for integration tests we want to engage
        # startup script
        if platform.system() == 'Windows':
            self.process = subprocess.Popen(
                ['startup.cmd', self.config_file.name, '&'])
        else:
            self.process = subprocess.Popen(
                ['./startup.sh',
                 '--config=' + self.config_file.name, '&'],
                preexec_fn=os.setsid)
        # give the app some time to start up...
        time.sleep(3)

    def tearDown(self):
        # stop TabPy
        if self.process is not None:
            if platform.system() == 'Windows':
                subprocess.call(['taskkill', '/F', '/T', '/PID',
                                str(self.process.pid)])
            else:
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            self.process.kill()

        # remove temporary files
        os.remove(self.state_file.name)
        os.remove(self.config_file.name)
        shutil.rmtree(self.tmp_dir)

        super(IntegTestBase, self).tearDown()

    def _get_connection(self) -> http.client.HTTPConnection:
        connection = http.client.HTTPConnection('localhost:9004')
        return connection
