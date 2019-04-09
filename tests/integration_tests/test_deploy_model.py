import unittest
import subprocess
import os
import requests
import time
import platform
import signal
import tempfile
import shutil


class TestDeployModel(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestDeployModel, self).__init__(*args, **kwargs)
        self.cwd = os.getcwd()
        self.tabpy_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
        self.tabpy_server = os.path.join(self.tabpy_root, 'tabpy-server', 'tabpy_server')
        if platform.system() == 'Windows':
            self.py = 'python'
        else:
            self.py = 'python3'

    def setUp(self):
        os.chdir(self.tabpy_server)
        prefix = '_TestDeployModel_'
        self.state_dir = tempfile.mkdtemp(prefix=prefix, dir=self.tabpy_server)
        self.state_file = open(os.path.join(self.state_dir, 'state.ini'), 'w+')
        self.state_file.write('[Service Info]\n'
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

        self.config_file = tempfile.NamedTemporaryFile(
            mode='w+t', prefix=prefix, suffix='.conf', dir= self.tabpy_server, delete=False)
        self.config_file.write('[TabPy]\n'
            'TABPY_PORT= 9004\n'
            'TABPY_STATE_PATH = {}'.format(self.state_dir))
        self.config_file.close()

        
        os.chdir(self.tabpy_root)
        # start TabPy server in the background
        if platform.system() == 'Windows':
            self.process = subprocess.Popen(['startup.cmd', os.path.basename(self.config_file.name), '&'])
        else:
            self.process = subprocess.Popen(['./startup.sh', '--config=' + os.path.basename(self.config_file.name), '&'],
                                             preexec_fn=os.setsid)
        time.sleep(10)

    def tearDown(self):
        os.chdir(self.tabpy_server)
        os.remove(self.config_file.name)
        os.remove(self.state_file.name)
        shutil.rmtree(self.state_dir)

        os.chdir(self.cwd)
        # kill TabPy server
        if platform.system() == 'Windows':
            subprocess.call(['taskkill', '/F', '/T', '/PID',
                             str(self.process.pid)])
        else:
            os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
        self.process.kill()

    def test_deploy_model_with_script(self):
        """
        Deploys a model using the provided deployment script.
        
        :return:
        """
        # run script
        path = os.path.join(self.tabpy_root, 'models', 'setup.py') #os.getcwd()
        os.system(self.py + ' ' + path)

        # query endpoint
        PCA_req = requests.get('http://localhost:9004/endpoints/PCA')
        SentimentAnalysis_req = requests.get('http://localhost:9004/endpoints/'
                                             'Sentiment Analysis')
        self.assertEqual(PCA_req.status_code, 200)
        self.assertEqual(SentimentAnalysis_req.status_code, 200)
