# Eyegrade: grading multiple choice questions with a webcam
# Copyright (C) 2010-2011 Jesus Arias Fisteus
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see
# <http://www.gnu.org/licenses/>.
#
from __future__ import division

import sys
import os
from optparse import OptionParser
import time
import webbrowser

# Local imports
import imageproc
import utils
import qtgui.gui as gui

utils.EyegradeException.register_error('no_camera',
    'There is no suitable webcam. Eyegrade needs a webcam to work.\n'
    'If your computer already has a camera, check that it is not being\n'
    'used by another application.')

param_fps = 8
capture_period = 1.0 / param_fps

def read_cmd_options():
    parser = OptionParser(usage = 'usage: %prog [options] EXAM_CONFIG_FILE',
                          version = utils.program_name + ' ' + utils.version)
    parser.add_option('-a', '--answers-file', dest = 'answers_filename',
                      help = 'write students answers to FILENAME')
    parser.add_option('-s', '--start-id', dest = 'start_id', type = 'int',
                      help = 'start at the given exam id',
                      default = 1)
    parser.add_option('-o', '--output-dir', dest = 'output_dir', default = '.',
                      help = 'store captured images at the given directory')
    parser.add_option('-d', '--debug', action='store_true', dest = 'debug',
                      default = False, help = 'activate debugging features')
    parser.add_option('-c', '--camera', type='int', dest = 'camera_dev',
                      help = 'camera device to be selected (-1 for default)')
    parser.add_option('--stats', action='store_true', dest = 'save_stats',
                      default = False,
                      help = 'save performance stats to the answers file')
    parser.add_option('-l', '--id-list', dest = 'ids_file', default = None,
                      help = 'file with the list of valid student ids')
    parser.add_option('--capture-raw', dest = 'raw_file', default = None,
                      help = 'capture from raw file')
    parser.add_option('--capture-proc', dest = 'proc_file', default = None,
                      help = 'capture from pre-processed file')
    parser.add_option('--fixed-hough', dest = 'fixed_hough', default = None,
                      type = 'int', help = 'fixed Hough transform threshold')
    parser.add_option('-f', '--ajust-first', action='store_true',
                      dest = 'adjust', default = False,
                      help = 'don\'t lock on an exam until SPC is pressed')
    parser.add_option('--accept-model-0', action='store_true',
                      dest = 'accept_model_0', default = False,
                      help = 'accept model 0 as a valid exam model')

    (options, args) = parser.parse_args()
    if len(args) == 1:
        options.ex_data_filename = args[0]
    elif len(args) == 0:
        parser.error('Exam configuration file required')
    elif len(args) > 1:
        parser.error('Too many input command-line parameters')
    if options.raw_file is not None and options.proc_file is not None:
        parser.error('--capture-raw and --capture-proc are mutually exclusive')
    return options

def cell_clicked(image, point):
    min_dst = None
    clicked_row = None
    clicked_col = None
    for i, row in enumerate(image.centers):
        for j, center in enumerate(row):
            dst = imageproc.distance(point, center)
            if min_dst is None or dst < min_dst:
                min_dst = dst
                clicked_row = i
                clicked_col = j
    if (min_dst is not None and
        min_dst <= image.diagonals[clicked_row][clicked_col] / 2):
        return (clicked_row, clicked_col + 1)
    else:
        return None

def dump_camera_buffer(camera, delay_suffered):
    if camera is not None and delay_suffered > 0.1:
        frames_to_drop = min(8, int(1 + (delay_suffered - 0.1) / 0.04))
        for i in range(0, frames_to_drop):
            imageproc.capture(camera, False)

def select_camera(options, config):
    if options.camera_dev is None:
        camera = config['camera-dev']
    else:
        camera = options.camera_dev
    return camera


class ImageDetectTask(object):
    def __init__(self, image):
        self.image = image

    def run(self):
        from PyQt4.QtCore import QThread
        print 'processing starts', QThread.currentThreadId()
        self.image.detect_safe()
        print 'processing ends'


class GradingSession(object):
    """Manages a grading session."""

    mode_no_session = 0
    mode_search = 1
    mode_review = 2
    mode_manual_detect = 3

    def __init__(self, interface):
        self.interface = interface
        ## self.imageproc_context = imageproc.ExamCaptureContext()
        ## self.imageproc_options = imageproc.ExamCapture.get_default_options()
        ## self.imageproc_context.init_camera(0)
        self.mode = GradingSession.mode_no_session
        self.config = utils.read_config()
        self._register_listeners()

    def _start_search_mode(self):
        self.mode = GradingSession.mode_search
        self.interface.activate_search_mode()
        self.exam = None
        self.latest_graded_exam = None
        self.latest_image = None
        self.interface.update_text('', 'Searching...')
        self.interface.register_timer(50, self._next_search)
        dump_camera_buffer(self.imageproc_context.camera, 1.0)
        self.next_capture = time.time() + 0.05

    def _start_review_mode(self):
        self.mode = GradingSession.mode_review
        self.interface.activate_review_mode()
        self.interface.display_capture(self.exam.image.image_drawn)
        self.interface.update_text_up(self.exam.get_student_id_and_name())
        if self.exam.score is not None:
            self.interface.update_status(self.exam.score,
                                         model=self.exam.model,
                                         seq_num=self.exam.im_id,
                                         survey_mode=self.exam_data.survey_mode)
        else:
            self.interface.update_text_down('')
        if not self.exam.image.status['infobits']:
            self.interface.enable_manual_detect(True)

    def _start_manual_detect_mode(self):
        self.mode = GradingSession.mode_manual_detect
        self.interface.activate_manual_detect_mode()
        self.interface.display_capture(self.exam.image.image_drawn)
        self.interface.update_text_up('')
        self.interface.update_text_down( \
            'Manual detection: click on the outer corners of the answer tables')
        self.manual_points = []

    def _next_search(self):
        if self.mode != GradingSession.mode_search:
            return
        image = imageproc.ExamCapture(self.exam_data.dimensions,
                                      self.imageproc_context,
                                      self.imageproc_options)
        self.latest_image = image
        task = ImageDetectTask(image)
        self.interface.run_worker(task, self._after_image_detection)

    def _after_image_detection(self):
        print 'Image processed'
        image = self.latest_image
        exam = self._process_capture(image)
        if exam is None or not image.success:
            if exam is not None:
                exam.draw_answers()
            else:
                image.draw_status()
            self.interface.display_capture(image.image_drawn)
            self._schedule_next_capture()
        else:
            exam.lock_capture()
            exam.draw_answers()
            self.exam = exam
            self._start_review_mode()

    def _schedule_next_capture(self):
        """Schedules the next image capture and registers the timer.

        Call it from search mode, after an image has been processed.

        """
        current_time = time.time()
        self.next_capture += capture_period
        if current_time > self.next_capture:
            dump_camera_buffer(self.imageproc_context.camera,
                               current_time - self.next_capture)
            wait = 0.010
            self.next_capture = time.time() + 0.010
        else:
            wait = self.next_capture - current_time
        self.interface.register_timer(int(wait * 1000), self._next_search)

    def _process_capture(self, image):
        """Processes a captured image."""
        exam = None
        if image.status['infobits']:
            model = utils.decode_model(image.bits)
            if model is not None and (model in self.exam_data.solutions
                                      or self.exam_data.survey_mode):
                exam = utils.Exam(image, model, self._solutions(model),
                                  self.valid_student_ids,
                                  self.image_id, self.exam_data.score_weights,
                                  save_image_func=self.interface.save_capture)
                exam.grade()
                self.latest_graded_exam = exam
        return exam

    def _new_session(self):
        """Callback for when the new session action is selected."""
        values = self.interface.dialog_new_session()
        if values is not None:
            # Save the exam config file augmented with session information
            self.exam_data = utils.ExamConfig(values['config'])
            self.exam_data.session['is-session'] = True
            if values['id_list']:
                self.exam_data.session['student-ids-file'] = values['id_list']
            else:
                self.exam_data.session['student-ids-file'] = None
            self.exam_data.session['save-filename-pattern'] = \
                self.config['save-filename-pattern']
            filename = os.path.join(values['directory'], 'session.eye')
            self.exam_data.save(filename)
            self.session_dir = values['directory']
            self._start_session()

    def _open_session(self):
        """Callback for when the open session action is selected."""
        filename = self.interface.dialog_open_session()
        if not filename:
            return
        self.exam_data = utils.ExamConfig(filename)
        if (self.exam_data.session == {}
            or not self.exam_data.session['is-session']):
            self.interface.show_error(('The file you selected contains no '
                                       'valid session.'))
            return
        self.session_dir = os.path.dirname(filename)
        self._start_session()

    def _close_session(self):
        """Callback that closes the current session."""
        if (self.mode == GradingSession.mode_review
            or self.mode == GradingSession.mode_manual_detect):
            if not self.interface.show_warning( \
                ('The current capture has not been saved and will be lost. '
                 'Are you sure you want to close this session?'),
                is_question=True):
                return
        self.imageproc_context.close_camera()
        self.mode = GradingSession.mode_no_session
        self.exam_data = None
        self.valid_student_ids = None
        self.imageproc_options = None
        self.imageproc_context = None
        self.save_pattern = None
        self.answers_file = None
        self.interface.activate_no_session_mode()

    def _exit_application(self):
        """Callback for when the user wants to exit the application."""
        if (self.mode == GradingSession.mode_review
            or self.mode == GradingSession.mode_manual_detect):
            if not self.interface.show_warning( \
                ('The current capture has not been saved and will be lost. '
                 'Are you sure you want to exit the application?'),
                is_question=True):
                return False
        return True

    def _action_snapshot(self):
        """Callback for the snapshot action."""
        if self.latest_graded_exam is None:
            if self.latest_image is None:
                return
            image = self.latest_image
            image.clean_drawn_image()
            if image.status['infobits']:
                model = utils.decode_model(image.bits)
            else:
                model = None
            self.exam = utils.Exam(image, model, {}, self.valid_student_ids,
                                   self.image_id, self.exam_data.score_weights,
                                   save_image_func=self.interface.save_capture)
            self.exam.grade()
            self.exam.lock_capture()
        else:
            self.exam = self.latest_graded_exam
            self.exam.image.clean_drawn_image()
            self.exam.lock_capture()
            self.exam.draw_answers()
        self._start_review_mode()

    def _action_discard(self):
        """Callback for cancelling the current capture."""
        self._start_search_mode()

    def _action_save(self):
        """Callback for saving the current capture."""
        self.exam.save_image(self.save_pattern)
        self.exam.save_answers(self.answers_file, self.config['csv-dialect'])
        self.image_id += 1
        self._start_search_mode()

    def _action_manual_detect(self):
        """Callback for the manual detection action."""
        from_search_mode = self.mode == GradingSession.mode_search
        if from_search_mode:
            # Take the current snapshot and go to review mode
            self.exam = utils.Exam(self.latest_image, None, {},
                                   self.valid_student_ids,
                                   self.image_id, self.exam_data.score_weights,
                                   save_image_func=self.interface.save_capture)
            self.exam.lock_capture()
        self.exam.image.clean_drawn_image()
        self._start_manual_detect_mode()

    def _action_edit_id(self):
        """Callback for the edit student id action."""
        if self.mode != GradingSession.mode_review:
            return
        students = self.exam.ranked_student_ids_and_names()
        student = self.interface.dialog_student_id(students)
        if student is not None:
            if student == '':
                self.exam.update_student_id(None)
            else:
                student_id, name = self._parse_student(student)
                if student_id is not None:
                    self.exam.update_student_id(student_id, name=name)
                else:
                    self.interface.show_error( \
                        'You typed and incorrect student id.')
            self.interface.update_text_up(self.exam.get_student_id_and_name())

    def _action_help(self):
        """Callback for the help action."""
        webbrowser.open(utils.help_location, new=2)

    def _action_website(self):
        """Callback for the website action."""
        webbrowser.open(utils.web_location, new=2)

    def _mouse_pressed(self, point):
        """Callback called when the mouse is pressed inside a capture."""
        if self.mode == GradingSession.mode_review:
            self._mouse_pressed_change_answer(point)
        elif self.mode == GradingSession.mode_manual_detect:
            self._mouse_pressed_manual_detection(point)

    def _digit_pressed(self, digit_string):
        """Callback called when a digit is pressed."""
        if self.mode == GradingSession.mode_review:
            pass

    def _mouse_pressed_change_answer(self, point):
        cell = self.exam.image.cell_clicked(point)
        if cell is not None:
            question, answer = cell
            self.exam.toggle_answer(question, answer)
            self.interface.display_capture(self.exam.image.image_drawn)
            self.interface.update_status(self.exam.score, self.exam.model,
                                         self.exam.im_id,
                                         survey_mode=self.exam_data.survey_mode)

    def _mouse_pressed_manual_detection(self, point):
        success = False
        self.manual_points.append(point)
        self.exam.image.draw_corner(point)
        self.interface.display_capture(self.exam.image.image_drawn)
        if len(self.manual_points) == 4 * len(self.exam.image.boxes_dim):
            corner_matrixes = imageproc.process_box_corners(
                self.manual_points, self.exam.image.boxes_dim)
            if corner_matrixes != []:
                self.exam.image.detect_manual(corner_matrixes)
                if self.exam.image.status['infobits']:
                    self.exam.model = utils.decode_model(self.exam.image.bits)
                    if self.exam.model is not None:
                        self.exam.solutions = self._solutions(self.exam.model)
                        self.exam.grade()
                        self.exam.draw_answers()
                        self.interface.update_status( \
                            self.exam.score, self.exam.model, self.exam.im_id,
                            survey_mode=self.exam_data.survey_mode)
                        success = True
            if not success:
                self.exam.image.clean_drawn_image()
                self.interface.show_error('Manual detection failed!')
            self._start_review_mode()

    def _start_session(self):
        """Starts a session (either a new one or one that has been loaded)."""
        exam_data = self.exam_data
        session_cfg = exam_data.session
        self.save_pattern = os.path.join(self.session_dir,
                                         session_cfg['save-filename-pattern'])
        self.answers_file = os.path.join(self.session_dir,
                                         'eyegrade-answers.csv')
        if exam_data.session['student-ids-file'] is not None:
            self.valid_student_ids = utils.read_student_ids( \
                filename=exam_data.session['student-ids-file'],
                with_names=True)
        else:
            self.valid_student_ids = None
        self.imageproc_options = imageproc.ExamCapture.get_default_options()
        if exam_data.id_num_digits and exam_data.id_num_digits > 0:
            self.imageproc_options['read-id'] = True
            self.imageproc_options['id-num-digits'] = exam_data.id_num_digits
        self.imageproc_options['left-to-right-numbering'] = \
                                            exam_data.left_to_right_numbering
        self.imageproc_context = imageproc.ExamCaptureContext()
        self.imageproc_context.init_camera(self.config['camera-dev'])
        if self.imageproc_context.camera is None:
            self.interface.show_error('No camera found. Connect a camera.')
            return
        self.image_id = 1
        self._start_search_mode()

    def _solutions(self, model):
        """Returns the solutions for the given model, or []."""
        if not self.exam_data.survey_mode:
            return self.exam_data.solutions[model]
        else:
            return []

    def _parse_student(self, student):
        """Parses a string with student id (first) and student name.

        Returns the tuple (student_id, student_name).  If the student
        id is not valid (incorrect length or contains non-digits)
        returns (None, None). The returned name is None if not present
        in the parsed string.

        """
        student_id = None
        name = None
        parts = [p for p in student.split(' ') if p.strip()]
        if len(parts) > 0:
            student_id = parts[0]
            if len(parts) > 1:
                name = ' '.join(parts[1:])
            if (self.exam_data.id_num_digits > 0
                and len(student_id) != self.exam_data.id_num_digits
                or not min([c.isdigit() for c in student_id])):
                student_id = None
        if student_id is None:
            name = None
        return student_id, name

    def _register_listeners(self):
        listeners = {
            ('actions', 'session', 'new'): self._new_session,
            ('actions', 'session', 'open'): self._open_session,
            ('actions', 'session', 'close'): self._close_session,
            ('actions', 'grading', 'snapshot'): self._action_snapshot,
            ('actions', 'grading', 'discard'): self._action_discard,
            ('actions', 'grading', 'save'): self._action_save,
            ('actions', 'grading', 'manual_detect'): self._action_manual_detect,
            ('actions', 'grading', 'edit_id'): self._action_edit_id,
            ('actions', 'help', 'help'): self._action_help,
            ('actions', 'help', 'website'): self._action_website,
            ('center_view', 'camview', 'mouse_pressed'): self._mouse_pressed,
            ('window', 'exit'): self._exit_application,
        }
        self.interface.register_listeners(listeners)


def main():
    interface = gui.Interface(False, False, sys.argv)
    session = GradingSession(interface)
    interface.run()

if __name__ == '__main__':
    try:
        main()
    except utils.EyegradeException as ex:
        print >>sys.stderr, ex
        sys.exit(1)
