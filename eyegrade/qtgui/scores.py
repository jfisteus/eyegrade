# Eyegrade: grading multiple choice questions with a webcam
# Copyright (C) 2010-2022 Jesus Arias Fisteus
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
import copy
from typing import Optional, Union, Dict, List, Tuple, cast

from PyQt6.QtWidgets import (
    QFormLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QDialog,
    QDialogButtonBox,
)

from PyQt6.QtCore import Qt, pyqtBoundSignal, QAbstractTableModel, QModelIndex, QVariant

from . import widgets
from . import dialogs
from .. import utils
from .. import scoring
from .. import exams

t = gettext.translation("eyegrade", utils.locale_dir(), fallback=True)
_ = t.gettext


class ScoreWeightsTableModel(QAbstractTableModel):
    """Table for editing score weight values."""

    changes: bool
    exam_config: exams.ExamConfig
    models: List[str]
    has_permutations: bool
    permutations: Dict[str, List[Tuple[int, List[int]]]]
    weights: List[List[int]]
    sum_weights: List[int]

    def __init__(self, exam_config: exams.ExamConfig, parent=None):
        super().__init__(parent=parent)
        self.exam_config = exam_config
        self.data_reset()
        self.changes = False
        cast(pyqtBoundSignal, self.dataChanged).connect(self._update_weights_sum)

    def data_reset(self) -> None:
        self.beginResetModel()
        self.models = sorted(self.exam_config.models)
        self.has_permutations = False
        if not self.models:
            self.models = ["A"]
        elif all(self.exam_config.get_permutations(m) for m in self.models):
            self.has_permutations = True
            self.models.insert(0, "0")
            self.permutations = self.exam_config.permutations
        if not self.has_permutations:
            self.weights = [
                self.exam_config.get_question_weights(m) for m in self.models
            ]
            for i in range(len(self.weights)):
                if not self.weights[i]:
                    self.weights[i] = [1] * self.exam_config.num_questions
        else:
            weights_0 = [1] * self.exam_config.num_questions
            weights_m = self.exam_config.get_question_weights(self.models[1])
            if weights_m:
                for i, value in enumerate(weights_m):
                    weights_0[self._to_model_0(1, i)] = value
            else:
                weights_0 = [1] * self.exam_config.num_questions
            self.weights = [weights_0]
        self.sum_weights = [sum(w) for w in self.weights]
        self.changes = False
        self.endResetModel()

    def clear(self) -> None:
        self.beginResetModel()
        for i in range(len(self.weights)):
            self.weights[i] = [1] * self.exam_config.num_questions
        self.sum_weights = [sum(w) for w in self.weights]
        self.changes = False
        self.endResetModel()

    def validate(self) -> bool:
        """Checks that the weights are valid.

        When there are no permutations, it checks that all the models
        have the same weight elements, regardless their order.

        """
        if self.has_permutations:
            # The weights are necessarily valid
            valid = True
        else:
            # All the weights must have the same elements
            reference = sorted(self.weights[0])
            for w in self.weights[1:]:
                if reference != sorted(w):
                    valid = False
                    break
            else:
                valid = True
        return valid

    def consolidate(self) -> bool:
        """Consolidate the weights into the exam_config object.

        Returns True if the values are correct and consolidated,
        and False if not.

        """
        if not self.validate():
            return False
        self.exam_config.reset_question_weights()
        if self.has_permutations:
            for i, model in enumerate(self.models[1:]):
                w = []
                model_idx = i + 1
                for q in range(self.exam_config.num_questions):
                    w.append(self.weights[0][self._to_model_0(model_idx, q)])
                self.exam_config.set_question_weights(model, w)
        else:
            # All the weights must have the same elements
            for model, w in zip(self.models, self.weights):
                self.exam_config.set_question_weights(model, w)
        return True

    def rowCount(self, parent=QModelIndex()) -> int:
        return self.exam_config.num_questions + 1

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self.models)

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Union[str, QVariant]:
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return "{0} {1}".format(_("Model"), self.models[section])
            else:
                if section < self.exam_config.num_questions:
                    return "{0} {1}".format(_("Question"), section + 1)
                else:
                    return _("Total")
        else:
            return QVariant()

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            r = index.row()
            c = index.column()
            if r < self.exam_config.num_questions:
                if not self.has_permutations or c == 0:
                    value = self.weights[c][r]
                else:
                    value = self.weights[0][self._to_model_0(c, r)]
                return scoring.format_number(value, short=True)
            else:
                if not self.has_permutations:
                    value = self.sum_weights[c]
                else:
                    value = self.sum_weights[0]
                return scoring.format_number(value, short=True, no_fraction=True)
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignCenter
        else:
            return QVariant()

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if index.row() < self.exam_config.num_questions:
            return Qt.ItemFlag(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsEditable)
        else:
            return Qt.ItemFlag(Qt.ItemFlag.ItemIsEnabled)

    def setData(
        self, index: QModelIndex, value_qvar: str, role: int = Qt.ItemDataRole.EditRole
    ) -> bool:
        success = False
        r = index.row()
        c = index.column()
        try:
            value = scoring.parse_number(value_qvar)
        except ValueError:
            return False
        if r < self.exam_config.num_questions:
            if not self.has_permutations or c == 0:
                old_value = self.weights[c][r]
                self.weights[c][r] = value
                r_0 = r
            else:
                r_0 = self._to_model_0(c, r)
                old_value = self.weights[0][r_0]
                self.weights[0][r_0] = value
            if old_value != value:
                self.changes = True
                # Emit the signal for all the affected cells
                data_changed_signal = cast(pyqtBoundSignal, self.dataChanged)
                if not self.has_permutations:
                    data_changed_signal.emit(index, index)
                else:
                    changed_idx = self.index(r_0, 0)
                    data_changed_signal.emit(changed_idx, changed_idx)
                    for model_idx in range(1, len(self.models)):
                        for i in range(self.exam_config.num_questions):
                            if self._to_model_0(model_idx, i) == r_0:
                                changed_idx = self.index(i, model_idx)
                                data_changed_signal.emit(changed_idx, changed_idx)
            success = True
        return success

    def _update_weights_sum(self, index_1: QModelIndex, index_2: QModelIndex) -> None:
        """Handler for the dataChanged signal."""
        if index_1.row() < self.exam_config.num_questions:
            col_1 = index_1.column()
            col_2 = index_2.column()
            if self.has_permutations:
                # Only changes to column 0 are relevant
                col_end = 0
            else:
                col_end = col_2
            for i in range(col_1, col_end + 1):
                self.sum_weights[i] = sum(self.weights[i])
            if col_1 <= col_end:
                if self.has_permutations:
                    # The change affects all the sums
                    col_2 = len(self.models) - 1
                changed_1 = self.index(self.exam_config.num_questions, col_1)
                changed_2 = self.index(self.exam_config.num_questions, col_2)
                data_changed_signal = cast(pyqtBoundSignal, self.dataChanged)
                data_changed_signal.emit(changed_1, changed_2)

    def _to_model_0(self, model_idx: int, question: int) -> int:
        question_0, opt = self.permutations[self.models[model_idx]][question]
        return question_0 - 1


class DialogEditScores(QDialog):
    """Dialog to edit exam scores"""

    exam_config: exams.ExamConfig
    scores_widget: "EditScoresWidget"

    def __init__(self, exam_config: exams.ExamConfig, parent=None):
        super().__init__(parent=parent)
        self.setWindowTitle(_("Edit question scores"))
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        self.scores_widget = EditScoresWidget(exam_config)
        layout.addWidget(self.scores_widget)
        buttons = QDialogButtonBox(
            (
                QDialogButtonBox.StandardButton.Ok
                | QDialogButtonBox.StandardButton.Cancel
            )
        )
        layout.addWidget(buttons)
        accepted_signal = cast(pyqtBoundSignal, buttons.accepted)
        rejected_signal = cast(pyqtBoundSignal, buttons.rejected)
        accepted_signal.connect(self.accept)
        rejected_signal.connect(self.reject)

    def exec(self) -> bool:
        """Shows the dialog and waits until it is closed.

        Returns true if the configuration has been modified,
        or false otherwise.

        """
        terminate = False
        changes = False
        while not terminate:
            result = super().exec()
            if result == QDialog.DialogCode.Accepted:
                old_scores_mode = self.scores_widget.exam_config.scores_mode
                old_base_scores = copy.deepcopy(
                    self.scores_widget.exam_config.base_scores
                )
                old_scores = copy.deepcopy(self.scores_widget.exam_config.scores)
                if self.scores_widget.validate_and_consolidate():
                    terminate = True
                    if (
                        old_scores_mode != self.scores_widget.exam_config.scores_mode
                        or old_base_scores != self.scores_widget.exam_config.base_scores
                        or old_scores != self.scores_widget.exam_config.scores
                    ):
                        changes = True
            else:
                terminate = True
        return changes


class EditScoresWidget(QWidget):
    """Widget for editing score mode, scores and score weights."""

    exam_config: exams.ExamConfig
    current_mode: Optional[int]

    def __init__(self, exam_config: exams.ExamConfig, parent=None):
        super().__init__(parent)
        self.exam_config = exam_config
        self.current_mode = None
        form_widget = QWidget(parent=self)
        table_widget = QWidget(parent=self)
        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout(form_widget)
        table_layout = QVBoxLayout(table_widget)
        main_layout.addWidget(form_widget)
        main_layout.addWidget(table_widget)
        main_layout.setAlignment(table_widget, Qt.AlignmentFlag.AlignHCenter)
        self.combo = widgets.CustomComboBox(parent=self)
        self.combo.set_items(
            [
                _("No scores"),
                _("Same score for all the questions"),
                _("Base score plus per-question weight"),
            ]
        )
        index_changed_signal = cast(pyqtBoundSignal, self.combo.currentIndexChanged)
        index_changed_signal.connect(self._update_combo)
        self.correct_score = widgets.InputScore(is_positive=True)
        correct_score_label = QLabel(_("Score for correct answers"))
        incorrect_score_label = QLabel(_("Score for incorrect answers"))
        blank_score_label = QLabel(_("Score for blank answers"))
        self.incorrect_score = widgets.InputScore(is_positive=False)
        self.blank_score = widgets.InputScore(is_positive=False)
        self.button_reset = QPushButton(_("Reset question weights"))
        button_defaults = QPushButton(_("Compute default scores"))
        self.weights_table = widgets.CustomTableView()
        weights_table_label = QLabel(_("Per-question score weights:"))
        form_layout.addRow(self.combo)
        form_layout.addRow(correct_score_label, self.correct_score)
        form_layout.addRow(incorrect_score_label, self.incorrect_score)
        form_layout.addRow(blank_score_label, self.blank_score)
        table_layout.addWidget(weights_table_label)
        table_layout.addWidget(self.weights_table)
        table_layout.addWidget(self.button_reset)
        table_layout.addWidget(button_defaults)
        table_layout.setAlignment(weights_table_label, Qt.AlignmentFlag.AlignHCenter)
        table_layout.setAlignment(self.weights_table, Qt.AlignmentFlag.AlignHCenter)
        table_layout.setAlignment(self.button_reset, Qt.AlignmentFlag.AlignHCenter)
        table_layout.setAlignment(button_defaults, Qt.AlignmentFlag.AlignHCenter)
        button_reset_clicked_signal = cast(pyqtBoundSignal, self.button_reset.clicked)
        button_reset_clicked_signal.connect(self._reset_weights)
        button_defaults_clicked_signal = cast(pyqtBoundSignal, button_defaults.clicked)
        button_defaults_clicked_signal.connect(self._compute_default_values)
        self.base_score_widgets = [
            self.correct_score,
            correct_score_label,
            self.incorrect_score,
            incorrect_score_label,
            self.blank_score,
            blank_score_label,
            button_defaults,
        ]
        self.weights_widgets = [self.weights_table, weights_table_label]
        self.initialize()

    def initialize(self) -> None:
        model = ScoreWeightsTableModel(self.exam_config, parent=self)
        self.weights_table.setModel(model)
        data_changed_signal = cast(pyqtBoundSignal, model.dataChanged)
        data_changed_signal.connect(self._weights_changed)
        self.weights_table.adjust_size()
        scores = self.exam_config.base_scores
        if scores is not None:
            self._set_score_fields(scores)
        # If the exam is a survey, disable all the controls
        if self.exam_config.survey_mode:
            self.combo.set_item_enabled(1, False)
            self.combo.set_item_enabled(2, False)
            initial_mode = 0
            model.clear()
        else:
            if not self.exam_config.scores or self.exam_config.all_weights_are_one():
                self.combo.set_item_enabled(1, True)
                self.combo.set_item_enabled(2, True)
                initial_mode = 1
                model.clear()
            else:
                self.combo.set_item_enabled(1, True)
                self.combo.set_item_enabled(2, True)
                initial_mode = 2
        self.combo.setCurrentIndex(initial_mode)

    def validate_and_consolidate(self) -> bool:
        """Call it to check the values of this page.

        Checks the values and consolidates them into the exam_config object if valid.

        """
        if self.current_mode == 0:
            valid = self._consolidate_no_scores()
        elif self._consolidate_base_scores():
            if self.current_mode == 1:
                valid = True
            else:
                valid = self._consolidate_weights()
        else:
            valid = False
        return valid

    def clear_base_scores(self) -> None:
        self.correct_score.setText("")
        self.incorrect_score.setText("")
        self.blank_score.setText("")

    def _reset_weights(self) -> None:
        model = cast(ScoreWeightsTableModel, self.weights_table.model())
        if model.changes and self._show_warning_weights_reset():
            model.data_reset()

    def _weights_changed(self, index_1, index_2) -> None:
        model = cast(ScoreWeightsTableModel, self.weights_table.model())
        self.button_reset.setEnabled(model.changes)

    def _compute_default_values(self) -> None:
        model = cast(ScoreWeightsTableModel, self.weights_table.model())
        if self.current_mode == 2 and not model.validate():
            self._show_error_weights()
            return
        dialog = dialogs.DialogComputeScores(parent=self)
        score, penalize = dialog.exec()
        if score is None:
            return
        choices = self.exam_config.get_num_choices()
        if self.current_mode == 1:
            # All the questions have the same score
            total_weight = self.exam_config.num_questions
        elif self.current_mode == 2:
            # Weighted questions
            total_weight = model.sum_weights[0]
        else:
            raise NotImplementedError("Bad mode in scores wizard page")
        if self.exam_config.num_questions and choices and choices > 1:
            c_score = score / total_weight
            if penalize:
                i_score = score / (choices - 1) / total_weight
            else:
                i_score = 0
            b_score = 0
            scores = scoring.QuestionScores(c_score, i_score, b_score)
            self._set_score_fields(scores)
        else:
            QMessageBox.critical(
                self,
                _("Error"),
                _("Automatic scores cannot be computed for this exam."),
            )

    def _show_warning_weights_reset(self) -> bool:
        result = QMessageBox.warning(
            self,
            _("Warning"),
            _(
                "The changes you have done to the weights "
                "table will be lost. "
                "Are you sure you want to continue?"
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return result == QMessageBox.StandardButton.Yes

    def _show_error_weights(self) -> None:
        QMessageBox.critical(
            self,
            _("Error"),
            _(
                "The weights must be the same "
                "in all the models, although they may "
                "be in a different order. "
                "You must fix this before computing "
                "default scores."
            ),
        )

    def _set_score_fields(self, scores: scoring.QuestionScores) -> None:
        self.correct_score.setText(scores.format_correct_score(signed=False))
        self.incorrect_score.setText(scores.format_incorrect_score(signed=True))
        self.blank_score.setText(scores.format_blank_score(signed=True))

    def _update_combo(self, new_index: int) -> None:
        if new_index != self.current_mode:
            # Ask the user if changes to weights may be lost
            model = cast(ScoreWeightsTableModel, self.weights_table.model())
            if (
                self.current_mode == 2
                and model.changes
                and not self._show_warning_weights_reset()
            ):
                self.combo.setCurrentIndex(self.current_mode)
                return
            self.button_reset.setEnabled(False)
            if new_index == 0:
                self._enable_weights_widgets(False, False)
            elif new_index == 1:
                self._enable_weights_widgets(True, False)
            else:
                self._enable_weights_widgets(True, True)
            # Reset the weights table
            if self.current_mode == 2:
                model.clear()
            elif new_index == 2:
                model.data_reset()
            # Reset the scores
            if new_index == 0:
                self.clear_base_scores()
            self.current_mode = new_index

    def _enable_weights_widgets(
        self, enable_base_scores: bool, enable_weights: bool
    ) -> None:
        for widget in self.base_score_widgets:
            widget.setEnabled(enable_base_scores)
        for widget in self.weights_widgets:
            widget.setEnabled(enable_weights)

    def _consolidate_no_scores(self) -> bool:
        self.exam_config.enter_score_mode_none()
        return True

    def _consolidate_base_scores(self) -> bool:
        valid = False
        c_score = self.correct_score.value()
        i_score = self.incorrect_score.value()
        b_score = self.blank_score.value()
        if c_score is not None and c_score > 0:
            if i_score is None:
                i_score = 0
            else:
                i_score = -i_score
            if b_score is None:
                b_score = 0
            else:
                b_score = -b_score
            if i_score >= 0 and b_score >= 0:
                base_scores = scoring.QuestionScores(c_score, i_score, b_score)
                same_weights = self.current_mode == 1
                self.exam_config.set_base_scores(base_scores, same_weights=same_weights)
                valid = True
            else:
                QMessageBox.critical(
                    self,
                    _("Error"),
                    _(
                        "The score for incorrect and blank answers "
                        "cannot be greater than 0."
                    ),
                )
        else:
            QMessageBox.critical(
                self, _("Error"), _("You must enter the score for correct answers.")
            )
        return valid

    def _consolidate_weights(self) -> bool:
        model = cast(ScoreWeightsTableModel, self.weights_table.model())
        valid = model.consolidate()
        if not valid:
            self._show_error_weights()
        return valid
