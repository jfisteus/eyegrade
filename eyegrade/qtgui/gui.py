# Eyegrade: grading multiple choice questions with a webcam
# Copyright (C) 2012-2013 Jesus Arias Fisteus
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

#from PyQt4 import QtCore, QtGui
from PyQt4.QtGui import (QImage, QWidget, QMainWindow, QPainter,
                         QSizePolicy, QApplication, QVBoxLayout,
                         QLabel, QIcon, QAction, QMenu, QDialog,
                         QFormLayout, QLineEdit, QDialogButtonBox,
                         QComboBox, QFileDialog, QHBoxLayout, QPushButton,
                         QMessageBox, QPixmap, QCompleter,
                         QSortFilterProxyModel, QKeySequence, QColor,
                         QWizard, QWizardPage, QListWidget, QAbstractItemView,
                         QRegExpValidator, QCheckBox,)

from PyQt4.QtCore import Qt, QTimer, QThread, QRegExp, pyqtSignal

from eyegrade.utils import (resource_path, program_name, version, web_location,
                            source_location)
import eyegrade.utils as utils

_filter_exam_config = 'Exam configuration (*.eye)'
_filter_student_list = 'Student list (*.csv *.tsv *.txt *.lst *.list)'

color_eyegrade_blue = QColor(32, 73, 124)

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
        layout.addWidget(self.filename_widget)
        layout.addWidget(self.button)
        self.last_validated_value = None

    def text(self):
        return self.filename_widget.text()

    def setEnabled(self, enabled):
        self.filename_widget.setEnabled(enabled)
        self.button.setEnabled(enabled)

    def is_validated(self):
        """Returns True if the value equals the latest validated value.

        This way, the file needs not to be validated again if it has not been
        changed since the last validation.

        """
        return self.last_validated_value == self.filename_widget.text()

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
            QMessageBox.critical(self, 'Error', msg)
        else:
            self.last_validated_value = filename
        return valid

    def _open_dialog(self, value):
        if self.select_directory:
            filename = \
                QFileDialog.getExistingDirectory(self, self.title, '',
                                            (QFileDialog.ShowDirsOnly
                                             | QFileDialog.DontResolveSymlinks))
        else:
            filename = QFileDialog.getOpenFileName(self, self.title, '',
                                                   self.name_filter)
        if filename:
            valid = self.check_value(filename=filename)
            if valid:
                self.filename_widget.setText(filename)


class InputScore(QLineEdit):
    """Allows the user to enter a score."""
    def __init__(self, parent=None, minimum_width=100, is_positive=True):
        super(InputScore, self).__init__(parent=parent)
        self.setMinimumWidth(minimum_width)
        if is_positive:
            placeholder = 'e.g.: 2; 2.5; 5/2'
        else:
            placeholder = 'e.g.: 0; -1; -1.25; -5/4'
        self.setPlaceholderText(placeholder)
        regex = r'((\d*(\.\d+))|(\d+\/\d+))'
        if not is_positive:
            regex = '-?' + regex
        validator = QRegExpValidator(QRegExp(regex))
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
        button_add = QPushButton('Add files')
        self.button_remove = QPushButton('Remove selected')
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
                                                   self.file_name_filter)
        erroneous_files = []
        model = self.file_list.model()
        for file_name in file_list_q:
            valid = True
            if self._check_file is not None:
                valid, msg = self._check_file(file_name)
            if valid:
                # Check if the file is already in the list:
                match = model.match(model.index(0, 0), 0, file_name, 1,
                                    Qt.MatchExactly)
                if len(match) == 0:
                    self.file_list.addItem(file_name)
            else:
                erroneous_files.append(unicode(file_name))
        if len(erroneous_files) > 0:
            files = '<br>'.join(erroneous_files)
            QMessageBox.critical(self, 'Error',
                                 ('The following files are not valid:<br><br>'
                                  + files))

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
        self.setWindowTitle('Change the student id')
        layout = QFormLayout()
        self.setLayout(layout)
        self.combo = CompletingComboBox(self)
        self.combo.setEditable(True)
        self.combo.setAutoCompletion(True)
        for student in students:
            self.combo.addItem(student)
        self.combo.lineEdit().selectAll()
        self.combo.showPopup()
        buttons = QDialogButtonBox((QDialogButtonBox.Ok
                                    | QDialogButtonBox.Cancel))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow('Student id:', self.combo)
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
        self.setWindowTitle('Compute default scores')
        layout = QFormLayout()
        self.setLayout(layout)
        self.score = InputScore(parent=self)
        self.penalize = QCheckBox('Penalize incorrect answers', self)
        buttons = QDialogButtonBox((QDialogButtonBox.Ok
                                    | QDialogButtonBox.Cancel))
        layout.addRow('Maximum score', self.score)
        layout.addRow('Penalizations', self.penalize)
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
                    QMessageBox.critical(self, 'Error', 'Enter a valid score.')
            else:
                score, penalize = None, None
                success = True
        return (score, penalize)


class NewSessionPageInitial(QWizardPage):
    """First page of WizardNewSession.

    It asks for the directory in which the session has to be stored and
    the exam config file.

    """
    def __init__(self):
        super(NewSessionPageInitial, self).__init__()
        self.setTitle('Directory and exam configuration')
        self.setSubTitle(('Select or create an empty directory in which you '
                          'want to store the session, '
                          'and the exam configuration file.'))
        self.directory = OpenFileWidget(self, select_directory=True,
                            title='Select or create an empty directory',
                            check_file_function=self._check_directory)
        self.config_file = OpenFileWidget(self,
                            title='Select the exam configuration file',
                            name_filter=_filter_exam_config,
                            check_file_function=self._check_exam_config_file)
        self.registerField('directory*', self.directory.filename_widget)
        self.registerField('config_file*', self.config_file.filename_widget)
        layout = QFormLayout(self)
        self.setLayout(layout)
        layout.addRow('Directory', self.directory)
        layout.addRow('Exam configuration file', self.config_file)

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
            msg = 'The directory does not exist or is not a directory.'
        else:
            dir_content = os.listdir(dir_name)
            if dir_content:
                valid = False
                msg = ('The directory is not empty. '
                       'Choose another directory or create a new one.')
        return valid, msg

    def _check_exam_config_file(self, file_name):
        valid = True
        msg = ''
        if not os.path.exists(file_name):
            valid = False
            msg = 'The exam configuration file does not exist.'
        elif not os.path.isfile(file_name):
            valid = False
            msg = 'The exam configuration file is not a regular file.'
        else:
            try:
                utils.ExamConfig(filename=file_name)
            except IOError:
                valid = False
                msg = 'The exam configuration file cannot be read.'
            except Exception as e:
                valid = False
                msg = 'The exam configuration file contains errors'
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
        self.setTitle('Scores for correct and incorrect answers')
        self.setSubTitle(('Enter the scores of correct and incorrect '
                          'answers. The program will compute scores based '
                          'on them. Setting these scores is optional.'))
        layout = QFormLayout(self)
        self.setLayout(layout)
        self.correct_score = InputScore(is_positive=True)
        self.incorrect_score = InputScore(is_positive=False)
        self.blank_score = InputScore(is_positive=False)
        self.button_clear = QPushButton('Clear values')
        self.button_defaults = QPushButton('Compute default values')
        layout.addRow('Score for correct answers', self.correct_score)
        layout.addRow('Score for incorrect answers', self.incorrect_score)
        layout.addRow('Score for blank answers', self.blank_score)
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
             QMessageBox.critical(self, 'Error',
                                 'Automatic scores cannot be computed for '
                                 'this exam.')

    def validatePage(self):
        """Called by QWizardPage to check the values of this page."""
        valid = True
        c_score = self.correct_score.value()
        i_score = self.incorrect_score.value()
        b_score = self.blank_score.value()
        if c_score is None and (i_score is not None or b_score is not None):
            valid= False
            QMessageBox.critical(self, 'Error',
                                 'A correct score must be set, or the three '
                                 'scores must be left empty.')
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
                    QMessageBox.critical(self, 'Error',
                                 'The score for incorrect and blank answers '
                                 'cannot be greater than 0.')
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

    """
    def __init__(self, parent):
        super(WizardNewSession, self).__init__(parent)
        self.exam_config = None
        self.setWindowTitle('Create a new session')
        self.page_initial = self._create_page_initial()
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

    def _create_page_initial(self):
        """Creates the first page, which asks for directory and .eye file."""
        return NewSessionPageInitial()

    def _create_page_id_files(self):
        """Creates a page for selecting student id files."""
        page = QWizardPage(self)
        page.setTitle('Student id files')
        page.setSubTitle(('You can select zero, one or more files with the '
                          'list of student ids. Go to the user manual '
                          'if you don\'t know the format of the files.'))
        self.files_w = MultipleFilesWidget('Select student list files',
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
            utils.read_student_ids(filename=file_name)
        except:
            valid = False
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
        self.setWindowTitle('Select a camera')
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        self.camview = CamView((320, 240), self, border=True)
        self.label = QLabel(self)
        self.button = QPushButton('Try next camera')
        self.button.clicked.connect(self._next_camera)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(self.camview)
        layout.addWidget(self.label)
        layout.addWidget(self.button)
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
        QMessageBox.critical(self, 'Camera not available',
                             'No camera is available.')
        self.reject()

    def _next_camera(self):
        current_camera = self.capture_context.current_camera_id()
        success = self.capture_context.next_camera()
        if not success:
            self.camera_error.emit()
        elif self.capture_context.current_camera_id() == current_camera:
            QMessageBox.critical(self, 'No more cameras',
                                 'No more cameras are available.')
        else:
            self._update_camera_label()

    def _update_camera_label(self):
        camera_id = self.capture_context.current_camera_id()
        if camera_id is not None and camera_id >= 0:
            self.label.setText('<center>Current camera: {0}</center>'\
                               .format(camera_id))
        else:
            self.label.setText('<center>No camera</center>')

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
        text = \
             """
             <center>
             <p><img src='{0}' width='64'> <br>
             {1} {2} <br>
             (c) 2010-2013 Jesus Arias Fisteus <br>
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
             PARTICULAR PURPOSE. See the GNU General Public License<br>
             for more details.
             </p>
             <p>
             You should have received a copy of the GNU General Public<br>
             License along with this program.  If not, see<br>
             <a href='http://www.gnu.org/licenses/gpl.txt'>
             http://www.gnu.org/licenses/gpl.txt</a>.
             </p>
             </center>
             """.format(resource_path('logo.svg'), program_name, version,
                        web_location, source_location)
        self.setWindowTitle('About')
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        label = QLabel(text)
        label.setTextInteractionFlags((Qt.LinksAccessibleByKeyboard
                                       | Qt.LinksAccessibleByMouse
                                       | Qt.TextBrowserInteraction
                                       | Qt.TextSelectableByKeyboard
                                       | Qt.TextSelectableByMouse))
        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(QLabel(text))
        layout.addWidget(buttons)


class Worker(QThread):
    """Generic worker class for spawning a task to other thread."""

    def __init__(self, task, parent):
        """Inits a new worker.

        The `task` must be an object that implements a `run()` method.

        """
        super(Worker, self).__init__(parent)
        self.task = task

    def __del__(self):
        self.wait()

    def run(self):
        """Run the task."""
        self.task.run()


class ActionsManager(object):
    """Creates and manages the toolbar buttons."""

    _actions_grading_data = [
        ('snapshot', 'snapshot.svg', '&Capture the current image', Qt.Key_C),
        ('manual_detect', 'manual_detect.svg',
         '&Manual detection of answer tables', Qt.Key_M),
        ('edit_id', 'edit_id.svg', '&Edit student id', Qt.Key_I),
        ('save', 'save.svg', '&Save and capture next exam', Qt.Key_Space),
        ('discard', 'discard.svg', '&Discard capture', Qt.Key_Backspace),
        ]

    _actions_session_data = [
        ('new', 'new.svg', '&New session', None),
        ('open', 'open.svg', '&Open session', None),
        ('close', 'close.svg', '&Close session', None),
        ('*separator*', None, None, None),
        ('exit', 'exit.svg', '&Exit', Qt.Key_Escape),
        ]

    _actions_tools_data = [
        ('camera', 'camera.svg', 'Select &camera', None),
        ('+auto-change', None, 'Continue on exam &removal', None),
        ]

    _actions_help_data = [
        ('help', None, 'Online &Help', None),
        ('website', None, '&Website', None),
        ('source', None, '&Source code at GitHub', None),
        ('about', None, '&About', None),
        ]

    _actions_debug_data = [
        ('+lines', None, 'Show &lines', None),
        ('+processed', None, 'Show &processed image', None),
        ]

    def __init__(self, window):
        """Creates a manager for the given toolbar object."""
        self.window = window
        self.menubar = window.menuBar()
        self.toolbar = window.addToolBar('Grade Toolbar')
        self.menus = {}
        self.actions_grading = {}
        self.actions_session = {}
        self.actions_tools = {}
        self.actions_help = {}
        action_lists = {'session': [], 'grading': [], 'tools': [], 'help': []}
        for key, icon, text, shortcut in ActionsManager._actions_session_data:
            self._add_action(key, icon, text, shortcut, self.actions_session,
                             action_lists['session'])
        for key, icon, text, shortcut in ActionsManager._actions_grading_data:
            self._add_action(key, icon, text, shortcut, self.actions_grading,
                             action_lists['grading'])
        for key, icon, text, shortcut in ActionsManager._actions_tools_data:
            self._add_action(key, icon, text, shortcut, self.actions_tools,
                             action_lists['tools'])
        for key, icon, text, shortcut in ActionsManager._actions_help_data:
            self._add_action(key, icon, text, shortcut, self.actions_help,
                             action_lists['help'])
        self._populate_menubar(action_lists)
        self._populate_toolbar(action_lists)
        self._add_debug_actions()

    def set_search_mode(self):
        self.actions_grading['snapshot'].setEnabled(True)
        self.actions_grading['manual_detect'].setEnabled(True)
        self.actions_grading['edit_id'].setEnabled(False)
        self.actions_grading['save'].setEnabled(False)
        self.actions_grading['discard'].setEnabled(False)
        self.actions_session['new'].setEnabled(False)
        self.actions_session['open'].setEnabled(False)
        self.actions_session['close'].setEnabled(True)
        self.actions_session['exit'].setEnabled(True)
        self.actions_tools['camera'].setEnabled(False)

    def set_review_mode(self):
        self.actions_grading['snapshot'].setEnabled(False)
        self.actions_grading['manual_detect'].setEnabled(False)
        self.actions_grading['edit_id'].setEnabled(True)
        self.actions_grading['save'].setEnabled(True)
        self.actions_grading['discard'].setEnabled(True)
        self.actions_session['new'].setEnabled(False)
        self.actions_session['open'].setEnabled(False)
        self.actions_session['close'].setEnabled(True)
        self.actions_session['exit'].setEnabled(True)
        self.actions_tools['camera'].setEnabled(False)

    def set_manual_detect_mode(self):
        self.actions_grading['snapshot'].setEnabled(False)
        self.actions_grading['manual_detect'].setEnabled(True)
        self.actions_grading['edit_id'].setEnabled(False)
        self.actions_grading['save'].setEnabled(False)
        self.actions_grading['discard'].setEnabled(True)
        self.actions_session['new'].setEnabled(False)
        self.actions_session['open'].setEnabled(False)
        self.actions_session['close'].setEnabled(True)
        self.actions_session['exit'].setEnabled(True)
        self.actions_tools['camera'].setEnabled(False)

    def set_no_session_mode(self):
        for key in self.actions_grading:
            self.actions_grading[key].setEnabled(False)
        self.actions_session['new'].setEnabled(True)
        self.actions_session['open'].setEnabled(True)
        self.actions_session['close'].setEnabled(False)
        self.actions_session['exit'].setEnabled(True)
        self.actions_tools['camera'].setEnabled(True)

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
        self.menus['session'] = QMenu('&Session', self.menubar)
        self.menus['grading'] = QMenu('&Grading', self.menubar)
        self.menus['tools'] = QMenu('&Tools', self.menubar)
        self.menus['help'] = QMenu('&Help', self.menubar)
        self.menubar.addMenu(self.menus['session'])
        self.menubar.addMenu(self.menus['grading'])
        self.menubar.addMenu(self.menus['tools'])
        self.menubar.addMenu(self.menus['help'])
        for action in action_lists['session']:
            self.menus['session'].addAction(action)
        for action in action_lists['grading']:
            self.menus['grading'].addAction(action)
        for action in action_lists['tools']:
            self.menus['tools'].addAction(action)
        for action in action_lists['help']:
            self.menus['help'].addAction(action)

    def _populate_toolbar(self, action_lists):
        for action in action_lists['grading']:
            self.toolbar.addAction(action)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.actions_session['new'])
        self.toolbar.addAction(self.actions_session['open'])
        self.toolbar.addAction(self.actions_session['close'])

    def _add_debug_actions(self):
        actions_list = []
        for key, icon, text, shortcut in ActionsManager._actions_debug_data:
            self._add_action(key, icon, text, shortcut, self.actions_tools,
                             actions_list)
        menu = QMenu('&Debug options', self.menus['tools'])
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
        self.image = QImage(ipl_image.tostring(),
                            ipl_image.width, ipl_image.height,
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
        self.camview = CamView((640, 480), self, draw_logo=True)
        self.label_up = QLabel()
        self.label_down = QLabel()
        layout.addWidget(self.camview)
        layout.addWidget(self.label_up)
        layout.addWidget(self.label_down)

    def update_status(self, score, model=None, seq_num=None, survey_mode=False):
        parts = []
        if score is not None:
            if not survey_mode:
                correct, incorrect, blank, indet, score, max_score = score
                parts.append(CenterView.img_correct)
                parts.append(str(correct) + '  ')
                parts.append(CenterView.img_incorrect)
                parts.append(str(incorrect) + '  ')
                parts.append(CenterView.img_unanswered)
                parts.append(str(blank) + '  ')
                if score is not None and max_score is not None:
                    parts.append('Score: %.2f / %.2f  '%(score, max_score))
            else:
                parts.append('[Survey mode on]  ')
        if model is not None:
            parts.append('Model: ' + model + '  ')
        if seq_num is not None:
            parts.append('Num.: ' + str(seq_num) + '  ')
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
        self.setCentralWidget(self.center_view)
        self.setWindowTitle("Eyegrade")
        self.setWindowIcon(QIcon(resource_path('logo.svg')))
        self.adjustSize()
        self.setFixedSize(self.sizeHint())
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


class Interface(object):
    def __init__(self, id_enabled, id_list_enabled, argv):
        self.app = QApplication(argv)
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

    def activate_review_mode(self):
        self.actions_manager.set_review_mode()

    def activate_manual_detect_mode(self):
        self.actions_manager.set_manual_detect_mode()

    def activate_no_session_mode(self):
        self.actions_manager.set_no_session_mode()
        self.display_wait_image()
        self.update_text_up('')
        self.show_version()

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

    def dialog_new_session(self):
        """Displays a new session dialog.

        The data introduced by the user is returned as a dictionary with
        keys `directory`, `config` and `id_list`. `id_list` may be None.

        The return value is None if the user cancels the dialog.

        """
        dialog = WizardNewSession(self.window)
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
                                               'Select the session file',
                                               '', _filter_exam_config)
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
            result = QMessageBox.warning(self.window, 'Warning', message)
            if result == QMessageBox.Ok:
                return True
            else:
                return False
        else:
            result = QMessageBox.warning(self.window, 'Warning', message,
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
        self.worker = Worker(task, self.window)
        self.worker.finished.connect(callback)
        self.worker.start()

    def show_about_dialog(self):
        dialog = DialogAbout(self.window)
        dialog.exec_()
