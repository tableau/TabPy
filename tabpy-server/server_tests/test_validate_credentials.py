import base64
import hashlib
import logging
import pathlib
import os
import unittest
from argparse import Namespace
from tempfile import NamedTemporaryFile

from tabpy_server.handlers.util import(validate_basic_auth_credentials,
    handle_authentication, check_and_validate_basic_auth_credentials)

from unittest.mock import patch, call

class TestValidateBasicAuthCredentials(unittest.TestCase):
    def setUp(self):
        self.credentials = {
            # SHA3('password')
            'user1': 'c0067d4af4e87f00dbac63b6156828237059172d1bbeac67427345d6a9fda484'
        }
    
    
    def test_given_unknown_username_expect_validation_fails(self):
        self.assertFalse(validate_basic_auth_credentials('user2', 'pwd@2', self.credentials))


    def test_given_wrong_password_expect_validation_fails(self):
        self.assertFalse(validate_basic_auth_credentials('user1', 'password#1', self.credentials))


    def test_given_valid_creds_expect_validation_passes(self):
        self.assertTrue(validate_basic_auth_credentials('user1', 'password', self.credentials))


    def test_given_valid_creds_uppercase_username_expect_validation_passes(self):
        self.assertTrue(validate_basic_auth_credentials('UsEr1', 'password', self.credentials))


class TestCheckAndValidateBasicAuthCredentials(unittest.TestCase):
    def setUp(self):
        self.credentials = {
            # SHA3('password')
            'user1': 'c0067d4af4e87f00dbac63b6156828237059172d1bbeac67427345d6a9fda484'
        }


    def test_given_no_headers_expect_validation_fails(self):
        self.assertFalse(check_and_validate_basic_auth_credentials({}, self.credentials))


    def test_given_bad_auth_header_expect_validation_fails(self):
        self.assertFalse(check_and_validate_basic_auth_credentials(
            {
                'Authorization': 'Some unexpected string'
            }, self.credentials))

    def test_given_bad_encoded_credentials_expect_validation_fails(self):
        self.assertFalse(check_and_validate_basic_auth_credentials(
            {
                'Authorization': 'Basic abc'
            }, self.credentials))


    def test_given_malformed_credentials_expect_validation_fails(self):
        self.assertFalse(check_and_validate_basic_auth_credentials(
            {
                'Authorization': 'Basic {}'.format(base64.b64encode('user1-password'.encode('utf-8')).decode('utf-8'))
            }, self.credentials))


    def test_given_unknown_username_expect_validation_fails(self):
        self.assertFalse(check_and_validate_basic_auth_credentials(
            {
                'Authorization': 'Basic {}'.format(base64.b64encode('unknown_user:password'.encode('utf-8')))
            }, self.credentials))


    def test_given_wrong_pwd_expect_validation_fails(self):
        self.assertFalse(check_and_validate_basic_auth_credentials(
            {
                'Authorization': 'Basic {}'.format(base64.b64encode('user1:p@ssw0rd'.encode('utf-8')))
            }, self.credentials))


    def test_given_valid_creds_expect_validation_passes(self):
        b64_username_pwd = base64.b64encode('user1:password'.encode('utf-8')).decode('utf-8')
        self.assertTrue(check_and_validate_basic_auth_credentials(
            {
                'Authorization': 'Basic {}'.format(b64_username_pwd)
            }, self.credentials))


class TestHandleAuthentication(unittest.TestCase):
    def setUp(self):
        self.credentials = {
            # SHA3('password')
            'user1': 'c0067d4af4e87f00dbac63b6156828237059172d1bbeac67427345d6a9fda484'
        }

        self.settings = {
            'versions': 
            {
                'v0.1a':
                {
                    'features': {}
                },
                'v0.2beta': 
                {
                    'features':
                    {
                        'authentication':
                        {
                            'required': True,
                        }
                    }
                },
                'v0.3gamma': 
                {
                    'features':
                    {
                        'authentication':
                        {
                            'required': True,
                            'methods':
                            {
                                'unknown-auth': {}
                            }
                        }
                    }
                },
                'v0.4yota': {},
                'v1': 
                {
                    'features':
                    {
                        'authentication':
                        {
                            'required': True,
                            'methods':
                            {
                                'basic-auth': {}
                            }
                        }
                    }
                }
            }
        }


    def test_given_no_api_version_expect_failure(self):
        self.assertFalse(handle_authentication({}, '', self.settings, self.credentials))

    
    def test_given_unknown_api_version_expect_failure(self):
        self.assertFalse(handle_authentication({}, 'v0.314p', self.settings, self.credentials))

    
    def test_given_auth_is_not_configured_expect_success(self):
        self.assertTrue(handle_authentication({}, 'v0.1a', self.settings, self.credentials))


    def test_given_auth_method_not_provided_expect_failure(self):
        self.assertFalse(handle_authentication({}, 'v0.2beta', self.settings, self.credentials))


    def test_given_auth_method_is_unknown_expect_failure(self):
        self.assertFalse(handle_authentication({}, 'v0.3gamma', self.settings, self.credentials))


    def test_given_features_not_configured_expect_success(self):
        self.assertTrue(handle_authentication({}, 'v0.4yota', self.settings, self.credentials))


    def test_given_headers_not_provided_expect_failure(self):
        self.assertFalse(handle_authentication({}, 'v1', self.settings, self.credentials))

    
    def test_given_valid_creds_expect_success(self):
        b64_username_pwd = base64.b64encode('user1:password'.encode('utf-8')).decode('utf-8')
        self.assertTrue(handle_authentication(
            {
                'Authorization': 'Basic {}'.format(b64_username_pwd)
            },
            'v1',
            self.settings,
            self.credentials))
