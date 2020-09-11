import json
from tabpy.tabpy_server.app.app_parameters import SettingsParameters
from tabpy.tabpy_server.handlers import ManagementHandler
from tabpy.tabpy_server.handlers.util import AuthErrorStates

class ServiceInfoHandler(ManagementHandler):
    def initialize(self, app):
        super(ServiceInfoHandler, self).initialize(app)

    def get(self):
        if self.should_fail_with_auth_error() != AuthErrorStates.NONE:
            self.fail_with_auth_error()
            return

        self._add_CORS_header()
        info = {}
        info["description"] = self.tabpy_state.get_description()
        info["creation_time"] = self.tabpy_state.creation_time
        info["state_path"] = self.settings[SettingsParameters.StateFilePath]
        info["server_version"] = self.settings[SettingsParameters.ServerVersion]
        info["name"] = self.tabpy_state.name
        info["versions"] = self.settings[SettingsParameters.ApiVersions]
        self.write(json.dumps(info))
