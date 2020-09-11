from tabpy.tabpy_server.app.app_parameters import SettingsParameters
from tabpy.tabpy_server.handlers import ManagementHandler
import os
from tabpy.tabpy_server.handlers.util import AuthErrorStates


_QUERY_OBJECT_STAGING_FOLDER = "staging"


class UploadDestinationHandler(ManagementHandler):
    def initialize(self, app):
        super(UploadDestinationHandler, self).initialize(app)

    def get(self):
        if self.should_fail_with_auth_error() != AuthErrorStates.NONE:
            self.fail_with_auth_error()
            return

        path = self.settings[SettingsParameters.StateFilePath]
        path = os.path.join(path, _QUERY_OBJECT_STAGING_FOLDER)
        self.write({"path": path})
