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

#from PyQt4 import QtCore, QtGui
from PyQt4.QtGui import (QImage, QWidget, QMainWindow, QPainter,
                         QSizePolicy, QApplication, QVBoxLayout,
                         QLabel, QIcon, QAction, QMenu,)

from PyQt4.QtCore import Qt, QTimer

from eyegrade.utils import resource_path


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
        self.set_manual_detect_enabled(False)

    def set_search_mode(self):
        self.actions_grading['snapshot'].setEnabled(True)
        ## self.actions_grading['manual_detect'].setEnabled(True)
        self.actions_grading['next_id'].setEnabled(False)
        self.actions_grading['edit_id'].setEnabled(False)
        self.actions_grading['save'].setEnabled(False)
        self.actions_grading['discard'].setEnabled(False)
        self.actions_session['close'].setEnabled(True)
        self.menus['grading'].setEnabled(True)

    def set_review_mode(self):
        self.actions_grading['snapshot'].setEnabled(False)
        ## self.actions_grading['manual_detect'].setEnabled(False)
        self.actions_grading['next_id'].setEnabled(True)
        self.actions_grading['edit_id'].setEnabled(True)
        self.actions_grading['save'].setEnabled(True)
        self.actions_grading['discard'].setEnabled(True)
        self.actions_session['close'].setEnabled(True)
        self.menus['grading'].setEnabled(True)

    def set_manual_detect_enabled(self, enabled):
        self.actions_grading['manual_detect'].setEnabled(enabled)

    def set_session_closed_mode(self):
        for key in self.actions_grading:
            self.actions_grading[key].setEnabled(False)
        self.menus['grading'].setEnabled(False)

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
        self.toolbar.addAction(self.actions_session['close'])


class CamView(QWidget):
    def __init__(self, parent=None):
        super(CamView, self).__init__(parent)
        self.image = QImage(640, 480, QImage.Format_RGB888)
        self.image.fill(Qt.darkBlue)
        self.setFixedSize(640, 480)
#        self.cam = cv.CaptureFromCAM(0)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawImage(event.rect(), self.image)

    def new_frame(self):
        self._capture_image()
        self.update()

    ## def _capture_image(self):
    ##     cvimage = cv.QueryFrame(self.cam)
    ##     self.image = QImage(cvimage.tostring(),
    ##                         cvimage.width, cvimage.height,
    ##                         QImage.Format_RGB888).rgbSwapped()


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


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        policy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setSizePolicy(policy)
        self.center_view = CenterView()
        self.setCentralWidget(self.center_view)
        self.setWindowTitle("Test cam")
        self.adjustSize()
        self.setFixedSize(self.sizeHint())

        ## timer = QTimer(self)
        ## timer.timeout.connect(self.cam_view.new_frame)
        ## timer.setInterval(100)
        ## timer.start(500)


class Interface(object):
    def __init__(self, id_enabled, id_list_enabled):
        self.id_enabled = id_enabled
        self.id_list_enabled = id_list_enabled
        self.last_score = None
        self.last_model = None
        self.manual_detect_enabled = False
        self.window = MainWindow()
        self.actions_manager = ActionsManager(self.window)
        self.actions_manager.set_search_mode()
        self.window.show()

    def set_manual_detect_enabled(self, enabled):
        self.manual_detect_enabled = enabled
        self.actions_manager.set_manual_detect_enabled(enabled)

    def activate_search_mode(self):
        self.actions_manager.set_search_mode()

    def activate_review_mode(self):
        self.actions_manager.set_review_mode()

    def update_status(self, score, model=None, seq_num=None, survey_mode=False):
        self.window.center_view.update_status(score, model=model,
                                              seq_num=seq_num,
                                              survey_mode=survey_mode)

    def update_text_up(self, text):
        self.window.center_view.update_text_up(text)


if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    interface = Interface(True, True)
    interface.update_status((8, 9, 2, 0, 8.0, 10.0), model='A', seq_num=23)
    interface.update_text_up('100099999 Bastian Baltasar Bux')
    sys.exit(app.exec_())
