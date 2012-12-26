# Eyegrade: grading multiple choice questions with a webcam
# Copyright (C) 2012 Jesus Arias Fisteus
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

import os.path

#from PyQt4 import QtCore, QtGui
from PyQt4.QtGui import (QImage, QWidget, QMainWindow, QPainter,
                         QSizePolicy, QApplication, QVBoxLayout,
                         QLabel, QIcon, QAction, QMenu, QDialog,
                         QFormLayout, QLineEdit, QDialogButtonBox,
                         QComboBox, QFileDialog, QHBoxLayout, QPushButton,
                         QMessageBox, QPixmap,)

from PyQt4.QtCore import Qt, QTimer

from eyegrade.utils import resource_path, program_name, version, web_location

_filter_exam_config = 'Exam configuration (*.eye)'
_filter_student_list = 'Student list (*.csv *.tsv *.txt *.lst *.list)'


class OpenFileWidget(QWidget):
    """Dialog with a text field and a button to open a file selector."""
    def __init__(self, parent, select_directory=False, name_filter='',
                 minimum_width=200, title=''):
        super(OpenFileWidget, self).__init__(parent)
        self.select_directory = select_directory
        self.name_filter = name_filter
        self.title = title
        layout = QHBoxLayout(self)
        self.setLayout(layout)
        self.filename_widget = QLineEdit(self)
        self.filename_widget.setMinimumWidth(minimum_width)
        self.button = QPushButton(QIcon(resource_path('open_file.svg')), '',
                                  parent=self)
        self.button.clicked.connect(self._open_dialog)
        layout.addWidget(self.filename_widget)
        layout.addWidget(self.button)

    def text(self):
        return self.filename_widget.text()

    def setEnabled(self, enabled):
        self.filename_widget.setEnabled(enabled)
        self.button.setEnabled(enabled)

    def _open_dialog(self, value):
        if self.select_directory:
            directory = \
                QFileDialog.getExistingDirectory(self, self.title, '',
                                            (QFileDialog.ShowDirsOnly
                                             | QFileDialog.DontResolveSymlinks))
            if directory:
                self.filename_widget.setText(directory)
        else:
            filename = QFileDialog.getOpenFileName(self, self.title, '',
                                                   self.name_filter)
            if filename:
                self.filename_widget.setText(filename)


class DialogStudentId(QDialog):
    """Dialog to change the student id.

    Example (replace `parent` by the parent widget):

    dialog = DialogStudentId(parent)
    id = dialog.exec_()

    """
    def __init__(self, parent, students):
        super(DialogStudentId, self).__init__(parent)
        self.setWindowTitle('Change the student id')
        layout = QFormLayout()
        self.setLayout(layout)
        self.combo = QComboBox(parent)
        self.combo.setEditable(True)
        self.combo.setAutoCompletion(True)
        for student in students:
            self.combo.addItem(student)
        buttons = QDialogButtonBox((QDialogButtonBox.Ok
                                    | QDialogButtonBox.Cancel))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow('Student id:', self.combo)
        layout.addRow(buttons)

    def exec_(self):
        """Shows the dialog and waits until it is closed.

        Returns the text of the option selected by the user, or None if
        the dialog is cancelled.

        """
        result = super(DialogStudentId, self).exec_()
        if result == QDialog.Accepted:
            return str(self.combo.currentText())
        else:
            return None


class DialogNewSession(QDialog):
    """Dialog to receive parameters for creating a new grading session.

    Example (replace `parent` by the parent widget):

    dialog = DialogNewSession(parent)
    values = dialog.exec_()

    """
    def __init__(self, parent):
        super(DialogNewSession, self).__init__(parent)
        self.setWindowTitle('New session')
        layout = QFormLayout()
        self.setLayout(layout)
        self.directory_w = OpenFileWidget(self, select_directory=True,
                                 title='Select or create an empty directory')
        self.config_file_w = OpenFileWidget(self,
                                 title='Select the exam configuration file',
                                 name_filter=_filter_exam_config)
        self.use_id_list_w = QComboBox(self)
        self.use_id_list_w.addItems(['Yes', 'No'])
        self.use_id_list_w.currentIndexChanged.connect(self._id_list_listener)
        self.id_list_w = OpenFileWidget(self, name_filter=_filter_student_list)
        buttons = QDialogButtonBox((QDialogButtonBox.Ok
                                    | QDialogButtonBox.Cancel))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow('Directory:', self.directory_w)
        layout.addRow('Exam configuration file:', self.config_file_w)
        layout.addRow('Load student list:', self.use_id_list_w)
        layout.addRow('Student list:', self.id_list_w)
        layout.addRow(buttons)

    def _get_values(self):
        values = {}
        values['directory'] = str(self.directory_w.text()).strip()
        values['config'] = str(self.config_file_w.text()).strip()
        print self.use_id_list_w.currentIndex()
        if self.use_id_list_w.currentIndex() == 0:
            values['id_list'] = str(self.id_list_w.text()).strip()
        else:
            values['id_list'] = None
        # Check the values (the files must exist, etc.)
        if not os.path.isdir(values['directory']):
            QMessageBox.critical(self, 'Error',
                          'The directory does not exist or is not a directory.')
            return None
        dir_content = os.listdir(values['directory'])
        if dir_content:
            if 'session.eye' in dir_content:
                QMessageBox.critical(self, 'Error',
                            ('The directory already contains a session. '
                             'Choose another directory or create a new one.'))
                return None
            else:
                result = QMessageBox.question(self, 'Warning',
                            ('The directory is not empty. '
                             'Are you sure you want to create a session here?'),
                            QMessageBox.Yes | QMessageBox.No,
                            QMessageBox.No)
                if result == QMessageBox.No:
                    return None
        if not os.path.isfile(values['config']):
            QMessageBox.critical(self, 'Error',
                                 ('The exam configuration file does not'
                                  'exist or is not a regular file.'))
            return None
        if (values['id_list'] is not None
              and not os.path.isfile(values['id_list'])):
            QMessageBox.critical(self, 'Error',
                                 ('The student list file does not'
                                  'exist or is not a regular file.'))
            return None
        return values

    def exec_(self):
        finish = False
        while not finish:
            result = super(DialogNewSession, self).exec_()
            if result == QDialog.Accepted:
                values = self._get_values()
                if values is not None:
                    finish = True
            else:
                values = None
                finish = True
        return values

    def _id_list_listener(self, index):
        if index == 0:
            self.id_list_w.setEnabled(True)
        else:
            self.id_list_w.setEnabled(False)


class ActionsManager(object):
    """Creates and manages the toolbar buttons."""

    _actions_grading_data = [
        ('snapshot', 'snapshot.svg', 'Sna&pshot'),
        ('manual_detect', 'manual_detect.svg', '&Manual bounds'),
        ('next_id', 'next_id.svg', '&Next student id'),
        ('edit_id', 'edit_id.svg', '&Edit student id'),
        ('save', 'save.svg', '&Save capture'),
        ('discard', 'discard.svg', '&Discard capture'),
        ]

    _actions_session_data = [
        ('new', 'new.svg', '&New session'),
        ('open', 'open.svg', '&Open session'),
        ('close', 'close.svg', '&Close session'),
        ('*separator*', None, None),
        ('exit', 'exit.svg', '&Exit'),
        ]

    _actions_help_data = [
        ('about', None, '&About'),
        ]

    def __init__(self, window):
        """Creates a manager for the given toolbar object."""
        self.window = window
        self.menubar = window.menuBar()
        self.toolbar = window.addToolBar('Grade Toolbar')
        self.menus = {}
        self.actions_grading = {}
        self.actions_session = {}
        action_lists = {'session': [], 'grading': []}
        for key, icon, tooltip in ActionsManager._actions_session_data:
            self._add_action(key, icon, tooltip, self.actions_session,
                             action_lists['session'])
        for key, icon, tooltip in ActionsManager._actions_grading_data:
            self._add_action(key, icon, tooltip, self.actions_grading,
                             action_lists['grading'])
        self._populate_menubar(action_lists)
        self._populate_toolbar(action_lists)

    def set_search_mode(self):
        self.actions_grading['snapshot'].setEnabled(True)
        self.actions_grading['manual_detect'].setEnabled(True)
        self.actions_grading['next_id'].setEnabled(False)
        self.actions_grading['edit_id'].setEnabled(False)
        self.actions_grading['save'].setEnabled(False)
        self.actions_grading['discard'].setEnabled(False)
        self.menus['grading'].setEnabled(True)
        self.actions_session['new'].setEnabled(False)
        self.actions_session['open'].setEnabled(False)
        self.actions_session['close'].setEnabled(True)
        self.actions_session['exit'].setEnabled(True)

    def set_review_mode(self):
        self.actions_grading['snapshot'].setEnabled(False)
        self.actions_grading['manual_detect'].setEnabled(False)
        self.actions_grading['next_id'].setEnabled(True)
        self.actions_grading['edit_id'].setEnabled(True)
        self.actions_grading['save'].setEnabled(True)
        self.actions_grading['discard'].setEnabled(True)
        self.menus['grading'].setEnabled(True)
        self.actions_session['new'].setEnabled(False)
        self.actions_session['open'].setEnabled(False)
        self.actions_session['close'].setEnabled(True)
        self.actions_session['exit'].setEnabled(True)

    def set_manual_detect_mode(self):
        self.actions_grading['snapshot'].setEnabled(False)
        self.actions_grading['manual_detect'].setEnabled(True)
        self.actions_grading['next_id'].setEnabled(False)
        self.actions_grading['edit_id'].setEnabled(False)
        self.actions_grading['save'].setEnabled(False)
        self.actions_grading['discard'].setEnabled(True)
        self.menus['grading'].setEnabled(True)
        self.actions_session['new'].setEnabled(False)
        self.actions_session['open'].setEnabled(False)
        self.actions_session['close'].setEnabled(True)
        self.actions_session['exit'].setEnabled(True)

    def set_no_session_mode(self):
        for key in self.actions_grading:
            self.actions_grading[key].setEnabled(False)
        self.menus['grading'].setEnabled(False)
        self.actions_session['new'].setEnabled(True)
        self.actions_session['open'].setEnabled(True)
        self.actions_session['close'].setEnabled(False)
        self.actions_session['exit'].setEnabled(True)

    def enable_manual_detect(self, enabled):
        """Enables or disables the manual detection mode.

        If `enable` is True, it is enabled. Otherwise, it is disabled.

        """
        self.actions_grading['manual_detect'].setEnabled(enabled)

    def register_listener(self, key, listener):
        actions = None
        if key[0] == 'session':
            actions = self.actions_session
        elif key[0] == 'grading':
            actions = self.actions_grading
        if actions:
            assert key[1] in actions
            actions[key[1]].triggered.connect(listener)
        else:
            assert False, 'Undefined listener key: {0}'.format(key)

    def _add_action(self, action_name, icon_file, tooltip, group, actions_list):
        action = self._create_action(action_name, icon_file, tooltip)
        if not action.isSeparator():
            group[action_name] = action
        actions_list.append(action)

    def _populate_menu(self, menu, actions_data):
        for key, icon, tooltip in actions_data:
            menu.addAction(self._create_action(key, icon, tooltip))

    def _create_action(self, action_name, icon_file, tooltip):
        if action_name == '*separator*':
            action = QAction(self.window)
            action.setSeparator(True)
        else:
            if icon_file:
                action = QAction(QIcon(resource_path(icon_file)),
                                 tooltip, self.window)
            else:
                action = QAction(tooltip, self.window)
        return action

    def _populate_menubar(self, action_lists):
        self.menus['session'] = QMenu('&Session', self.menubar)
        self.menus['grading'] = QMenu('&Grading', self.menubar)
        self.menubar.addMenu(self.menus['session'])
        self.menubar.addMenu(self.menus['grading'])
        for action in action_lists['session']:
            self.menus['session'].addAction(action)
        for action in action_lists['grading']:
            self.menus['grading'].addAction(action)
        help_menu = QMenu('&Help', self.menubar)
        self.menubar.addMenu(help_menu)
        self._populate_menu(help_menu, ActionsManager._actions_help_data)

    def _populate_toolbar(self, action_lists):
        for action in action_lists['grading']:
            self.toolbar.addAction(action)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.actions_session['new'])
        self.toolbar.addAction(self.actions_session['open'])
        self.toolbar.addAction(self.actions_session['close'])


class CamView(QWidget):
    def __init__(self, parent=None):
        super(CamView, self).__init__(parent)
        self.setFixedSize(640, 480)
        self.display_wait_image()
        self.logo = QPixmap(resource_path('logo.svg'))
        self.mouse_listener = None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawImage(event.rect(), self.image)

    def display_capture(self, ipl_image):
        """Displays a captured image in the window.

        The image is in the OpenCV IPL format.

        """
        self.image = QImage(ipl_image.tostring(),
                            ipl_image.width, ipl_image.height,
                            QImage.Format_RGB888).rgbSwapped()
        painter = QPainter(self.image)
        painter.drawPixmap(600, 440, 36, 36, self.logo)
        self.update()

    def display_wait_image(self):
        self.image = QImage(640, 480, QImage.Format_RGB888)
        self.image.fill(Qt.darkBlue)
        self.update()

    def register_mouse_pressed_listener(self, listener):
        """Registers a function to receive a mouse clicked event.

        The listener must receive as parameter a tuple (x, y).

        """
        self.mouse_listener = listener

    def mousePressEvent(self, event):
        if self.mouse_listener:
            self.mouse_listener((event.x(), event.y()))


class CenterView(QWidget):
    img_correct = '<img src="%s" height="22" width="22">'%\
                  resource_path('correct.svg')
    img_incorrect = '<img src="%s" height="22" width="22">'%\
                    resource_path('incorrect.svg')
    img_unanswered = '<img src="%s" height="22" width="22">'%\
                     resource_path('unanswered.svg')

    def __init__(self, parent=None):
        super(CenterView, self).__init__(parent)
        layout = QVBoxLayout()
        self.setLayout(layout)
        self.camview = CamView(parent=self)
        self.label_up = QLabel()
        self.label_down = QLabel()
        layout.addWidget(self.camview)
        layout.addWidget(self.label_up)
        layout.addWidget(self.label_down)

    def update_status(self, score, model=None, seq_num=None, survey_mode=False):
        parts = []
        if score is not None:
            if not survey_mode:
                correct, incorrect, blank, indet, score, max_score = score
                parts.append(CenterView.img_correct)
                parts.append(str(correct) + '  ')
                parts.append(CenterView.img_incorrect)
                parts.append(str(incorrect) + '  ')
                parts.append(CenterView.img_unanswered)
                parts.append(str(blank) + '  ')
                if score is not None and max_score is not None:
                    parts.append('Score: %.2f / %.2f  '%(score, max_score))
            else:
                parts.append('[Survey mode on]  ')
        if model is not None:
            parts.append('Model: ' + model + '  ')
        if seq_num is not None:
            parts.append('Num.: ' + str(seq_num) + '  ')
        self.label_down.setText(('<span style="white-space: pre">'
                                 + ' '.join(parts) + '</span>'))

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
        if key[0] == 'camview':
            if key[1] == 'mouse_pressed':
                self.camview.register_mouse_pressed_listener(listener)
            else:
                assert False, 'Undefined listener key: {0}'.format(key)
        else:
            assert False, 'Undefined listener key: {0}'.format(key)


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        policy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setSizePolicy(policy)
        self.center_view = CenterView()
        self.setCentralWidget(self.center_view)
        self.setWindowTitle("Eyegrade")
        self.setWindowIcon(QIcon(resource_path('logo.svg')))
        self.adjustSize()
        self.setFixedSize(self.sizeHint())
        self.digit_key_listener = None
        self.exit_listener = False

    def keyPressEvent(self, event):
        if (self.digit_key_listener
            and event.key() >= Qt.Key_0 and event.key() <= Qt.Key_9):
            self.digit_key_listener(event.text())

    def register_listener(self, key, listener):
        if key[0] == 'key_pressed':
            if key[1] == 'digit':
                self.digit_key_listener = listener
            else:
                assert False, 'Undefined listener key: {0}'.format(key)
        elif key[0] == 'exit':
            self.exit_listener = listener
        else:
            assert False, 'Undefined listener key: {0}'.format(key)

    def closeEvent(self, event):
        accept = True
        if self.exit_listener is not None:
            accept = self.exit_listener()
        if accept:
            event.accept()
        else:
            event.ignore()


class Interface(object):
    def __init__(self, id_enabled, id_list_enabled, argv):
        self.app = QApplication(argv)
        self.id_enabled = id_enabled
        self.id_list_enabled = id_list_enabled
        self.last_score = None
        self.last_model = None
        self.manual_detect_enabled = False
        self.window = MainWindow()
        self.actions_manager = ActionsManager(self.window)
        self.activate_no_session_mode()
        self.window.show()
        self.register_listener(('actions', 'session', 'exit'),
                               self.window.close)

    def run(self):
        return self.app.exec_()

    def set_manual_detect_enabled(self, enabled):
        self.manual_detect_enabled = enabled
        self.actions_manager.set_manual_detect_enabled(enabled)

    def activate_search_mode(self):
        self.actions_manager.set_search_mode()

    def activate_review_mode(self):
        self.actions_manager.set_review_mode()

    def activate_manual_detect_mode(self):
        self.actions_manager.set_manual_detect_mode()

    def activate_no_session_mode(self):
        self.actions_manager.set_no_session_mode()
        self.display_wait_image()
        self.update_text_up('')
        self.show_version()

    def enable_manual_detect(self, enabled):
        """Enables or disables the manual detection mode.

        If `enable` is True, it is enabled. Otherwise, it is disabled.

        """
        self.actions_manager.enable_manual_detect(enabled)

    def update_status(self, score, model=None, seq_num=None, survey_mode=False):
        self.window.center_view.update_status(score, model=model,
                                              seq_num=seq_num,
                                              survey_mode=survey_mode)

    def update_text_up(self, text):
        if text is None:
            text = ''
        self.window.center_view.update_text_up(text)

    def update_text_down(self, text):
        if text is None:
            text = ''
        self.window.center_view.update_text_down(text)

    def update_text(self, text_up, text_down):
        self.window.center_view.update_text_up(text_up)
        self.window.center_view.update_text_down(text_down)

    def register_listeners(self, listeners):
        """Registers a dictionary of listeners for the events of the gui.

        The listeners are specified as a dictionary with pairs
        event_key->listener. Keys are tuples of strings such as
        ('action', 'session', 'close').

        """
        for key, listener in listeners.iteritems():
            self.register_listener(key, listener)

    def register_listener(self, key, listener):
        """Registers a single listener for the events of the gui.

        Keys are tuples of strings such as ('action', 'session',
        'close').

        """
        if key[0] == 'actions':
            self.actions_manager.register_listener(key[1:], listener)
        elif key[0] == 'center_view':
            self.window.center_view.register_listener(key[1:], listener)
        elif key[0] == 'window':
            self.window.register_listener(key[1:], listener)
        else:
            assert False, 'Unknown event key {0}'.format(key)

    def register_timer(self, time_delta, callback):
        """Registers a callback function to be run after time_delta ms."""
        timer = QTimer(self.window)
        timer.setSingleShot(True)
        timer.timeout.connect(callback)
        timer.setInterval(time_delta)
        timer.start()

    def display_capture(self, ipl_image):
        """Displays a captured image in the window.

        The image is in the OpenCV IPL format.

        """
        self.window.center_view.display_capture(ipl_image)

    def save_capture(self, filename):
        """Saves the current capture and its annotations to the given file."""
        pixmap = QPixmap(self.window.center_view.size())
        self.window.center_view.render(pixmap)
        pixmap.save(filename)

    def display_wait_image(self):
        """Displays the default image instead of a camera capture."""
        self.window.center_view.display_wait_image()

    def dialog_new_session(self):
        """Displays a new session dialog.

        The data introduced by the user is returned as a dictionary with
        keys `directory`, `config` and `id_list`. `id_list` may be None.

        The return value is None if the user cancels the dialog.

        """
        dialog = DialogNewSession(self.window)
        return dialog.exec_()

    def dialog_student_id(self, student_ids):
        """Displays a dialog to change the student id.

        A string with the option selected by the user (possibly
        student id and name) is returned.

        The return value is None if the user cancels the dialog.

        """
        dialog = DialogStudentId(self.window, student_ids)
        return dialog.exec_()

    def dialog_open_session(self):
        """Displays an open session dialog.

        The filename of the session file is returned or None.

        """
        filename = QFileDialog.getOpenFileName(self.window,
                                               'Select the session file',
                                               '', _filter_exam_config)
        return str(filename) if filename else None

    def show_error(self, message, title='Error'):
        """Displays an error dialog with the given message.

        The method blocks until the user closes the dialog.

        """
        QMessageBox.critical(self.window, title, message)

    def show_warning(self, message, title='Warning', is_question=True):
        """Displays a warning dialog.

        Returns True if the the user accepts and False otherwise.

        """
        if not is_question:
            result = QMessageBox.warning(self.window, 'Warning', message)
            if result == QMessageBox.Ok:
                return True
            else:
                return False
        else:
            result = QMessageBox.warning(self.window, 'Warning', message,
                                         QMessageBox.Yes | QMessageBox.No,
                                         QMessageBox.No)
            if result == QMessageBox.Yes:
                return True
            else:
                return False

    def show_version(self):
        version_line = '{0} {1} - <a href="{2}">{2}</a>'\
                       .format(program_name, version, web_location)
        self.update_text_down(version_line)


if __name__ == '__main__':
    import sys
    interface = Interface(True, True, sys.argv)
    interface.update_status((8, 9, 2, 0, 8.0, 10.0), model='A', seq_num=23)
    interface.update_text('100099999 Bastian Baltasar Bux')
    def sample_listener(self):
        print 'In listener'
    interface.register_listener(('actions', 'session', 'close'),
                                sample_listener)
    sys.exit(interface.run())
