# Eyegrade: grading multiple choice questions with a webcam
# Copyright (C) 2010-2013 Jesus Arias Fisteus
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
import shutil
import time
import webbrowser
import gettext

# Local imports
import imageproc
import utils
import qtgui.gui as gui

t = gettext.translation('eyegrade', utils.locale_dir(), fallback=True)
_ = t.ugettext

utils.EyegradeException.register_error('no_camera',
    _('There is no suitable webcam. Eyegrade needs a webcam to work.\n'
      'If your computer already has a camera, check that it is not being\n'
      'used by another application.'))

param_fps = 8
capture_period = 1.0 / param_fps
capture_change_period = 1.0
capture_change_period_failure = 0.3
after_removal_delay = 1.0

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
    """Used for running image detection in another thread."""
    def __init__(self, image):
        self.image = image

    def run(self):
        self.image.detect_safe()


class ImageChangeTask(object):
    """Used for running image change detection in another thread."""
    def __init__(self, image, reference_image):
        self.image = image
        self.reference_image = reference_image

    def run(self):
        self.image.exam_detected()


class ProgramManager(object):
    """Manages a grading session."""

    mode_no_session = 0
    mode_search = 1
    mode_review = 2
    mode_manual_detect = 3

    def __init__(self, interface, session_file=None):
        self.interface = interface
        self.mode = ProgramManager.mode_no_session
        self.config = utils.config
        self.imageproc_context = \
              imageproc.ExamCaptureContext(camera_id=self.config['camera-dev'])
        self.imageproc_options = None
        self.drop_next_capture = False
        self.dump_buffer = False
        self._register_listeners()
        self.from_manual_detection = False
        if session_file is not None:
            self._try_session_file(session_file)

    def run(self):
        """Starts the program manager."""
        self.interface.run()

    def _try_session_file(self, session_file):
        if os.path.isdir(session_file):
            filename = os.path.join(session_file, 'session.eye')
            if os.path.exists(filename):
                session_file = filename
            else:
                self.interface.show_error(_('The directory has no Eyegrade '
                                            'session') + ': ' + session_file,
                                          _('Error opening the session file'))
                return
        valid, msg = self._validate_session(session_file)
        if not valid:
            if self.exam_data and (self.exam_data.session == {}
                                   or not self.exam_data.session.is_session):
                # It is not a session file. Start the new session wizard.
                values = self.interface.dialog_new_session( \
                                                   config_filename=session_file)
                if values is not None:
                    self._new_session_internal(values)
            else:
                self.interface.show_error(msg,
                                          _('Error opening the session file'))
        else:
            self._start_session()

    def _start_search_mode(self):
        self.mode = ProgramManager.mode_search
        self.from_manual_detection = False
        self.interface.activate_search_mode()
        self.exam = None
        self.latest_graded_exam = None
        self.latest_image = None
        self.interface.update_text('', _('Searching...'))
        self.interface.register_timer(50, self._next_search)
        dump_camera_buffer(self.imageproc_context.camera, 1.0)
        self.next_capture = time.time() + 0.05

    def _start_review_mode(self):
        self.mode = ProgramManager.mode_review
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
        # Automatic detection of exam removal to go to the next exam
        if self.interface.is_action_checked(('tools', 'auto_change')):
            self._start_auto_change_detection()
        self.drop_next_capture = False

    def _start_auto_change_detection(self):
        if not self.from_manual_detection:
            self.change_failures = 0
            self.interface.register_timer(1000, self._next_change_detection)

    def _start_manual_detect_mode(self):
        self.mode = ProgramManager.mode_manual_detect
        self.interface.activate_manual_detect_mode()
        self.interface.display_capture(self.exam.image.image_drawn)
        self.interface.update_text_up('')
        self.interface.update_text_down(_('Manual detection: click on the '
                                        'outer corners of the answer tables'))
        self.manual_points = []

    def _next_search(self):
        if self.mode != ProgramManager.mode_search:
            return
        if self.dump_buffer:
            self.dump_buffer = False
            dump_camera_buffer(self.imageproc_context.camera,
                               after_removal_delay)
        image = imageproc.ExamCapture(self.exam_data.dimensions,
                                      self.imageproc_context,
                                      self.imageproc_options)
        self.current_image = image
        task = ImageDetectTask(image)
        self.interface.run_worker(task, self._after_image_detection)

    def _after_image_detection(self):
        image = self.current_image
        self.current_image = None
        if self.mode != ProgramManager.mode_search:
            # The user switched to other mode while the image was processed
            return
        self.latest_image = image
        if image.status['boxes'] and self.imageproc_context.threshold_locked:
            self.imageproc_context.unlock_threshold()
        exam = self._process_capture(image)
        if exam is None or not image.success:
            if exam is not None:
                exam.draw_answers()
                self.interface.enable_manual_detect(False)
            else:
                image.draw_status()
            self.interface.display_capture(image.image_drawn)
            self._schedule_next_capture(capture_period, self._next_search)
        elif not self.drop_next_capture:
            exam.lock_capture()
            exam.draw_answers()
            self.exam = exam
            self._start_review_mode()
        else:
            # Special mode: do not lock until another capture is
            # available.  Used after auto exam removal detection.
            exam.draw_answers()
            self.interface.display_capture(image.image_drawn)
            self._schedule_next_capture(after_removal_delay, self._next_search)
            self.drop_next_capture = False
            self.dump_buffer = True

    def _next_change_detection(self):
        """Used to detect exam removal.

        This method captures an image and launches its analysis.
        Continuation of work is done at `_after_change_detection`.

        """
        if (self.mode != ProgramManager.mode_review
            or not self.interface.is_action_checked(('tools', 'auto_change'))):
            return
        dump_camera_buffer(self.imageproc_context.camera, 1.0)
        image = imageproc.ExamCapture(self.exam_data.dimensions,
                                      self.imageproc_context,
                                      self.imageproc_options)
        self.current_image = image
        task = ImageChangeTask(image, self.exam.image)
        self.interface.run_worker(task, self._after_change_detection)

    def _after_change_detection(self):
        """Continuation of `_next_change_detection`.

        Executed after the image has been processed. This method decides
        whether the exam has been removed.

        """
        image = self.current_image
        self.current_image = None
        if image is None:
            # This needs to be investigated: this case should never
            # happen, but I saw it happen...
            return
        if (self.mode != ProgramManager.mode_review
            or not self.interface.is_action_checked(('tools', 'auto_change'))):
            return
        exam_removed = False
        if image.exam_detected:
            period = capture_change_period
            self.change_failures = 0
        else:
            period = capture_change_period_failure
            self.change_failures += 1
            if self.change_failures >= 4:
                exam_removed = True
        if not exam_removed:
            self._schedule_next_capture(period, self._next_change_detection)
        else:
            self.imageproc_context.lock_threshold()
            self.drop_next_capture = True
            self._action_save()

    def _schedule_next_capture(self, period, function):
        """Schedules the next image capture and registers the timer.

        Call it from search mode, after an image has been processed, or
        in review mode if automatic exam removal detection is active.

        """
        current_time = time.time()
        self.next_capture += period
        if current_time > self.next_capture:
            dump_camera_buffer(self.imageproc_context.camera,
                               current_time - self.next_capture)
            wait = 0.010
            self.next_capture = time.time() + 0.010
        else:
            wait = self.next_capture - current_time
        self.interface.register_timer(int(wait * 1000), function)

    def _process_capture(self, image):
        """Processes a captured image."""
        exam = None
        if image.status['infobits']:
            model = utils.decode_model(image.bits)
            if model is not None:
                if (model in self.exam_data.solutions
                    or self.exam_data.survey_mode):
                    exam = utils.Exam(image, model, self._solutions(model),
                                  self.valid_student_ids,
                                  self.image_id, self.exam_data.score_weights,
                                  save_image_func=self.interface.save_capture)
                    exam.grade()
                    self.latest_graded_exam = exam
                elif model not in self.exam_data.solutions:
                    msg = _('There are no solutions for model {0}.')\
                          .format(model)
                    self.interface.show_error(msg)
        return exam

    def _new_session(self):
        """Callback for when the new session action is selected."""
        values = self.interface.dialog_new_session()
        if values is not None:
            self._new_session_internal(values)

    def _new_session_internal(self, values):
        """Callback for when the new session action is selected."""
        # Save the exam config file augmented with session information
        self.exam_data = values['config']
        self.exam_data.session['is-session'] = True
        self.exam_data.session['save-filename-pattern'] = \
            self.config['save-filename-pattern']
        dirname = os.path.join(values['directory'], 'student_ids')
        try:
            os.mkdir(dirname)
            if values['id_list_files']:
                for name in values['id_list_files']:
                    ProgramManager._copy_id_list(name, dirname)
        except IOError as e:
            self.interface.show_error(_('Input/output error:')
                                      + ' ' + e.message)
        except Exception as e:
            self.interface.show_error(_('Error:') + ' ' + e.message)
        try:
            dirname = os.path.join(values['directory'], 'captures')
            os.mkdir(dirname)
        except IOError as e:
            self.interface.show_error(_('Input/output error:')
                                      + ' ' + e.message)
        except Exception as e:
            self.interface.show_error(_('Error:') + ' ' + e.message)
        filename = os.path.join(values['directory'], 'session.eye')
        self.exam_data.save(filename)
        self.session_dir = values['directory']
        self._start_session()

    def _open_session(self):
        """Callback for when the open session action is selected."""
        filename = self.interface.dialog_open_session()
        if not filename:
            return
        valid, message = self._validate_session(filename)
        if not valid:
            self.interface.show_error(message)
        else:
            self._start_session()

    def _validate_session(self, filename):
        """Checks that the given session directory is valid.

        It loads and checks the exam configuration file from
        `filename` and checks the directories that should be at the
        directory. The file is stored as self.exam_data, and its directory
        is stored as self.session_dir.

        Returns (valid, error_message) where exam_data is the exam
        configuration object, valid is True if the session is valid
        and error message contains a textal description of the error
        in case the session is not valid.

        """
        self.exam_data = None
        try:
            self.exam_data = utils.ExamConfig(filename)
        except Exception as e:
            return False, _('Error loading the session') + ': ' + str(e)
        if (self.exam_data.session == {}
            or not self.exam_data.session['is-session']):
            return False, _('The file you selected contains no session marks.')
        self.session_dir = os.path.dirname(filename)
        students_dir = os.path.join(self.session_dir, 'student_ids')
        captures_dir = os.path.join(self.session_dir, 'captures')
        if not os.path.exists(students_dir) or not os.path.exists(captures_dir):
            return False, _('The session directory has been corrupted.')
        return True, ''

    def _close_session(self):
        """Callback that closes the current session."""
        if (self.mode == ProgramManager.mode_review
            or self.mode == ProgramManager.mode_manual_detect):
            if not self.interface.show_warning( \
                _('The current capture has not been saved and will be lost. '
                  'Are you sure you want to close this session?'),
                is_question=True):
                return
        self.imageproc_context.close_camera()
        self.mode = ProgramManager.mode_no_session
        self.exam_data = None
        self.valid_student_ids = None
        self.imageproc_options = None
        self.save_pattern = None
        self.answers_file = None
        self.interface.activate_no_session_mode()

    def _exit_application(self):
        """Callback for when the user wants to exit the application."""
        if (self.mode == ProgramManager.mode_review
            or self.mode == ProgramManager.mode_manual_detect):
            if not self.interface.show_warning( \
                _('The current capture has not been saved and will be lost. '
                  'Are you sure you want to exit the application?'),
                is_question=True):
                return False
        return True

    def _action_snapshot(self):
        """Callback for the snapshot action."""
        enable_manual_detection = False
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
            enable_manual_detection = True
        self._start_review_mode()
        if enable_manual_detection:
            self.interface.enable_manual_detect(True)

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
        from_search_mode = self.mode == ProgramManager.mode_search
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
        if self.mode != ProgramManager.mode_review:
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
                        _('You typed and incorrect student id.'))
            self.interface.update_text_up(self.exam.get_student_id_and_name())

    def _action_camera_selection(self):
        """Callback for opening the camera selection dialog."""
        self.interface.dialog_camera_selection(self.imageproc_context)

    def _action_help(self):
        """Callback for the help action."""
        webbrowser.open(utils.help_location, new=2)

    def _action_website(self):
        """Callback for the website action."""
        webbrowser.open(utils.web_location, new=2)

    def _action_source_code(self):
        """Callback for the website action."""
        webbrowser.open(utils.source_location, new=2)

    def _action_debug_changed(self):
        """Callback for the checkable actions in the debug options menu."""
        if self.imageproc_options is not None:
            self.imageproc_options['show-lines'] = \
                   self.interface.is_action_checked(('tools', 'lines'))
            self.imageproc_options['show-image-proc'] = \
                   self.interface.is_action_checked(('tools', 'processed'))
            self.imageproc_options['show-status'] = \
                   self.interface.is_action_checked(('tools', 'show_status'))

    def _action_auto_change_changed(self):
        """Callback for the checkable 'auto_change' option."""
        if self.interface.is_action_checked(('tools', 'auto_change')):
            self._start_auto_change_detection()

    def _mouse_pressed(self, point):
        """Callback called when the mouse is pressed inside a capture."""
        if self.mode == ProgramManager.mode_review:
            self._mouse_pressed_change_answer(point)
        elif self.mode == ProgramManager.mode_manual_detect:
            self._mouse_pressed_manual_detection(point)

    def _digit_pressed(self, digit_string):
        """Callback called when a digit is pressed."""
        if self.mode == ProgramManager.mode_review:
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
                        if self.exam.solutions is None:
                            msg = _('There are no solutions for model {0}.')\
                                  .format(self.exam.model)
                            self.interface.show_error(msg)
                        else:
                            self.exam.grade()
                            self.exam.draw_answers()
                            self.interface.update_status( \
                                self.exam.score, self.exam.model,
                                self.exam.im_id,
                                survey_mode=self.exam_data.survey_mode)
                            success = True
            if not success:
                self.exam.image.clean_drawn_image()
                self.interface.show_error(_('Manual detection failed'))
            self.from_manual_detection = True
            self._start_review_mode()

    def _start_session(self):
        """Starts a session (either a new one or one that has been loaded)."""
        exam_data = self.exam_data
        session_cfg = exam_data.session
        self.save_pattern = os.path.join(self.session_dir, 'captures',
                                         session_cfg['save-filename-pattern'])
        self.answers_file = os.path.join(self.session_dir,
                                         'eyegrade-answers.csv')
        try:
            self._read_student_ids()
        except Exception as e:
            self.interface.show_error((_('The student list cannot be read')
                                       + ': ' + str(e)))
            return
        self.imageproc_options = imageproc.ExamCapture.get_default_options()
        if exam_data.id_num_digits and exam_data.id_num_digits > 0:
            self.imageproc_options['read-id'] = True
            self.imageproc_options['id-num-digits'] = exam_data.id_num_digits
        self.imageproc_options['left-to-right-numbering'] = \
                                            exam_data.left_to_right_numbering
        # Set the debug options in imageproc_options:
        self._action_debug_changed()
        self.imageproc_context.open_camera()
        if self.imageproc_context.camera is None:
            self.interface.show_error(_('No camera found. Connect a camera and '
                                        'start the session again.'))
            return
        if not os.path.isfile(self.answers_file):
            self.image_id = 1
        else:
            results = utils.read_results(self.answers_file,
                                         allow_question_mark=True)
            self.image_id = 1 + max([int(r['seq-num']) for r in results])
        self._start_search_mode()

    def _solutions(self, model):
        """Returns the solutions for the given model.

        If in survey mode it returns []. If there are no solutions for
        this, model it returns None.

        """
        if not self.exam_data.survey_mode:
            if model in self.exam_data.solutions:
                return self.exam_data.solutions[model]
            else:
                return None
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
            ('actions', 'tools', 'camera'): self._action_camera_selection,
            ('actions', 'tools', 'lines'): self._action_debug_changed,
            ('actions', 'tools', 'processed'): self._action_debug_changed,
            ('actions', 'tools', 'show_status'): self._action_debug_changed,
            ('actions', 'tools', 'auto_change'): \
                                            self._action_auto_change_changed,
            ('actions', 'help', 'help'): self._action_help,
            ('actions', 'help', 'website'): self._action_website,
            ('actions', 'help', 'source'): self._action_source_code,
            ('center_view', 'camview', 'mouse_pressed'): self._mouse_pressed,
            ('window', 'exit'): self._exit_application,
        }
        self.interface.register_listeners(listeners)

    def _read_student_ids(self):
        ids = None
        dirname = os.path.join(self.session_dir, 'student_ids')
        if os.path.isdir(dirname):
            files = [os.path.join(dirname, f) for f in os.listdir(dirname)]
            if files:
                ids = utils.read_student_ids_multiple(filenames=files,
                                                      with_names=True)
        self.valid_student_ids = ids

    @staticmethod
    def _copy_id_list(src_file, dst_dir):
        file_basename = os.path.basename(src_file)
        dst_file = os.path.join(dst_dir, file_basename)
        if os.path.exists(dst_file):
            # Try with other names
            success = False
            base, extension = os.path.splitext(dst_file)
            for i in range(1, 10000):
                dst_file = '{0}-{1}{2}'.format(base, i, extension)
                if not os.path.exists(dst_file):
                    success = True
                    break
            if not success:
                raise Exception(_('Cannot copy file') + ': ' + src_file)
        shutil.copy(src_file, dst_file)


def main():
    # For the translations to work, the initialization of QApplication and
    # the loading of the translations must be done here instead of the
    # gui module:
    #
    from PyQt4.QtGui import QApplication
    from PyQt4.QtCore import QTranslator, QLocale, QLibraryInfo
    app = QApplication(sys.argv)
    translator = QTranslator()
    translator.load(QLocale.system(), 'qt', '_',
                    QLibraryInfo.location(QLibraryInfo.TranslationsPath))
    app.installTranslator(translator)
    if len(sys.argv) >= 2:
        filename = sys.argv[1]
    else:
        filename = None
    interface = gui.Interface(app, False, False, [])
    manager = ProgramManager(interface, session_file=filename)
    manager.run()

if __name__ == '__main__':
    try:
        main()
    except utils.EyegradeException as ex:
        print >>sys.stderr, ex
        sys.exit(1)
