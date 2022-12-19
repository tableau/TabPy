import base64
import binascii
import concurrent
import json
import logging
import tornado.web
import uuid




class BaseStaticHandler(tornado.web.StaticFileHandler):
    def set_extra_headers(self, path):
        # set content type to application/json
        self.set_header("TestHeader", "ThisIsATest")
        #self._headers["testheader"] = "test"
