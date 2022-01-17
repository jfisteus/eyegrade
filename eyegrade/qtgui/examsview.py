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

from PyQt5.QtGui import QIcon, QImage, QPainter

from PyQt5.QtWidgets import (
    QListView,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from PyQt5.QtCore import QEvent, QItemSelection, QObject, QSize, pyqtSignal, pyqtSlot

from .. import exams


class ExamIcon(QIcon):
    def __init__(self, exam):
        super().__init__(exam.image_drawn_path())


class ExamImage(QImage):
    def __init__(self, exam):
        super().__init__(exam.image_drawn_path())


class ThumbnailsViewItem(QListWidgetItem):
    def __init__(self, exam):
        self.exam = exam
        super().__init__(ExamIcon(exam), self._label())

    def update(self):
        self.setText(self._label())
        self.setIcon(ExamIcon(self.exam))

    def _label(self):
        if self.exam.decisions.student:
            label = self.exam.decisions.student.name_or_id
        else:
            label = ""
        return label


class ThumbnailsView(QListWidget):
    selection_changed = pyqtSignal(exams.Exam)

    def __init__(self, parent):
        super().__init__(parent)
        self.setIconSize(QSize(120, 80))
        self.setViewMode(QListView.IconMode)
        self.setMovement(QListView.Static)
        self.setUniformItemSizes(True)
        self.setResizeMode(QListView.Adjust)
        self.exams = []
        self.selectionModel().selectionChanged.connect(self.on_selection)
        self.keyboard_filter = KeyboardEventsFilter()
        self.installEventFilter(self.keyboard_filter)

    def add_exams(self, exams):
        for exam in exams:
            self.add_exam(exam, scroll=False)

    def add_exam(self, exam, scroll=True):
        self.addItem(ThumbnailsViewItem(exam))
        if scroll:
            self.scrollToBottom()
        self.exams.append(exam)

    def clear_exams(self):
        self.clear()
        self.exams = []

    def update_exam(self, exam):
        pos = self.exams.index(exam)
        self.item(pos).update()

    def remove_exam(self, exam):
        pos = self.exams.index(exam)
        del self.exams[pos]
        self.takeItem(pos)

    def selected_exam(self):
        items = self.selectedItems()
        if items:
            return items[0].exam
        else:
            return None

    def select_next_exam(self):
        current_exam = self.selected_exam()
        if current_exam is not None:
            pos = 1 + self.exams.index(current_exam)
            if pos < len(self.exams):
                item = self.item(pos)
                item.setSelected(True)
                self.scrollToItem(item)

    def clear_selected_exam(self):
        items = self.selectedItems()
        if items:
            items[0].setSelected(False)

    def block_keyboard(self, block):
        self.keyboard_filter.setBlocking(block)

    @pyqtSlot(QItemSelection, QItemSelection)
    def on_selection(self, selected, deselected):
        indexes = selected.indexes()
        if len(indexes):
            selected = indexes[0].row()
            if selected < len(self.exams):
                self.selection_changed.emit(self.exams[selected])


class KeyboardEventsFilter(QObject):
    def __init__(self):
        self.blocking = True
        super().__init__()

    def setBlocking(self, blocking):
        self.blocking = blocking

    def eventFilter(self, widget, event):
        if self.blocking and event.type() == QEvent.KeyPress:
            return True
        else:
            return super().eventFilter(widget, event)


class CaptureView(QWidget):
    def __init__(self, size, parent):
        super().__init__(parent)
        self.setFixedSize(*size)
        self.exams = []
        self.icons = []
        self.selected_index = None
        self.selected_image = None

    def set_exams(self, exams):
        self.exams = exams
        self.selected_index = 0

    def clear(self):
        self.exams = []
        self.selected_index = None
        self.selected_image = None
        self.update()

    def paintEvent(self, event):
        if self.selected_image is not None:
            painter = QPainter(self)
            painter.drawImage(0, 0, self.selected_image)

    def _set_selected_exam(self, index):
        if index != self.selected_index:
            self.selected_index = index
            if index < len(self.exams):
                self.selected_image = ExamImage(self.exams[index]).scaledToHeight(
                    self.height()
                )
            else:
                self.selected_image = None
            self.update()

    @pyqtSlot(int)
    def show_exam(self, index):
        self._set_selected_exam(index)


class ExamsView(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        layout = QVBoxLayout()
        self.setLayout(layout)
        self.thumbnails_view = ThumbnailsView(self)
        self.capture_view = CaptureView((640, 300), self)
        layout.addWidget(self.capture_view)
        layout.addWidget(self.thumbnails_view)
        self.thumbnails_view.selection_changed.connect(self.capture_view.show_exam)

    def set_exams(self, exams):
        self.thumbnails_view.set_exams(exams)
        self.capture_view.set_exams(exams)
