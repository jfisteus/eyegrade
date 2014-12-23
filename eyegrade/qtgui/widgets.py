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

from PyQt4.QtGui import (QComboBox, QSortFilterProxyModel, QCompleter,
                         QStatusBar, QLabel, QHBoxLayout, QCheckBox,
                         QWidget, QLineEdit, QPushButton, QIcon, QMessageBox,
                         QFileDialog, QRegExpValidator,
                         QListWidget, QAbstractItemView,
                         QVBoxLayout, QImage, QPainter, QPixmap)
from PyQt4.QtCore import (Qt, QRegExp, )

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

    def add_students(self, students):
        for student in students:
            self.add_student(student)

    def add_student(self, student):
        self.addItem(student.get_id_and_name())


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
