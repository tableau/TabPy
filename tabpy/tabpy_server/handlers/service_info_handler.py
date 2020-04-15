import json
from tabpy.tabpy_server.app.SettingsParameters import SettingsParameters
from tabpy.tabpy_server.handlers import ManagementHandler


class ServiceInfoHandler(ManagementHandler):
    def initialize(self, app):
        super(ServiceInfoHandler, self).initialize(app)

    def get(self):
        # Optionally check for authentication - this method
        # is the only way for client to collect info about
        # supported API versions and required features so auth is not checked
        # by default.
        # Some clients may wish to lock down the entire API which can be done through
        # the configuration file.

        if self.settings[SettingsParameters.AuthInfo]:
            if self.should_fail_with_not_authorized():
                self.fail_with_not_authorized()
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
