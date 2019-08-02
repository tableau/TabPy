import logging
from tabpy.tabpy_server.app.SettingsParameters import SettingsParameters
from tabpy.tabpy_server.handlers import ManagementHandler
import os


_QUERY_OBJECT_STAGING_FOLDER = 'staging'


class UploadDestinationHandler(ManagementHandler):
    def initialize(self, app):
        super(UploadDestinationHandler, self).initialize(app)

    def get(self):
        if self.should_fail_with_not_authorized():
            self.fail_with_not_authorized()
            return

        path = self.settings[SettingsParameters.StateFilePath]
        path = os.path.join(path, _QUERY_OBJECT_STAGING_FOLDER)
        self.write({"path": path})
