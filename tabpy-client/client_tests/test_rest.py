import unittest
import json
import sys

try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock

import requests


from tabpy_client.rest import *

class TestRequestsNetworkWrapper(unittest.TestCase):

    def test_init(self):
        rnw = RequestsNetworkWrapper()


    def test_init_with_session(self):
        session = {}

        rnw = RequestsNetworkWrapper(session=session)

        self.assertIs(session, rnw.session)

    def setUp(self):
        def mock_response(status_code):
            response = Mock(requests.Response())
            response.json.return_value = 'json'
            response.status_code = status_code

            return response

        session = Mock(requests.session())
        session.get.return_value = mock_response(200)
        session.post.return_value = mock_response(200)
        session.put.return_value = mock_response(200)
        session.delete.return_value = mock_response(204)

        self.rnw = RequestsNetworkWrapper(session=session)

    def test_GET(self):
        url = 'abc'
        data = {'foo':'bar'}
        self.assertEqual(self.rnw.GET(url, data), 'json')
        self.rnw.session.get.assert_called_once_with(url,
            params=data,
            timeout=None)

    def test_GET_InvalidData(self):
        url = 'abc'
        data = {'cat'}
        try:
            self.assertEqual(self.rnw.GET(url, data), 'json')
        except:
            e=sys.exc_info()[0]
            self.assertEquals(e,TypeError)

    def test_GET_InvalidURL(self):
        url = ''
        data = {'foo':'bar'}
        try:
            self.assertEqual(self.rnw.GET(url, data), 'json')
        except:
            e=sys.exc_info()[0]
            self.assertEquals(e,TypeError)

    def test_POST(self):
        url = 'abc'
        data = {'foo':'bar'}
        self.assertEqual(self.rnw.POST(url, data), 'json')
        self.rnw.session.post.assert_called_once_with(url,
            data=json.dumps(data),
            headers={'content-type':'application/json'},
            timeout=None)

    def test_POST_InvalidURL(self):
        url = ''
        data = {'foo':'bar'}
        try:
            self.assertEqual(self.rnw.POST(url, data), 'json')
        except:
            e=sys.exc_info()[0]
            self.assertEquals(e,TypeError)

    def test_POST_InvalidData(self):
        url = 'url'
        data = {'cat'}
        try:
            self.assertEqual(self.rnw.POST(url, data), 'json')
        except:
            e=sys.exc_info()[0]
            self.assertEquals(e,TypeError)

    def test_PUT(self):
        url = 'abc'
        data = {'foo':'bar'}
        self.assertEqual(self.rnw.PUT(url, data), 'json')
        self.rnw.session.put.assert_called_once_with(url,
            data=json.dumps(data),
            headers={'content-type':'application/json'},
            timeout=None)

    def test_PUT_InvalidData(self):
        url = 'url'
        data = {'cat'}
        try:
            self.assertEqual(self.rnw.PUT(url, data), 'json')
        except:
            e=sys.exc_info()[0]
            self.assertEquals(e,TypeError)

    def test_PUT_InvalidURL(self):
        url = ''
        data = {'foo:bar'}
        try:
            self.assertEqual(self.rnw.PUT(url, data), 'json')
        except:
            e=sys.exc_info()[0]
            self.assertEquals(e,TypeError)

    def test_DELETE(self):
        url = 'abc'
        data = {'foo':'bar'}
        self.assertIs(self.rnw.DELETE(url, data), None)
        self.rnw.session.delete.assert_called_once_with(url,
            data=json.dumps(data),
            timeout=None)

    def test_DELETE_InvalidData(self):
        url = 'abc'
        data = {'cat'}
        try:
            self.assertEqual(self.rnw.DELETE(url, data), 'json')
        except:
            e=sys.exc_info()[0]
            self.assertEquals(e,TypeError)

    def test_DELETE_InvalidURL(self):
        url = ''
        data = {'foo:bar'}
        try:
            self.assertEqual(self.rnw.DELETE(url, data), 'json')
        except:
            e=sys.exc_info()[0]
            self.assertEquals(e,TypeError)


class TestServiceClient(unittest.TestCase):

    def setUp(self):
        nw = Mock(RequestsNetworkWrapper())
        nw.GET.return_value = 'GET'
        nw.POST.return_value = 'POST'
        nw.PUT.return_value = 'PUT'
        nw.DELETE.return_value = 'DELETE'

        self.sc = ServiceClient('endpoint', network_wrapper=nw)

    def test_GET(self):
        self.assertEquals(self.sc.GET('test'), 'GET')
        self.sc.network_wrapper.GET.assert_called_once_with('endpoint/test',
            None, None)

    def test_POST(self):
        self.assertEquals(self.sc.POST('test'), 'POST')
        self.sc.network_wrapper.POST.assert_called_once_with('endpoint/test',
            None, None)

    def test_PUT(self):
        self.assertEquals(self.sc.PUT('test'), 'PUT')
        self.sc.network_wrapper.PUT.assert_called_once_with('endpoint/test',
            None, None)

    def test_DELETE(self):
        self.assertEquals(self.sc.DELETE('test'), None)
        self.sc.network_wrapper.DELETE.assert_called_once_with('endpoint/test',
            None, None)
