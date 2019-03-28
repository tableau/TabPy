import base64
import os
import tempfile
import unittest

from argparse import Namespace
from tabpy_server.app.app import TabPyApp
from tabpy_server.handlers.evaluation_plane_handler\
    import EvaluationPlaneHandler
from tabpy_server.handlers.util import hash_password
from tornado.testing import AsyncHTTPTestCase
from unittest.mock import patch


class TestEvaluationPlainHandlerWithAuth(AsyncHTTPTestCase):
    @classmethod
    def setUpClass(cls):
        cls.patcher = patch(
            'tabpy_server.app.app.TabPyApp._parse_cli_arguments',
            return_value=Namespace(
                config=None))
        cls.patcher.start()

        prefix = '__TestEvaluationPlainHandlerWithAuth_'
        # create password file
        cls.pwd_file = tempfile.NamedTemporaryFile(
            mode='w+t', prefix=prefix, suffix='.txt', delete=False)
        username = 'username'
        password = 'password'
        cls.pwd_file.write('{} {}\n'.format(
            username,
            hash_password(username, password)))
        cls.pwd_file.close()

        # create state.ini dir and file
        cls.state_dir = tempfile.mkdtemp(prefix=prefix)
        cls.state_file = open(os.path.join(cls.state_dir, 'state.ini'), 'w+')
        cls.state_file.write('[Service Info]\n'
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
        cls.state_file.close()

        # create config file
        cls.config_file = tempfile.NamedTemporaryFile(
            mode='w+t', prefix=prefix, suffix='.conf', delete=False)
        cls.config_file.write(
            '[TabPy]\n'
            'TABPY_PWD_FILE = {}\n'
            'TABPY_STATE_PATH = {}'.format(
                cls.pwd_file.name,
                cls.state_dir))
        cls.config_file.close()

        cls.script =\
            '{"data":{"_arg1":[2,3],"_arg2":[3,-1]},'\
            '"script":"res=[]\\nfor i in range(len(_arg1)):\\n  '\
            'res.append(_arg1[i] * _arg2[i])\\nreturn res"}'

    @classmethod
    def tearDownClass(cls):
        cls.patcher.stop()
        os.remove(cls.pwd_file.name)
        os.remove(cls.state_file.name)
        os.remove(cls.config_file.name)
        os.rmdir(cls.state_dir)

    def get_app(self):
        self.app = TabPyApp(self.config_file.name)
        return self.app._create_tornado_web_app()

    def test_no_creds_required_auth_fails(self):
        response = self.fetch(
            '/evaluate',
            method='POST',
            body=self.script)
        self.assertEqual(401, response.code)

    def test_invalid_creds_fails(self):
        response = self.fetch(
            '/evaluate',
            method='POST',
            body=self.script,
            headers={
                'Authorization': 'Basic {}'.
                format(
                    base64.b64encode('user:wrong_password'.encode('utf-8')).
                    decode('utf-8'))
            })
        self.assertEqual(401, response.code)

    def test_valid_creds_pass(self):
        response = self.fetch(
            '/evaluate',
            method='POST',
            body=self.script,
            headers={
                'Authorization': 'Basic {}'.
                format(
                    base64.b64encode('username:password'.encode('utf-8')).
                    decode('utf-8'))
            })
        self.assertEqual(200, response.code)
