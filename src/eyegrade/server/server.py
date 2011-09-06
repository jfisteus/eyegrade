import cherrypy
import array
import os

import eyegrade.server.utils as utils

# Needs CherryPy 3.2 or later.

class EyegradeServer(object):

    def error_page_404(status, message, traceback, version):
        return 'Error 404 - Not Found'
    cherrypy.config.update({'error_page.404': error_page_404})

    def index(self):
        raise cherrypy.HTTPError('404 Not Found', 'Resource not available')
    index.exposed = True

    def process(self):
        bitmap = array.array('B')
        while True:
            data = cherrypy.request.body.fp.read(8192)
            if not data:
                break
            bitmap.extend(map(ord, data))
        output = utils.process_exam(bitmap)
        return output
    process.exposed = True

if __name__ == '__main__':
    config_file = os.path.expanduser('~/.eyegrade-server.cfg')
    if not os.path.isfile(config_file):
        config_file = None
    cherrypy.quickstart(EyegradeServer(), config=config_file)
