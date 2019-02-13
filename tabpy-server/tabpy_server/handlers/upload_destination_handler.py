from tabpy_server.handlers import ManagementHandler
import os


_QUERY_OBJECT_STAGING_FOLDER = 'staging'


class UploadDestinationHandler(ManagementHandler):
    def initialize(self):
        super(UploadDestinationHandler, self).initialize()

    def get(self):
        path = self.settings['state_file_path']
        path = os.path.join(path, _QUERY_OBJECT_STAGING_FOLDER)
        self.write({"path": path})
