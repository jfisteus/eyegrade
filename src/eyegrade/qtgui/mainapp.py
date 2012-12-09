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
        self.label_up = QLabel('Test 1 <img src="%s" height="16" width="16">'\
                               %resource_path('../icons-src/correct.svg'))
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
        self.adjustSize()
        self.setFixedSize(self.sizeHint())
        self.toolbar = self.addToolBar('Eyegrade Toolbar')
        self.toolbar.addAction(QAction(QIcon(resource_path('save.png')),
                                       'Save', self))
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
