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
from __future__ import unicode_literals, division

import gettext
import locale

from PyQt4.QtGui import (QMessageBox, QVBoxLayout,
                         QFormLayout,
                         QScrollArea, QDialogButtonBox,
                         QCheckBox, QSpinBox,
                         QPushButton, QTabWidget,
                         QDialog, QLabel, QLineEdit,
                         QRegExpValidator, QIcon,
                         QComboBox, )

from PyQt4.QtCore import (Qt, QTimer, pyqtSignal, QRegExp, )

from .. import utils
from . import widgets

t = gettext.translation('eyegrade', utils.locale_dir(), fallback=True)
_ = t.ugettext


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
        self.combo = widgets.StudentComboBox(parent=self)
        self.combo.add_students(students)
        self.combo.editTextChanged.connect(self._check_value)
        self.combo.currentIndexChanged.connect(self._check_value)
        new_student_button = QPushButton( \
                                 QIcon(utils.resource_path('new_id.svg')),
                                 _('New student'), parent=self)
        new_student_button.clicked.connect(self._new_student)
        self.buttons = QDialogButtonBox((QDialogButtonBox.Ok
                                         | QDialogButtonBox.Cancel))
        self.buttons.addButton(new_student_button, QDialogButtonBox.ActionRole)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addRow(_('Student id:'), self.combo)
        layout.addRow(self.buttons)

    def exec_(self):
        """Shows the dialog and waits until it is closed.

        Returns a student object with the option selected by the user.
        The return value is None if the user cancels the dialog.

        """
        result = super(DialogStudentId, self).exec_()
        if result == QDialog.Accepted:
            return self.combo.current_student()
        else:
            return None

    def _new_student(self):
        dialog = NewStudentDialog(parent=self)
        student = dialog.exec_()
        if student is not None:
            self.combo.add_student(student, set_current=True)
            self.buttons.button(QDialogButtonBox.Ok).setFocus()
            self.buttons.button(QDialogButtonBox.Ok).setEnabled(True)

    def _check_value(self, param):
        if self.combo.current_student() is not None:
            self.buttons.button(QDialogButtonBox.Ok).setEnabled(True)
        else:
            self.buttons.button(QDialogButtonBox.Ok).setEnabled(False)


class NewStudentDialog(QDialog):
    """Dialog to ask for a new student.

    It returns a Student object with the data of the student.

    """
    _last_combo_value = None

    def __init__(self, parent=None):
        super(NewStudentDialog, self).__init__(parent)
        self.setMinimumWidth(300)
        self.setWindowTitle(_('Add a new student'))
        layout = QFormLayout()
        self.setLayout(layout)
        self.id_field = QLineEdit(self)
        self.id_field.setValidator(QRegExpValidator(QRegExp(r'\d+'), self))
        self.id_field.textEdited.connect(self._check_values)
        self.name_field = QLineEdit(self)
        self.surname_field = QLineEdit(self)
        self.full_name_field = QLineEdit(self)
        self.name_label = QLabel(_('Given name'))
        self.surname_label = QLabel(_('Surname'))
        self.full_name_label = QLabel(_('Full name'))
        self.email_field = QLineEdit(self)
        self.email_field.setValidator( \
                        QRegExpValidator(QRegExp(utils.re_exp_email), self))
        self.email_field.textEdited.connect(self._check_values)
        self.combo = QComboBox(parent=self)
        self.combo.addItem(_('Separate given name and surname'))
        self.combo.addItem(_('Full name in just one field'))
        self.combo.currentIndexChanged.connect(self._update_combo)
        layout.addRow(self.combo)
        layout.addRow(_('Id number'), self.id_field)
        layout.addRow(self.name_label, self.name_field)
        layout.addRow(self.surname_label, self.surname_field)
        layout.addRow(self.full_name_label, self.full_name_field)
        layout.addRow(_('Email'), self.email_field)
        self.buttons = QDialogButtonBox((QDialogButtonBox.Ok
                                         | QDialogButtonBox.Cancel))
        layout.addRow(self.buttons)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self._check_values()
        # Set the combo box
        if NewStudentDialog._last_combo_value is None:
            NewStudentDialog._last_combo_value = 0
        self.combo.setCurrentIndex(NewStudentDialog._last_combo_value)
        self._update_combo(NewStudentDialog._last_combo_value)

    def exec_(self):
        """Shows the dialog and waits until it is closed.

        Returns the text of the option selected by the user, or None if
        the dialog is cancelled.

        """
        result = super(NewStudentDialog, self).exec_()
        if result == QDialog.Accepted:
            NewStudentDialog._last_combo_value = self.combo.currentIndex()
            email = unicode(self.email_field.text())
            if not email:
                email = None
            if self.combo.currentIndex() == 0:
                # First name, last name
                student = utils.Student(None, unicode(self.id_field.text()),
                                        None,
                                        unicode(self.name_field.text()),
                                        unicode(self.surname_field.text()),
                                        email, 0, None)
            else:
                # Full name
                student = utils.Student(None, unicode(self.id_field.text()),
                                        unicode(self.full_name_field.text()),
                                        None,
                                        None,
                                        email, 0, None)
        else:
            student = None
        return student

    def _check_values(self):
        if (self.id_field.hasAcceptableInput()
            and (not self.email_field.text()
                 or self.email_field.hasAcceptableInput())):
            self.buttons.button(QDialogButtonBox.Ok).setEnabled(True)
        else:
            self.buttons.button(QDialogButtonBox.Ok).setEnabled(False)

    def _update_combo(self, new_index):
        if new_index == 0:
            self.name_field.setEnabled(True)
            self.surname_field.setEnabled(True)
            self.full_name_field.setEnabled(False)
            self.name_label.setEnabled(True)
            self.surname_label.setEnabled(True)
            self.full_name_label.setEnabled(False)
            self.full_name_field.setText('')
        else:
            self.name_field.setEnabled(False)
            self.surname_field.setEnabled(False)
            self.full_name_field.setEnabled(True)
            self.name_label.setEnabled(False)
            self.surname_label.setEnabled(False)
            self.full_name_label.setEnabled(True)
            self.name_field.setText('')
            self.surname_field.setText('')


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
        self.score = widgets.InputScore(parent=self)
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

        `capture_context` is the detection.ExamCaptureContext object
        to be used.

        """
        super(DialogCameraSelection, self).__init__(parent)
        self.capture_context = capture_context
        self.setWindowTitle(_('Select a camera'))
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        self.camview = widgets.CamView((320, 240), self, border=True)
        self.label = QLabel(self)
        self.button = QPushButton(_('Try this camera'))
        self.camera_selector = QSpinBox(self)
        container = widgets.LineContainer(self, self.camera_selector,
                                          self.button)
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
    _tuple_strcoll = staticmethod(lambda x, y: locale.strcoll(x[0], y[0]))

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
             (c) 2010-2015 Jesús Arias Fisteus and contributors<br>
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
             """).format(utils.resource_path('logo.svg'),
                         utils.program_name,
                         utils.version,
                         utils.web_location,
                         utils.source_location)
        label = QLabel(text)
        label.setOpenExternalLinks(True)
        label.setTextInteractionFlags((Qt.LinksAccessibleByKeyboard
                                       | Qt.LinksAccessibleByMouse
                                       | Qt.TextBrowserInteraction
                                       | Qt.TextSelectableByKeyboard
                                       | Qt.TextSelectableByMouse))
        return label

    def _create_developers_tab(self):
        text = u"""<p><b>{0}:</b></p>
                   <ul><li>Jesús Arias Fisteus</li></ul>
                   <p><b>{1}:</b></p>
                   <ul><li>Jonathan Araneda Labarca</li></ul>
                   <p><b>{2}:</b></p>
                   <ul><li>Rodrigo Argüello</li></ul>
                   """.format(_('Lead developers'),
                              _('Exam configuration dialogs'),
                              _('Manuscript digits recognition'))
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
        for language, names in sorted(translators,
                                      cmp=DialogAbout._tuple_strcoll):
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
