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

import gettext
import os.path

from PyQt4.QtGui import (QPushButton, QMessageBox, QVBoxLayout,
                         QWizard, QWizardPage, QFormLayout,
                         QLabel, QWidget, )
from PyQt4.QtCore import Qt

from .. import utils
from . import widgets
from . import dialogs
from . import FileNameFilters

t = gettext.translation('eyegrade', utils.locale_dir(), fallback=True)
_ = t.ugettext


class NewSessionPageInitial(QWizardPage):
    """First page of WizardNewSession.

    It asks for the directory in which the session has to be stored and
    the exam config file.

    """
    def __init__(self, config_filename=None):
        super(NewSessionPageInitial, self).__init__()
        self.setTitle(_('Directory and exam configuration'))
        self.setSubTitle(_('Select or create an empty directory in which you '
                           'want to store the session, '
                           'and the exam configuration file.'))
        self.directory = widgets.OpenFileWidget(self, select_directory=True,
                            title=_('Select or create an empty directory'),
                            check_file_function=self._check_directory)
        self.config_file = widgets.OpenFileWidget(self,
                            title=_('Select the exam configuration file'),
                            name_filter=FileNameFilters.exam_config,
                            check_file_function=self._check_exam_config_file)
        if config_filename is not None:
            self.config_file.set_text(config_filename)
        self.registerField('directory*', self.directory.filename_widget)
        if config_filename is None:
            self.registerField('config_file*', self.config_file.filename_widget)
        else:
            # If '*' is used, the next button is not enabled.
            self.registerField('config_file', self.config_file.filename_widget)
        layout = QFormLayout(self)
        self.setLayout(layout)
        layout.addRow(_('Directory'), self.directory)
        layout.addRow(_('Exam configuration file'), self.config_file)

    def validatePage(self):
        """Called by QWizardPage to check the values of this page."""
        if not self.directory.is_validated():
            ok_dir = self.directory.check_value()
        else:
            ok_dir = True
        if not self.config_file.is_validated():
            ok_config = self.config_file.check_value()
        else:
            ok_config = True
        if ok_dir and ok_config:
            self.wizard().exam_config = \
                           utils.ExamConfig(filename=self.config_file.text())
        return ok_dir and ok_config

    def _check_directory(self, dir_name):
        valid = True
        msg = ''
        if not os.path.isdir(dir_name):
            valid = False
            msg = _('The directory does not exist or is not a directory.')
        else:
            dir_content = os.listdir(dir_name)
            if dir_content:
                valid = False
                msg = _('The directory is not empty. '
                        'Choose another directory or create a new one.')
        return valid, msg

    def _check_exam_config_file(self, file_name):
        valid = True
        msg = ''
        if not os.path.exists(file_name):
            valid = False
            msg = _('The exam configuration file does not exist.')
        elif not os.path.isfile(file_name):
            valid = False
            msg = _('The exam configuration file is not a regular file.')
        else:
            try:
                utils.ExamConfig(filename=file_name)
            except IOError:
                valid = False
                msg = _('The exam configuration file cannot be read.')
            except Exception as e:
                valid = False
                msg = _('The exam configuration file contains errors')
                if str(e):
                    msg += ':<br><br>' + str(e)
                else:
                    msg += '.'
        self.wizard().exam_config_reset()
        return valid, msg


class NewSessionPageScores(QWizardPage):
    """Page of WizardNewSession that asks for the scores for answers."""
    def __init__(self):
        super(NewSessionPageScores, self).__init__()
        self.setTitle(_('Scores for correct and incorrect answers'))
        self.setSubTitle(_('Enter the scores of correct and incorrect '
                           'answers. The program will compute scores based '
                           'on them. Setting these scores is optional.'))
        form_widget = QWidget(parent=self)
        table_widget = QWidget(parent=self)
        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout(form_widget)
        table_layout = QVBoxLayout(table_widget)
        self.setLayout(main_layout)
        form_widget.setLayout(form_layout)
        table_widget.setLayout(table_layout)
        main_layout.addWidget(form_widget)
        main_layout.addWidget(table_widget)
        main_layout.setAlignment(table_widget, Qt.AlignHCenter)
        self.combo = widgets.CustomComboBox(parent=self)
        self.combo.set_items([
            _('No scores'),
            _('Same score for all the questions'),
            _('Base score plus per-question weight'),
        ])
        self.combo.currentIndexChanged.connect(self._update_combo)
        self.correct_score = widgets.InputScore(is_positive=True)
        correct_score_label = QLabel(_('Score for correct answers'))
        incorrect_score_label = QLabel(_('Score for incorrect answers'))
        blank_score_label = QLabel(_('Score for blank answers'))
        self.incorrect_score = widgets.InputScore(is_positive=False)
        self.blank_score = widgets.InputScore(is_positive=False)
        self.button_reset = QPushButton(_('Reset question weights'))
        button_defaults = QPushButton(_('Compute default scores'))
        self.weights_table = widgets.CustomTableView()
        weights_table_label = QLabel(_('Per-question score weights:'))
        form_layout.addRow(self.combo)
        form_layout.addRow(correct_score_label, self.correct_score)
        form_layout.addRow(incorrect_score_label, self.incorrect_score)
        form_layout.addRow(blank_score_label, self.blank_score)
        table_layout.addWidget(weights_table_label)
        table_layout.addWidget(self.weights_table)
        table_layout.addWidget(self.button_reset)
        table_layout.addWidget(button_defaults)
        table_layout.setAlignment(weights_table_label, Qt.AlignHCenter)
        table_layout.setAlignment(self.weights_table, Qt.AlignHCenter)
        table_layout.setAlignment(self.button_reset, Qt.AlignHCenter)
        table_layout.setAlignment(button_defaults, Qt.AlignHCenter)
        self.button_reset.clicked.connect(self._reset_weights)
        button_defaults.clicked.connect(self._compute_default_values)
        self.base_score_widgets = [
            self.correct_score, correct_score_label,
            self.incorrect_score, incorrect_score_label,
            self.blank_score, blank_score_label,
            button_defaults,
        ]
        self.weights_widgets = [
            self.weights_table, weights_table_label,
        ]
        self.current_mode = None

    def initializePage(self):
        """Loads the values from the exam config, if any."""
        exam_config = self.wizard().exam_config
        self.weights_table.setModel(widgets.ScoreWeightsTableModel( \
                                                 exam_config, parent=self))
        self.weights_table.model().dataChanged.connect(self._weights_changed)
        self.weights_table.adjust_size()
        if (not self.correct_score.text() and not self.correct_score.text()
            and not self.blank_score.text()):
            # Change values only if they have not been set manually
            scores = exam_config.base_scores
            if scores is not None:
                self._set_score_fields(scores)
        # If the exam is a survey, disable all the controls
        if exam_config.survey_mode:
            self.combo.set_item_enabled(1, False)
            self.combo.set_item_enabled(2, False)
            initial_mode = 0
            self.weights_table.model().clear()
        else:
            if not exam_config.scores or exam_config.all_weights_are_one():
                self.combo.set_item_enabled(1, True)
                self.combo.set_item_enabled(2, True)
                initial_mode = 1
                self.weights_table.model().clear()
            else:
                self.combo.set_item_enabled(1, True)
                self.combo.set_item_enabled(2, True)
                initial_mode = 2
        self.combo.setCurrentIndex(initial_mode)

    def validatePage(self):
        """Called by QWizardPage to check the values of this page.

           Checks the values and consolidates them if valid.
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

    def clear_base_scores(self):
        self.correct_score.setText('')
        self.incorrect_score.setText('')
        self.blank_score.setText('')

    def _update_combo(self, new_index):
        if new_index != self.current_mode:
            # Ask the user if changes to weights may be lost
            if (self.current_mode == 2
                and self.weights_table.model().changes):
                if not self._show_warning_weights_reset():
                    self.combo.setCurrentIndex(self.current_mode)
                    return
            self.button_reset.setEnabled(False)
            if new_index == 0:
                for widget in self.base_score_widgets:
                    widget.setEnabled(False)
                for widget in self.weights_widgets:
                    widget.setEnabled(False)
            elif new_index == 1:
                for widget in self.base_score_widgets:
                    widget.setEnabled(True)
                for widget in self.weights_widgets:
                    widget.setEnabled(False)
            else:
                for widget in self.base_score_widgets:
                    widget.setEnabled(True)
                for widget in self.weights_widgets:
                    widget.setEnabled(True)
            # Reset the weights table
            if self.current_mode == 2:
                self.weights_table.model().clear()
            elif new_index == 2:
                self.weights_table.model().data_reset()
            # Reset the scores
            if new_index == 0:
                self.clear_base_scores()
            self.current_mode = new_index

    def _reset_weights(self):
        if (self.weights_table.model().changes
            and self._show_warning_weights_reset()):
            self.weights_table.model().data_reset()

    def _weights_changed(self, index_1, index_2):
        self.button_reset.setEnabled(self.weights_table.model().changes)

    def _compute_default_values(self):
        if (self.current_mode == 2
            and not self.weights_table.model().validate()):
                self._show_error_weights()
                return
        dialog = dialogs.DialogComputeScores(parent=self)
        score, penalize = dialog.exec_()
        if score is None:
            return
        config = self.wizard().exam_config
        choices = config.get_num_choices()
        if self.current_mode == 1:
            # All the questions have the same score
            total_weight = config.num_questions
        elif self.current_mode == 2:
            # Weighted questions
            total_weight = self.weights_table.model().sum_weights[0]
        else:
            raise NotImplementedError('Bad mode in scores wizard page')
        if config.num_questions and choices and choices > 1:
            c_score = score / total_weight
            if penalize:
                i_score = score / (choices - 1) / total_weight
            else:
                i_score = 0
            b_score = 0
            scores = utils.QuestionScores(c_score, i_score, b_score)
            self._set_score_fields(scores)
        else:
             QMessageBox.critical(self, _('Error'),
                                 _('Automatic scores cannot be computed for '
                                   'this exam.'))

    def _set_score_fields(self, scores):
        self.correct_score.setText(scores.format_correct_score(signed=False))
        self.incorrect_score.setText( \
                                 scores.format_incorrect_score(signed=True))
        self.blank_score.setText(scores.format_blank_score(signed=True))

    def _consolidate_no_scores(self):
        self.wizard().exam_config.enter_score_mode_none()
        return True

    def _consolidate_base_scores(self):
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
                base_scores = utils.QuestionScores(c_score, i_score, b_score)
                same_weights = True if self.current_mode == 1 else False
                self.wizard().exam_config.set_base_scores(base_scores,
                                                   same_weights=same_weights)
                valid = True
            else:
                QMessageBox.critical(self, _('Error'),
                                _('The score for incorrect and blank answers '
                                  'cannot be greater than 0.'))
        else:
            QMessageBox.critical(self, _('Error'),
                                 _('You must enter the score for correct '
                                   'answers.'))
        return valid

    def _consolidate_weights(self):
        valid = self.weights_table.model().consolidate()
        if not valid:
            self._show_error_weights()
        return valid

    def _show_error_weights(self):
        QMessageBox.critical(self, _('Error'),
                             _('The weights must be the same '
                               'in all the models, although they may '
                               'be in a different order. '
                               'You must fix this before computing '
                               'default scores.'))

    def _show_warning_weights_reset(self):
        result = QMessageBox.warning(self, _('Warning'),
                             _('The changes you have done to the weights '
                               'table will be lost. '
                               'Are you sure you want to continue?'),
                             QMessageBox.Yes | QMessageBox.No,
                             QMessageBox.No)
        return (result == QMessageBox.Yes)


class WizardNewSession(QWizard):
    """Wizard for the creation of a new session.

    It asks for a directory in which to store the session, the .eye file,
    student lists and scores for correct/incorrect answers.

    An initial value for the path of the .eye file can be passed as
    `config_filename`.

    """
    def __init__(self, parent, config_filename=None):
        super(WizardNewSession, self).__init__(parent)
        self.exam_config = None
        self.setWindowTitle(_('Create a new session'))
        self.page_initial = \
                 self._create_page_initial(config_filename=config_filename)
        self.page_id_files = self._create_page_id_files()
        self.page_scores = self._create_page_scores()
        self.page_scores.setFinalPage(True)
        self.addPage(self.page_initial)
        self.addPage(self.page_id_files)
        self.addPage(self.page_scores)

    def get_directory(self):
        return unicode(self.page_initial.directory.text())

    def get_config_file_path(self):
        return unicode(self.page_initial.config_file.text())

    def student_id_files(self):
        return self.files_w.get_files()

    def values(self):
        values = {}
        values['directory'] = self.get_directory()
        values['config_file_path'] = self.get_config_file_path()
        values['config'] = self.exam_config
        values['id_list_files'] = self.student_id_files()
        return values

    def exam_config_reset(self):
        """Called when the exam config file is set or its value is changed."""
        self.page_scores.clear_base_scores()

    def _create_page_initial(self, config_filename=None):
        """Creates the first page, which asks for directory and .eye file."""
        return NewSessionPageInitial(config_filename=config_filename)

    def _create_page_id_files(self):
        """Creates a page for selecting student id files."""
        page = QWizardPage(self)
        page.setTitle(_('Student id files'))
        page.setSubTitle(_('You can select zero, one or more files with the '
                           'list of student ids. Go to the user manual '
                           'if you don\'t know the format of the files.'))
        self.files_w = widgets.MultipleFilesWidget(
                              _('Select student list files'),
                              file_name_filter=FileNameFilters.student_list,
                              check_file_function=self._check_student_ids_file)
        layout = QVBoxLayout()
        page.setLayout(layout)
        layout.addWidget(self.files_w)
        return page

    def _create_page_scores(self):
        """Creates the scores page, which asks for (in)correct scores."""
        return NewSessionPageScores()

    def _check_student_ids_file(self, file_name):
        valid = True
        try:
            utils.read_student_ids(filename=file_name)
        except Exception as e:
            valid = False
            QMessageBox.critical(self, _('Error in student list'),
                                 file_name + '\n\n' + str(e))
        return valid, ''
