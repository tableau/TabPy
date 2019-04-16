import logging
from tabpy_server.app.SettingsParameters import SettingsParameters
from tabpy_server.handlers import ManagementHandler
import os


logger = logging.getLogger(__name__)

_QUERY_OBJECT_STAGING_FOLDER = 'staging'


class UploadDestinationHandler(ManagementHandler):
    def initialize(self, app):
        super(UploadDestinationHandler, self).initialize(app)

    def get(self):
        logger.debug(self.append_request_context(
            'Processing GET for /configurations/endpoint_upload_destination'))
        if self.should_fail_with_not_authorized():
            self.fail_with_not_authorized()
            return

        path = self.settings[SettingsParameters.StateFilePath]
        path = os.path.join(path, _QUERY_OBJECT_STAGING_FOLDER)
        self.write({"path": path})
