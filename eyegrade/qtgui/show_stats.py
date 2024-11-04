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
    QSizePolicy,
    QWidget,
)

from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt, QVariant

from PyQt6.QtGui import QBrush, QColor

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

    def __init__(self, parent, q_by_q_stats: stats_core.QByQStats) -> None:
        super().__init__(parent)
        self.setWindowTitle(_("Exam statistics"))
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)
        tabs = QTabWidget(self)
        q_by_q_stats_widget = QByQStatsWidget(self, q_by_q_stats)
        tabs.addTab(q_by_q_stats_widget, _("Question by question"))
        layout.addWidget(tabs)
        layout.addWidget(buttons)
        self.adjustSize()
        self.setModal(True)


class QByQStatsWidget(QTabWidget):

    q_by_q_stats: stats_core.QByQStats

    def __init__(self, parent, q_by_q_stats: stats_core.QByQStats) -> None:
        super().__init__(parent)
        self.q_by_q_stats = q_by_q_stats
        self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        for model in self.q_by_q_stats.all_models:
            widget = QWidget(self)
            tab_layout = QVBoxLayout(widget)
            widget.setLayout(tab_layout)
            table = self._create_table(model, widget)
            tab_layout.addWidget(table, Qt.AlignmentFlag.AlignCenter)
            tab_layout.setAlignment(table, Qt.AlignmentFlag.AlignHCenter)
            self.addTab(widget, _("Model ") + model)

    def _create_table(self, model: str, parent) -> QTableView:
        table = widgets.CustomTableView(
            parent=parent, maximum_width=750, maximum_height=500
        )
        table.setModel(QByQStatsTableModel(self.q_by_q_stats, model))
        table.adjust_size()
        return table


class QByQStatsTableModel(QAbstractTableModel):
    q_by_q_stats: stats_core.QByQStats
    answer_counts: list[list[int]]
    answer_percentages: list[list[float]]
    model: str

    def __init__(
        self, q_by_q_stats: stats_core.QByQStats, model: str, parent=None
    ) -> None:
        super().__init__(parent=parent)
        self.q_by_q_stats = q_by_q_stats
        self.answer_counts = self.q_by_q_stats.get_answer_counts(model)
        self.answer_percentages = self.q_by_q_stats.get_answer_percentages(model)
        self.model = model

    def rowCount(self, parent=QModelIndex()) -> int:
        return self.q_by_q_stats.num_questions

    def columnCount(self, parent=QModelIndex()) -> int:
        return self.q_by_q_stats.num_choices + 1

    def headerData(
        self,
        index: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Union[str, QVariant]:
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                if index < self.q_by_q_stats.num_choices:
                    return "{} {}".format(_("Answer"), chr(65 + index))
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
            if c < self.q_by_q_stats.num_choices:
                return str(self.answer_counts[r][c + 1])
            else:
                return str(self.answer_counts[r][0])
        elif role == Qt.ItemDataRole.ToolTipRole:
            r = index.row()
            c = index.column()
            if c < self.q_by_q_stats.num_choices:
                return f"{self.answer_percentages[r][c + 1]:.1f}%"
            else:
                return f"{self.answer_percentages[r][0]:.1f}%"
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignRight
        elif role == Qt.ItemDataRole.BackgroundRole:
            r = index.row()
            c = index.column()
            if c < self.q_by_q_stats.num_choices and self.q_by_q_stats.is_correct(
                c + 1, r + 1, self.model
            ):
                return QVariant(QBrush(QColor(205, 255, 212)))
            else:
                return QVariant()
        else:
            return QVariant()

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        return Qt.ItemFlag(Qt.ItemFlag.ItemIsEnabled)
