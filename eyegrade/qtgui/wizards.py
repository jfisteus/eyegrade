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
import fractions
import os.path

from PyQt4.QtGui import (QPushButton, QMessageBox, QVBoxLayout,
                         QWizard, QWizardPage, QFormLayout, QCheckBox, QTabWidget, QWidget, QHBoxLayout,
                         QTabBar, QScrollArea, QComboBox, QGroupBox, QRadioButton, QButtonGroup, )

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
            self.registerField('config_file', self.config_file.filename_widget)
            #self.registerField('config_file*', self.config_file.filename_widget)
        #else:
            ## If '*' is used, the next button is not enabled.
            #self.registerField('config_file', self.config_file.filename_widget)

        self.new_config_file = QCheckBox(_('QCheckBox new_config_file'))
        self.new_config_file.stateChanged.connect(self._validate_config_file)

        layout = QFormLayout(self)
        self.setLayout(layout)
        layout.addRow(_('Directory'), self.directory)
        layout.addRow(self.new_config_file)
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
            if not self.new_config_file.isChecked():
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

    def _validate_config_file(self):
        """Validates if the user needs to create a new exam config file"""
        state = self.new_config_file.isChecked()
        if state:
            self.config_file.setEnabled(False)
        else:
            self.config_file.setEnabled(True)
        return

    def nextId(self):
        if self.new_config_file.isChecked():
            return WizardNewSession.PageExamParams
        else:
            return WizardNewSession.PageIdFiles

class NewSessionPageExamParams(QWizardPage):

    def __init__(self):
        super(NewSessionPageExamParams, self).__init__()
        self.setTitle(_('Title NewSessionPageExamParams'))
        self.setSubTitle(_('SubTitle NewSessionPageExamParams'))
        layout = QFormLayout(self)
        self.setLayout(layout)

        self.paramNEIDs = widgets.InputCustomPattern(fixed_size=100, regex=r'\d+')
        self.registerField("paramNEIDs",self.paramNEIDs)
        #self.registerField("paramNEIDs",self.paramNEIDs, "currentItemData")
        
        self.paramNAlts = widgets.InputCustomPattern(fixed_size=100, regex=r'\d+')
        self.registerField("paramNAlts",self.paramNAlts)
        #self.registerField("paramNAlts",self.paramNAlts, "currentItemData")
        
        self.paramNCols = widgets.InputCustomPattern(fixed_size=100, regex=r'\d+(\,\d+)+', placeholder='num,num,...')
        self.registerField("paramNCols",self.paramNCols)
        #self.registerField("paramNCols",self.paramNCols, "currentItemData")
        
        self.paramNPerm = widgets.InputCustomPattern(fixed_size=100, regex=r'\d+')
        self.registerField("paramNPerm",self.paramNPerm)
        #self.registerField("paramNPerm",self.paramNPerm, "currentItemData")

        layout.addRow(_('params_eids_numb'), self.paramNEIDs)
        layout.addRow(_('params_alts_numb'), self.paramNAlts)
        layout.addRow(_('params_cols_numb'), self.paramNCols)
        layout.addRow(_('params_perm_numb'), self.paramNPerm)

    def validatePage(self):

        if not self.paramNEIDs.text():
            QMessageBox.critical(self, _('Error'), _('validatePage paramNEIDs'))
            return False       

        if not self.paramNAlts.text():
            QMessageBox.critical(self, _('Error'), _('validatePage paramNAlts'))
            return False 

        if not self.paramNCols.text():
            QMessageBox.critical(self, _('Error'), _('validatePage paramNCols'))
            return False    

        if not self.paramNPerm.text():
            QMessageBox.critical(self, _('Error'), _('validatePage paramNPerm'))
            return False  

        return True

    def nextId(self):
        return WizardNewSession.PageExamAnswers

class NewSessionPageExamAnswers(QWizardPage):

    def __init__(self):
        super(NewSessionPageExamAnswers, self).__init__() 
        self.setTitle(_('Title NewSessionPageExamAnswers'))
        self.setSubTitle(_('SubTitle NewSessionPageExamAnswers'))

        layout = QFormLayout()
        self.setLayout(layout)

        self.tabs = QTabWidget()
        layout.addRow(self.tabs)

    def initializePage(self):
        self.paramNAlts     = self.field("paramNAlts")
        self.paramNCols     = self.field("paramNCols")
        self.paramNPerm     = self.field("paramNPerm")

        self.total_answers  = 0
        
        self.radioGroups    = {}

        for x in range(int(self.paramNPerm.toString())):

            mygroupbox          = QScrollArea()
            mygroupbox.setWidget(QWidget())
            mygroupbox.setWidgetResizable(True)
            myform              = QHBoxLayout(mygroupbox.widget())

            cols            = self.paramNCols.toString().split(',')
            ansID           = 0
            radioGroupList  = {}
            
            for col in cols:
                mygroupboxCol   = QGroupBox()
                myformCol       = QFormLayout()
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
            self.tabs.addTab(mygroupbox, "Fila %s" % chr(97+x).upper())

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

        local_radioGroups   = self._get_values(formated=True)
        local_total_answers = sum(len(filter(lambda a: a != 0, v)) for v in local_radioGroups.itervalues())

        if self.total_answers == local_total_answers:
            return True
        else:
            return False

    def validatePage(self):
        valid = True
        msg = ''
        if not self._check_count_answers():
            valid = False
            msg = _('Select all answers for the exam.')
        else:
            try:

                self.wizard().exam_config = utils.ExamConfig()

                # solutions generation
                current_solutions = self._get_values(formated=True)
                for k, v in current_solutions.iteritems():
                    self.wizard().exam_config.set_solutions(k, v)

                # dimentions generation
                dimensions = [] 
                for c in self.paramNCols.toString().split(','):
                    dimensions.append("%s,%s" % (self.paramNAlts.toString(),c))

                self.wizard().exam_config.set_dimensions(';'.join(dimensions))

                # students ids generation
                self.wizard().exam_config.id_num_digits = int(self.field("paramNEIDs").toString())

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

class NewSessionPageScores(QWizardPage):
    """Page of WizardNewSession that asks for the scores for answers."""
    def __init__(self):
        super(NewSessionPageScores, self).__init__()
        self.setTitle(_('Scores for correct and incorrect answers'))
        self.setSubTitle(_('Enter the scores of correct and incorrect '
                           'answers. The program will compute scores based '
                           'on them. Setting these scores is optional.'))
        layout = QFormLayout(self)
        self.setLayout(layout)
        self.correct_score = widgets.InputScore(is_positive=True)
        self.incorrect_score = widgets.InputScore(is_positive=False)
        self.blank_score = widgets.InputScore(is_positive=False)
        self.button_clear = QPushButton(_('Clear values'))
        self.button_defaults = QPushButton(_('Compute default values'))
        layout.addRow(_('Score for correct answers'), self.correct_score)
        layout.addRow(_('Score for incorrect answers'), self.incorrect_score)
        layout.addRow(_('Score for blank answers'), self.blank_score)
        layout.addRow('', self.button_defaults)
        layout.addRow('', self.button_clear)
        self.button_clear.clicked.connect(self.clear_values)
        self.button_defaults.clicked.connect(self._compute_default_values)

    def initializePage(self):
        """Loads the values from the exam config, if any."""
        if (not self.correct_score.text() and not self.correct_score.text()
            and not self.blank_score.text()):
            # Change values only if they have been not been set manually
            weights = self.wizard().exam_config.score_weights
            if weights is not None:
                self.correct_score.setText(self._format_score(weights[0],
                                                              True))
                self.incorrect_score.setText(self._format_score(weights[1],
                                                                False))
                self.blank_score.setText(self._format_score(weights[2], False))
        # If the exam is a survey, disable all the controls
        if self.wizard().exam_config.survey_mode:
            self.correct_score.setEnabled(False)
            self.incorrect_score.setEnabled(False)
            self.blank_score.setEnabled(False)
            self.button_clear.setEnabled(False)
            self.button_defaults.setEnabled(False)
        else:
            # Just in case the exam config changes in the lifetime of this
            #   wizard.
            self.correct_score.setEnabled(True)
            self.incorrect_score.setEnabled(True)
            self.blank_score.setEnabled(True)
            self.button_clear.setEnabled(True)
            self.button_defaults.setEnabled(True)

    def clear_values(self):
        self.correct_score.setText('')
        self.incorrect_score.setText('')
        self.blank_score.setText('')

    def _compute_default_values(self):
        dialog = dialogs.DialogComputeScores(parent=self)
        score, penalize = dialog.exec_()
        if score is None:
            return
        config = self.wizard().exam_config
        choices = config.get_num_choices()
        if config.num_questions and choices and choices > 1:
            i_score = '0'
            b_score = '0'
            if type(score) == fractions.Fraction:
                c_score = utils.fraction_to_str(score / config.num_questions)
                if penalize:
                    i_score = utils.fraction_to_str( \
                        -score / (choices - 1) / config.num_questions)
            else:
                c_score = str(score / config.num_questions)
                if penalize:
                    i_score = str(-score / config.num_questions
                                  / (choices - 1))
            self.correct_score.setText(c_score)
            self.incorrect_score.setText(i_score)
            self.blank_score.setText(b_score)
        else:
             QMessageBox.critical(self, _('Error'),
                                 _('Automatic scores cannot be computed for '
                                   'this exam.'))

    def validatePage(self):
        """Called by QWizardPage to check the values of this page."""
        valid = True
        c_score = self.correct_score.value()
        i_score = self.incorrect_score.value()
        b_score = self.blank_score.value()
        if c_score is None and (i_score is not None or b_score is not None):
            valid= False
            QMessageBox.critical(self, _('Error'),
                                 _('A correct score must be set, or the three '
                                   'scores must be left empty.'))
        else:
            if c_score is not None:
                if i_score is None:
                    i_score = 0
                else:
                    i_score = -i_score
                if b_score is None:
                    b_score = 0
                else:
                    b_score = -b_score
                scores = (c_score, i_score, b_score)
                if scores[1] < 0 or scores[2] < 0:
                    # Note that the sign is inverted!
                    valid = False
                    QMessageBox.critical(self, _('Error'),
                                 _('The score for incorrect and blank answers '
                                   'cannot be greater than 0.'))
            else:
                scores = None
            if valid:
                self.wizard().exam_config.score_weights = scores
        return valid

    def _format_score(self, value, is_positive):
        if is_positive:
            return str(value)
        else:
            if value == 0:
                return '0'
            else:
                return '-' + str(value)

    def nextId(self):
        return -1

class WizardNewSession(QWizard):
    """Wizard for the creation of a new session.

    It asks for a directory in which to store the session, the .eye file,
    student lists and scores for correct/incorrect answers.

    An initial value for the path of the .eye file can be passed as
    `config_filename`.

    """
    NUM_PAGES = 5
    (PageInitial, PageExamParams, PageExamAnswers, PageIdFiles, PageScores) = range(NUM_PAGES)

    def __init__(self, parent, config_filename=None):
        super(WizardNewSession, self).__init__(parent)
        self.exam_config = None
        self.setWindowTitle(_('Create a new session'))
        self.page_initial = \
                 self._create_page_initial(config_filename=config_filename)
        self.page_id_files = self._create_page_id_files()
        self.page_exam_params = self._create_page_exam_file()
        self.page_exam_answers = self._create_page_exam_answers()
        self.page_scores = self._create_page_scores()

        self.setPage(self.PageInitial, self.page_initial)
        self.setPage(self.PageExamParams, self.page_exam_params)
        self.setPage(self.PageExamAnswers, self.page_exam_answers)
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
        self.page_scores.clear_values()

    def _create_page_initial(self, config_filename=None):
        """Creates the first page, which asks for directory and .eye file."""
        return NewSessionPageInitial(config_filename=config_filename)

    def _create_page_exam_file(self):
        return NewSessionPageExamParams()

    def _create_page_exam_answers(self):
        return NewSessionPageExamAnswers()

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
            utils.read_student_ids(filename=file_name, with_names=True)
        except Exception as e:
            valid = False
            QMessageBox.critical(self, _('Error in student list'),
                                 file_name + '\n\n' + str(e))
        return valid, ''
