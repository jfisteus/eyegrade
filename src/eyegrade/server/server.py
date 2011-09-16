import cherrypy
import array
import os
import logging

import eyegrade.server.utils as utils
import eyegrade.imageproc as imageproc
import eyegrade.utils

# Needs CherryPy 3.2 or later.

class EyegradeServer(object):

    def error_page_404(status, message, traceback, version):
        return 'Error 404 - Not Found'
    cherrypy.config.update({'error_page.404': error_page_404})

    def index(self):
        raise cherrypy.HTTPError('404 Not Found', 'Resource not available')
    index.exposed = True

    def init(self):
        data = cherrypy.request.body.read()
        exam_config = eyegrade.utils.ExamConfig()
        exam_config.read(data=data)
        cherrypy.session['exam_config'] = exam_config
        cherrypy.session['imageproc_context'] = imageproc.ExamCaptureContext()
        cherrypy.session['student_ids'] = None
        cherrypy.log('New context created')
        return 'OK'
    init.exposed = True

    def process(self):
        if not 'exam_config' in cherrypy.session:
            raise cherrypy.HTTPError('403 Forbidden',
                                     'Please, send exam configuration first')
        bitmap = array.array('B')
        while True:
            data = cherrypy.request.body.fp.read(8192)
            if not data:
                break
            bitmap.extend(map(ord, data))
        imageproc_context = cherrypy.session['imageproc_context']
        exam_config = cherrypy.session['exam_config']
        student_ids = cherrypy.session['student_ids']
        output = utils.process_exam(bitmap, imageproc_context,
                                    exam_config, student_ids)
        return output
    process.exposed = True

    def students(self):
        if not 'exam_config' in cherrypy.session:
            raise cherrypy.HTTPError('403 Forbidden',
                                     'Please, send exam configuration first')
        data = cherrypy.request.body.read()
        student_ids = eyegrade.utils.read_student_ids(data=data,
                                                      with_names=True)
        cherrypy.session['student_ids'] = student_ids
        return 'OK'
    students.exposed = True

    def close(self):
        if not 'exam_config' in cherrypy.session:
            raise cherrypy.HTTPError('403 Forbidden',
                                     'Session was not open')
        cherrypy.session.clear()
        cherrypy.lib.sessions.expire()
        return 'OK'
    close.exposed = True

if __name__ == '__main__':
    config_file = os.path.expanduser('~/.eyegrade-server.cfg')
    if not os.path.isfile(config_file):
        config_file = None
    cherrypy.quickstart(EyegradeServer(), config=config_file)
