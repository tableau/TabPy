import json
from tabpy_server.handlers import ManagementHandler


class ServiceInfoHandler(ManagementHandler):
    def initialize(self, app):
        super(ServiceInfoHandler, self).initialize(app)

    def get(self):
        # do not check for authentication - this method
        # is the only way for client to collect info about
        # supported API versions and required features
        self._add_CORS_header()
        info = {}
        info['description'] = self.tabpy_state.get_description()
        info['creation_time'] = self.tabpy_state.creation_time
        info['state_path'] = self.settings['state_file_path']
        info['server_version'] = self.settings['server_version']
        info['name'] = self.tabpy_state.name
        info['versions'] = self.settings['versions']
        self.write(json.dumps(info))
