# Eyegrade: grading multiple choice questions with a webcam
# Copyright (C) 2010-2021 Jesus Arias Fisteus
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
# <https://www.gnu.org/licenses/>.
#

# The gettext module needs in Windows an environment variable
# to be defined before importing the gettext module itself
import os
import locale
import sys
import time
import webbrowser
import gettext

# Local imports
from . import detection
from . import utils
from . import exams
from .qtgui import gui
from . import sessiondb
from . import export

if (
    not os.getenv("LANG")
    and not os.getenv("LANGUAGE")
    and not os.getenv("LC_MESSAGES")
    and not os.getenv("LC_ALL")
):
    lang, enc = locale.getdefaultlocale()
    if lang is not None:
        os.environ["LANG"] = lang

t = gettext.translation("eyegrade", utils.locale_dir(), fallback=True)
_ = t.gettext

utils.EyegradeException.register_error(
    "no_camera",
    _(
        "There is no suitable webcam. Eyegrade needs a webcam to work.\n"
        "If your computer already has a camera, check that it is not being\n"
        "used by another application."
    ),
)
utils.EyegradeException.register_error(
    "no_session_db", short_message=_("Session database file not found")
)
utils.EyegradeException.register_error(
    "session_db_exists",
    short_message=_("The session database cannot be created: " "it already exists"),
)
utils.EyegradeException.register_error(
    "session_invalid", short_message=_("The session database is not valid")
)
utils.EyegradeException.register_error(
    "corrupt_session_dir", short_message=_("The session directory has been corrupted.")
)
utils.EyegradeException.register_error(
    "incompatible_schema",
    short_message=_(
        "Incompatible session format. This is {0} version {1} "
        "but the session was created by version {2}"
    ),
)

param_fps = 8
capture_period = 1.0 / param_fps
capture_change_period = 1.0
capture_change_period_failure = 0.3
after_removal_delay = 1.0


class ImageDetectTask:
    """Used for running image detection in another thread."""

    def __init__(self, detector):
        self.detector = detector

    def run(self):
        self.detector.detect_safe()
        self.detector = None


class ImageChangeTask:
    """Used for running image change detection in another thread."""

    def __init__(self, detector, reference_image):
        self.detector = detector
        self.reference_image = reference_image

    def run(self):
        self.detector.try_to_detect()
        self.detector = None


class ManualDetectionManager:
    def __init__(self, exam, dimensions, detection_context, detector_options):
        self.exam = exam
        self.points = []
        self.detector = detection.ExamDetector(
            dimensions,
            detection_context,
            detector_options,
            image_raw=exam.capture.image_raw,
        )

    def add_point(self, point):
        self.points.append(point)

    def is_ready(self):
        return len(self.points) == 4 * len(self.detector.dimensions)

    def detect(self):
        assert self.is_ready()
        return self.detector.detect_manual(self.points)


class ProgramMode:
    """Represents the mode in which the program is."""

    no_session = 0
    session = 1
    search = 2
    review_from_session = 3
    review_from_grading = 4
    manual_detect = 5

    def __init__(self):
        self.mode = ProgramMode.no_session

    def in_mode(self, mode):
        return self.mode == mode

    def in_no_session(self):
        return self.mode == ProgramMode.no_session

    def in_session(self):
        return self.mode == ProgramMode.session

    def in_search(self):
        return self.mode == ProgramMode.search

    def in_review(self):
        return (
            self.mode == ProgramMode.review_from_session
            or self.mode == ProgramMode.review_from_grading
        )

    def in_review_from_session(self):
        return self.mode == ProgramMode.review_from_session

    def in_review_from_grading(self):
        return self.mode == ProgramMode.review_from_grading

    def in_manual_detect(self):
        return self.mode == ProgramMode.manual_detect

    def in_grading(self):
        return (
            self.in_search() or self.in_review_from_grading() or self.in_manual_detect()
        )

    def enter_mode(self, mode):
        self.mode = mode

    def enter_no_session(self):
        self.mode = ProgramMode.session

    def enter_session(self):
        self.mode = ProgramMode.no_session

    def enter_search(self):
        self.mode = ProgramMode.search

    def enter_review(self):
        if self.in_grading():
            self.mode = ProgramMode.review_from_grading
        else:
            self.mode = ProgramMode.review_from_session

    def enter_manual_detect(self):
        self.mode = ProgramMode.manual_detect


class ProgramManager:
    """Manages a grading session."""

    def __init__(self, interface, session_file=None):
        self.interface = interface
        self.mode = ProgramMode()
        self.config = utils.config
        self.sessiondb = None
        self.detection_context = self._get_detection_context()
        self.detection_options = None
        self.drop_next_capture = False
        self.dump_buffer = False
        self._register_listeners()
        self.from_manual_detection = False
        self.manual_detect_manager = None
        if session_file is not None:
            self._try_session_file(session_file)

    def run(self):
        """Starts the program manager."""
        self.interface.run()

    def _get_detection_context(self):
        false_detector_session = os.getenv("EYEGRADE_CAMERA_SESSION")
        if not false_detector_session:
            return detection.ExamDetectorContext(camera_id=self.config["camera-dev"])
        else:
            return detection.FalseExamDetectorContext(false_detector_session)

    def _try_session_file(self, session_file):
        if os.path.isdir(session_file):
            filename = os.path.join(session_file, "session.eyedb")
            if os.path.exists(filename):
                session_file = filename
            else:
                self.interface.show_error(
                    _("The directory has no Eyegrade " "session") + ": " + session_file,
                    _("Error opening the session file"),
                )
                return
        valid, msg = self._validate_session(session_file)
        if valid:
            self._start_session()
        else:
            self.interface.show_error(msg)

    def _start_search_mode(self):
        self.mode.enter_search()
        self.from_manual_detection = False
        self.interface.activate_search_mode()
        self.exam = None
        self.latest_graded_exam = None
        self.latest_detector = None
        self.manual_detect_manager = None
        self.interface.register_timer(50, self._next_search)
        self.detection_context.dump_buffer(1.0)
        self.next_capture = time.time() + 0.05

    def _start_review_mode(self):
        if self.mode.in_grading():
            self._store_exam(self.exam)
            # Automatic detection of exam removal to go to the next exam
            if self.interface.is_action_checked(("tools", "auto_change")):
                self._start_auto_change_detection()
            self.drop_next_capture = False
        self.mode.enter_review()
        self.interface.activate_review_mode(self.mode.in_review_from_grading())
        self.interface.display_capture(self.exam.get_image_drawn())
        self.interface.update_text_up(self.exam.get_student_id_and_name())
        if self.exam.score is not None:
            self.interface.update_status(
                self.exam.score,
                model=self.exam.decisions.model,
                seq_num=self.exam.exam_id,
                survey_mode=self.exam_data.survey_mode,
            )
        else:
            self.interface.update_text_down("")
        if not self.exam.decisions.model:
            self.interface.enable_manual_detect(True)
        if self.mode.in_grading():
            # Run later so that the widget gets fully painted before being
            # grabbed and saved:
            self.interface.run_later(self._store_capture_and_add, delay=0)

    def _start_auto_change_detection(self):
        if not self.from_manual_detection:
            self.change_failures = 0
            self.interface.register_timer(1000, self._next_change_detection)

    def _start_manual_detect_mode(self):
        self.mode.enter_manual_detect()
        self.interface.activate_manual_detect_mode()
        self.interface.display_capture(self.exam.get_image_drawn())
        self.manual_detect_manager = ManualDetectionManager(
            self.exam,
            self.exam_data.dimensions,
            self.detection_context,
            self.detection_options,
        )

    def _next_search(self):
        if not self.mode.in_search():
            return
        if self.dump_buffer:
            self.dump_buffer = False
            self.detection_context.dump_buffer(after_removal_delay)
        detector = detection.ExamDetector(
            self.exam_data.dimensions, self.detection_context, self.detection_options
        )
        self.current_detector = detector
        task = ImageDetectTask(detector)
        self.interface.run_worker(task, self._after_image_detection)

    def _after_image_detection(self):
        detector = self.current_detector
        self.current_detector = None
        if not self.mode.in_search():
            # The user switched to other mode while the image was processed
            return
        self.latest_detector = detector
        if detector.status["boxes"] and self.detection_context.threshold_locked:
            self.detection_context.unlock_threshold()
        exam = self._process_capture(detector)
        if exam is None or not detector.success:
            if exam is not None:
                exam.draw_answers()
                exam.draw_status()
                self.interface.enable_manual_detect(False)
            elif detector.capture is not None:
                detector.capture.draw_status()
            if detector.capture is not None:
                self.interface.display_capture(detector.capture.image_drawn)
            self._schedule_next_capture(capture_period, self._next_search)
        elif not self.drop_next_capture:
            exam.draw_answers()
            self.exam = exam
            self._start_review_mode()
        else:
            # Special mode: do not lock until another capture is
            # available.  Used after auto exam removal detection.
            exam.draw_answers()
            self.interface.display_capture(detector.capture.image_drawn)
            self._schedule_next_capture(after_removal_delay, self._next_search)
            self.drop_next_capture = False
            self.dump_buffer = True

    def _next_change_detection(self):
        """Used to detect exam removal.

        This method captures an image and launches its analysis.
        Continuation of work is done at `_after_change_detection`.

        """
        if not self.mode.in_review_from_grading() or not self.interface.is_action_checked(
            ("tools", "auto_change")
        ):
            return
        self.detection_context.dump_buffer(1.0)
        detector = detection.ExamDetector(
            self.exam_data.dimensions, self.detection_context, self.detection_options
        )
        self.current_detector = detector
        task = ImageChangeTask(detector, self.exam.capture)
        self.interface.run_worker(task, self._after_change_detection)

    def _after_change_detection(self):
        """Continuation of `_next_change_detection`.

        Executed after the image has been processed. This method decides
        whether the exam has been removed.

        """
        image = self.current_detector
        self.current_detector = None
        if image is None:
            # This needs to be investigated: this case should never
            # happen, but I saw it happen...
            return
        if not self.mode.in_review_from_grading() or not self.interface.is_action_checked(
            ("tools", "auto_change")
        ):
            return
        exam_removed = False
        if image.try_to_detect:
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
            self.detection_context.lock_threshold()
            self.drop_next_capture = True
            self._action_continue()

    def _schedule_next_capture(self, period, function):
        """Schedules the next image capture and registers the timer.

        Call it from search mode, after an image has been processed, or
        in review mode if automatic exam removal detection is active.

        """
        current_time = time.time()
        self.next_capture += period
        if current_time > self.next_capture:
            self.detection_context.dump_buffer((current_time - self.next_capture))
            wait = 0.010
            self.next_capture = time.time() + 0.010
        else:
            wait = self.next_capture - current_time
        self.interface.register_timer(int(wait * 1000), function)

    def _process_capture(self, detector):
        """Processes a captured image."""
        exam = None
        if detector.status["infobits"] or not self.detection_options["infobits"]:
            if not self.detection_options["infobits"]:
                # If models are configured not to be detected, assume the default model "A"
                detector.decisions.model = "A"
            model = detector.decisions.model
            if model is not None:
                if model in self.exam_data.solutions or self.exam_data.survey_mode:
                    if model in self.exam_data.scores:
                        scores = self.exam_data.scores[model]
                    else:
                        scores = None
                    exam = exams.Exam(
                        detector.capture,
                        detector.decisions,
                        self.exam_data.get_solutions(model),
                        self.sessiondb.student_listings,
                        self.exam_id,
                        scores,
                        sessiondb=self.sessiondb,
                    )
                    self.latest_graded_exam = exam
                elif model not in self.exam_data.solutions:
                    msg = _("There are no solutions for model {0}.").format(model)
                    self.interface.show_error(msg)
        return exam

    def _new_session(self):
        """Callback for when the new session action is selected."""
        values = self.interface.dialog_new_session()
        if values is not None:
            self.exam_data = values["config"]
            self.exam_data.capture_pattern = self.config["save-filename-pattern"]
            try:
                sessiondb.create_session_directory(
                    values["directory"], self.exam_data, values["student_listings"]
                )
                self.sessiondb = sessiondb.SessionDB(values["directory"])
                self.sessiondb.capture_save_func = self.interface.save_capture
            except IOError as e:
                self.interface.show_error(_("Input/output error:") + " " + str(e))
            except utils.EyegradeException as e:
                self.interface.show_error(_("Error:") + " " + str(e))
            else:
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
        directory. The file is stored as self.exam_data.

        Returns (valid, error_message) where exam_data is the exam
        configuration object, valid is True if the session is valid
        and error message contains a textal description of the error
        in case the session is not valid.

        """
        try:
            self.sessiondb = sessiondb.SessionDB(filename)
            self.exam_data = self.sessiondb.exam_config
            self.sessiondb.capture_save_func = self.interface.save_capture
            success = True
            message = ""
        except utils.EyegradeException as e:
            self.sessiondb = None
            self.exam_data = None
            success = False
            message = _("Error loading the session") + ": " + str(e)
        except IOError as e:
            self.sessiondb = None
            self.exam_data = None
            success = False
            message = _("Error loading the session") + ": " + str(e)
        return success, message

    def _close_session(self):
        """Callback that closes the current session."""
        if self.mode.in_manual_detect():
            if not self.interface.show_warning(
                _(
                    "The current capture has not been saved and will be lost. "
                    "Are you sure you want to close this session?"
                ),
                is_question=True,
            ):
                return
        if self.mode.in_grading() or self.mode.in_review_from_session():
            self._stop_grading()
        self.sessiondb.save_legacy_answers()
        self.sessiondb.close()
        self.mode.enter_no_session()
        self.sessiondb = None
        self.exam_data = None
        self.detection_options = None
        self.interface.activate_no_session_mode()

    def _exit_application(self):
        """Callback for when the user wants to exit the application."""
        if self.mode.in_manual_detect():
            exit_ = self.interface.show_warning(
                _(
                    "The current capture has not been saved and will be lost. "
                    "Are you sure you want to exit the application?"
                ),
                is_question=True,
            )
        elif self.mode.in_grading() or self.mode.in_review_from_session():
            self._stop_grading()
            exit_ = True
        else:
            exit_ = True
        if exit and self.sessiondb is not None:
            self.sessiondb.save_legacy_answers()
            self.sessiondb.close()
        return exit_

    def _action_start(self):
        if self.mode.in_review_from_session():
            self._stop_grading()
        self._start_grading()

    def _action_stop(self):
        self._stop_grading()

    def _action_back(self):
        if self.mode.in_review_from_session():
            self._stop_grading()
            self.interface.clear_selected_exam()
            self.exam = None

    def _action_snapshot(self):
        """Callback for the snapshot action."""
        if self.latest_graded_exam is None:
            if self.latest_detector is None:
                return
            detector = self.latest_detector
            self.exam = exams.Exam(
                detector.capture,
                detector.decisions,
                [],
                self.sessiondb.student_listings,
                self.exam_id,
                None,
                sessiondb=self.sessiondb,
            )
            self.exam.reset_image()
            enable_manual_detection = True
        else:
            self.exam = self.latest_graded_exam
            self.exam.reset_image()
            self.exam.draw_answers()
            enable_manual_detection = False
        self._start_review_mode()
        self.interface.enable_manual_detect(enable_manual_detection)

    def _action_discard(self):
        """Callback for cancelling/removing the current capture."""
        if self.mode.in_review_from_grading():
            self.sessiondb.remove_exam(self.exam.exam_id)
            self.interface.remove_exam(self.exam)
            self._start_search_mode()
        elif self.mode.in_manual_detect():
            self._start_search_mode()
        elif self.mode.in_review_from_session():
            remove = self.interface.show_warning(
                _("The selected exam will be removed. Are you sure?"), is_question=True
            )
            if remove:
                self.sessiondb.remove_exam(self.exam.exam_id)
                self.interface.remove_exam(self.exam)
                exam = self.interface.selected_exam()
                if exam is not None:
                    self._exam_selected(exam)
                else:
                    self.exam = None
                    self._activate_session_mode()

    def _action_continue(self):
        """Callback for saving the current capture."""
        if self.mode.in_review_from_grading():
            self.exam_id += 1
            self._start_search_mode()
        elif self.mode.in_review_from_session():
            self.interface.select_next_exam()

    def _action_manual_detect(self):
        """Callback for the manual detection action."""
        if self.mode.in_search():
            # Take the current snapshot and go to manual detect mode
            self.exam = exams.Exam(
                self.latest_detector.capture,
                self.latest_detector.decisions,
                [],
                self.sessiondb.student_listings,
                self.exam_id,
                None,
                sessiondb=self.sessiondb,
            )
            # Store the exam in order to emulate entering this mode
            # from review mode.
            self._store_exam(self.exam)
            self.interface.run_later(self._store_capture_and_add, delay=100)
        self.exam.reset_image()
        self._start_manual_detect_mode()

    def _action_edit_id(self):
        """Callback for the edit student id action."""
        if not self.mode.in_review():
            return
        students = self.exam.ranked_student_ids()
        student = self.interface.dialog_student_id(
            students, self.sessiondb.student_listings
        )
        if student is not None:
            self.exam.update_student_id(student)
            self.interface.update_text_up(self.exam.get_student_id_and_name())
            self.sessiondb.update_student(
                self.exam.exam_id,
                self.exam.capture,
                self.exam.decisions,
                store_captures=False,
            )
            self.interface.run_later(self._store_capture_and_update, delay=100)

    def _action_camera_selection(self):
        """Callback for opening the camera selection dialog."""
        self.interface.dialog_camera_selection(self.detection_context)

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
        if self.detection_options is not None:
            self.detection_options["show-lines"] = self.interface.is_action_checked(
                ("tools", "lines")
            )
            self.detection_options[
                "show-image-proc"
            ] = self.interface.is_action_checked(("tools", "processed"))
            self.detection_options["show-status"] = self.interface.is_action_checked(
                ("tools", "show_status")
            )

    def _action_auto_change_changed(self):
        """Callback for the checkable 'auto_change' option."""
        if self.interface.is_action_checked(("tools", "auto_change")):
            self._start_auto_change_detection()

    def _action_export_grades(self):
        """Action for exporting the list of grades."""
        helper = export.GradesExportHelper(
            self.exam_data, self.sessiondb.get_student_groups()
        )
        result = self.interface.dialog_export_grades(helper)
        if result:
            try:
                self.sessiondb.export_grades(helper)
            except IOError as e:
                msg = _("Input/output error: {0}").format(e.strerror)
                self.interface.show_error(msg)
            else:
                self.interface.show_information(
                    _("The file has been saved."), title=_("File saved")
                )

    def _action_students(self):
        student_listings = self.sessiondb.student_listings
        self.interface.dialog_students(student_listings)

    def _action_export_exam_config(self):
        """Callback for exporting the current exam configuration."""
        filename = self.interface.dialog_export_exam_config()
        if filename is not None:
            try:
                self.exam_data.save(filename)
            except IOError as e:
                msg = _("Input/output error: {0}").format(e.strerror)
                self.interface.show_error(msg)
            else:
                self.interface.show_information(
                    _("The file has been saved."), title=_("File saved")
                )

    def _mouse_pressed(self, point):
        """Callback called when the mouse is pressed inside a capture."""
        if self.mode.in_review():
            self._mouse_pressed_change_answer(point)
        elif self.mode.in_manual_detect():
            self._mouse_pressed_manual_detection(point)

    def _mouse_pressed_change_answer(self, point):
        if self.exam.capture.has_answer_cells():
            question, answer = self.exam.capture.get_cell_clicked(point)
            if question is not None:
                self.exam.toggle_answer(question, answer)
                self.interface.display_capture(self.exam.get_image_drawn())
                self.interface.update_status(
                    self.exam.score,
                    self.exam.decisions.model,
                    self.exam.exam_id,
                    survey_mode=self.exam_data.survey_mode,
                )
                self.sessiondb.update_answer(
                    self.exam.exam_id,
                    question,
                    self.exam.capture,
                    self.exam.decisions,
                    self.exam.score,
                    store_captures=False,
                )
                self.interface.run_later(self._store_capture_and_update, delay=100)

    def _mouse_pressed_manual_detection(self, point):
        manager = self.manual_detect_manager
        success = False
        manager.add_point(point)
        self.exam.draw_corner(point)
        self.interface.display_capture(self.exam.get_image_drawn())
        if manager.is_ready():
            success = manager.detect()
            if success:
                new_exam = self._process_capture(manager.detector)
                if new_exam is not None:
                    new_exam.draw_answers()
                else:
                    success = False
            # Remove the exam that was saved previously,
            # before having started the manual review mode:
            self.sessiondb.remove_exam(self.exam.exam_id)
            self.interface.remove_exam(self.exam)
            if not success:
                self.exam.reset_image()
                self.interface.show_error(_("Manual detection failed"))
                self._start_search_mode()
            else:
                self.exam = new_exam
                self.from_manual_detection = True
                self._start_review_mode()

    def _exam_selected(self, exam):
        if self.mode.in_grading():
            if self.mode.in_review_from_grading():
                self.exam_id += 1
            self._activate_session_mode()
        exam.load_capture()
        exam.reset_image()
        exam.draw_answers()
        self.exam = exam
        self._start_review_mode()

    def _start_session(self):
        """Starts a session (either a new one or one that has been loaded)."""
        self.interface.add_exams(self.sessiondb.read_exams())
        self._activate_session_mode()

    def _activate_session_mode(self):
        self.mode.enter_session()
        self.interface.activate_session_mode()

    def _start_grading(self):
        exam_data = self.exam_data
        self.detection_options = detection.ExamDetector.get_default_options()
        if self.exam_data.survey_mode:
            self.detection_options["infobits"] = False
        self.detection_options["error-logging"] = self.config["error-logging"]
        if exam_data.id_num_digits and exam_data.id_num_digits > 0:
            self.detection_options["read-id"] = True
            self.detection_options["id-num-digits"] = exam_data.id_num_digits
        self.detection_options[
            "left-to-right-numbering"
        ] = exam_data.left_to_right_numbering
        # Set the debug options in detection_options:
        self._action_debug_changed()
        self.detection_context.open_camera()
        if self.detection_context.camera is None:
            self.interface.show_error(
                _("No camera found. Connect a camera and " "start the session again.")
            )
            return
        self.exam_id = self.sessiondb.next_exam_id()
        self.interface.clear_selected_exam()
        self._start_search_mode()

    def _stop_grading(self):
        if self.mode.in_grading():
            self.detection_context.close_camera()
        self._activate_session_mode()

    def _store_capture_and_add(self):
        self._store_capture(self.exam)
        self.interface.add_exam(self.exam)

    def _store_capture_and_update(self):
        self._store_capture(self.exam)
        self.interface.update_exam(self.exam)

    def _store_exam(self, exam):
        self.sessiondb.store_exam(
            exam.exam_id, exam.capture, exam.decisions, exam.score, store_captures=False
        )
        self.sessiondb.save_raw_capture(exam.exam_id, exam.capture)

    def _store_capture(self, exam):
        self.sessiondb.save_drawn_capture(
            exam.exam_id, exam.capture, exam.decisions.student
        )

    def _register_listeners(self):
        listeners = {
            ("actions", "session", "new"): self._new_session,
            ("actions", "session", "open"): self._open_session,
            ("actions", "session", "close"): self._close_session,
            ("actions", "grading", "start"): self._action_start,
            ("actions", "grading", "stop"): self._action_stop,
            ("actions", "grading", "back"): self._action_back,
            ("actions", "grading", "snapshot"): self._action_snapshot,
            ("actions", "grading", "discard"): self._action_discard,
            ("actions", "grading", "continue"): self._action_continue,
            ("actions", "grading", "manual_detect"): self._action_manual_detect,
            ("actions", "grading", "edit_id"): self._action_edit_id,
            ("actions", "tools", "camera"): self._action_camera_selection,
            ("actions", "tools", "export_exam_config"): self._action_export_exam_config,
            ("actions", "tools", "lines"): self._action_debug_changed,
            ("actions", "tools", "processed"): self._action_debug_changed,
            ("actions", "tools", "show_status"): self._action_debug_changed,
            ("actions", "tools", "auto_change"): self._action_auto_change_changed,
            ("actions", "exams", "export"): self._action_export_grades,
            ("actions", "exams", "students"): self._action_students,
            ("actions", "help", "help"): self._action_help,
            ("actions", "help", "website"): self._action_website,
            ("actions", "help", "source"): self._action_source_code,
            ("center_view", "camview", "mouse_pressed"): self._mouse_pressed,
            ("window", "exit"): self._exit_application,
            ("window", "exam", "selected"): self._exam_selected,
        }
        self.interface.register_listeners(listeners)


def main():
    # For the translations to work, the initialization of QApplication and
    # the loading of the translations must be done here instead of the
    # gui module:
    #
    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtCore import QTranslator, QLocale, QLibraryInfo

    app = QApplication(sys.argv)
    translator = QTranslator()
    success = translator.load(
        QLocale.system(),
        "qt",
        "_",
        QLibraryInfo.location(QLibraryInfo.TranslationsPath),
    )
    if not success:
        success = translator.load(
            QLocale.system(), "qt", "_", utils.qt_translations_dir()
        )
    app.installTranslator(translator)
    if len(sys.argv) >= 2:
        filename = sys.argv[1]
    else:
        filename = None
    try:
        interface = gui.Interface(
            app, False, False, preferred_styles=utils.config["gui-styles"]
        )
        manager = ProgramManager(interface, session_file=filename)
        manager.run()
    except utils.EyegradeException as ex:
        print(ex)
        sys.exit(1)


if __name__ == "__main__":
    main()
