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
import gettext

from PyQt4.QtGui import (QDialog, QComboBox, QWidget, QVBoxLayout,
                         QFormLayout, QDialogButtonBox, QFileDialog, )

from .widgets import LabelledCheckBox
from .. import utils

t = gettext.translation('eyegrade', utils.locale_dir(), fallback=True)
_ = t.ugettext


class DialogExportGrades(QDialog):
    """Dialog to export grades listings.

    Example (replace `parent` by the parent widget):

    dialog = DialogExportGrades(parent)
    file_name, options = dialog.exec_()

    """
    def __init__(self, parent):
        super(DialogExportGrades, self).__init__(parent)
        self.setWindowTitle(_('Export grades listing'))
        self.type_combo = QComboBox(parent=self)
        self.type_combo.addItem(_('Tabs-separated file'))
        self.students_combo = QComboBox(parent=self)
        self.students_combo.addItem(_('All the students in the list'))
        self.students_combo.addItem(_('Only the students who attended'
                                      ' the exam'))
        self.sort_combo = QComboBox(parent=self)
        self.sort_combo.addItem(_('Student list'))
        self.sort_combo.addItem(_('Exam grading sequence'))
        self.export_items = ExportItems(self)
        buttons = QDialogButtonBox((QDialogButtonBox.Ok
                                    | QDialogButtonBox.Cancel))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QFormLayout(parent=self)
        self.setLayout(layout)
        layout.addRow(_('File type:'), self.type_combo)
        layout.addRow(_('Students:'), self.students_combo)
        layout.addRow(_('Sort by:'), self.sort_combo)
        layout.addRow(_('Export fields:'), self.export_items)
        layout.addRow(buttons)

    def exec_(self):
        """Shows the dialog and waits until it is closed.

        Returns the options selected by the user, or None if the dialog
        is cancelled.

        """
        result = None
        dialog_result = super(DialogExportGrades, self).exec_()
        if dialog_result == QDialog.Accepted:
            filename = self._get_save_file_name()
            if filename:
                result = (filename,
                          self.type_combo.currentIndex(),
                          self.students_combo.currentIndex(),
                          self.sort_combo.currentIndex(),
                          self.export_items.get_state())
        return result

    def _get_save_file_name(self):
        save_dialog = QFileDialog(parent=self, caption=_('Save listing as...'),
                                  filter=_('Data file (*.csv)'))
        save_dialog.setOptions(QFileDialog.DontUseNativeDialog)
        save_dialog.setDefaultSuffix('csv')
        save_dialog.setFileMode(QFileDialog.AnyFile)
        save_dialog.setAcceptMode(QFileDialog.AcceptSave)
        filename = None
        if save_dialog.exec_():
            filename_list = save_dialog.selectedFiles()
            if len(filename_list) == 1:
                filename = filename_list[0]
        return filename


class ExportItems(QWidget):
    def __init__(self, parent):
        super(ExportItems, self).__init__(parent=parent)
        self.checkboxes = [
            ('student_id',
             LabelledCheckBox(_('Student id number'), self, True)),
            ('student_name',
             LabelledCheckBox(_('Student name'), self, True)),
            ('seq_num',
             LabelledCheckBox(_('Exam sequence number'), self, True)),
            ('model',
             LabelledCheckBox(_('Exam model letter'), self, True)),
            ('correct',
             LabelledCheckBox(_('Number of correct answers'), self, True)),
            ('incorrect',
             LabelledCheckBox(_('Number of incorrect answers'), self, True)),
            ('score',
             LabelledCheckBox(_('Score'), self, True)),
            ('answers',
             LabelledCheckBox(_('List of answers'), self, True)),
        ]
        layout = QVBoxLayout(self)
        for key, checkbox in self.checkboxes:
            layout.addWidget(checkbox)
        self.setLayout(layout)

    def get_state(self):
        state = {}
        for key, checkbox in self.checkboxes:
            state[key] = checkbox.is_checked()
        return state
