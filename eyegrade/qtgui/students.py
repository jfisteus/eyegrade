# Eyegrade: grading multiple choice questions with a webcam
# Copyright (C) 2010-2019 Jesus Arias Fisteus
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

from PyQt5.QtGui import (
    QRegExpValidator,
    QIcon,
)

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

from PyQt5.QtCore import (
    Qt,
    QAbstractTableModel,
    QModelIndex,
    QVariant,
    QRegExp,
)

from . import FileNameFilters
from . import widgets
from .. import utils
from .. import students


t = gettext.translation('eyegrade', utils.locale_dir(), fallback=True)
_ = t.gettext


class DialogStudentId(QDialog):
    """Dialog to change the student id.

    Example (replace `parent` by the parent widget):

    dialog = DialogStudentId(parent)
    id = dialog.exec_()

    """
    def __init__(self, parent, student_list):
        super().__init__(parent)
        self.setWindowTitle(_('Change the student id'))
        layout = QFormLayout()
        self.setLayout(layout)
        self.combo = widgets.StudentComboBox(parent=self)
        self.combo.add_students(student_list)
        self.combo.editTextChanged.connect(self._check_value)
        self.combo.currentIndexChanged.connect(self._check_value)
        new_student_button = QPushButton( \
                                 QIcon(utils.resource_path('new_id.svg')),
                                 _('New student'), parent=self)
        new_student_button.clicked.connect(self._new_student)
        self.buttons = QDialogButtonBox((QDialogButtonBox.Ok
                                         | QDialogButtonBox.Cancel))
        self.buttons.addButton(new_student_button, QDialogButtonBox.ActionRole)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addRow(_('Student id:'), self.combo)
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
        dialog = NewStudentDialog(parent=self)
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

    def __init__(self, parent=None):
        super(NewStudentDialog, self).__init__(parent)
        self.setMinimumWidth(300)
        self.setWindowTitle(_('Add a new student'))
        layout = QFormLayout()
        self.setLayout(layout)
        self.id_field = QLineEdit(self)
        self.id_field.setValidator(QRegExpValidator(QRegExp(r'\d+'), self))
        self.id_field.textEdited.connect(self._check_values)
        self.name_field = QLineEdit(self)
        self.surname_field = QLineEdit(self)
        self.full_name_field = QLineEdit(self)
        self.name_label = QLabel(_('Given name'))
        self.surname_label = QLabel(_('Surname'))
        self.full_name_label = QLabel(_('Full name'))
        self.email_field = QLineEdit(self)
        self.email_field.setValidator( \
                        QRegExpValidator(QRegExp(students.re_email), self))
        self.email_field.textEdited.connect(self._check_values)
        self.combo = QComboBox(parent=self)
        self.combo.addItem(_('Separate given name and surname'))
        self.combo.addItem(_('Full name in just one field'))
        self.combo.currentIndexChanged.connect(self._update_combo)
        layout.addRow(self.combo)
        layout.addRow(_('Id number'), self.id_field)
        layout.addRow(self.name_label, self.name_field)
        layout.addRow(self.surname_label, self.surname_field)
        layout.addRow(self.full_name_label, self.full_name_field)
        layout.addRow(_('Email'), self.email_field)
        self.buttons = QDialogButtonBox((QDialogButtonBox.Ok
                                         | QDialogButtonBox.Cancel))
        layout.addRow(self.buttons)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self._check_values()
        # Set the combo box
        if NewStudentDialog._last_combo_value is None:
            NewStudentDialog._last_combo_value = 0
        self.combo.setCurrentIndex(NewStudentDialog._last_combo_value)
        self._update_combo(NewStudentDialog._last_combo_value)

    def exec_(self):
        """Shows the dialog and waits until it is closed.

        Returns the text of the option selected by the user, or None if
        the dialog is cancelled.

        """
        result = super(NewStudentDialog, self).exec_()
        if result == QDialog.Accepted:
            NewStudentDialog._last_combo_value = self.combo.currentIndex()
            email = self.email_field.text()
            if not email:
                email = None
            if self.combo.currentIndex() == 0:
                # First name, last name
                student = students.Student( \
                                    self.id_field.text(),
                                    None,
                                    self.name_field.text(),
                                    self.surname_field.text(),
                                    email)
            else:
                # Full name
                student = students.Student( \
                                    self.id_field.text(),
                                    self.full_name_field.text(),
                                    None,
                                    None,
                                    email)
        else:
            student = None
        return student

    def _check_values(self):
        if (self.id_field.hasAcceptableInput()
            and (not self.email_field.text()
                 or self.email_field.hasAcceptableInput())):
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
            self.full_name_field.setText('')
        else:
            self.name_field.setEnabled(False)
            self.surname_field.setEnabled(False)
            self.full_name_field.setEnabled(True)
            self.name_label.setEnabled(False)
            self.surname_label.setEnabled(False)
            self.full_name_label.setEnabled(True)
            self.name_field.setText('')
            self.surname_field.setText('')


class DialogStudents(QDialog):
    """Dialog to list students."""

    def __init__(self, parent, student_listings):
        super().__init__(parent)
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


class GroupNameDialog(QDialog):
    def __init__(self, parent=None, group_name=''):
        super().__init__(parent)
        if not group_name:
            window_title = _('Create a new group of students')
            message = _('Please, enter the name of the new group of students '
                        'you want to create:')
        else:
            window_title = _('Rename the group of students')
            message = _('Please, enter the new name of the group of students')
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
            self,
            QLabel(_('Group name')),
            self._name_widget)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
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
            default_group = students.StudentGroup(0, _('Default group'))
            self.student_listings.create_listing(default_group)
        else:
            self.student_listings = student_listings
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        self.tabs = QTabWidget(self)
        # Special tab for creating a new group:
        self.tabs.addTab(QWidget(), '  +  ')
        for listing in self.student_listings:
            self._add_group_tab(listing)
        button_load = QPushButton(_('Add students from file'), parent=self)
        button_new_student = QPushButton(
            QIcon(utils.resource_path('new_id.svg')),
            _('New student'),
            parent=self)
        button_remove = QPushButton(
            QIcon(utils.resource_path('discard.svg')),
            _('Remove group'),
            parent=self)
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
        button_remove.setEnabled(False)
        self._button_remove = button_remove

    def _load_students(self):
        index = self.tabs.currentIndex()
        file_name, __ = QFileDialog.getOpenFileName(
            self,
            _('Select the student list file'),
            '',
            FileNameFilters.student_list,
            None,
            QFileDialog.DontUseNativeDialog)
        try:
            if file_name:
                student_list = students.read_students(file_name)
                self.tabs.widget(index).add_students(student_list)
        except Exception as e:
            QMessageBox.critical(
                self,
                _('Error in student list'),
                file_name + '\n\n' + str(e))

    def _new_student(self):
        index = self.tabs.currentIndex()
        dialog = NewStudentDialog(parent=self)
        student = dialog.exec_()
        if student is not None:
            self.tabs.widget(index).add_students([student])

    def _remove_group(self):
        index = self.tabs.currentIndex()
        if len(self.student_listings[index]) > 0:
            result = QMessageBox.warning(
                self,
                _('Warning'),
                _('This group and its students will be removed. '
                  'Are you sure you want to continue?'),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No)
            remove = (result == QMessageBox.Yes)
        else:
            remove = True
        if remove:
            try:
                self.student_listings.remove_at(index)
                if index == self.tabs.count() - 2:
                    self.tabs.setCurrentIndex(index - 1)
                else:
                    self.tabs.setCurrentIndex(index + 1)
                self.tabs.removeTab(index)
            except students.CantRemoveGroupException:
                QMessageBox.critical(
                    self,
                    _('Error'),
                    _('This group cannot be removed because '
                      'exams have been graded for some of its students.'))

    def _add_group_tab(self, listing, show=False):
        self.tabs.insertTab(
            self.tabs.count() - 1,
            GroupWidget(listing, self),
            listing.group.name
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

    def _rename_group(self, index):
        name = self.student_listings[index].group.name
        new_name = GroupNameDialog(group_name=name, parent=self).exec_()
        if new_name is not None and new_name != name:
            self.student_listings[index].rename(new_name)
            self.tabs.setTabText(index, new_name)

    def _tab_changed(self, index):
        if index == self.tabs.count() - 1:
            # The last (special) tab has been activated: create a new group
            self._new_group()
        self._active_tab = self.tabs.currentIndex()
        self._button_remove.setEnabled(self._active_tab != 0)


class GroupWidget(QWidget):
    def __init__(self, listing, student_tabs):
        super().__init__(student_tabs.tabs)
        self.listing = listing
        layout = QVBoxLayout()
        self.setLayout(layout)
        self.table = QTableView()
        self.table.setMinimumWidth(500)
        self.table.setMinimumHeight(400)
        layout.addWidget(self.table)
        self.model = StudentsTableModel(listing, self)
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        layout.setAlignment(self.table, Qt.AlignHCenter)
        self._resize_table()

    def add_students(self, student_list):
        self.listing.add_students(student_list)
        self.model.data_reset()
        self._resize_table()

    def _resize_table(self):
        self.table.resizeColumnToContents(0)
        self.table.horizontalHeader().setStretchLastSection(True)


class StudentsTableModel(QAbstractTableModel):
    """ Table for showing a student list."""

    _headers = (
        '#',
        _('Id'),
        _('Name'),
    )

    _extract = (
        lambda s: s.sequence_num,
        lambda s: s.student_id,
        lambda s: s.name,
    )

    _column_alignment = (
        Qt.AlignRight,
        Qt.AlignRight,
        Qt.AlignLeft,
    )

    def __init__(self, listing, parent=None):
        super().__init__(parent=None)
        self.data_reset(listing=listing)

    def data_reset(self, listing=None):
        self.beginResetModel()
        if listing is not None:
            self.listing = listing
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return len(self.listing)

    def columnCount(self, parent=QModelIndex()):
        # Columns: sequence num, id, full name
        return len(StudentsTableModel._headers)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return StudentsTableModel._headers[section]
            else:
                return QVariant()
        else:
            return QVariant(QVariant.Invalid)

    def data(self, index, role=Qt.DisplayRole):
        column = index.column()
        if role == Qt.DisplayRole:
            student = self.listing[index.row()]
            return StudentsTableModel._extract[column](student)
        elif role == Qt.TextAlignmentRole:
            return StudentsTableModel._column_alignment[column]
        else:
            return QVariant(QVariant.Invalid)

    def flags(self, index):
        return Qt.ItemFlags(Qt.ItemIsEnabled|Qt.ItemIsSelectable)
