import unittest
import subprocess
import os
import requests
import time
import platform
import signal


class TestDeployModel(unittest.TestCase):
    _cwd: str
    _py: str

    def __init__(self, *args, **kwargs):
        super(TestDeployModel, self).__init__(*args, **kwargs)
        self._cwd = os.getcwd()
        if platform.system() == 'Windows':
            self._py = 'python'
        else:
            self._py = 'python3'

    def setUp(self):
        tabpy_root = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  '..', '..')
        os.chdir(tabpy_root)
        # start TabPy server in the background
        if platform.system() == 'Windows':
            self._process = subprocess.Popen(['startup.cmd', '&'])
        else:
            self._process = subprocess.Popen(['./startup.sh', '&'],
                                             preexec_fn=os.setsid)
        time.sleep(1)

    def tearDown(self):
        os.chdir(self._cwd)

        # kill TabPy server
        if platform.system() == 'Windows':
            subprocess.call(['taskkill', '/F', '/T', '/PID',
                             str(self._process.pid)])
        else:
            os.killpg(os.getpgid(self._process.pid), signal.SIGTERM)
        self._process.kill()

    def test_deploy_model_with_script(self):
        """
        Deploys a model using the provided deployment script.

        Has side effects - modifies state.ini file. Only run in clean,
        testing environment.
        :return:
        """
        # run script
        path = os.path.join(os.getcwd(), 'models', 'setup.py')
        os.system(self._py + ' ' + path)

        # query endpoint
        PCA_req = requests.get('http://localhost:9004/endpoints/PCA')
        SentimentAnalysis_req = requests.get('http://localhost:9004/endpoints/'
                                             'Sentiment Analysis')
        self.assertEqual(PCA_req.status_code, 200)
        self.assertEqual(SentimentAnalysis_req.status_code, 200)
