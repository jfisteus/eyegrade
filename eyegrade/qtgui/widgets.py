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
from __future__ import division, unicode_literals

import gettext
import fractions

from PyQt4.QtGui import (QComboBox, QSortFilterProxyModel, QCompleter,
                         QStatusBar, QLabel, QHBoxLayout, QCheckBox,
                         QWidget, QLineEdit, QPushButton, QIcon, QMessageBox,
                         QFileDialog, QRegExpValidator,
                         QListWidget, QAbstractItemView,
                         QVBoxLayout, QImage, QPainter, QPixmap,
                         QTableView, QStyle, )
from PyQt4.QtCore import (Qt, QRegExp, QAbstractTableModel,
                          QAbstractListModel,
                          QModelIndex, QVariant, )

from .. import utils
from . import Colors

t = gettext.translation('eyegrade', utils.locale_dir(), fallback=True)
_ = t.ugettext


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


class CompletingComboBox(QComboBox):
    """An editable combo box that filters and autocompletes."""
    def __init__(self, parent=None, editable=True):
        super(CompletingComboBox, self).__init__(parent)
        self.setEditable(editable)
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


class StudentComboBox(CompletingComboBox):
    def __init__(self, parent=None, editable=True):
        super(StudentComboBox, self).__init__(parent=parent, editable=editable)
        self.lineEdit().selectAll()
        self.lineEdit().setFocus()
        self.students = []

    def add_students(self, students):
        for student in students:
            self.add_student(student)

    def add_student(self, student, set_current=False):
        self.addItem(student.id_and_name)
        self.students.append(student)
        if set_current:
            self.setCurrentIndex(len(self.students) - 1)

    def current_student(self):
        student = self.students[self.currentIndex()]
        if self.currentText() != student.id_and_name:
            # The user has edited the text of this item
            student = None
        return student


class StatusBar(QStatusBar):
    """Status bar for the main window.

    For now it just contains a simple QLabel.

    """

    def __init__(self, parent):
        """Creates a new instance.

        :param parent: The parent of this status bar.

        """
        super(StatusBar, self).__init__(parent=parent)
        self.status_label = QLabel(parent=self)
        self.addWidget(self.status_label)
        self._show_program_version()
        self.setStyleSheet('QStatusBar {border-top: 1px solid '
                                            'rgb(128, 128, 128); }')

    def set_message(self, text):
        """Sets a new left-side status text.

        :param str text: The text to display in the status bar.

        """
        self.status_label.setText(text)

    def _show_program_version(self):
        version_line = '{0} {1} - <a href="{2}">{2}</a>'\
               .format(utils.program_name, utils.version, utils.web_location)
        label = QLabel(version_line)
        label.setOpenExternalLinks(True)
        self.addPermanentWidget(label)


class LabelledCheckBox(QWidget):
    """A checkbox with a label."""
    def __init__(self, label_text, parent, checked=False):
        """Creates a new instance.

        :param label: The label to show with the checkbox.
        :param parent: The parent of this widget.
        :param checked: Initial state of the checkbox (defaults to False).

        """
        super(LabelledCheckBox, self).__init__(parent=parent)
        layout = QHBoxLayout(self)
        self.checkbox = QCheckBox(parent=self)
        self.checkbox.setChecked(checked)
        layout.addWidget(self.checkbox, alignment=Qt.AlignLeft)
        layout.addWidget(QLabel(label_text, parent=self), stretch=1,
                         alignment=Qt.AlignLeft)
        self.setLayout(layout)

    def is_checked(self):
        """Returns True if the checkbox is checked, False otherwise."""
        return self.checkbox.isChecked()


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
        self.button = QPushButton(QIcon(utils.resource_path('open_file.svg')),
                                  '', parent=self)
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
            self.logo = QPixmap(utils.resource_path('logo.svg'))
        else:
            self.logo = None
        self.mouse_listener = None

    def paintEvent(self, event):
        painter = QPainter(self)
        if self.border:
            size = self.size()
            painter.setPen(Colors.eyegrade_blue)
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


class ScoreWeightsTableModel(QAbstractTableModel):
    """ Table for editing score weight values.

    """
    def __init__(self, exam_config, parent=None):
        super(ScoreWeightsTableModel, self).__init__(parent=parent)
        self.data_reset(exam_config)
        self.dataChanged.connect(self._update_weights_sum)
        self.changes = False

    def data_reset(self, exam_config=None):
        if exam_config is None:
            exam_config = self.exam_config
        else:
            self.exam_config = exam_config
        self.models = sorted(exam_config.models)
        self.has_permutations = False
        if not self.models:
            self.models = ['A']
        elif all(exam_config.get_permutations(m) for m in self.models):
            self.has_permutations = True
            self.models.insert(0, '0')
            self.permutations = exam_config.permutations
        if not self.has_permutations:
            self.weights = [exam_config.get_question_weights(m) \
                            for m in self.models]
            for i in range(len(self.weights)):
                if not self.weights[i]:
                    self.weights[i] = [1] * exam_config.num_questions
        else:
            weights_0 = [1] * exam_config.num_questions
            weights_m = exam_config.get_question_weights(self.models[1])
            if weights_m:
                for i, value in enumerate(weights_m):
                    weights_0[self._to_model_0(1, i)] = value
            else:
                weights_0 = [1] * exam_config.num_questions
            self.weights = [weights_0]
        self.sum_weights = [sum(w) for w in self.weights]
        self.changes = False
        self.reset()

    def clear(self):
        for i in range(len(self.weights)):
            self.weights[i] = [None] * self.exam_config.num_questions
        self.sum_weights = [None] * len(self.weights)
        self.changes = False
        self.reset()

    def validate(self):
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

    def consolidate(self):
        """Consolidate the weights into the exam_config object.

        Returns True if the values are correct and consolidated,
        and False if not.

        """
        if not self.validate():
            return False
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

    def rowCount(self, parent=QModelIndex()):
        return self.exam_config.num_questions + 1

    def columnCount(self, parent=QModelIndex()):
        return len(self.models)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return '{0} {1}'.format(_('Model'), self.models[section])
            else:
                if section < self.exam_config.num_questions:
                    return '{0} {1}'.format(_('Question'), section + 1)
                else:
                    return (_('Total'))
        else:
            return QVariant(QVariant.Invalid)

    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            r = index.row()
            c = index.column()
            if r < self.exam_config.num_questions:
                if not self.has_permutations or c == 0:
                    value = self.weights[c][r]
                else:
                    value = self.weights[0][self._to_model_0(c, r)]
                return utils.format_number(value, short=True)
            else:
                if not self.has_permutations:
                    value = self.sum_weights[c]
                else:
                    value = self.sum_weights[0]
                return utils.format_number(value, short=True, no_fraction=True)
        elif role == Qt.TextAlignmentRole:
            return Qt.AlignCenter
        else:
            return QVariant(QVariant.Invalid)

    def flags(self, index):
        if index.row() < self.exam_config.num_questions:
            return Qt.ItemFlags(Qt.ItemIsEnabled | Qt.ItemIsEditable)
        else:
            return Qt.ItemFlags(Qt.ItemIsEnabled)

    def setData (self, index, value_qvar, role=Qt.EditRole):
        success = False
        r = index.row()
        c = index.column()
        try:
            value = utils.parse_number(unicode(value_qvar.toString()))
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
            if (old_value != value):
                # Emit the signal for all the affected cells
                if not self.has_permutations:
                    self.dataChanged.emit(index, index)
                else:
                    changed_idx = self.index(r_0, 0)
                    self.dataChanged.emit(changed_idx, changed_idx)
                    for model_idx in range(1, len(self.models)):
                        for i in range(self.exam_config.num_questions):
                            if self._to_model_0(model_idx, i) == r_0:
                                changed_idx = self.index(i, model_idx)
                                self.dataChanged.emit(changed_idx, changed_idx)
            success = True
        if success:
            self.changes = True
        return success

    def _update_weights_sum(self, index_1, index_2):
        """Handler for the dataChanged signal."""
        if index_1.row() < self.exam_config.num_questions:
            col_1 = index_1.column()
            col_2 = index_2.column()
            if self.has_permutations:
                # Only changes to column 0 are relevant
                col_2 = 0
            for i in range(col_1, col_2 + 1):
                self.sum_weights[i] = sum(self.weights[i])
                changed_idx = self.index(self.exam_config.num_questions, i)
                self.dataChanged.emit(changed_idx, changed_idx)

    def _to_model_0(self, model_idx, question):
        question_0, opt = self.permutations[self.models[model_idx]][question]
        return question_0 - 1


class CustomTableView(QTableView):
    """QTableView that can compute its own size."""
    def __init__(self, parent=None, maximum_width=500, maximum_height=300):
        super(CustomTableView, self).__init__(parent=parent)
        self.maximum_height = maximum_height
        self.maximum_width=maximum_width

    def adjust_size(self):
        self.resizeRowsToContents()
        self.resizeColumnsToContents()
        self._set_dimension_hints()

    def _set_dimension_hints(self):
        # Maximum width:
        vwidth = self.verticalHeader().width()
        hwidth = self.horizontalHeader().length()
        swidth = self.style().pixelMetric(QStyle.PM_ScrollBarExtent)
        fwidth = self.frameWidth() * 2
        current_width = vwidth + hwidth + swidth + fwidth + 1
        # Minimum and maximum height:
        vheight = 0
        for i in range(self.model().rowCount()):
            vheight += self.rowHeight(i)
        hheight = self.horizontalHeader().height()
        sheight = swidth
        fheight = fwidth
        current_height = vheight + hheight + sheight + fheight
        # Check whether the scrollbars are visible:
        if current_height < self.maximum_height:
            # vertical scrollbar not visible
            current_width -= swidth
        if current_width < self.maximum_width:
            current_height -= swidth
        # Set the table dimensions
        if self.maximum_width < current_width:
            self.setMinimumWidth(self.maximum_width)
            self.setMaximumWidth(self.maximum_width)
        else:
            self.setMinimumWidth(current_width)
            self.setMaximumWidth(current_width)
        if self.maximum_height < current_height:
            self.setMinimumHeight(self.maximum_height)
            self.setMaximumHeight(self.maximum_height)
        else:
            self.setMinimumHeight(current_height)
            self.setMaximumHeight(current_height)


class CustomComboBox(QComboBox):
    """QComboBox that allows enabling / disabling items."""
    def __init__(self, parent=None):
        super(CustomComboBox, self).__init__(parent=parent)
        self.setModel(_CustomComboBoxModel(parent=self))

    def set_items(self, items):
        self.model().set_items(items)

    def set_item_enabled(self, index, enabled):
        self.model().set_item_enabled(index, enabled)


class _CustomComboBoxModel(QAbstractListModel):
    def __init__(self, parent=None):
        super(_CustomComboBoxModel, self).__init__(parent=parent)
        self.items = []
        self.enabled = []

    def set_items(self, items):
        self.items = items
        self.enabled = [True] * len(items)
        self.reset()

    def set_item_enabled(self, index, enabled):
        self.enabled[index] = enabled
        idx = self.createIndex(index, 0)
        self.dataChanged.emit(idx, idx)

    def rowCount(self, parent=QModelIndex()):
        return len(self.items)

    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            return self.items[index.row()]

    def flags(self, index):
        if self.enabled[index.row()]:
            return Qt.ItemFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        else:
            return Qt.ItemFlags()
