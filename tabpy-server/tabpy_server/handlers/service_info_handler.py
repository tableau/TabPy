import simplejson
from tabpy_server import __version__
from tabpy_server.handlers import ManagementHandler


class ServiceInfoHandler(ManagementHandler):
    def initialize(self):
        super(ServiceInfoHandler, self).initialize()

    def get(self):
        self._add_CORS_header()
        info = {}
        info['description'] = self.tabpy.get_description()
        info['creation_time'] = self.tabpy.creation_time
        info['state_path'] = self.settings['state_file_path']
        info['server_version'] = self.settings['server_version']
        info['name'] = self.tabpy.name
        info['version'] = __version__
        self.write(simplejson.dumps(info))

