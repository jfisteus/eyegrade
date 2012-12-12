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
                         QLabel, QIcon, QAction,)

from PyQt4.QtCore import Qt, QTimer

from eyegrade.utils import resource_path


class ToolbarManager(object):
    """Creates and manages the toolbar buttons."""

    _action_data = [
        ('snapshot', 'snapshot.svg', 'Snapshot'),
        ('manual_detect', 'manual_detect.svg', 'Set exam bounds manually'),
        ('next_id', 'next_id.svg', 'Next student id'),
        ('edit_id', 'edit_id.svg', 'Edit student id'),
        ('save', 'save.svg', 'Save the current exam'),
        ('discard', 'discard.svg', 'Discard the current capture'),
        ('exit', 'exit.svg', 'Exit'),
        ]

    def __init__(self, toolbar, window):
        """Creates a manager for the given toolbar object."""
        self.toolbar = toolbar
        self.window = window
        self.actions = {}
        for key, icon, tooltip in ToolbarManager._action_data:
            self._add_action(key, icon, tooltip)

    def set_search_mode(self):
        self.actions['snapshot'].setEnabled(True)
        self.actions['manual_detect'].setEnabled(True)
        self.actions['next_id'].setEnabled(False)
        self.actions['edit_id'].setEnabled(False)
        self.actions['save'].setEnabled(False)
        self.actions['discard'].setEnabled(False)
        self.actions['exit'].setEnabled(True)

    def set_review_mode(self):
        self.actions['snapshot'].setEnabled(False)
        self.actions['manual_detect'].setEnabled(False)
        self.actions['next_id'].setEnabled(True)
        self.actions['edit_id'].setEnabled(True)
        self.actions['save'].setEnabled(True)
        self.actions['discard'].setEnabled(True)
        self.actions['exit'].setEnabled(True)

    def _add_action(self, action_name, icon_file, tooltip):
        action = QAction(QIcon(resource_path(icon_file)), tooltip, self.window)
        self.actions[action_name] = action
        self.toolbar.addAction(action)


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
    def __init__(self, parent=None):
        super(CenterView, self).__init__(parent)
        layout = QVBoxLayout()
        self.setLayout(layout)
        self.camview = CamView(parent=self)
        self.label_up = QLabel(('<img src="%s" height="16" width="16"> 5 '
                                '<img src="%s" height="16" width="16"> 7 '
                                '<img src="%s" height="16" width="16"> 3')\
                               %(resource_path('correct.svg'),
                                 resource_path('incorrect.svg'),
                                 resource_path('unanswered.svg')))
        self.label_down = QLabel('Test 2')
        layout.addWidget(self.camview)
        layout.addWidget(self.label_up)
        layout.addWidget(self.label_down)


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        policy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setSizePolicy(policy)
        self.center_view = CenterView()
        self.setCentralWidget(self.center_view)
        self.setWindowTitle("Test cam")
        toolbar = self.addToolBar('Eyegrade Toolbar')
        self.toolbar_manager = ToolbarManager(toolbar, self)
        self.toolbar_manager.set_search_mode()
        self.adjustSize()
        self.setFixedSize(self.sizeHint())

        ## timer = QTimer(self)
        ## timer.timeout.connect(self.cam_view.new_frame)
        ## timer.setInterval(100)
        ## timer.start(500)


if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
