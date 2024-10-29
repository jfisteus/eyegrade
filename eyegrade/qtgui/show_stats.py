# Eyegrade: grading multiple choice questions with a webcam
# Copyright (C) 2010-2024 Jesus Arias Fisteus
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

import gettext
from typing import Union

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QDialogButtonBox,
    QTabWidget,
    QTableView,
)

from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt, QVariant

from . import widgets
from ..stats import stats_core
from .. import utils


t = gettext.translation("eyegrade", utils.locale_dir(), fallback=True)
_ = t.gettext


class DialogShowStats(QDialog):
    """Dialog to show question by question statistics.

    Example (replace `parent` by the parent widget):

    dialog = DialogShowStats(parent)
    dialog.exec()

    """

    exam_stats: stats_core.ExamStats

    def __init__(self, parent, exam_stats: stats_core.ExamStats) -> None:
        super().__init__(parent)
        self.exam_stats = exam_stats
        self.setWindowTitle(_("Exam statistics"))
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)
        tabs = QTabWidget(parent)
        for model in self.exam_stats.models:
            table = self._create_table(model)
            tabs.addTab(table, _("Model: ") + model)
        layout.addWidget(tabs)
        layout.addWidget(buttons)

    def _create_table(self, model: str) -> QTableView:
        table = widgets.CustomTableView(self)
        table.setModel(ExamStatsTableModel(self.exam_stats, model))
        table.adjust_size()
        return table


class ExamStatsTableModel(QAbstractTableModel):
    exam_stats: stats_core.ExamStats
    answer_counts: list[list[int]]

    def __init__(
        self, exam_stats: stats_core.ExamStats, model: str, parent=None
    ) -> None:
        super().__init__(parent=parent)
        self.exam_stats = exam_stats
        self.answer_counts = self.exam_stats.get_answer_counts(model)

    def rowCount(self, parent=QModelIndex()) -> int:
        return self.exam_stats.num_questions

    def columnCount(self, parent=QModelIndex()) -> int:
        return self.exam_stats.num_choices + 1

    def headerData(
        self,
        index: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Union[str, QVariant]:
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                if index < self.exam_stats.num_choices:
                    return chr(65 + index)
                else:
                    return _("Blank")
            else:
                return "{0} {1}".format(_("Question"), index + 1)
        else:
            return QVariant()

    def data(
        self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole
    ) -> Union[str, Qt.AlignmentFlag, QVariant]:
        if role == Qt.ItemDataRole.DisplayRole:
            r = index.row()
            c = index.column()
            if c < self.exam_stats.num_choices:
                return str(self.answer_counts[r][c + 1])
            else:
                return str(self.answer_counts[r][0])
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignRight
        else:
            return QVariant()

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        return Qt.ItemFlag(Qt.ItemFlag.ItemIsEnabled)
