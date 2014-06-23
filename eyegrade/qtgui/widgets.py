# -*- coding: utf-8 -*-

# Eyegrade: grading multiple choice questions with a webcam
# Copyright (C) 2010-2014 Jesus Arias Fisteus
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

from PyQt4.QtGui import (QComboBox, QSortFilterProxyModel, QCompleter,
                         QStatusBar, QLabel, QHBoxLayout, QCheckBox,
                         QWidget, )
from PyQt4.QtCore import Qt

from .. import utils


class CompletingComboBox(QComboBox):
    """An editable combo box that filters and autocompletes."""
    def __init__(self, parent=None, editable=True):
        super(CompletingComboBox, self).__init__(parent)
        self.setEditable(editable)
        self.filter = QSortFilterProxyModel(self)
        self.filter.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.filter.setSourceModel(self.model())
        self.completer = QCompleter(self.filter, self)
        self.completer.setCompletionMode(QCompleter.UnfilteredPopupCompletion)
        self.setCompleter(self.completer)
        self.lineEdit().textEdited[unicode]\
            .connect(self.filter.setFilterFixedString)
        self.currentIndexChanged.connect(self._index_changed)
        self.setAutoCompletion(True)

    def _index_changed(self, index):
        self.lineEdit().selectAll()


class StudentComboBox(CompletingComboBox):
    def __init__(self, parent=None, editable=True):
        super(StudentComboBox, self).__init__(parent=parent, editable=editable)

    def add_students(self, students):
        for student in students:
            self.add_student(student)

    def add_student(self, student):
        self.addItem(student.get_id_and_name())


class StatusBar(QStatusBar):
    """Status bar for the main window.

    For now it just contains a simple QLabel.

    """

    def __init__(self, parent):
        """Creates a new instance.

        :param parent: The parent of this status bar.

        """
        super(StatusBar, self).__init__(parent=parent)
        self.status_label = QLabel(parent=self)
        self.addWidget(self.status_label)
        self._show_program_version()
        self.setStyleSheet('QStatusBar {border-top: 1px solid '
                                            'rgb(128, 128, 128); }')

    def set_message(self, text):
        """Sets a new left-side status text.

        :param str text: The text to display in the status bar.

        """
        self.status_label.setText(text)

    def _show_program_version(self):
        version_line = '{0} {1} - <a href="{2}">{2}</a>'\
               .format(utils.program_name, utils.version, utils.web_location)
        self.addPermanentWidget(QLabel(version_line))


class LabelledCheckBox(QWidget):
    """A checkbox with a label."""
    def __init__(self, label_text, parent, checked=False):
        """Creates a new instance.

        :param label: The label to show with the checkbox.
        :param parent: The parent of this widget.
        :param checked: Initial state of the checkbox (defaults to False).

        """
        super(LabelledCheckBox, self).__init__(parent=parent)
        layout = QHBoxLayout(self)
        self.checkbox = QCheckBox(parent=self)
        self.checkbox.setChecked(checked)
        layout.addWidget(self.checkbox, alignment=Qt.AlignLeft)
        layout.addWidget(QLabel(label_text, parent=self), stretch=1,
                         alignment=Qt.AlignLeft)
        self.setLayout(layout)

    def is_checked(self):
        """Returns True if the checkbox is checked, False otherwise."""
        return self.checkbox.isChecked()
