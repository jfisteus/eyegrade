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

import os.path
import fractions
import gettext
import locale

#from PyQt4 import QtCore, QtGui
from PyQt4.QtGui import (QImage, QWidget, QMainWindow, QPainter,
                         QSizePolicy, QVBoxLayout, QStackedLayout,
                         QLabel, QIcon, QAction, QMenu, QDialog,
                         QFormLayout, QLineEdit, QDialogButtonBox,
                         QComboBox, QFileDialog, QHBoxLayout, QPushButton,
                         QMessageBox, QPixmap, QCompleter,
                         QSortFilterProxyModel, QKeySequence, QColor,
                         QWizard, QWizardPage, QListWidget, QAbstractItemView,
                         QRegExpValidator, QCheckBox, QSpinBox, QTabWidget,
                         QScrollArea,)

from PyQt4.QtCore import (Qt, QTimer, QRunnable, QThreadPool, QRegExp,
                          QObject, pyqtSignal,)

from eyegrade.utils import (resource_path, program_name, version, web_location,
                            source_location)
import eyegrade.utils as utils
from . import examsview


color_eyegrade_blue = QColor(32, 73, 124)

t = gettext.translation('eyegrade', utils.locale_dir(), fallback=True)
_ = t.ugettext

_filter_exam_config = _('Exam configuration (*.eye)')
_filter_session_db = _('Eyegrade session (*.eyedb)')
_filter_student_list = _('Student list (*.csv *.tsv *.txt *.lst *.list)')

_tuple_strcoll = lambda x, y: locale.strcoll(x[0], y[0])

class LineContainer(QWidget):
    """Container that disposes other widgets horizontally."""
    def __init__(self, parent, *widgets):
        super(LineContainer, self).__init__(parent)
        self.layout = QHBoxLayout(self)
        self.setLayout(self.layout)
        for widget in widgets:
            self.add(widget)

    def add(self, widget):
        self.layout.addWidget(widget)


class OpenFileWidget(QWidget):
    """Dialog with a text field and a button to open a file selector."""
    def __init__(self, parent, select_directory=False, name_filter='',
                 minimum_width=200, title='', check_file_function=None):
        super(OpenFileWidget, self).__init__(parent)
        self.select_directory = select_directory
        self.name_filter = name_filter
        self.title = title
        self._check_file = check_file_function
        layout = QHBoxLayout(self)
        self.setLayout(layout)
        self.filename_widget = QLineEdit(self)
        self.filename_widget.setMinimumWidth(minimum_width)
        self.button = QPushButton(QIcon(resource_path('open_file.svg')), '',
                                  parent=self)
        self.button.clicked.connect(self._open_dialog)
        container = LineContainer(self, self.filename_widget, self.button)
        layout.addWidget(container)
        self.last_validated_value = None

    def text(self):
        return unicode(self.filename_widget.text())

    def set_text(self, filename):
        self.filename_widget.setText(filename)

    def setEnabled(self, enabled):
        self.filename_widget.setEnabled(enabled)
        self.button.setEnabled(enabled)

    def is_validated(self):
        """Returns True if the value equals the latest validated value.

        This way, the file needs not to be validated again if it has not been
        changed since the last validation.

        """
        return self.last_validated_value == self.text()

    def check_value(self, filename=None):
        """Checks the file and returns True if it is valid.

        If it is not valid, shows an error message. It the validation function
        has not been set (it is None), returns always True.

        If `filename` is None, the internal value is used instead.

        """
        if filename is None:
            filename = self.text()
        valid = True
        if self._check_file is not None:
            valid, msg = self._check_file(filename)
        if not valid:
            QMessageBox.critical(self, _('Error'), msg)
        else:
            self.last_validated_value = filename
        return valid

    def _open_dialog(self, value):
        if self.select_directory:
            filename = \
                QFileDialog.getExistingDirectory(self, self.title, '',
                                        (QFileDialog.ShowDirsOnly
                                         | QFileDialog.DontResolveSymlinks
                                         | QFileDialog.DontUseNativeDialog))
        else:
            filename = QFileDialog.getOpenFileName(self, self.title, '',
                                              self.name_filter, None,
                                              QFileDialog.DontUseNativeDialog)
        if filename:
            filename = unicode(filename)
            valid = self.check_value(filename=filename)
            if valid:
                self.filename_widget.setText(filename)


class InputScore(QLineEdit):
    """Allows the user to enter a score."""
    def __init__(self, parent=None, minimum_width=100, is_positive=True):
        super(InputScore, self).__init__(parent=parent)
        self.setMinimumWidth(minimum_width)
        if is_positive:
            placeholder = _('e.g.: 2; 2.5; 5/2')
        else:
            placeholder = _('e.g.: 0; -1; -1.25; -5/4')
        self.setPlaceholderText(placeholder)
        regex = r'((\d*(\.\d+))|(\d+\/\d+))'
        if not is_positive:
            regex = '-?' + regex
        validator = QRegExpValidator(QRegExp(regex), self)
        self.setValidator(validator)

    def value(self, force_float=False):
        """Returns the value as a fractions.Fraction or a float.

        Returns None if the field is empty or the value is not
        correct.  If `force_float` a float is returned always.

        """
        value_str = self.text()
        if value_str:
            if '/' in value_str:
                parts = [int(v) for v in value_str.split('/')]
                try:
                    value = fractions.Fraction(parts[0], parts[1])
                    if force_float:
                        value = float(value)
                except:
                    value = None
            elif not '.' in value_str:
                value = fractions.Fraction(int(value_str), 1)
            else:
                value = float(value_str)
        else:
            value = None
        return value

    def setPlaceholderText(self, text):
        """Proxy for the same method in QLineEdit.

        This method is overridden because some old versions of Qt4 do
        not provide the method. This proxy method just calls the one
        from QLineEdit, and fails silently if the method does not
        exist there.

        """
        try:
            super(InputScore, self).setPlaceholderText(text)
        except AttributeError:
            # Just do nothing if the version of Qt/PyQt is old...
            pass


class MultipleFilesWidget(QWidget):
    """Widget that allows the selection of multiple files."""
    def __init__(self, title, file_name_filter='', check_file_function=None):
        """Creates a new widget for selecting multiple files.

        - `title`: title of the file selection dialog that is opened
          when the user clicks on 'Add File'.

        - `file_name_filter`: filter to use for the selection of files
          (See the documentation of QFileDialog).

        - `check_file_function`: function that receives a file name and
          returns True if its contents are correct. If None, files are
          not checked. An error dialog is shown for the files that are
          not correct. The rest are just added.

        """
        super(MultipleFilesWidget, self).__init__()
        self.title = title
        self.file_name_filter = file_name_filter
        self._check_file = check_file_function
        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        button_add = QPushButton(_('Add files'))
        self.button_remove = QPushButton(_('Remove selected'))
        self.button_remove.setEnabled(False)
        buttons = QWidget()
        buttons_layout = QVBoxLayout()
        buttons_layout.setAlignment(Qt.AlignTop)
        buttons.setLayout(buttons_layout)
        buttons_layout.addWidget(button_add)
        buttons_layout.addWidget(self.button_remove)
        main_layout = QHBoxLayout()
        self.setLayout(main_layout)
        main_layout.addWidget(self.file_list)
        main_layout.addWidget(buttons)
        button_add.clicked.connect(self._add_files)
        self.button_remove.clicked.connect(self._remove_files)
        self.file_list.selectionModel().selectionChanged.connect( \
                                                       self._selection_changed)

    def get_files(self):
        """Returns the list of selected file names."""
        files = []
        model = self.file_list.model()
        count = model.rowCount()
        for i in range(0, count):
            index = model.index(i, 0)
            files.append(unicode(model.data(index).toString()))
        return files

    def _add_files(self):
        file_list_q = QFileDialog.getOpenFileNames(self, self.title, '',
                                               self.file_name_filter, None,
                                               QFileDialog.DontUseNativeDialog)
        model = self.file_list.model()
        for file_name in file_list_q:
            valid = True
            if self._check_file is not None:
                valid, msg = self._check_file(unicode(file_name))
            if valid:
                # Check if the file is already in the list:
                match = model.match(model.index(0, 0), 0, file_name, 1,
                                    Qt.MatchExactly)
                if len(match) == 0:
                    self.file_list.addItem(file_name)

    def _remove_files(self):
        ranges = self.file_list.selectionModel().selection()
        model = self.file_list.model()
        to_remove = []
        for r in ranges:
            to_remove.extend(range(r.top(), r.bottom() + 1))
        for row in sorted(to_remove, reverse=True):
            model.removeRow(row)

    def _selection_changed(self, deselected, selected):
        if len(self.file_list.selectionModel().selection()) > 0:
            self.button_remove.setEnabled(True)
        else:
            self.button_remove.setEnabled(False)


class CompletingComboBox(QComboBox):
    """An editable combo box that filters and autocompletes."""
    def __init__(self, parent=None):
        super(CompletingComboBox, self).__init__(parent)
        self.setEditable(True)
        self.filter = QSortFilterProxyModel(self)
        self.filter.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.filter.setSourceModel(self.model())
        self.completer = QCompleter(self.filter, self)
        self.completer.setCompletionMode(QCompleter.UnfilteredPopupCompletion)
        self.setCompleter(self.completer)
        self.lineEdit().textEdited[unicode]\
            .connect(self.filter.setFilterFixedString)
        self.currentIndexChanged.connect(self._index_changed)
        self.setAutoCompletion(True)

    def _index_changed(self, index):
        self.lineEdit().selectAll()


class DialogStudentId(QDialog):
    """Dialog to change the student id.

    Example (replace `parent` by the parent widget):

    dialog = DialogStudentId(parent)
    id = dialog.exec_()

    """
    def __init__(self, parent, students):
        super(DialogStudentId, self).__init__(parent)
        self.setWindowTitle(_('Change the student id'))
        layout = QFormLayout()
        self.setLayout(layout)
        self.combo = CompletingComboBox(self)
        for student in students:
            self.combo.addItem(student)
        self.combo.lineEdit().selectAll()
        self.combo.lineEdit().setFocus()
        buttons = QDialogButtonBox((QDialogButtonBox.Ok
                                    | QDialogButtonBox.Cancel))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(_('Student id:'), self.combo)
        layout.addRow(buttons)

    def exec_(self):
        """Shows the dialog and waits until it is closed.

        Returns the text of the option selected by the user, or None if
        the dialog is cancelled.

        """
        result = super(DialogStudentId, self).exec_()
        if result == QDialog.Accepted:
            return unicode(self.combo.currentText())
        else:
            return None


class DialogComputeScores(QDialog):
    """Dialog to set the parameters to compute scores automatically.

    Example (replace `parent` by the parent widget):

    dialog = DialogComputeScores(parent)
    max_score, penalize = dialog.exec_()

    """
    def __init__(self, parent=None):
        super(DialogComputeScores, self).__init__(parent)
        self.setWindowTitle(_('Compute default scores'))
        layout = QFormLayout()
        self.setLayout(layout)
        self.score = InputScore(parent=self)
        self.penalize = QCheckBox(_('Penalize incorrect answers'), self)
        buttons = QDialogButtonBox((QDialogButtonBox.Ok
                                    | QDialogButtonBox.Cancel))
        layout.addRow(_('Maximum score'), self.score)
        layout.addRow(_('Penalizations'), self.penalize)
        layout.addRow(buttons)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

    def exec_(self):
        """Shows the dialog and waits until it is closed.

        Returns the tuple (max_score, penalize) or (None, None) if the
        user cancels.

        """
        success = False
        score = None
        penalize = None
        while not success:
            result = super(DialogComputeScores, self).exec_()
            if result == QDialog.Accepted:
                if self.score.text():
                    score = self.score.value()
                    if score is not None and score > 0:
                        penalize = self.penalize.checkState() == Qt.Checked
                        success = True
                if not success:
                    QMessageBox.critical(self, _('Error'),
                                         _('Enter a valid score.'))
            else:
                score, penalize = None, None
                success = True
        return (score, penalize)


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
        self.directory = OpenFileWidget(self, select_directory=True,
                            title=_('Select or create an empty directory'),
                            check_file_function=self._check_directory)
        self.config_file = OpenFileWidget(self,
                            title=_('Select the exam configuration file'),
                            name_filter=_filter_exam_config,
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
        layout = QFormLayout(self)
        self.setLayout(layout)
        self.correct_score = InputScore(is_positive=True)
        self.incorrect_score = InputScore(is_positive=False)
        self.blank_score = InputScore(is_positive=False)
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
        dialog = DialogComputeScores(parent=self)
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
        self.page_scores.clear_values()

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
        self.files_w = MultipleFilesWidget(_('Select student list files'),
                              file_name_filter=_filter_student_list,
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


class DialogCameraSelection(QDialog):
    """Shows a dialog that allows choosing a camera.

    Example (replace `parent` by the parent widget):

    dialog = DialogNewSession(parent)
    values = dialog.exec_()

    At the end of the dialog, the chosen camera is automatically
    set in the context object.

    """
    capture_period = 0.1
    camera_error = pyqtSignal()

    def __init__(self, capture_context, parent):
        """Initializes the dialog.

        `capture_context` is the imageproc.ExamCaptureContext object
        to be used.

        """
        super(DialogCameraSelection, self).__init__(parent)
        self.capture_context = capture_context
        self.setWindowTitle(_('Select a camera'))
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        self.camview = CamView((320, 240), self, border=True)
        self.label = QLabel(self)
        self.button = QPushButton(_('Try this camera'))
        self.camera_selector = QSpinBox(self)
        container = LineContainer(self, self.camera_selector, self.button)
        self.button.clicked.connect(self._select_camera)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(self.camview)
        layout.addWidget(self.label)
        layout.addWidget(container)
        layout.addWidget(buttons)
        self.camera_error.connect(self._show_camera_error,
                                  type=Qt.QueuedConnection)
        self.timer = None

    def __del__(self):
        if self.timer is not None:
            self.timer.stop()
        self.capture_context.close_camera()

    def exec_(self):
        success = self.capture_context.open_camera()
        if success:
            self._update_camera_label()
            self.timer = QTimer(self)
            self.timer.setSingleShot(False)
            self.timer.timeout.connect(self._next_capture)
            self.timer.setInterval(DialogCameraSelection.capture_period)
            self.timer.start()
        else:
            self.camera_error.emit()
        return super(DialogCameraSelection, self).exec_()

    def _show_camera_error(self):
        QMessageBox.critical(self, _('Camera not available'),
                      _('Eyegrade has not detected any camera in your system.'))
        self.reject()

    def _select_camera(self):
        current_camera = self.capture_context.current_camera_id()
        new_camera = self.camera_selector.value()
        if new_camera != current_camera:
            success = self.capture_context.open_camera(camera_id=new_camera)
            if not success:
                self.camera_error.emit()
            else:
                self._update_camera_label()
                camera_id = self.capture_context.current_camera_id()
                if camera_id != new_camera:
                    QMessageBox.critical(self, _('Camera not available'),
                           _('Camera {0} is not available.').format(new_camera))

    def _update_camera_label(self):
        camera_id = self.capture_context.current_camera_id()
        if camera_id is not None and camera_id >= 0:
            self.label.setText(_('<center>Viewing camera: {0}</center>')\
                               .format(camera_id))
            self.camera_selector.setValue(camera_id)
        else:
            self.label.setText(_('<center>No camera</center>'))

    def _next_capture(self):
        if not self.isVisible():
            self.timer.stop()
            self.capture_context.close_camera()
        else:
            image = self.capture_context.capture(resize=(320, 240))
            self.camview.display_capture(image)


class DialogAbout(QDialog):
    """About dialog.

    Example (replace `parent` by the parent widget):

    dialog = DialogAbout(parent)
    values = dialog.exec_()

    """
    def __init__(self, parent):
        super(DialogAbout, self).__init__(parent)
        self.setWindowTitle(_('About'))
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(self.accept)
        tabs = QTabWidget(parent)
        tabs.setDocumentMode(True)
        tabs.addTab(self._create_about_tab(), _('About'))
        tabs.addTab(self._create_developers_tab(), _('Developers'))
        tabs.addTab(self._create_translators_tab(), _('Translators'))
        layout.addWidget(tabs)
        layout.addWidget(buttons)

    def _create_about_tab(self):
        text = \
             _(u"""
             <center>
             <p><img src='{0}' width='64'> <br>
             {1} {2} <br>
             (c) 2010-2013 Jesús Arias Fisteus <br>
             <a href='{3}'>{3}</a> <br>
             <a href='{4}'>{4}</a>

             <p>
             This program is free software: you can redistribute it<br>
             and/or modify it under the terms of the GNU General<br>
             Public License as published by the Free Software<br>
             Foundation, either version 3 of the License, or (at your<br>
             option) any later version.
             </p>
             <p>
             This program is distributed in the hope that it will be<br>
             useful, but WITHOUT ANY WARRANTY; without even the<br>
             implied warranty of MERCHANTABILITY or FITNESS FOR A<br>
             PARTICULAR PURPOSE. See the GNU General Public<br>
             License for more details.
             </p>
             <p>
             You should have received a copy of the GNU General<br>
             Public License along with this program.  If not, see<br>
             <a href='http://www.gnu.org/licenses/gpl.txt'>
             http://www.gnu.org/licenses/gpl.txt</a>.
             </p>
             </center>
             """).format(resource_path('logo.svg'), program_name, version,
                         web_location, source_location)
        label = QLabel(text)
        label.setTextInteractionFlags((Qt.LinksAccessibleByKeyboard
                                       | Qt.LinksAccessibleByMouse
                                       | Qt.TextBrowserInteraction
                                       | Qt.TextSelectableByKeyboard
                                       | Qt.TextSelectableByMouse))
        return label

    def _create_developers_tab(self):
        text = u"""<center><p><b>{0}:</b></p>
                   <ul><li>Jesús Arias Fisteus</li></ul>
                   </center>""".format(_('Lead developers'))
        label = QLabel(text)
        label.setTextInteractionFlags((Qt.LinksAccessibleByKeyboard
                                       | Qt.LinksAccessibleByMouse
                                       | Qt.TextBrowserInteraction
                                       | Qt.TextSelectableByKeyboard
                                       | Qt.TextSelectableByMouse))
        scroll_area = QScrollArea(self.parent())
        scroll_area.setWidget(label)
        return scroll_area

    def _create_translators_tab(self):
        translators = [
            (_('Catalan'), [u'Jaume Barcelo']),
            (_('German'), []),
            (_('Galician'), [u'Jesús Arias Fisteus']),
            (_('French'), []),
            (_('Portuguese'), []),
            (_('Spanish'), [u'Jesús Arias Fisteus']),
            ]
        parts = []
        for language, names in sorted(translators, cmp=_tuple_strcoll):
            if names:
                parts.append(u'<p><b>{0}:</b></p>'.format(language))
                parts.append(u'<ul>')
                for name in names:
                    parts.append(u'<li>{0}</li>'.format(name))
                parts.append(u'</ul>')
        label = QLabel(u''.join(parts))
        label.setTextInteractionFlags((Qt.LinksAccessibleByKeyboard
                                       | Qt.LinksAccessibleByMouse
                                       | Qt.TextBrowserInteraction
                                       | Qt.TextSelectableByKeyboard
                                       | Qt.TextSelectableByMouse))
        scroll_area = QScrollArea(self.parent())
        scroll_area.setWidget(label)
        return scroll_area


class _WorkerSignalEmitter(QObject):
    """Convenience class for generating signals from a Worker."""
    finished = pyqtSignal()


class Worker(QRunnable):
    """Generic worker class for spawning a task to other thread."""

    _active_workers = []
    _worker_count = 0

    def __init__(self, task):
        """Inits a new worker.

        The `task` must be an object that implements a `run()` method.

        """
        super(Worker, self).__init__()
        self.task = task
        self.is_done = False
        self.signals = _WorkerSignalEmitter()
        if Worker._worker_count > 63:
            Worker._cleanup_done_workers()
        Worker._active_workers.append(self)
        Worker._worker_count += 1

    def run(self):
        """Run the task and emit the signal at its completion."""
        self.task.run()
        self.is_done = True
        self.signals.finished.emit()

    @property
    def finished(self):
        """The `finished` signal as a property."""
        return self.signals.finished

    @staticmethod
    def _cleanup_done_workers():
        Worker._active_workers = [w for w in Worker._active_workers \
                                  if not w.is_done]
        Worker._worker_count = len(Worker._active_workers)


class ActionsManager(object):
    """Creates and manages the toolbar buttons."""

    _actions_grading_data = [
        ('start', 'start.svg', _('&Start grading'), None),
        ('stop', 'stop.svg', _('S&top grading'), None),
        ('back', 'back.svg', _('&Back to session home'), None),
        ('continue', 'continue.svg', _('Continue to the &next exam'),
         Qt.Key_Space),
        ('*separator*', None, None, None),
        ('snapshot', 'snapshot.svg', _('&Capture the current image'),
         Qt.Key_C),
        ('manual_detect', 'manual_detect.svg',
         _('&Manual detection of answer tables'), Qt.Key_M),
        ('edit_id', 'edit_id.svg', _('&Edit student id'), Qt.Key_I),
        ('discard', 'discard.svg', _('&Discard exam'), Qt.Key_Backspace),
        ]

    _actions_session_data = [
        ('new', 'new.svg', _('&New session'), None),
        ('open', 'open.svg', _('&Open session'), None),
        ('close', 'close.svg', _('&Close session'), Qt.Key_Escape),
        ('*separator*', None, None, None),
        ('exit', 'exit.svg', _('&Exit'), None),
        ]

    _actions_exams_data = [
        ('search', 'search.svg', _('&Search'), None),
        ]

    _actions_tools_data = [
        ('camera', 'camera.svg', _('Select &camera'), None),
        ]

    _actions_help_data = [
        ('help', None, _('Online &Help'), None),
        ('website', None, _('&Website'), None),
        ('source', None, _('&Source code at GitHub'), None),
        ('about', None, _('&About'), None),
        ]

    _actions_debug_data = [
        ('+show_status', None, _('Show &status'), None),
        ('+lines', None, _('Show &lines'), None),
        ('+processed', None, _('Show &processed image'), None),
        ]

    _actions_experimental = [
        ('+auto_change', None, _('Continue on exam &removal'), None),
        ]

    def __init__(self, window):
        """Creates a manager for the given toolbar object."""
        self.window = window
        self.menubar = window.menuBar()
        self.toolbar = window.addToolBar('Grade Toolbar')
        self.menus = {}
        self.actions_grading = {}
        self.actions_session = {}
        self.actions_exams = {}
        self.actions_tools = {}
        self.actions_help = {}
        action_lists = {'session': [], 'grading': [], 'exams': [],
                        'tools': [], 'help': []}
        for key, icon, text, shortcut in ActionsManager._actions_session_data:
            self._add_action(key, icon, text, shortcut, self.actions_session,
                             action_lists['session'])
        for key, icon, text, shortcut in ActionsManager._actions_grading_data:
            self._add_action(key, icon, text, shortcut, self.actions_grading,
                             action_lists['grading'])
        for key, icon, text, shortcut in ActionsManager._actions_exams_data:
            self._add_action(key, icon, text, shortcut, self.actions_exams,
                             action_lists['exams'])
        for key, icon, text, shortcut in ActionsManager._actions_tools_data:
            self._add_action(key, icon, text, shortcut, self.actions_tools,
                             action_lists['tools'])
        for key, icon, text, shortcut in ActionsManager._actions_help_data:
            self._add_action(key, icon, text, shortcut, self.actions_help,
                             action_lists['help'])
        self._populate_menubar(action_lists)
        self._populate_toolbar(action_lists)
        self._add_debug_actions()
        self._add_experimental_actions()

    def set_search_mode(self):
        self.actions_grading['start'].setEnabled(False)
        self.actions_grading['stop'].setEnabled(True)
        self.actions_grading['back'].setEnabled(False)
        self.actions_grading['snapshot'].setEnabled(True)
        self.actions_grading['manual_detect'].setEnabled(True)
        self.actions_grading['edit_id'].setEnabled(False)
        self.actions_grading['continue'].setEnabled(False)
        self.actions_grading['discard'].setEnabled(False)
        self.actions_session['new'].setEnabled(False)
        self.actions_session['open'].setEnabled(False)
        self.actions_session['close'].setEnabled(True)
        self.actions_session['exit'].setEnabled(True)
        self.actions_tools['camera'].setEnabled(False)
        for key in self.actions_exams:
            self.actions_exams[key].setEnabled(False)

    def set_review_from_grading_mode(self):
        self.actions_grading['start'].setEnabled(False)
        self.actions_grading['stop'].setEnabled(True)
        self.actions_grading['back'].setEnabled(False)
        self.actions_grading['snapshot'].setEnabled(False)
        self.actions_grading['manual_detect'].setEnabled(False)
        self.actions_grading['edit_id'].setEnabled(True)
        self.actions_grading['continue'].setEnabled(True)
        self.actions_grading['discard'].setEnabled(True)
        self.actions_session['new'].setEnabled(False)
        self.actions_session['open'].setEnabled(False)
        self.actions_session['close'].setEnabled(True)
        self.actions_session['exit'].setEnabled(True)
        self.actions_tools['camera'].setEnabled(False)
        for key in self.actions_exams:
            self.actions_exams[key].setEnabled(False)

    def set_review_from_session_mode(self):
        self.actions_grading['start'].setEnabled(True)
        self.actions_grading['stop'].setEnabled(False)
        self.actions_grading['back'].setEnabled(True)
        self.actions_grading['snapshot'].setEnabled(False)
        self.actions_grading['manual_detect'].setEnabled(False)
        self.actions_grading['edit_id'].setEnabled(True)
        self.actions_grading['continue'].setEnabled(True)
        self.actions_grading['discard'].setEnabled(True)
        self.actions_session['new'].setEnabled(False)
        self.actions_session['open'].setEnabled(False)
        self.actions_session['close'].setEnabled(True)
        self.actions_session['exit'].setEnabled(True)
        self.actions_tools['camera'].setEnabled(True)
        self.actions_exams['search'].setEnabled(True)
        for key in self.actions_exams:
            self.actions_exams[key].setEnabled(False)

    def set_session_mode(self):
        self.actions_grading['start'].setEnabled(True)
        self.actions_grading['stop'].setEnabled(False)
        self.actions_grading['back'].setEnabled(False)
        self.actions_grading['snapshot'].setEnabled(False)
        self.actions_grading['manual_detect'].setEnabled(False)
        self.actions_grading['edit_id'].setEnabled(False)
        self.actions_grading['continue'].setEnabled(False)
        self.actions_grading['discard'].setEnabled(False)
        self.actions_session['new'].setEnabled(False)
        self.actions_session['open'].setEnabled(False)
        self.actions_session['close'].setEnabled(True)
        self.actions_session['exit'].setEnabled(True)
        self.actions_tools['camera'].setEnabled(True)
        self.actions_exams['search'].setEnabled(True)
        for key in self.actions_exams:
            self.actions_exams[key].setEnabled(False)

    def set_manual_detect_mode(self):
        self.actions_grading['start'].setEnabled(False)
        self.actions_grading['stop'].setEnabled(True)
        self.actions_grading['back'].setEnabled(False)
        self.actions_grading['snapshot'].setEnabled(False)
        self.actions_grading['manual_detect'].setEnabled(True)
        self.actions_grading['edit_id'].setEnabled(False)
        self.actions_grading['continue'].setEnabled(False)
        self.actions_grading['discard'].setEnabled(True)
        self.actions_session['new'].setEnabled(False)
        self.actions_session['open'].setEnabled(False)
        self.actions_session['close'].setEnabled(True)
        self.actions_session['exit'].setEnabled(True)
        self.actions_tools['camera'].setEnabled(False)
        for key in self.actions_exams:
            self.actions_exams[key].setEnabled(False)

    def set_no_session_mode(self):
        for key in self.actions_grading:
            self.actions_grading[key].setEnabled(False)
        self.actions_session['new'].setEnabled(True)
        self.actions_session['open'].setEnabled(True)
        self.actions_session['close'].setEnabled(False)
        self.actions_session['exit'].setEnabled(True)
        self.actions_tools['camera'].setEnabled(True)
        for key in self.actions_exams:
            self.actions_exams[key].setEnabled(False)

    def enable_manual_detect(self, enabled):
        """Enables or disables the manual detection mode.

        If `enable` is True, it is enabled. Otherwise, it is disabled.

        """
        self.actions_grading['manual_detect'].setEnabled(enabled)

    def register_listener(self, key, listener):
        actions = self._select_action_group(key[0])
        assert key[1] in actions
        actions[key[1]].triggered.connect(listener)

    def is_action_checked(self, key):
        """For checkabel actions, returns whether the action is checked.

        Action keys are tuples such as ('tools', 'lines').

        """
        actions = self._select_action_group(key[0])
        assert key[1] in actions
        assert actions[key[1]].isCheckable()
        return actions[key[1]].isChecked()

    def _select_action_group(self, key):
        if key == 'session':
            return self.actions_session
        elif key == 'grading':
            return self.actions_grading
        elif key == 'tools':
            return self.actions_tools
        elif key == 'help':
            return self.actions_help
        assert False, 'Undefined action group key: {0}.format(key)'

    def _add_action(self, action_name, icon_file, text, shortcut,
                    group, actions_list):
        action = self._create_action(action_name, icon_file, text, shortcut)
        if action_name.startswith('+'):
            if action_name.startswith('++'):
                action_name = action_name[2:]
            else:
                action_name = action_name[1:]
        if not action.isSeparator():
            group[action_name] = action
        actions_list.append(action)

    def _create_action(self, action_name, icon_file, text, shortcut):
        if action_name == '*separator*':
            action = QAction(self.window)
            action.setSeparator(True)
        else:
            if icon_file:
                action = QAction(QIcon(resource_path(icon_file)),
                                 text, self.window)
            else:
                action = QAction(text, self.window)
        if shortcut is not None:
            action.setShortcut(QKeySequence(shortcut))
        if action_name.startswith('+'):
            action.setCheckable(True)
            if action_name.startswith('++'):
                action.setChecked(True)
        return action

    def _populate_menubar(self, action_lists):
        self.menus['session'] = QMenu(_('&Session'), self.menubar)
        self.menus['grading'] = QMenu(_('&Grading'), self.menubar)
        self.menus['exams'] = QMenu(_('&Exams'), self.menubar)
        self.menus['tools'] = QMenu(_('&Tools'), self.menubar)
        self.menus['help'] = QMenu(_('&Help'), self.menubar)
        self.menubar.addMenu(self.menus['session'])
        self.menubar.addMenu(self.menus['grading'])
        self.menubar.addMenu(self.menus['exams'])
        self.menubar.addMenu(self.menus['tools'])
        self.menubar.addMenu(self.menus['help'])
        for action in action_lists['session']:
            self.menus['session'].addAction(action)
        for action in action_lists['grading']:
            self.menus['grading'].addAction(action)
        for action in action_lists['exams']:
            self.menus['exams'].addAction(action)
        for action in action_lists['tools']:
            self.menus['tools'].addAction(action)
        for action in action_lists['help']:
            self.menus['help'].addAction(action)

    def _populate_toolbar(self, action_lists):
        for action in action_lists['grading']:
            self.toolbar.addAction(action)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.actions_exams['search'])
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.actions_session['new'])
        self.toolbar.addAction(self.actions_session['open'])
        self.toolbar.addAction(self.actions_session['close'])

    def _add_debug_actions(self):
        actions_list = []
        for key, icon, text, shortcut in ActionsManager._actions_debug_data:
            self._add_action(key, icon, text, shortcut, self.actions_tools,
                             actions_list)
        menu = QMenu(_('&Debug options'), self.menus['tools'])
        for action in actions_list:
            menu.addAction(action)
        self.menus['tools'].addMenu(menu)

    def _add_experimental_actions(self):
        actions_list = []
        for key, icon, text, shortcut in ActionsManager._actions_experimental:
            self._add_action(key, icon, text, shortcut, self.actions_tools,
                             actions_list)
        menu = QMenu(_('&Experimental'), self.menus['tools'])
        for action in actions_list:
            menu.addAction(action)
        self.menus['tools'].addMenu(menu)


class CamView(QWidget):
    def __init__(self, size, parent, draw_logo=False, border=False):
        super(CamView, self).__init__(parent)
        if not border:
            fixed_size = size
        else:
            fixed_size = (size[0] + 10, size[1] + 10)
        self.setFixedSize(*fixed_size)
        self.border = border
        self.image_size = size
        self.display_wait_image()
        if draw_logo:
            self.logo = QPixmap(resource_path('logo.svg'))
        else:
            self.logo = None
        self.mouse_listener = None

    def paintEvent(self, event):
        painter = QPainter(self)
        if self.border:
            size = self.size()
            painter.setPen(color_eyegrade_blue)
            painter.drawRoundedRect(0, 0, size.width() - 2, size.height() - 2,
                                    10, 10)
            painter.drawImage(5, 5, self.image)
        else:
            painter.drawImage(event.rect(), self.image)

    def display_capture(self, ipl_image):
        """Displays a captured image in the window.

        The image is in the OpenCV IPL format.

        """
        # It is important to use the variable data to prevent issue #58.
        data = ipl_image.tostring()
        self.image = QImage(data, ipl_image.width, ipl_image.height,
                            QImage.Format_RGB888).rgbSwapped()
        if self.logo is not None:
            painter = QPainter(self.image)
            painter.drawPixmap(ipl_image.width - 40, ipl_image.height - 40,
                               36, 36, self.logo)
        self.update()

    def display_wait_image(self):
        self.image = QImage(self.image_size[0], self.image_size[1],
                            QImage.Format_RGB888)
        self.image.fill(Qt.darkBlue)
        self.update()

    def register_mouse_pressed_listener(self, listener):
        """Registers a function to receive a mouse clicked event.

        The listener must receive as parameter a tuple (x, y).

        """
        self.mouse_listener = listener

    def mousePressEvent(self, event):
        if self.mouse_listener:
            self.mouse_listener((event.x(), event.y()))


class CenterView(QWidget):
    img_correct = '<img src="%s" height="22" width="22">'%\
                  resource_path('correct.svg')
    img_incorrect = '<img src="%s" height="22" width="22">'%\
                    resource_path('incorrect.svg')
    img_unanswered = '<img src="%s" height="22" width="22">'%\
                     resource_path('unanswered.svg')

    def __init__(self, parent=None):
        super(CenterView, self).__init__(parent)
        layout = QVBoxLayout()
        self.setLayout(layout)
        self.center = QStackedLayout()
        self.camview = CamView((640, 480), self, draw_logo=True)
        self.label_up = QLabel()
        self.label_down = QLabel()
        self.center.addWidget(self.camview)
        layout.addLayout(self.center)
        layout.addWidget(self.label_up)
        layout.addWidget(self.label_down)
        self.adjustSize()
        self.setFixedSize(self.sizeHint())

    def update_status(self, score, model=None, seq_num=None, survey_mode=False):
        parts = []
        if score is not None:
            if not survey_mode:
                parts.append(CenterView.img_correct)
                parts.append(str(score.correct) + '  ')
                parts.append(CenterView.img_incorrect)
                parts.append(str(score.incorrect) + '  ')
                parts.append(CenterView.img_unanswered)
                parts.append(str(score.blank) + '  ')
                if score.score is not None and score.max_score is not None:
                    parts.append(_('Score: {0:.2f} / {1:.2f}')\
                                 .format(score.score, score.max_score))
                    parts.append('  ')
            else:
                parts.append(_('[Survey mode on]'))
                parts.append('  ')
        if model is not None:
            parts.append(_('Model:') + ' ' + model + '  ')
        if seq_num is not None:
            parts.append(_('Num.:') + ' ' + str(seq_num) + '  ')
        self.label_down.setText(('<span style="white-space: pre">'
                                 + ' '.join(parts) + '</span>'))

    def update_text_up(self, text):
        self.label_up.setText(text)

    def update_text_down(self, text):
        self.label_down.setText(text)

    def display_capture(self, ipl_image):
        """Displays a captured image in the window.

        The image is in the OpenCV IPL format.

        """
        self.camview.display_capture(ipl_image)

    def display_wait_image(self):
        """Displays the default image instead of a camera capture."""
        self.camview.display_wait_image()

    def register_listener(self, key, listener):
        """Registers listeners for the center view.

        Available listeners are:

        - ('camview', 'mouse_pressed'): mouse pressed in the camview
          area. The listener receives the coordinates (x, y) as a
          tuple.

        """
        if key[0] == 'camview':
            if key[1] == 'mouse_pressed':
                self.camview.register_mouse_pressed_listener(listener)
            else:
                assert False, 'Undefined listener key: {0}'.format(key)
        else:
            assert False, 'Undefined listener key: {0}'.format(key)


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        policy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setSizePolicy(policy)
        self.center_view = CenterView()
        self.exams_view = examsview.ThumbnailsView(self)
#        self.center_layout = QStackedLayout()
        self.center_layout = QHBoxLayout()
        self.center_layout.addWidget(self.center_view)
        self.center_layout.addWidget(self.exams_view)
        center_container = QWidget(self)
        center_container.setLayout(self.center_layout)
        self.setCentralWidget(center_container)
        self.setWindowTitle("Eyegrade")
        self.setWindowIcon(QIcon(resource_path('logo.svg')))
        self.adjustSize()
#        self.setFixedSize(self.sizeHint())
        self.digit_key_listener = None
        self.exit_listener = False

    def keyPressEvent(self, event):
        if (self.digit_key_listener
            and event.key() >= Qt.Key_0 and event.key() <= Qt.Key_9):
            self.digit_key_listener(event.text())

    def register_listener(self, key, listener):
        if key[0] == 'key_pressed':
            if key[1] == 'digit':
                self.digit_key_listener = listener
            else:
                assert False, 'Undefined listener key: {0}'.format(key)
        elif key[0] == 'exit':
            self.exit_listener = listener
        elif key[0] == 'exam':
            if key[1] == 'selected':
                self.exams_view.selection_changed.connect(listener)
        else:
            assert False, 'Undefined listener key: {0}'.format(key)

    def closeEvent(self, event):
        accept = True
        if self.exit_listener is not None:
            accept = self.exit_listener()
        if accept:
            event.accept()
        else:
            event.ignore()

    def clear_exams_view(self):
        self.exams_view.clear_exams()


class Interface(object):
    def __init__(self, app, id_enabled, id_list_enabled, argv):
        self.app = app
        self.id_enabled = id_enabled
        self.id_list_enabled = id_list_enabled
        self.last_score = None
        self.last_model = None
        self.manual_detect_enabled = False
        self.window = MainWindow()
        self.actions_manager = ActionsManager(self.window)
        self.activate_no_session_mode()
        self.window.show()
        self.register_listener(('actions', 'session', 'exit'),
                               self.window.close)
        self.register_listener(('actions', 'help', 'about'),
                               self.show_about_dialog)

    def run(self):
        return self.app.exec_()

    def set_manual_detect_enabled(self, enabled):
        self.manual_detect_enabled = enabled
        self.actions_manager.set_manual_detect_enabled(enabled)

    def activate_search_mode(self):
        self.actions_manager.set_search_mode()

    def activate_review_mode(self, from_grading):
        if from_grading:
            self.actions_manager.set_review_from_grading_mode()
        else:
            self.actions_manager.set_review_from_session_mode()

    def activate_manual_detect_mode(self):
        self.actions_manager.set_manual_detect_mode()

    def activate_session_mode(self):
        self.actions_manager.set_session_mode()
        self.display_wait_image()
        self.update_text_up('')
        self.show_version()

    def activate_no_session_mode(self):
        self.actions_manager.set_no_session_mode()
        self.display_wait_image()
        self.update_text_up('')
        self.show_version()
        self.window.clear_exams_view()

    def add_exams(self, exams):
        self.window.exams_view.add_exams(exams)

    def add_exam(self, exam):
        self.window.exams_view.add_exam(exam)

    def update_exam(self, exam):
        self.window.exams_view.update_exam(exam)

    def remove_exam(self, exam):
        self.window.exams_view.remove_exam(exam)

    def selected_exam(self):
        return self.window.exams_view.selected_exam()

    def select_next_exam(self):
        return self.window.exams_view.select_next_exam()

    def clear_selected_exam(self):
        return self.window.exams_view.clear_selected_exam()

    def enable_manual_detect(self, enabled):
        """Enables or disables the manual detection mode.

        If `enable` is True, it is enabled. Otherwise, it is disabled.

        """
        self.actions_manager.enable_manual_detect(enabled)

    def update_status(self, score, model=None, seq_num=None, survey_mode=False):
        self.window.center_view.update_status(score, model=model,
                                              seq_num=seq_num,
                                              survey_mode=survey_mode)

    def update_text_up(self, text):
        if text is None:
            text = ''
        self.window.center_view.update_text_up(text)

    def update_text_down(self, text):
        if text is None:
            text = ''
        self.window.center_view.update_text_down(text)

    def update_text(self, text_up, text_down):
        self.window.center_view.update_text_up(text_up)
        self.window.center_view.update_text_down(text_down)

    def register_listeners(self, listeners):
        """Registers a dictionary of listeners for the events of the gui.

        The listeners are specified as a dictionary with pairs
        event_key->listener. Keys are tuples of strings such as
        ('action', 'session', 'close').

        """
        for key, listener in listeners.iteritems():
            self.register_listener(key, listener)

    def register_listener(self, key, listener):
        """Registers a single listener for the events of the gui.

        Keys are tuples of strings such as ('action', 'session',
        'close').

        """
        if key[0] == 'actions':
            self.actions_manager.register_listener(key[1:], listener)
        elif key[0] == 'center_view':
            self.window.center_view.register_listener(key[1:], listener)
        elif key[0] == 'window':
            self.window.register_listener(key[1:], listener)
        else:
            assert False, 'Unknown event key {0}'.format(key)

    def is_action_checked(self, action_key):
        """For checkabel actions, returns whether the action is checked.

        Action keys are tuples such as ('tools', 'lines').

        """
        return self.actions_manager.is_action_checked(action_key)

    def register_timer(self, time_delta, callback):
        """Registers a callback function to be run after time_delta ms."""
        timer = QTimer(self.window)
        timer.setSingleShot(True)
        timer.timeout.connect(callback)
        timer.setInterval(time_delta)
        timer.start()

    def display_capture(self, ipl_image):
        """Displays a captured image in the window.

        The image is in the OpenCV IPL format.

        """
        self.window.center_view.display_capture(ipl_image)

    def save_capture(self, filename):
        """Saves the current capture and its annotations to the given file."""
        pixmap = QPixmap(self.window.center_view.size())
        self.window.center_view.render(pixmap)
        pixmap.save(filename)

    def display_wait_image(self):
        """Displays the default image instead of a camera capture."""
        self.window.center_view.display_wait_image()

    def dialog_new_session(self, config_filename=None):
        """Displays a new session dialog.

        An initial value for the path of the .eye file can be passed as
        `config_filename`.

        The data introduced by the user is returned as a dictionary with
        keys `directory`, `config` and `id_list`. `id_list` may be None.

        The return value is None if the user cancels the dialog.

        """
        dialog = WizardNewSession(self.window, config_filename=config_filename)
        result = dialog.exec_()
        if result == QDialog.Accepted:
            return dialog.values()
        else:
            return None

    def dialog_student_id(self, student_ids):
        """Displays a dialog to change the student id.

        A string with the option selected by the user (possibly
        student id and name) is returned.

        The return value is None if the user cancels the dialog.

        """
        dialog = DialogStudentId(self.window, student_ids)
        return dialog.exec_()

    def dialog_open_session(self):
        """Displays an open session dialog.

        The filename of the session file is returned or None.

        """
        filename = QFileDialog.getOpenFileName(self.window,
                                               _('Select the session file'),
                                               '', _filter_session_db, None,
                                               QFileDialog.DontUseNativeDialog)
        return str(filename) if filename else None

    def dialog_camera_selection(self, capture_context):
        """Displays a camera selection dialog.

        `capture_context` is the imageproc.ExamCaptureContext object
        to be used.

        """
        dialog = DialogCameraSelection(capture_context, self.window)
        return dialog.exec_()

    def show_error(self, message, title='Error'):
        """Displays an error dialog with the given message.

        The method blocks until the user closes the dialog.

        """
        QMessageBox.critical(self.window, title, message)

    def show_warning(self, message, title='Warning', is_question=True):
        """Displays a warning dialog.

        Returns True if the the user accepts and False otherwise.

        """
        if not is_question:
            result = QMessageBox.warning(self.window, _('Warning'), message)
            if result == QMessageBox.Ok:
                return True
            else:
                return False
        else:
            result = QMessageBox.warning(self.window, _('Warning'), message,
                                         QMessageBox.Yes | QMessageBox.No,
                                         QMessageBox.No)
            if result == QMessageBox.Yes:
                return True
            else:
                return False

    def show_version(self):
        version_line = '{0} {1} - <a href="{2}">{2}</a>'\
               .format(program_name, version, web_location)
        self.update_text_down(version_line)

    def run_worker(self, task, callback):
        """Runs a task in another thread.

        The `task` must be an object that implements a `run()`
        method. Completion is notified to the given `callback` function.

        """
        worker = Worker(task)
        worker.finished.connect(callback)
        QThreadPool.globalInstance().start(worker)

    def show_about_dialog(self):
        dialog = DialogAbout(self.window)
        dialog.exec_()
