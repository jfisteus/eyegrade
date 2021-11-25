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

from PyQt5.QtGui import QRegExpValidator, QIcon, QColor, QBrush

from PyQt5.QtWidgets import (
    QWidget,
    QDialog,
    QVBoxLayout,
    QDialogButtonBox,
    QTabWidget,
    QTableView,
    QPushButton,
    QMessageBox,
    QFileDialog,
    QComboBox,
    QLineEdit,
    QFormLayout,
    QLabel,
)

from PyQt5.QtCore import Qt, QAbstractTableModel, QModelIndex, QVariant, QRegExp

from . import FileNameFilters
from . import widgets
from .. import utils
from .. import students


t = gettext.translation("eyegrade", utils.locale_dir(), fallback=True)
_ = t.gettext


class DialogStudentId(QDialog):
    """Dialog to change the student id.

    Example (replace `parent` by the parent widget):

    dialog = DialogStudentId(parent)
    id = dialog.exec_()

    """

    def __init__(self, parent, ranked_students, student_listings):
        super().__init__(parent)
        self.student_listings = student_listings
        self.setWindowTitle(_("Change the student id"))
        layout = QFormLayout()
        self.setLayout(layout)
        self.combo = widgets.StudentComboBox(parent=self)
        self.combo.add_students(ranked_students)
        self.combo.editTextChanged.connect(self._check_value)
        self.combo.currentIndexChanged.connect(self._check_value)
        new_student_button = QPushButton(
            QIcon(utils.resource_path("new_id.svg")), _("New student"), parent=self
        )
        new_student_button.clicked.connect(self._new_student)
        self.buttons = QDialogButtonBox((QDialogButtonBox.Ok | QDialogButtonBox.Cancel))
        self.buttons.addButton(new_student_button, QDialogButtonBox.ActionRole)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addRow(_("Student id:"), self.combo)
        layout.addRow(self.buttons)

    def exec_(self):
        """Shows the dialog and waits until it is closed.

        Returns a student object with the option selected by the user.
        The return value is None if the user cancels the dialog.

        """
        result = super().exec_()
        if result == QDialog.Accepted:
            return self.combo.current_student()
        else:
            return None

    def _new_student(self):
        dialog = NewStudentDialog(self.student_listings, parent=self)
        student = dialog.exec_()
        if student is not None:
            self.combo.add_student(student, set_current=True)
            self.buttons.button(QDialogButtonBox.Ok).setFocus()
            self.buttons.button(QDialogButtonBox.Ok).setEnabled(True)

    def _check_value(self, param):
        if self.combo.current_student() is not None:
            self.buttons.button(QDialogButtonBox.Ok).setEnabled(True)
        else:
            self.buttons.button(QDialogButtonBox.Ok).setEnabled(False)


class NewStudentDialog(QDialog):
    """Dialog to ask for a new student.

    It returns a Student object with the data of the student.

    """

    _last_combo_value = None

    def __init__(self, student_listings, group_index=None, parent=None):
        super().__init__(parent)
        self.student_listings = student_listings
        self.group_index = group_index
        self.setMinimumWidth(300)
        self.setWindowTitle(_("Add a new student"))
        layout = QFormLayout()
        self.setLayout(layout)
        self.id_field = QLineEdit(self)
        self.id_field.setValidator(QRegExpValidator(QRegExp(r"\d+"), self))
        self.id_field.textEdited.connect(self._check_values)
        self.name_field = QLineEdit(self)
        self.surname_field = QLineEdit(self)
        self.full_name_field = QLineEdit(self)
        self.name_label = QLabel(_("Given name"))
        self.surname_label = QLabel(_("Surname"))
        self.full_name_label = QLabel(_("Full name"))
        self.email_field = QLineEdit(self)
        self.email_field.setValidator(
            QRegExpValidator(QRegExp(students.re_email), self)
        )
        self.email_field.textEdited.connect(self._check_values)
        self.combo = QComboBox(parent=self)
        self.combo.addItem(_("Separate given name and surname"))
        self.combo.addItem(_("Full name in just one field"))
        self.combo.currentIndexChanged.connect(self._update_combo)
        self.group_combo = QComboBox(parent=self)
        for listing in self.student_listings[1:]:
            self.group_combo.addItem(listing.group.name)
        layout.addRow(self.combo)
        layout.addRow(_("Id number"), self.id_field)
        layout.addRow(self.name_label, self.name_field)
        layout.addRow(self.surname_label, self.surname_field)
        layout.addRow(self.full_name_label, self.full_name_field)
        layout.addRow(_("Email"), self.email_field)
        layout.addRow(_("Group"), self.group_combo)
        self.buttons = QDialogButtonBox((QDialogButtonBox.Ok | QDialogButtonBox.Cancel))
        layout.addRow(self.buttons)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self._check_values()
        # Set the combo box
        if NewStudentDialog._last_combo_value is None:
            NewStudentDialog._last_combo_value = 0
        self.combo.setCurrentIndex(NewStudentDialog._last_combo_value)
        if self.group_index is not None:
            self.group_combo.setCurrentIndex(self.group_index)
            self.group_combo.setEnabled(False)
        self._update_combo(NewStudentDialog._last_combo_value)

    def exec_(self):
        """Shows the dialog and waits until it is closed.

        Returns the text of the option selected by the user, or None if
        the dialog is cancelled.

        """
        result = super().exec_()
        if result == QDialog.Accepted:
            NewStudentDialog._last_combo_value = self.combo.currentIndex()
            listing = self.student_listings[self.group_combo.currentIndex() + 1]
            email = self.email_field.text()
            if not email:
                email = None
            if self.combo.currentIndex() == 0:
                # First name, last name
                student = students.Student(
                    self.id_field.text(),
                    None,
                    self.name_field.text(),
                    self.surname_field.text(),
                    email,
                    group_id=listing.group.identifier,
                )
            else:
                # Full name
                student = students.Student(
                    self.id_field.text(),
                    self.full_name_field.text(),
                    None,
                    None,
                    email,
                    group_id=listing.group.identifier,
                )
            try:
                listing.add_students((student,))
            except students.DuplicateStudentIdException:
                QMessageBox.critical(
                    self,
                    _("Adding a new student"),
                    _(
                        "The student cannot be added: "
                        "a student with the same id is already in the list"
                    ),
                )
        else:
            student = None
        return student

    def _check_values(self):
        if self.id_field.hasAcceptableInput() and (
            not self.email_field.text() or self.email_field.hasAcceptableInput()
        ):
            self.buttons.button(QDialogButtonBox.Ok).setEnabled(True)
        else:
            self.buttons.button(QDialogButtonBox.Ok).setEnabled(False)

    def _update_combo(self, new_index):
        if new_index == 0:
            self.name_field.setEnabled(True)
            self.surname_field.setEnabled(True)
            self.full_name_field.setEnabled(False)
            self.name_label.setEnabled(True)
            self.surname_label.setEnabled(True)
            self.full_name_label.setEnabled(False)
            self.full_name_field.setText("")
        else:
            self.name_field.setEnabled(False)
            self.surname_field.setEnabled(False)
            self.full_name_field.setEnabled(True)
            self.name_label.setEnabled(False)
            self.surname_label.setEnabled(False)
            self.full_name_label.setEnabled(True)
            self.name_field.setText("")
            self.surname_field.setText("")


class DialogStudents(QDialog):
    """Dialog to list students."""

    def __init__(self, parent, student_listings):
        super().__init__(parent)
        self.setWindowTitle(_("Manage students and student groups"))
        main_layout = QVBoxLayout(self)
        self.setLayout(main_layout)
        tabs = StudentGroupsTabs(self, student_listings=student_listings)
        main_layout.addWidget(tabs)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(self.accept)
        main_layout.addWidget(buttons)

    def exec_(self):
        """Shows the dialog and waits until it is closed."""
        result = super().exec_()
        if result == QDialog.Accepted:
            return True
        else:
            return False


class DialogPreviewStudents(QDialog):
    """Dialog to preview and adjust a just loaded list students."""

    def __init__(self, parent, student_list, column_map):
        super().__init__(parent)
        self.setWindowTitle(_("Preview the students to be loaded"))
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        self.table = PreviewWidget(student_list, column_map, parent=self)
        self.button_swap = QPushButton(_("Swap first/last names"), parent=self)
        self.button_take_first = QPushButton(
            _("Take first name as full name"), parent=self
        )
        self.button_take_last = QPushButton(
            _("Take last name as full name"), parent=self
        )
        self.button_remove = QPushButton(_("Remove duplicate students"), parent=self)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_accept = buttons.button(QDialogButtonBox.Ok)
        layout.addWidget(self.table)
        layout.addWidget(self.button_swap)
        layout.addWidget(self.button_take_first)
        layout.addWidget(self.button_take_last)
        layout.addWidget(self.button_remove)
        layout.addWidget(buttons)
        layout.setAlignment(self.button_swap, Qt.AlignHCenter)
        layout.setAlignment(self.button_take_first, Qt.AlignHCenter)
        layout.setAlignment(self.button_take_last, Qt.AlignHCenter)
        layout.setAlignment(self.button_remove, Qt.AlignHCenter)
        self.button_swap.clicked.connect(self.table.swap_names)
        self.button_take_first.clicked.connect(self._take_first_name)
        self.button_take_last.clicked.connect(self._take_last_name)
        self.button_remove.clicked.connect(self._remove_duplicates)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        if students.StudentColumn.FIRST_NAME not in column_map:
            self._disable_buttons()
        if any(s.is_duplicate for s in student_list):
            self.button_accept.setEnabled(False)
            self.button_remove.setEnabled(True)
        else:
            self.button_remove.setEnabled(False)

    def exec_(self):
        """Shows the dialog and waits until it is closed."""
        result = super().exec_()
        if result == QDialog.Accepted:
            return True
        else:
            return False

    def _disable_buttons(self):
        self.button_swap.setEnabled(False)
        self.button_take_first.setEnabled(False)
        self.button_take_last.setEnabled(False)

    def _take_first_name(self):
        self.table.to_full_name(students.StudentColumn.FIRST_NAME)
        self._disable_buttons()

    def _take_last_name(self):
        self.table.to_full_name(students.StudentColumn.LAST_NAME)
        self._disable_buttons()

    def _remove_duplicates(self):
        self.table.remove_duplicates()
        self.button_accept.setEnabled(True)
        self.button_remove.setEnabled(False)


class GroupNameDialog(QDialog):
    def __init__(self, parent=None, group_name=""):
        super().__init__(parent)
        if not group_name:
            window_title = _("Create a new group of students")
            message = _(
                "Please, enter the name of the new group of students "
                "you want to create:"
            )
        else:
            window_title = _("Rename the group of students")
            message = _("Please, enter the new name of the group of students")
        self.setWindowTitle(window_title)
        self.group_name = group_name
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        self._name_widget = QLineEdit(self)
        if group_name:
            self._name_widget.setText(group_name)
            self._name_widget.selectAll()
        self._name_widget.textChanged.connect(self._group_name_changed)
        main_line = widgets.LineContainer(
            self, QLabel(_("Group name")), self._name_widget
        )
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self._button_ok = buttons.button(QDialogButtonBox.Ok)
        layout.addWidget(QLabel(message))
        layout.addWidget(main_line)
        layout.addWidget(buttons)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self._group_name_changed(group_name)

    def exec_(self):
        result = super().exec_()
        if result == QDialog.Accepted:
            return self._name_widget.text()
        else:
            return None

    def _group_name_changed(self, group_name):
        if group_name:
            self._button_ok.setEnabled(True)
        else:
            self._button_ok.setEnabled(False)


class StudentGroupsTabs(QWidget):
    def __init__(self, parent, student_listings=None):
        super().__init__(parent)
        if student_listings is None:
            self.student_listings = students.StudentListings()
            inserted_group = students.StudentGroup(0, "INSERTED")
            self.student_listings.create_listing(inserted_group)
        else:
            self.student_listings = student_listings
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        self.tabs = QTabWidget(self)
        # Special tab for creating a new group:
        self.tabs.addTab(QWidget(), "  +  ")
        # Group 0 is special: don't show it
        for listing in self.student_listings[1:]:
            self._add_group_tab(listing)
        # At least one normal group needs to be present:
        if len(self.student_listings) == 1:
            self._create_default_group()
        button_load = QPushButton(_("Add students from file"), parent=self)
        button_new_student = QPushButton(
            QIcon(utils.resource_path("new_id.svg")), _("New student"), parent=self
        )
        button_remove = QPushButton(
            QIcon(utils.resource_path("discard.svg")), _("Remove group"), parent=self
        )
        layout.addWidget(self.tabs)
        layout.addWidget(button_load)
        layout.addWidget(button_new_student)
        layout.addWidget(button_remove)
        layout.setAlignment(button_load, Qt.AlignHCenter)
        layout.setAlignment(button_new_student, Qt.AlignHCenter)
        layout.setAlignment(button_remove, Qt.AlignHCenter)
        self.tabs.setCurrentIndex(0)
        self._active_tab = 0
        self.tabs.currentChanged.connect(self._tab_changed)
        self.tabs.tabBarDoubleClicked.connect(self._rename_group)
        button_load.clicked.connect(self._load_students)
        button_new_student.clicked.connect(self._new_student)
        button_remove.clicked.connect(self._remove_group)

    def _load_students(self):
        index = self.tabs.currentIndex()
        file_name, __ = QFileDialog.getOpenFileName(
            self,
            _("Select the student list file"),
            "",
            FileNameFilters.student_list,
            None,
            QFileDialog.DontUseNativeDialog,
        )
        try:
            if file_name:
                with students.StudentReader.create(file_name) as reader:
                    student_list = list(reader.students())
                # Flag duplicate student ids:
                warn_duplicates = False
                for s in self.student_listings.find_duplicates(student_list):
                    s.is_duplicate = True
                    warn_duplicates = True
                if warn_duplicates:
                    QMessageBox.warning(
                        self,
                        _("Importing a student list"),
                        _(
                            "Some student ids are already in the list. "
                            "Remove them or cancel the import operation."
                        ),
                    )
                column_map = reader.column_map.normalize()
                preview_dialog = DialogPreviewStudents(self, student_list, column_map)
                result = preview_dialog.exec_()
                if result == QMessageBox.Accepted:
                    self.tabs.widget(index).add_students(student_list)
        except Exception as e:
            QMessageBox.critical(
                self, _("Error in student list"), file_name + "\n\n" + str(e)
            )

    def _new_student(self):
        index = self.tabs.currentIndex()
        dialog = NewStudentDialog(self.student_listings, group_index=index, parent=self)
        student = dialog.exec_()
        if student is not None:
            self.tabs.widget(index).listing_updated()

    def _remove_group(self):
        index = self.tabs.currentIndex()
        if len(self.student_listings[index + 1]) > 0:
            result = QMessageBox.warning(
                self,
                _("Warning"),
                _(
                    "This group and its students will be removed. "
                    "Are you sure you want to continue?"
                ),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            remove = result == QMessageBox.Yes
        else:
            remove = True
        if remove:
            try:
                self.student_listings.remove_at(index + 1)
                if len(self.student_listings) > 1:
                    if index == self.tabs.count() - 2:
                        self.tabs.setCurrentIndex(index - 1)
                    else:
                        self.tabs.setCurrentIndex(index + 1)
                else:
                    self._create_default_group()
                    self.tabs.setCurrentIndex(1)
                self.tabs.removeTab(index)
            except students.CantRemoveGroupException:
                QMessageBox.critical(
                    self,
                    _("Error"),
                    _(
                        "This group cannot be removed because "
                        "exams have been graded for some of its students."
                    ),
                )

    def _add_group_tab(self, listing, show=False):
        self.tabs.insertTab(
            self.tabs.count() - 1, GroupWidget(listing, self), listing.group.name
        )
        if show:
            self.tabs.setCurrentIndex(self.tabs.count() - 2)

    def _new_group(self):
        group_name = GroupNameDialog(parent=self).exec_()
        if group_name is not None:
            group = students.StudentGroup(None, group_name)
            listing = self.student_listings.create_listing(group)
            self._add_group_tab(listing, show=True)
        else:
            self.tabs.setCurrentIndex(self._active_tab)

    def _create_default_group(self):
        group = students.StudentGroup(None, _("Students"))
        listing = self.student_listings.create_listing(group)
        self._add_group_tab(listing, show=True)

    def _rename_group(self, index):
        name = self.student_listings[index + 1].group.name
        new_name = GroupNameDialog(group_name=name, parent=self).exec_()
        if new_name is not None and new_name != name:
            self.student_listings[index + 1].rename(new_name)
            self.tabs.setTabText(index, new_name)

    def _tab_changed(self, index):
        if index == self.tabs.count() - 1:
            # The last (special) tab has been activated: create a new group
            self._new_group()
        self._active_tab = self.tabs.currentIndex()


class GroupWidget(QWidget):

    _COLUMN_MAP = students.StudentColumnMap(
        columns=[
            students.StudentColumn.SEQUENCE_NUM,
            students.StudentColumn.ID,
            students.StudentColumn.NAME,
        ]
    )

    def __init__(self, listing, student_tabs):
        super().__init__(student_tabs.tabs)
        self.listing = listing
        layout = QVBoxLayout()
        self.setLayout(layout)
        self.table = QTableView()
        self.table.setMinimumWidth(500)
        self.table.setMinimumHeight(300)
        layout.addWidget(self.table)
        self.model = StudentsTableModel(listing, GroupWidget._COLUMN_MAP, self)
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        layout.setAlignment(self.table, Qt.AlignHCenter)
        self._resize_table()

    def add_students(self, student_list):
        self.listing.add_students(student_list)
        self.listing_updated()

    def listing_updated(self):
        self.model.data_reset()
        self._resize_table()

    def _resize_table(self):
        self.table.resizeColumnToContents(0)
        self.table.horizontalHeader().setStretchLastSection(True)


class PreviewWidget(QWidget):
    def __init__(self, student_list, column_map, parent=None):
        super().__init__(parent)
        self.listing = students.GroupListing(None, student_list)
        self.column_map = column_map
        layout = QVBoxLayout()
        self.setLayout(layout)
        self.table = QTableView()
        self.table.setMinimumWidth(600)
        self.table.setMinimumHeight(300)
        layout.addWidget(self.table)
        self.model = StudentsTableModel(self.listing, column_map, self)
        self.table.setModel(self.model)
        self.table.setSelectionMode(QTableView.NoSelection)
        layout.setAlignment(self.table, Qt.AlignHCenter)
        self._resize_table()

    def swap_names(self):
        for s in self.listing.students:
            s.first_name, s.last_name = s.last_name, s.first_name
        self.model.data_reset()
        self._resize_table()

    def to_full_name(self, column):
        attr_name = students.ATTR_NAME[column]
        for s in self.listing.students:
            s.full_name = getattr(s, attr_name)
            s.first_name = ""
            s.last_name = ""
        self.column_map = self.column_map.to_full_name()
        self.model.data_reset(column_map=self.column_map)
        self._resize_table()

    def remove_duplicates(self):
        self.listing.remove_students(
            [s for s in self.listing.students if s.is_duplicate]
        )
        self.model.data_reset()

    def _resize_table(self):
        for i in range(len(self.column_map) - 1):
            self.table.resizeColumnToContents(i)
        self.table.horizontalHeader().setStretchLastSection(True)


class StudentsTableModel(QAbstractTableModel):
    """ Table for showing a student list."""

    _headers = {
        students.StudentColumn.SEQUENCE_NUM: "#",
        students.StudentColumn.ID: _("Id"),
        students.StudentColumn.NAME: _("Name"),
        students.StudentColumn.FIRST_NAME: _("First name"),
        students.StudentColumn.LAST_NAME: _("Last name"),
        students.StudentColumn.FULL_NAME: _("Name"),
        students.StudentColumn.EMAIL: _("Email"),
    }

    _alignment = {
        students.StudentColumn.SEQUENCE_NUM: Qt.AlignRight,
        students.StudentColumn.ID: Qt.AlignRight,
        students.StudentColumn.NAME: Qt.AlignLeft,
        students.StudentColumn.FIRST_NAME: Qt.AlignLeft,
        students.StudentColumn.LAST_NAME: Qt.AlignLeft,
        students.StudentColumn.FULL_NAME: Qt.AlignLeft,
        students.StudentColumn.EMAIL: Qt.AlignLeft,
    }

    def __init__(self, listing, column_map, parent=None):
        super().__init__(parent=None)
        self.column_map = column_map
        self.data_reset(listing=listing)

    def data_reset(self, listing=None, column_map=None):
        self.beginResetModel()
        if listing is not None:
            self.listing = listing
        if column_map is not None:
            self.column_map = column_map
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return len(self.listing)

    def columnCount(self, parent=QModelIndex()):
        # Columns: sequence num, id, full name
        return len(self.column_map)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return StudentsTableModel._headers[self.column_map[section]]
            else:
                return QVariant()
        else:
            return QVariant(QVariant.Invalid)

    def data(self, index, role=Qt.DisplayRole):
        column = index.column()
        student = self.listing[index.row()]
        if role == Qt.DisplayRole:
            return self.column_map.data(column, student)
        elif role == Qt.TextAlignmentRole:
            return StudentsTableModel._alignment[self.column_map[column]]
        elif role == Qt.BackgroundRole:
            if student.is_duplicate:
                return QBrush(QColor(255, 165, 165))
            else:
                return QVariant(QVariant.Invalid)
        else:
            return QVariant(QVariant.Invalid)

    def flags(self, index):
        return Qt.ItemFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
