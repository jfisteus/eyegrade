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

from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QVBoxLayout,
    QWidget,
)

from .widgets import LabelledCheckBox
from . import FileNameFilters
from .. import utils
from .. import export


t = gettext.translation("eyegrade", utils.locale_dir(), fallback=True)
_ = t.gettext


class DialogExportGrades(QDialog):
    """Dialog to export grades listings.

    `helper` is a `eyegrade.export.GradesExportHlper object
    ready to be configured. When the dialog finishes it will
    contain all the options selected by the user.

    Example (replace `parent` by the parent widget):

    helper = eyegrade.export.GradesExportHelper(exam_config, student_groups)
    dialog = DialogExportGrades(parent, helper)
    result = dialog.exec_()
    if result:
        # dialog accepted
    else:
        # dialog cancelled

    """

    def __init__(self, parent, helper):
        super().__init__(parent)
        self.helper = helper
        student_groups = helper.student_groups
        self.setWindowTitle(_("Export grades listing"))
        self.type_combo = QComboBox(parent=self)
        self.type_combo.addItem(_("Excel spreadsheet (.xlsx)"))
        self.type_combo.addItem(_("Tabs-separated file"))
        self.students_combo = QComboBox(parent=self)
        self.students_combo.addItem(_("All the students in the list"))
        self.students_combo.addItem(_("Only the students who attended the exam"))
        self.sort_combo = QComboBox(parent=self)
        self.sort_combo.addItem(_("Student list"))
        self.sort_combo.addItem(_("Last name"))
        self.sort_combo.addItem(_("Exam grading sequence"))
        if not student_groups:
            if not helper.survey_mode:
                self.students_combo.addItem(_("All the exams"))
            else:
                self.students_combo.addItem(_("All the surveys"))
            self.students_combo.setCurrentIndex(2)
            self.students_combo.setEnabled(False)
            self.sort_combo.setCurrentIndex(2)
            self.sort_combo.setEnabled(False)
        if len(student_groups) > 1:
            self.groups_combo = QComboBox(parent=self)
            self.groups_combo.addItem(_("All groups (one sheet)"))
            self.groups_combo.addItem(_("All groups (separate sheets)"))
            for group in student_groups:
                label = u"{0} #{1.identifier} ({1.name})".format(_("Group"), group)
                self.groups_combo.addItem(label)
        else:
            self.groups_combo = None
        self.headers_checkbox = LabelledCheckBox(
            _("Add column headers"), self, checked=True
        )
        self.export_items = ExportItems(helper.survey_mode, len(student_groups), self)
        buttons = QDialogButtonBox((QDialogButtonBox.Ok | QDialogButtonBox.Cancel))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QFormLayout(parent=self)
        self.setLayout(layout)
        layout.addRow(_("File type:"), self.type_combo)
        layout.addRow(_("Students:"), self.students_combo)
        if self.groups_combo is not None:
            layout.addRow(_("Student group:"), self.groups_combo)
        layout.addRow(_("Sort by:"), self.sort_combo)
        layout.addRow(_("Options:"), self.headers_checkbox)
        layout.addRow(_("Export fields:"), self.export_items)
        layout.addRow(buttons)

    def exec_(self):
        """Shows the dialog and waits until it is closed.

        Returns True if the dialog gets accepted, or False otherwise.

        """
        result = False
        dialog_result = super().exec_()
        if dialog_result == QDialog.Accepted:
            if self.type_combo.currentIndex() == 0:
                self.helper.file_format = export.FileFormat.XLSX
            elif self.type_combo.currentIndex() == 1:
                self.helper.file_format = export.FileFormat.CSV_TABS
            self.helper.file_name = self._get_save_file_name(self.helper.file_format)
            if self.helper.file_name:
                result = True
                if self.groups_combo is not None:
                    idx = self.groups_combo.currentIndex()
                    if idx > 1:
                        self.helper.export_group(idx - 2)
                    else:
                        self.helper.export_all_groups(idx == 0)
                elif self.helper.student_groups:
                    self.helper.export_group(0)
                else:
                    self.helper.export_all_exams()
                idx = self.sort_combo.currentIndex()
                if idx == 0:
                    self.helper.sort_by = export.SortBy.STUDENT_LIST
                elif idx == 1:
                    self.helper.sort_by = export.SortBy.LAST_NAME
                elif idx == 2:
                    self.helper.sort_by = export.SortBy.GRADING_SEQUENCE
                self.helper.all_students = self.students_combo.currentIndex() == 0
                self.helper.add_column_headers = self.headers_checkbox.is_checked()
                self.helper.export_columns(self.export_items.get_column_keys())
        return result

    def _get_save_file_name(self, file_format):
        if file_format == export.FileFormat.XLSX:
            file_filter = FileNameFilters.xlsx_file
            extension = "xlsx"
        else:
            file_filter = FileNameFilters.csv_file
            extension = "csv"
        save_dialog = QFileDialog(
            parent=self, caption=_("Save listing as..."), filter=file_filter
        )
        save_dialog.setOptions(QFileDialog.DontUseNativeDialog)
        save_dialog.setDefaultSuffix(extension)
        save_dialog.setFileMode(QFileDialog.AnyFile)
        save_dialog.setAcceptMode(QFileDialog.AcceptSave)
        filename = None
        if save_dialog.exec_():
            filename_list = save_dialog.selectedFiles()
            if len(filename_list) == 1:
                filename = filename_list[0]
        return filename


class ExportItems(QWidget):
    def __init__(self, survey_mode, there_are_students, parent):
        super().__init__(parent=parent)
        self.checkboxes = [
            (
                "student_id",
                LabelledCheckBox(
                    _("Student id number"),
                    self,
                    checked=not survey_mode,
                    enabled=there_are_students,
                ),
            ),
            (
                "name",
                LabelledCheckBox(
                    _("Student full name"),
                    self,
                    checked=not survey_mode,
                    enabled=there_are_students,
                ),
            ),
            (
                "last_name",
                LabelledCheckBox(
                    _("Student last name"),
                    self,
                    checked=False,
                    enabled=there_are_students,
                ),
            ),
            (
                "first_name",
                LabelledCheckBox(
                    _("Student first name"),
                    self,
                    checked=False,
                    enabled=there_are_students,
                ),
            ),
            (
                "exam_id",
                LabelledCheckBox(_("Exam sequence number"), self, checked=survey_mode),
            ),
            (
                "model",
                LabelledCheckBox(
                    _("Exam model letter"), self, checked=False, enabled=not survey_mode
                ),
            ),
            (
                "correct",
                LabelledCheckBox(
                    _("Number of correct answers"),
                    self,
                    checked=not survey_mode,
                    enabled=not survey_mode,
                ),
            ),
            (
                "incorrect",
                LabelledCheckBox(
                    _("Number of incorrect answers"),
                    self,
                    checked=not survey_mode,
                    enabled=not survey_mode,
                ),
            ),
            (
                "score",
                LabelledCheckBox(
                    _("Score"), self, checked=not survey_mode, enabled=not survey_mode
                ),
            ),
            (
                "answers",
                LabelledCheckBox(_("List of answers"), self, checked=survey_mode),
            ),
        ]
        layout = QVBoxLayout(self)
        for column, checkbox in self.checkboxes:
            layout.addWidget(checkbox)
        self.setLayout(layout)

    def get_column_keys(self):
        return [key for key, checkbox in self.checkboxes if checkbox.is_checked()]
