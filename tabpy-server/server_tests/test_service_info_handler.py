from tornado.testing import AsyncHTTPTestCase
from tabpy_server.app import TabPyApp
import simplejson as json
from tabpy_server import __version__
import tempfile, os


def _create_expected_info_response(settings, tabpy_state):
    """
    Create the expected
    :param settings:
    :param state:
    :return:
    """
    response = {}
    response['description'] = tabpy_state.get_description()
    response['creation_time'] = tabpy_state.creation_time
    response['state_path'] = settings['state_file_path']
    response['server_version'] = settings['server_version']
    response['name'] = tabpy_state.name
    response['version'] = __version__
    response['features'] = settings['features']
    return response


def _get_app_and_state(config_file=None):
    tabpy_app = TabPyApp(config_file=config_file)
    tornado_app = tabpy_app._create_tornado_web_app()

    return tornado_app, tabpy_app.settings, tabpy_app.tabpy_state


class TestServiceInfoHandlerDefault(AsyncHTTPTestCase):
    def get_app(self):
        app, self.settings, self.state = _get_app_and_state()
        return app

    def test_info(self):
        response = self.fetch('/info')
        self.assertEqual(response.code, 200)
        actual_response = json.loads(response.body)
        expected_response = _create_expected_info_response(self.settings, self.state)

        self.assertDictEqual(actual_response, expected_response)


class TestServiceInfoHandlerWithAuth(AsyncHTTPTestCase):
    def get_app(self):
        test_config = tempfile.NamedTemporaryFile(prefix='___TestServiceInfoHandlerWithAuth_', suffix='.conf',
                                                  delete=False)
        test_pwd_file = tempfile.NamedTemporaryFile(prefix='___TestServiceInfoHandlerWithAuth_', suffix='.txt')

        config = '[TabPy]\n' \
                 'TABPY_PWD_FILE = {}\n' \
                 'TABPY_STATE_PATH = ./tabpy-server/tabpy_server'.format(test_pwd_file.name)
        test_config.write(bytes(config, 'utf-8'))
        test_config.close()

        app, self.settings, self.state = _get_app_and_state(test_config.name)

        os.remove(test_config.name)

        return app

    def test_info(self):
        response = self.fetch('/info')
        self.assertEqual(response.code, 200)
        actual_response = json.loads(response.body)
        expected_response = _create_expected_info_response(self.settings, self.state)

        self.assertDictEqual(actual_response, expected_response)
        self.assertTrue('features' in actual_response)
        features = actual_response['features']
        self.assertDictEqual({
            'authentication': {
                'methods': {
                    'basic-auth': {}
                },
                'required': 'true',
            }
        }, features)
