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
)

from PyQt5.QtCore import (
    Qt,
    QAbstractTableModel,
    QModelIndex,
    QVariant,
)

from . import FileNameFilters
from .. import utils
from .. import students


t = gettext.translation('eyegrade', utils.locale_dir(), fallback=True)
_ = t.gettext


class DialogStudents(QDialog):
    """Dialog to list students."""

    def __init__(self, parent, group_listings):
        super().__init__(parent)
        self.group_listings = group_listings
        main_layout = QVBoxLayout(self)
        self.setLayout(main_layout)
        self.tabs = QTabWidget(self)
        main_layout.addWidget(self.tabs)
        for listing in group_listings:
            self._add_group_tab(listing)
        button_new_group = QPushButton(_('New student group'))
        button_new_group.clicked.connect(self._new_group)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.addButton(button_new_group, QDialogButtonBox.ActionRole)
        buttons.accepted.connect(self.accept)
        main_layout.addWidget(buttons)

    def exec_(self):
        """Shows the dialog and waits until it is closed."""
        result = super().exec_()
        if result == QDialog.Accepted:
            return True
        else:
            return False

    def _add_group_tab(self, listing, show=False):
        self.tabs.addTab(
            GroupWidget(listing, parent=self.tabs), listing.group.name)
        if show:
            self.tabs.setCurrentIndex(self.tabs.count() - 1)

    def _new_group(self):
        group = students.StudentGroup(None, _('New group'))
        listing = self.group_listings.create_listing(group)
        self._add_group_tab(listing, show=True)


class GroupWidget(QWidget):
    def __init__(self, listing, parent=None):
        super().__init__(parent)
        self.listing = listing
        layout = QVBoxLayout()
        self.setLayout(layout)
        self.table = QTableView()
        self.table.setMinimumWidth(500)
        self.table.setMinimumHeight(400)
        layout.addWidget(self.table)
        self.model = StudentsTableModel(listing, self)
        self.table.setModel(self.model)
        button_load = QPushButton(_('Add students from file'))
        layout.addWidget(button_load)
        layout.setAlignment(self.table, Qt.AlignHCenter)
        layout.setAlignment(button_load, Qt.AlignHCenter)
        button_load.clicked.connect(self._load_students)
        self._resize_table()

    def _resize_table(self):
        self.table.resizeColumnToContents(0)
        self.table.horizontalHeader().setStretchLastSection(True)

    def _load_students(self):
        file_name, __ = QFileDialog.getOpenFileName(
            self,
            _('Select the student list file'),
            '',
            FileNameFilters.student_list,
            None,
            QFileDialog.DontUseNativeDialog)
        try:
            student_list = students.read_students(file_name)
            self.listing.add_students(student_list)
            self.model.data_reset()
            self._resize_table()
        except Exception as e:
            QMessageBox.critical(
                self,
                _('Error in student list'),
                file_name + '\n\n' + str(e))


class StudentsTableModel(QAbstractTableModel):
    """ Table for showing a student list."""

    _headers = (
        _('Id'),
        _('Name'),
    )

    _column_alignment = (
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
        # Columns: id, full name
        return 2

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
            if column == 0:
                return student.student_id
            else:
                return student.name
        elif role == Qt.TextAlignmentRole:
            return StudentsTableModel._column_alignment[column]
        else:
            return QVariant(QVariant.Invalid)

    def flags(self, index):
        return Qt.ItemFlags(Qt.ItemIsEnabled)
