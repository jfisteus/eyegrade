# -*- coding: utf-8 -*-

# Eyegrade: grading multiple choice questions with a webcam
# Copyright (C) 2010-2015 Jesus Arias Fisteus
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

from PyQt4.QtGui import (QPushButton, QMessageBox, QVBoxLayout, QLabel,
                         QWizard, QWizardPage, QFormLayout,
                         QTabWidget, QWidget, QHBoxLayout,
                         QScrollArea, QGroupBox,
                         QRadioButton, QButtonGroup,
                         QGridLayout, QListWidget, QListWidgetItem, QColor)
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
                           'want to store the session '
                           'and configure the exam from a file or manually.'))
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
            self.registerField('config_file', self.config_file.filename_widget)
        self.combo = widgets.CustomComboBox(parent=self)
        self.combo.set_items([
            _('Configure the exam from an existing configuration file'),
            _('Configure the exam manually'),
        ])
        self.combo.setCurrentIndex(0)
        self.combo.currentIndexChanged.connect(self._update_combo)
        self.config_file_label = QLabel(_('Exam configuration file'))
        layout = QFormLayout(self)
        self.setLayout(layout)
        layout.addRow(_('Directory'), self.directory)
        layout.addRow(self.combo)
        layout.addRow(self.config_file_label, self.config_file)

    def validatePage(self):
        """Called by QWizardPage to check the values of this page."""
        if not self.directory.is_validated():
            ok_dir = self.directory.check_value()
        else:
            ok_dir = True
        if self.combo.currentIndex() == 0:
            if not self.config_file.is_validated():
                ok_config = self.config_file.check_value()
            else:
                ok_config = True
            if ok_dir and ok_config:
                self.wizard().exam_config = \
                            utils.ExamConfig(filename=self.config_file.text())
                return True
            else:
                return False
        else:
            return ok_dir

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

    def _update_combo(self, new_index):
        """Enable or disable the .eye file input"""
        if new_index == 0:
            self.config_file.setEnabled(True)
            self.config_file_label.setEnabled(True)
        else:
            self.config_file.setEnabled(False)
            self.config_file_label.setEnabled(False)
            self.config_file.set_text('')

    def nextId(self):
        if self.combo.currentIndex() == 0:
            return WizardNewSession.PageIdFiles
        else:
            return WizardNewSession.PageExamParams


class NewSessionPageExamParams(QWizardPage):
    """ Wizard's page that ask for the params of the test """
    def __init__(self):
        super(NewSessionPageExamParams, self).__init__()
        self.setTitle(_('Configuration of exam params'))
        self.setSubTitle(_('Enter the configuration parameters of the exam'))
        layout = QFormLayout(self)
        self.setLayout(layout)
        self.paramNEIDs = widgets.InputInteger(initial_value=8)
        self.registerField("paramNEIDs", self.paramNEIDs)
        self.paramNAlts = widgets.InputInteger(initial_value=3)
        self.registerField("paramNAlts", self.paramNAlts)
        self.paramNCols = widgets.InputCustomPattern(fixed_size=250,
                                          regex=r'[1-9][0-9]?(\,[1-9][0-9]?)+',
                                          placeholder=_('num,num,...'))
        self.registerField("paramNCols", self.paramNCols)
        self.paramNPerm = widgets.InputInteger(min_value=1, initial_value=2)
        self.registerField("paramNPerm", self.paramNPerm)
        ## self.paramTPerm = widgets.CustomComboBox(parent=self)
        ## self.paramTPerm.set_items([
        ##     _('No (recommended)'),
        ##     _('Yes (experimental)'),
        ## ])
        ## self.paramTPerm.setCurrentIndex(0)
        ## self.registerField("paramTPerm", self.paramTPerm)
        layout.addRow(_('Number of digits of the student ID'),
                      self.paramNEIDs)
        layout.addRow(_('Number of choices per question'),
                      self.paramNAlts)
        layout.addRow(_('Number of questions per answer box'),
                      self.paramNCols)
        layout.addRow(_('Number of models of the exam'),
                      self.paramNPerm)
        ## layout.addRow(_('Enter question permutations'),
        ##               self.paramTPerm)

    def validatePage(self):
        if not self.paramNEIDs.text():
            QMessageBox.critical(self, _('Error in form'),
                _('The number of digits of the student id is empty'))
            return False
        if not self.paramNAlts.text():
            QMessageBox.critical(self, _('Error in form'),
                _('The number of choices per question is empty'))
            return False
        if not self.paramNCols.text():
            QMessageBox.critical(self, _('Error in form'),
                _('The number of questions per answer box is empty.'
                  ' Enter a comma-separated list of natural numbers.'))
            return False
        if self.paramNCols.text().endsWith(','):
            self.paramNCols.setText(self.paramNCols.text()[:-1])
        if not self.paramNPerm.text():
            QMessageBox.critical(self, _('Error in form'),
                _('The number of exam models is empty'))
            return False
        return True

    def nextId(self):
        return WizardNewSession.PageExamAnswers


class NewSessionPageExamAnswers(QWizardPage):

    def __init__(self):
        super(NewSessionPageExamAnswers, self).__init__()
        self.setTitle(_('Selection of correct answers'))
        self.setSubTitle(_('Select the correct answers for each exam model'))
        layout = QFormLayout()
        self.setLayout(layout)
        self.tabs = QTabWidget()
        layout.addRow(self.tabs)

    def initializePage(self):
        self.paramNAlts = self.field("paramNAlts")
        self.paramNCols = self.field("paramNCols")
        self.paramNPerm = self.field("paramNPerm")
        ## self.paramTPerm = self.field("paramTPerm")
        self.tabs.clear()
        self.total_answers = 0
        self.radioGroups = {}
        filas = int(self.paramNPerm.toString())
        for x in range(filas):
            mygroupbox = QScrollArea()
            mygroupbox.setWidget(QWidget())
            mygroupbox.setWidgetResizable(True)
            myform = QHBoxLayout(mygroupbox.widget())
            cols = self.paramNCols.toString().split(',')
            ansID = 0
            radioGroupList = {}
            for col in cols:
                mygroupboxCol = QGroupBox()
                myformCol = QFormLayout()
                mygroupboxCol.setLayout(myformCol)
                for y in range(int(col)):
                    ansID += 1
                    radioGroupList[ansID] = QButtonGroup()
                    layoutRow = QHBoxLayout()
                    for j in range(int(self.paramNAlts.toString())):
                        myradio = QRadioButton(chr(97+j).upper())
                        layoutRow.addWidget(myradio)
                        radioGroupList[ansID].addButton(myradio)
                    self.total_answers  += 1
                    myformCol.addRow(str(ansID), layoutRow)
                myform.addWidget(mygroupboxCol)
            self.radioGroups[chr(97+x).upper()] = radioGroupList
            self.tabs.addTab(mygroupbox, _('Model ') + chr(97+x).upper())

    def _get_values(self, formated=False):
        response = dict()
        for k, v in self.radioGroups.iteritems():
            answer = dict()
            for ak, av in v.iteritems():
                answer[ak] = abs(int(av.checkedId())) - 1
            if formated:
                answer = answer.values()
            response[k] = answer
        return response

    def _check_count_answers(self):
        local_radioGroups = self._get_values(formated=True)
        local_total_answers = sum(len(filter(lambda a: a != 0, v)) \
                                  for v in local_radioGroups.itervalues())
        return (self.total_answers == local_total_answers)

    def validatePage(self):
        valid = True
        msg = ''
        if not self._check_count_answers():
            valid = False
            msg = _('You haven\'t entered the correct answer '
                    'for some questions.')
        else:
            try:
                self.wizard().exam_config = utils.ExamConfig()
                # dimentions generation:
                dimensions = []
                for c in self.paramNCols.toString().split(','):
                    dimensions.append("%s,%s" % (self.paramNAlts.toString(),c))
                self.wizard().exam_config.set_dimensions(';'.join(dimensions))
                # solutions generation:
                current_solutions = self._get_values(formated=True)
                for k, v in current_solutions.iteritems():
                    self.wizard().exam_config.set_solutions(k, v)
                # students ids generation:
                self.wizard().exam_config.id_num_digits = \
                    int(self.field("paramNEIDs").toString())
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
        if not valid:
            QMessageBox.critical(self, _('Error'), msg)
        return valid

    def nextId(self):
        return WizardNewSession.PageIdFiles
        ## if (int(self.paramTPerm.toString()) == 0
        ##     or int(self.paramNPerm.toString()) == 1):
        ##     return WizardNewSession.PageIdFiles
        ## elif int(self.paramTPerm.toString()) == 1:
        ##     return WizardNewSession.PagePermutations
        ## else:
        ##     return WizardNewSession.PageExamAnswers


class NewSessionPagePermutations(QWizardPage):
    def __init__(self):
        super(NewSessionPagePermutations, self).__init__()
        self.setTitle(_('Configuration of permutations'))
        self.setSubTitle(_('Select the position of each question'
                           ' and its choices in every model of the exam.'))
        layout = QGridLayout()
        self.question_list = QListWidget()
        self.permutation_grid = QGridLayout()
        self.alternatives_rows = {}
        layout.addWidget(QLabel(_('Questions of model A')), 0, 0, 1, 1)
        layout.addWidget(self.question_list, 1, 0, 1, 1)
        layout.addWidget(QLabel(_('Model equivalence')), 0, 1, 1, 5)
        self.permutation_grid.setVerticalSpacing(20)
        layout.addLayout(self.permutation_grid, 1, 1, 1, 5)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 5)
        self.setLayout(layout)

    def initializePage(self):
        paramNAlts = int(self.field("paramNAlts").toString())
        paramNPerm = int(self.field("paramNPerm").toString())
        self.question_list.clear()
        # Creation of the list section
        paramNCols_array = self.field("paramNCols").toString().split(',')
        total_questions = 1 + (int(paramNCols_array[0]) \
                               if len(paramNCols_array) == 1 \
                               else reduce(lambda x, y: int(x) + int(y),
                                           paramNCols_array))
        for i in range(1,total_questions):
            questions_list = QListWidgetItem(_('Question ') + str(i))
            questions_list.setData(Qt.UserRole,
                        widgets.ItemList(optionName=_('Question ') + str(i),
                                         optionNumber=i)) # Custom item list
            self.question_list.addItem(questions_list)
        self.question_list.setCurrentRow(0)
        self.question_list.itemClicked.connect(self._on_item_changed)
        # Creation of the grid section
        add_header = True # Header of the columns (Name of alternatives)
        for j in range(0, paramNPerm):
            self.permutation_grid.addWidget( \
                                QLabel(_('Model ') + chr(97 + j).upper()), j, 1)
            self.alternatives_rows[j] = {}
            for k in range(0, paramNAlts):
                if add_header:
                    if k == 0:
                        self.permutation_grid.addWidget(QLabel(''), 0, 1)
                    self.permutation_grid.addWidget( \
                                        QLabel(chr(97 + k).upper()), 0, k + 2)
                self.alternatives_rows[j][k] = \
                    widgets.InputComboBox(self, c_type='alternative',
                                          form=j, alternative=k)
                self.alternatives_rows[j][k].addItems( \
                            [chr(97+x).upper() for x in range(0,paramNAlts)])
                self.alternatives_rows[j][k].setCurrentIndex(0)
                self.permutation_grid.addWidget(self.alternatives_rows[j][k],
                                                j, k + 2)
            add_header = False
            self.alternatives_rows[j][k + 1] = \
                widgets.InputComboBox(self, c_type='question', form=j,
                                      alternative=self.question_list.\
                                          currentItem().\
                                          data(Qt.UserRole).toPyObject().\
                                               get_question_number())
            self.alternatives_rows[j][k + 1].addItems( \
                                [str(x) for x in range(1,total_questions)])
            self.alternatives_rows[j][k + 1].setCurrentIndex(0)
            self.permutation_grid.addWidget(QLabel(_('Question Number')),
                                            j, k + 3)
            self.permutation_grid.addWidget(self.alternatives_rows[j][k + 1],
                                            j, k + 4)
        button_save = QPushButton(_('Save values'))
        self.permutation_grid.addWidget(button_save, j + 1, 1, 1, k + 4)
        button_save.clicked.connect(self._save_values)

    def _on_item_changed(self, arg=None):
        permutation = arg.data(Qt.UserRole).toPyObject().get_permutation()
        for k, v in self.alternatives_rows.iteritems():
            for sk, sv in v.iteritems():
                if not permutation:
                    sv.setCurrentIndex(0)
                else:
                    sv.setCurrentIndex( \
                        [x for x in permutation \
                         if (x['altr'] == sv.alternative
                             and x['form'] == sv.form
                             and x['c_type'] == sv.c_type)][0]['perm'] - 1)
        return True

    def _save_values(self):
        localItem = self.question_list.currentItem()
        formatted_grid  = self._get_formatted_permutation_grid()
        if self._validate_grid(formatted_grid):
            localItem.setBackgroundColor(QColor(0, 255, 68))
            localItem.data(Qt.UserRole).toPyObject()\
                     .set_permutation(formatted_grid)
            self._reset_permutation_grid()
            QMessageBox.information(self, _('Information status'),
                _('The values for the question have been successfully saved'))
            return True
        else:
            QMessageBox.critical(self, _('Error in grid'),
                _('There is an inconsistence in the options'))
            return False

    def _get_formatted_permutation_grid(self):
        local_alternatives_rows = []
        for k, v in self.alternatives_rows.iteritems():
            for sk, sv in v.iteritems():
                alternative = {
                    'c_type': sv.c_type,
                    'form': sv.form,
                    'altr': sv.alternative,
                    'perm': sv.currentIndex() + 1
                }
                local_alternatives_rows.append(alternative)
        return local_alternatives_rows

    def _validate_grid(self, grid):
        #validate current grid and questions number
        forms = {}
        for row in grid:
            if row['c_type'] == 'alternative':
                if row['form'] not in forms:
                    forms[row['form']] = []
                if row['perm'] in forms[row['form']]:
                    return False
                else:
                    forms[row['form']].append(row['perm'])
            if row['c_type'] == 'question':
                for i in xrange(self.question_list.count()):
                    if i == self.question_list.currentRow():
                        continue
                    perm = self.question_list.item(i).data(Qt.UserRole)\
                               .toPyObject().get_permutation()
                    for perm_row in perm:
                        if (perm_row['c_type'] == 'question'
                            and perm_row['form'] == row['form']
                            and perm_row['perm'] == row['perm']):
                            return False
        return True

    def _reset_permutation_grid(self):
        for k,v in self.alternatives_rows.iteritems():
            for sk, sv in v.iteritems():
                sv.setCurrentIndex(0)

    def _get_values(self):
        formated_permutation = {}
        formated_permutation_m = {}
        for i in xrange(self.question_list.count()):
            permutations = self.question_list.item(i).data(Qt.UserRole)\
                               .toPyObject().get_permutation()
            a = {}
            for p in permutations:
                if p['form'] not in formated_permutation:
                    formated_permutation[p['form']] = []
                if p['form'] not in a:
                    a[p['form']] = []
                if p['c_type'] == 'alternative':
                    a[p['form']].append(p['perm'])
                if p['c_type'] == 'question':
                    formated_permutation[p['form']].append( \
                        "%s{%s}" % (p['perm'], ','.join(str(x) \
                                                       for x in a[p['form']])))
        for k,v in formated_permutation.iteritems():
            formated_permutation_m[chr(97+k).upper()] = '/'.join(v)
        return formated_permutation_m

    def validatePage(self):
        valid = True
        msg = ''
        for i in xrange(self.question_list.count()):
            if not self.question_list.item(i).data(Qt.UserRole)\
                .toPyObject().get_permutation():
                valid = False
                msg = _('You must select all permutations for all questions')
                break
        if not valid:
            QMessageBox.critical(self, _('Error'), msg)
        else:
            current_permutations = self._get_values()
            for k, v in current_permutations.iteritems():
                self.wizard().exam_config.set_permutations(k, v)
        return valid

    def nextId(self):
        return WizardNewSession.PageIdFiles


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

    def nextId(self):
        return -1


class WizardNewSession(QWizard):
    """Wizard for the creation of a new session.

    It asks for a directory in which to store the session, the .eye file,
    student lists and scores for correct/incorrect answers.

    An initial value for the path of the .eye file can be passed as
    `config_filename`.

    """
    NUM_PAGES = 6
    (PageInitial, PageExamParams, PageExamAnswers,
     PagePermutations, PageIdFiles, PageScores) = range(NUM_PAGES)

    def __init__(self, parent, config_filename=None):
        super(WizardNewSession, self).__init__(parent)
        self.exam_config = None
        self.setWindowTitle(_('Create a new session'))
        self.page_initial = \
                 self._create_page_initial(config_filename=config_filename)
        self.page_id_files = self._create_page_id_files()
        self.page_exam_params = self._create_page_exam_file()
        self.page_exam_answers = self._create_page_exam_answers()
        self.page_exam_permutations = self._create_page_exam_permutations()
        self.page_scores = self._create_page_scores()

        self.setPage(self.PageInitial, self.page_initial)
        self.setPage(self.PageExamParams, self.page_exam_params)
        self.setPage(self.PageExamAnswers, self.page_exam_answers)
        self.setPage(self.PagePermutations, self.page_exam_permutations)
        self.setPage(self.PageIdFiles, self.page_id_files)
        self.setPage(self.PageScores, self.page_scores)

        self.setStartId(self.PageInitial)

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

    def _create_page_exam_file(self):
        return NewSessionPageExamParams()

    def _create_page_exam_answers(self):
        return NewSessionPageExamAnswers()

    def _create_page_exam_permutations(self):
        return NewSessionPagePermutations()

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

