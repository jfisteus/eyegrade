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
import gettext

from typing import List, Tuple, Optional

from PyQt5.QtGui import QIcon, QKeySequence

from PyQt5.QtWidgets import (
    QAction,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QSizePolicy,
    QStackedLayout,
    QStyleFactory,
    QVBoxLayout,
    QWidget,
)

from PyQt5.QtCore import QObject, QRunnable, QThreadPool, QTimer, Qt, pyqtSignal

from .. import utils
from . import examsview
from . import widgets
from . import wizards
from . import dialogs
from . import export
from . import students
from . import FileNameFilters

t = gettext.translation("eyegrade", utils.locale_dir(), fallback=True)
_ = t.gettext


class _WorkerSignalEmitter(QObject):
    """Convenience class for generating signals from a Worker."""

    finished = pyqtSignal()


class Worker(QRunnable):
    """Generic worker class for spawning a task to other thread."""

    _active_workers: List["Worker"] = []
    _worker_count = 0

    def __init__(self, task):
        """Inits a new worker.

        The `task` must be an object that implements a `run()` method.

        """
        super().__init__()
        self.task = task
        self.is_done = False
        self.signals = _WorkerSignalEmitter()
        if Worker._worker_count > 63:
            Worker._cleanup_done_workers()
        Worker._active_workers.append(self)
        Worker._worker_count += 1

    def run(self):
        """Run the task and emit the signal at its completion."""
        self.task.run()
        self.is_done = True
        self.signals.finished.emit()

    @property
    def finished(self):
        """The `finished` signal as a property."""
        return self.signals.finished

    @staticmethod
    def _cleanup_done_workers():
        Worker._active_workers = [w for w in Worker._active_workers if not w.is_done]
        Worker._worker_count = len(Worker._active_workers)


class ActionsManager:
    """Creates and manages the toolbar buttons."""

    _actions_grading_data: List[Tuple[str, Optional[str], Optional[str], List[int]]] = [
        ("start", "start.svg", _("&Start grading"), []),
        ("stop", "stop.svg", _("S&top grading"), []),
        ("back", "back.svg", _("&Back to session home"), []),
        ("continue", "continue.svg", _("Continue to the &next exam"), [Qt.Key_Space]),
        ("*separator*", None, None, []),
        ("snapshot", "snapshot.svg", _("&Capture the current image"), [Qt.Key_C]),
        (
            "manual_detect",
            "manual_detect.svg",
            _("&Manual detection of answer tables"),
            [Qt.Key_M],
        ),
        ("edit_id", "edit_id.svg", _("&Edit student id"), [Qt.Key_I]),
        (
            "discard",
            "discard.svg",
            _("&Discard exam"),
            [Qt.Key_Delete, Qt.Key_Backspace],
        ),
    ]

    _actions_session_data: List[Tuple[str, Optional[str], Optional[str], List[int]]] = [
        ("new", "new.svg", _("&New session"), []),
        ("open", "open.svg", _("&Open session"), []),
        ("close", "close.svg", _("&Close session"), [Qt.Key_Escape]),
        ("*separator*", None, None, []),
        ("exit", "exit.svg", _("&Exit"), []),
    ]

    _actions_exams_data: List[Tuple[str, Optional[str], Optional[str], List[int]]] = [
        ("search", "search.svg", _("&Search"), []),
        ("students", None, _("S&tudents"), []),
        ("export", "export.svg", _("&Export grades listing"), []),
    ]

    _actions_tools_data: List[Tuple[str, Optional[str], Optional[str], List[int]]] = [
        ("camera", "camera.svg", _("Select &camera"), []),
        ("export_exam_config", None, _("E&xport exam configuration"), []),
    ]

    _actions_help_data: List[Tuple[str, Optional[str], Optional[str], List[int]]] = [
        ("help", None, _("Online &Help"), []),
        ("website", None, _("&Website"), []),
        ("source", None, _("&Source code at GitHub"), []),
        ("about", None, _("&About"), []),
    ]

    _actions_debug_data: List[Tuple[str, Optional[str], Optional[str], List[int]]] = [
        ("+show_status", None, _("Show &status"), []),
        ("+lines", None, _("Show &lines"), []),
        ("+processed", None, _("Show &processed image"), []),
    ]

    _actions_experimental: List[Tuple[str, Optional[str], Optional[str], List[int]]] = [
        ("+auto_change", None, _("Continue on exam &removal"), [])
    ]

    def __init__(self, window):
        """Creates a manager for the given toolbar object."""
        self.window = window
        self.menubar = window.menuBar()
        self.toolbar = window.addToolBar("Grade Toolbar")
        self.menus = {}
        self.actions_grading = {}
        self.actions_session = {}
        self.actions_exams = {}
        self.actions_tools = {}
        self.actions_help = {}
        action_lists = {
            "session": [],
            "grading": [],
            "exams": [],
            "tools": [],
            "help": [],
        }
        for key, icon, text, shortcuts in ActionsManager._actions_session_data:
            self._add_action(
                key,
                icon,
                text,
                shortcuts,
                self.actions_session,
                action_lists["session"],
            )
        for key, icon, text, shortcuts in ActionsManager._actions_grading_data:
            self._add_action(
                key,
                icon,
                text,
                shortcuts,
                self.actions_grading,
                action_lists["grading"],
            )
        for key, icon, text, shortcuts in ActionsManager._actions_exams_data:
            self._add_action(
                key, icon, text, shortcuts, self.actions_exams, action_lists["exams"]
            )
        for key, icon, text, shortcuts in ActionsManager._actions_tools_data:
            self._add_action(
                key, icon, text, shortcuts, self.actions_tools, action_lists["tools"]
            )
        for key, icon, text, shortcuts in ActionsManager._actions_help_data:
            self._add_action(
                key, icon, text, shortcuts, self.actions_help, action_lists["help"]
            )
        self._populate_menubar(action_lists)
        self._populate_toolbar(action_lists)
        self._add_debug_actions()
        self._add_experimental_actions()

    def set_search_mode(self):
        self.actions_grading["start"].setEnabled(False)
        self.actions_grading["stop"].setEnabled(True)
        self.actions_grading["back"].setEnabled(False)
        self.actions_grading["snapshot"].setEnabled(True)
        self.actions_grading["manual_detect"].setEnabled(True)
        self.actions_grading["edit_id"].setEnabled(False)
        self.actions_grading["continue"].setEnabled(False)
        self.actions_grading["discard"].setEnabled(False)
        self.actions_session["new"].setEnabled(False)
        self.actions_session["open"].setEnabled(False)
        self.actions_session["close"].setEnabled(True)
        self.actions_session["exit"].setEnabled(True)
        self.actions_tools["camera"].setEnabled(False)
        self.actions_tools["export_exam_config"].setEnabled(True)
        self.actions_exams["search"].setEnabled(False)
        self.actions_exams["students"].setEnabled(False)
        self.actions_exams["export"].setEnabled(False)

    def set_review_from_grading_mode(self):
        self.actions_grading["start"].setEnabled(False)
        self.actions_grading["stop"].setEnabled(True)
        self.actions_grading["back"].setEnabled(False)
        self.actions_grading["snapshot"].setEnabled(False)
        self.actions_grading["manual_detect"].setEnabled(False)
        self.actions_grading["edit_id"].setEnabled(True)
        self.actions_grading["continue"].setEnabled(True)
        self.actions_grading["discard"].setEnabled(True)
        self.actions_session["new"].setEnabled(False)
        self.actions_session["open"].setEnabled(False)
        self.actions_session["close"].setEnabled(True)
        self.actions_session["exit"].setEnabled(True)
        self.actions_tools["camera"].setEnabled(False)
        self.actions_tools["export_exam_config"].setEnabled(True)
        self.actions_exams["search"].setEnabled(False)
        self.actions_exams["students"].setEnabled(True)
        self.actions_exams["export"].setEnabled(True)

    def set_review_from_session_mode(self):
        self.actions_grading["start"].setEnabled(True)
        self.actions_grading["stop"].setEnabled(False)
        self.actions_grading["back"].setEnabled(True)
        self.actions_grading["snapshot"].setEnabled(False)
        self.actions_grading["manual_detect"].setEnabled(False)
        self.actions_grading["edit_id"].setEnabled(True)
        self.actions_grading["continue"].setEnabled(True)
        self.actions_grading["discard"].setEnabled(True)
        self.actions_session["new"].setEnabled(False)
        self.actions_session["open"].setEnabled(False)
        self.actions_session["close"].setEnabled(True)
        self.actions_session["exit"].setEnabled(True)
        self.actions_tools["camera"].setEnabled(True)
        self.actions_tools["export_exam_config"].setEnabled(True)
        self.actions_exams["search"].setEnabled(False)
        self.actions_exams["students"].setEnabled(True)
        self.actions_exams["export"].setEnabled(True)

    def set_session_mode(self):
        self.actions_grading["start"].setEnabled(True)
        self.actions_grading["stop"].setEnabled(False)
        self.actions_grading["back"].setEnabled(False)
        self.actions_grading["snapshot"].setEnabled(False)
        self.actions_grading["manual_detect"].setEnabled(False)
        self.actions_grading["edit_id"].setEnabled(False)
        self.actions_grading["continue"].setEnabled(False)
        self.actions_grading["discard"].setEnabled(False)
        self.actions_session["new"].setEnabled(False)
        self.actions_session["open"].setEnabled(False)
        self.actions_session["close"].setEnabled(True)
        self.actions_session["exit"].setEnabled(True)
        self.actions_tools["camera"].setEnabled(True)
        self.actions_tools["export_exam_config"].setEnabled(True)
        self.actions_exams["search"].setEnabled(True)
        self.actions_exams["search"].setEnabled(False)
        self.actions_exams["students"].setEnabled(True)
        self.actions_exams["export"].setEnabled(True)

    def set_manual_detect_mode(self):
        self.actions_grading["start"].setEnabled(False)
        self.actions_grading["stop"].setEnabled(True)
        self.actions_grading["back"].setEnabled(False)
        self.actions_grading["snapshot"].setEnabled(False)
        self.actions_grading["manual_detect"].setEnabled(True)
        self.actions_grading["edit_id"].setEnabled(False)
        self.actions_grading["continue"].setEnabled(False)
        self.actions_grading["discard"].setEnabled(True)
        self.actions_session["new"].setEnabled(False)
        self.actions_session["open"].setEnabled(False)
        self.actions_session["close"].setEnabled(True)
        self.actions_session["exit"].setEnabled(True)
        self.actions_tools["camera"].setEnabled(False)
        self.actions_tools["export_exam_config"].setEnabled(True)
        self.actions_exams["search"].setEnabled(False)
        self.actions_exams["students"].setEnabled(False)
        self.actions_exams["export"].setEnabled(False)

    def set_no_session_mode(self):
        for key in self.actions_grading:
            self.actions_grading[key].setEnabled(False)
        self.actions_session["new"].setEnabled(True)
        self.actions_session["open"].setEnabled(True)
        self.actions_session["close"].setEnabled(False)
        self.actions_session["exit"].setEnabled(True)
        self.actions_tools["camera"].setEnabled(True)
        self.actions_tools["export_exam_config"].setEnabled(False)
        for key in self.actions_exams:
            self.actions_exams[key].setEnabled(False)

    def enable_manual_detect(self, enabled):
        """Enables or disables the manual detection mode.

        If `enable` is True, it is enabled. Otherwise, it is disabled.

        """
        self.actions_grading["manual_detect"].setEnabled(enabled)

    def register_listener(self, key, listener):
        actions = self._select_action_group(key[0])
        assert key[1] in actions
        actions[key[1]].triggered.connect(listener)

    def is_action_checked(self, key):
        """For checkabel actions, returns whether the action is checked.

        Action keys are tuples such as ('tools', 'lines').

        """
        actions = self._select_action_group(key[0])
        assert key[1] in actions
        assert actions[key[1]].isCheckable()
        return actions[key[1]].isChecked()

    def _select_action_group(self, key):
        if key == "session":
            return self.actions_session
        elif key == "grading":
            return self.actions_grading
        elif key == "exams":
            return self.actions_exams
        elif key == "tools":
            return self.actions_tools
        elif key == "help":
            return self.actions_help
        assert False, "Undefined action group key: {0}".format(key)

    def _add_action(self, action_name, icon_file, text, shortcuts, group, actions_list):
        action = self._create_action(action_name, icon_file, text, shortcuts)
        if action_name.startswith("+"):
            if action_name.startswith("++"):
                action_name = action_name[2:]
            else:
                action_name = action_name[1:]
        if not action.isSeparator():
            group[action_name] = action
        actions_list.append(action)

    def _create_action(self, action_name, icon_file, text, shortcuts):
        if action_name == "*separator*":
            action = QAction(self.window)
            action.setSeparator(True)
        else:
            if icon_file:
                action = QAction(
                    QIcon(utils.resource_path(icon_file)), text, self.window
                )
            else:
                action = QAction(text, self.window)
        if shortcuts:
            sequences = [QKeySequence(s) for s in shortcuts]
            action.setShortcuts(sequences)
        if action_name.startswith("+"):
            action.setCheckable(True)
            if action_name.startswith("++"):
                action.setChecked(True)
        return action

    def _populate_menubar(self, action_lists):
        self.menus["session"] = QMenu(_("&Session"), self.menubar)
        self.menus["grading"] = QMenu(_("&Grading"), self.menubar)
        self.menus["exams"] = QMenu(_("&Exams"), self.menubar)
        self.menus["tools"] = QMenu(_("&Tools"), self.menubar)
        self.menus["help"] = QMenu(_("&Help"), self.menubar)
        self.menubar.addMenu(self.menus["session"])
        self.menubar.addMenu(self.menus["grading"])
        self.menubar.addMenu(self.menus["exams"])
        self.menubar.addMenu(self.menus["tools"])
        self.menubar.addMenu(self.menus["help"])
        for action in action_lists["session"]:
            self.menus["session"].addAction(action)
        for action in action_lists["grading"]:
            self.menus["grading"].addAction(action)
        for action in action_lists["exams"]:
            self.menus["exams"].addAction(action)
        for action in action_lists["tools"]:
            self.menus["tools"].addAction(action)
        for action in action_lists["help"]:
            self.menus["help"].addAction(action)

    def _populate_toolbar(self, action_lists):
        for action in action_lists["grading"]:
            self.toolbar.addAction(action)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.actions_exams["export"])
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.actions_session["new"])
        self.toolbar.addAction(self.actions_session["open"])
        self.toolbar.addAction(self.actions_session["close"])

    def _add_debug_actions(self):
        actions_list = []
        for key, icon, text, shortcuts in ActionsManager._actions_debug_data:
            self._add_action(
                key, icon, text, shortcuts, self.actions_tools, actions_list
            )
        menu = QMenu(_("&Debug options"), self.menus["tools"])
        for action in actions_list:
            menu.addAction(action)
        self.menus["tools"].addMenu(menu)

    def _add_experimental_actions(self):
        actions_list = []
        for key, icon, text, shortcuts in ActionsManager._actions_experimental:
            self._add_action(
                key, icon, text, shortcuts, self.actions_tools, actions_list
            )
        menu = QMenu(_("&Experimental"), self.menus["tools"])
        for action in actions_list:
            menu.addAction(action)
        self.menus["tools"].addMenu(menu)


class CenterView(QWidget):
    img_correct = '<img src="%s" height="22" width="22">' % utils.resource_path(
        "correct.svg"
    )
    img_incorrect = '<img src="%s" height="22" width="22">' % utils.resource_path(
        "incorrect.svg"
    )
    img_unanswered = '<img src="%s" height="22" width="22">' % utils.resource_path(
        "unanswered.svg"
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout()
        self.setLayout(layout)
        self.center = QStackedLayout()
        self.camview = widgets.CamView((640, 480), self, draw_logo=True)
        self.label_up = QLabel()
        self.label_down = QLabel()
        self.center.addWidget(self.camview)
        layout.addLayout(self.center)
        layout.addWidget(self.label_up)
        layout.addWidget(self.label_down)
        self.adjustSize()
        self.setFixedSize(self.sizeHint())

    def update_status(self, score, model=None, seq_num=None, survey_mode=False):
        parts = []
        if score is not None:
            if not survey_mode:
                parts.append(CenterView.img_correct)
                if score.correct is not None:
                    parts.append(str(score.correct) + "  ")
                else:
                    parts.append("---  ")
                parts.append(CenterView.img_incorrect)
                if score.incorrect is not None:
                    parts.append(str(score.incorrect) + "  ")
                else:
                    parts.append("---  ")
                parts.append(CenterView.img_unanswered)
                if score.blank is not None:
                    parts.append(str(score.blank) + "  ")
                else:
                    parts.append("---  ")
                if score.score is not None and score.max_score is not None:
                    parts.append(
                        _("Score: {0:.2f} / {1:.2f}").format(
                            score.score, score.max_score
                        )
                    )
                    parts.append("  ")
            else:
                parts.append(_("[Survey mode on]"))
                parts.append("  ")
        if model is not None:
            parts.append(_("Model:") + " " + model + "  ")
        if seq_num is not None:
            parts.append(_("Num.:") + " " + str(seq_num) + "  ")
        self.label_down.setText(
            ('<span style="white-space: pre">' + " ".join(parts) + "</span>")
        )

    def update_text_up(self, text):
        self.label_up.setText(text)

    def update_text_down(self, text):
        self.label_down.setText(text)

    def display_capture(self, ipl_image):
        """Displays a captured image in the window.

        The image is in the OpenCV IPL format.

        """
        self.camview.display_capture(ipl_image)

    def display_wait_image(self):
        """Displays the default image instead of a camera capture."""
        self.camview.display_wait_image()

    def register_listener(self, key, listener):
        """Registers listeners for the center view.

        Available listeners are:

        - ('camview', 'mouse_pressed'): mouse pressed in the camview
          area. The listener receives the coordinates (x, y) as a
          tuple.

        """
        if key[0] == "camview":
            if key[1] == "mouse_pressed":
                self.camview.register_mouse_pressed_listener(listener)
            else:
                assert False, "Undefined listener key: {0}".format(key)
        else:
            assert False, "Undefined listener key: {0}".format(key)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        policy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setSizePolicy(policy)
        self.setStatusBar(widgets.StatusBar(self))
        self.center_view = CenterView()
        self.exams_view = examsview.ThumbnailsView(self)
        #        self.center_layout = QStackedLayout()
        self.center_layout = QHBoxLayout()
        self.center_layout.addWidget(self.center_view)
        self.center_layout.addWidget(self.exams_view)
        center_container = QWidget(self)
        center_container.setLayout(self.center_layout)
        self.setCentralWidget(center_container)
        self.setWindowTitle("Eyegrade")
        self.setWindowIcon(QIcon(utils.resource_path("logo.svg")))
        self.adjustSize()
        #        self.setFixedSize(self.sizeHint())
        self.digit_key_listener = None
        self.exit_listener = False

    def keyPressEvent(self, event):
        if (
            self.digit_key_listener
            and event.key() >= Qt.Key_0
            and event.key() <= Qt.Key_9
        ):
            self.digit_key_listener(event.text())

    def register_listener(self, key, listener):
        if key[0] == "key_pressed":
            if key[1] == "digit":
                self.digit_key_listener = listener
            else:
                assert False, "Undefined listener key: {0}".format(key)
        elif key[0] == "exit":
            self.exit_listener = listener
        elif key[0] == "exam":
            if key[1] == "selected":
                self.exams_view.selection_changed.connect(listener)
        else:
            assert False, "Undefined listener key: {0}".format(key)

    def closeEvent(self, event):
        accept = True
        if self.exit_listener is not None:
            accept = self.exit_listener()
        if accept:
            event.accept()
        else:
            event.ignore()

    def clear_exams_view(self):
        self.exams_view.clear_exams()

    def update_status_bar(self, text):
        self.statusBar().set_message(text)


class Interface:
    def __init__(self, app, id_enabled, id_list_enabled, preferred_styles=None):
        self.app = app
        self.id_enabled = id_enabled
        self.id_list_enabled = id_list_enabled
        self.last_score = None
        self.last_model = None
        self.manual_detect_enabled = False
        self.window = MainWindow()
        self.actions_manager = ActionsManager(self.window)
        self.activate_no_session_mode()
        self.window.show()
        self.register_listener(("actions", "session", "exit"), self.window.close)
        self.register_listener(("actions", "help", "about"), self.show_about_dialog)
        self._configure_qt_style(preferred_styles)

    def run(self):
        return self.app.exec_()

    def set_manual_detect_enabled(self, enabled):
        self.manual_detect_enabled = enabled
        self.actions_manager.enable_manual_detect(enabled)

    def activate_search_mode(self):
        self.actions_manager.set_search_mode()
        self.window.exams_view.block_keyboard(True)
        self.update_text("", "")
        self.update_status_bar(_("Grading - Scanning exam"))

    def activate_review_mode(self, from_grading):
        if from_grading:
            self.actions_manager.set_review_from_grading_mode()
            self.update_status_bar(_("Grading - Reviewing exam"))
        else:
            self.actions_manager.set_review_from_session_mode()
            self.update_status_bar(_("Session open - Reviewing exam"))

    def activate_manual_detect_mode(self):
        self.actions_manager.set_manual_detect_mode()
        self.update_text(_("Click on the outer corners of the answer tables"), "")
        self.update_status_bar(_("Grading - Manual detection mode"))

    def activate_session_mode(self):
        self.actions_manager.set_session_mode()
        self.window.exams_view.block_keyboard(False)
        self.display_wait_image()
        self.update_text("", "")
        self.update_status_bar(_("Session open"))

    def activate_no_session_mode(self):
        self.actions_manager.set_no_session_mode()
        self.display_wait_image()
        self.update_text("", "")
        self.update_status_bar(_("No session: open or create a session " "to start"))
        self.window.clear_exams_view()

    def add_exams(self, exams):
        self.window.exams_view.add_exams(exams)

    def add_exam(self, exam):
        self.window.exams_view.add_exam(exam)

    def update_exam(self, exam):
        self.window.exams_view.update_exam(exam)

    def remove_exam(self, exam):
        self.window.exams_view.remove_exam(exam)

    def selected_exam(self):
        return self.window.exams_view.selected_exam()

    def select_next_exam(self):
        return self.window.exams_view.select_next_exam()

    def clear_selected_exam(self):
        return self.window.exams_view.clear_selected_exam()

    def enable_manual_detect(self, enabled):
        """Enables or disables the manual detection mode.

        If `enable` is True, it is enabled. Otherwise, it is disabled.

        """
        self.actions_manager.enable_manual_detect(enabled)

    def update_status(self, score, model=None, seq_num=None, survey_mode=False):
        self.window.center_view.update_status(
            score, model=model, seq_num=seq_num, survey_mode=survey_mode
        )

    def update_text_up(self, text):
        if text is None:
            text = ""
        self.window.center_view.update_text_up(text)

    def update_text_down(self, text):
        if text is None:
            text = ""
        self.window.center_view.update_text_down(text)

    def update_status_bar(self, text):
        self.window.update_status_bar(text)

    def update_text(self, text_up, text_down):
        self.window.center_view.update_text_up(text_up)
        self.window.center_view.update_text_down(text_down)

    def register_listeners(self, listeners):
        """Registers a dictionary of listeners for the events of the gui.

        The listeners are specified as a dictionary with pairs
        event_key->listener. Keys are tuples of strings such as
        ('action', 'session', 'close').

        """
        for key, listener in listeners.items():
            self.register_listener(key, listener)

    def register_listener(self, key, listener):
        """Registers a single listener for the events of the gui.

        Keys are tuples of strings such as ('action', 'session',
        'close').

        """
        if key[0] == "actions":
            self.actions_manager.register_listener(key[1:], listener)
        elif key[0] == "center_view":
            self.window.center_view.register_listener(key[1:], listener)
        elif key[0] == "window":
            self.window.register_listener(key[1:], listener)
        else:
            assert False, "Unknown event key {0}".format(key)

    def is_action_checked(self, action_key):
        """For checkabel actions, returns whether the action is checked.

        Action keys are tuples such as ('tools', 'lines').

        """
        return self.actions_manager.is_action_checked(action_key)

    def register_timer(self, time_delta, callback):
        """Registers a callback function to be run after time_delta ms."""
        timer = QTimer(self.window)
        timer.setSingleShot(True)
        timer.timeout.connect(callback)
        timer.setInterval(time_delta)
        timer.start()

    def run_later(self, callback, delay=0):
        """Registers a callback for immediate enqueueing in the event loop."""
        self.register_timer(delay, callback)

    def display_capture(self, ipl_image):
        """Displays a captured image in the window.

        The image is in the OpenCV IPL format.

        """
        self.window.center_view.display_capture(ipl_image)

    def save_capture(self, filename):
        """Saves the current capture and its annotations to the given file."""
        self.window.center_view.grab().save(filename)

    def display_wait_image(self):
        """Displays the default image instead of a camera capture."""
        self.window.center_view.display_wait_image()

    def dialog_new_session(self, config_filename=None):
        """Displays a new session dialog.

        An initial value for the path of the .eye file can be passed as
        `config_filename`.

        The data introduced by the user is returned as a dictionary with
        keys `directory`, `config` and `id_list`. `id_list` may be None.

        The return value is None if the user cancels the dialog.

        """
        dialog = wizards.WizardNewSession(self.window, config_filename=config_filename)
        result = dialog.exec_()
        if result == QDialog.Accepted:
            return dialog.values()
        else:
            return None

    def dialog_student_id(self, ranked_students, student_listings):
        """Displays a dialog to change the student id.

        Returns a student object with the option selected by the user.
        The return value is None if the user cancels the dialog.

        """
        dialog = students.DialogStudentId(
            self.window, ranked_students, student_listings
        )
        return dialog.exec_()

    def dialog_open_session(self):
        """Displays an open session dialog.

        The filename of the session file is returned or None.

        """
        filename, __ = QFileDialog.getOpenFileName(
            self.window,
            _("Select the session file"),
            "",
            FileNameFilters.session_db,
            None,
            QFileDialog.DontUseNativeDialog,
        )
        return filename if filename else None

    def dialog_camera_selection(self, capture_context):
        """Displays a camera selection dialog.

        `capture_context` is the detection.ExamCaptureContext object
        to be used.

        """
        dialog = dialogs.DialogCameraSelection(capture_context, self.window)
        return dialog.exec_()

    def dialog_export_grades(self, helper):
        """Displays the dialog for exporting grades.

        `helper` is a `eyegrade.export.GradesExportHelper object.

        If accepted by the user, it returns True, else False.

        """
        dialog = export.DialogExportGrades(self.window, helper)
        return dialog.exec_()

    def dialog_students(self, student_listings):
        """Displays the student list."""
        dialog = students.DialogStudents(self.window, student_listings)
        return dialog.exec_()

    def dialog_export_exam_config(self):
        """Displays the dialog for exporting the current exam configuration.

        If accepted by the user, it returns the filename.
        Returns None if cancelled.

        """
        save_dialog = QFileDialog(
            parent=self.window,
            caption=_("Save exam configration as..."),
            filter=_("Exam configuration (*.eye)"),
        )
        save_dialog.setOptions(QFileDialog.DontUseNativeDialog)
        save_dialog.setDefaultSuffix("eye")
        save_dialog.setFileMode(QFileDialog.AnyFile)
        save_dialog.setAcceptMode(QFileDialog.AcceptSave)
        filename = None
        if save_dialog.exec_():
            filename_list = save_dialog.selectedFiles()
            if len(filename_list) == 1:
                filename = filename_list[0]
        return filename

    def show_information(self, message, title="Information"):
        """Displays an dialog with an informative message.

        The method blocks until the user closes the dialog.

        """
        QMessageBox.information(self.window, title, message)

    def show_error(self, message, title="Error"):
        """Displays an error dialog with the given message.

        The method blocks until the user closes the dialog.

        """
        QMessageBox.critical(self.window, title, message)

    def show_warning(self, message, is_question=True):
        """Displays a warning dialog.

        Returns True if the the user accepts and False otherwise.

        """
        if not is_question:
            result = QMessageBox.warning(self.window, _("Warning"), message)
            if result == QMessageBox.Ok:
                return True
            else:
                return False
        else:
            result = QMessageBox.warning(
                self.window,
                _("Warning"),
                message,
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if result == QMessageBox.Yes:
                return True
            else:
                return False

    def run_worker(self, task, callback):
        """Runs a task in another thread.

        The `task` must be an object that implements a `run()`
        method. Completion is notified to the given `callback` function.

        """
        worker = Worker(task)
        worker.finished.connect(callback)
        QThreadPool.globalInstance().start(worker)

    def show_about_dialog(self):
        dialog = dialogs.DialogAbout(self.window)
        dialog.exec_()

    def _configure_qt_style(self, preferred_styles):
        if preferred_styles is not None:
            for style_key in preferred_styles:
                style = QStyleFactory.create(style_key)
                if style is not None:
                    self.app.setStyle(style)
                    break
