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
)

from PyQt5.QtCore import (
    Qt,
    QAbstractTableModel,
    QModelIndex,
    QVariant,
)

from .. import utils


t = gettext.translation('eyegrade', utils.locale_dir(), fallback=True)
_ = t.gettext


class DialogStudents(QDialog):
    """Dialog to list students."""

    def __init__(self, parent, group_listings):
        super().__init__(parent)
        self.group_listings = group_listings
        main_layout = QVBoxLayout(self)
        self.setLayout(main_layout)
        tabs = QTabWidget(self)
        main_layout.addWidget(tabs)
        for listing in group_listings:
            tabs.addTab(GroupWidget(listing, parent=tabs), listing.group.name)
        buttons = QDialogButtonBox((QDialogButtonBox.Ok
                                    | QDialogButtonBox.Cancel))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        main_layout.addWidget(buttons)

    def exec_(self):
        """Shows the dialog and waits until it is closed."""
        result = super().exec_()
        if result == QDialog.Accepted:
            return True
        else:
            return False


class GroupWidget(QWidget):
    def __init__(self, listing, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout()
        self.setLayout(layout)
        table = QTableView()
        table.setMinimumWidth(500)
        table.setMinimumHeight(400)
        layout.addWidget(table)
        layout.setAlignment(table, Qt.AlignHCenter)
        model = StudentsTableModel(listing, self)
        table.setModel(model)
        table.resizeColumnToContents(0)
        table.horizontalHeader().setStretchLastSection(True)


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
        self.data_reset(listing)

    def data_reset(self, listing):
        self.beginResetModel()
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
