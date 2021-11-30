# Eyegrade: grading multiple choice questions with a webcam
# Copyright (C) 2010-2021 Jesus Arias Fisteus
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
import locale

from PyQt5.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QComboBox,
)

from PyQt5.QtCore import QTimer, Qt, pyqtSignal

from . import widgets
from .. import utils
from .. import detection

t = gettext.translation("eyegrade", utils.locale_dir(), fallback=True)
_ = t.gettext


class DialogComputeScores(QDialog):
    """Dialog to set the parameters to compute scores automatically.

    Example (replace `parent` by the parent widget):

    dialog = DialogComputeScores(parent)
    max_score, penalize = dialog.exec_()

    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("Compute default scores"))
        layout = QFormLayout()
        self.setLayout(layout)
        self.score = widgets.InputScore(parent=self)
        self.penalize = QCheckBox(_("Penalize incorrect answers"), self)
        buttons = QDialogButtonBox((QDialogButtonBox.Ok | QDialogButtonBox.Cancel))
        layout.addRow(_("Maximum score"), self.score)
        layout.addRow(_("Penalizations"), self.penalize)
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
            result = super().exec_()
            if result == QDialog.Accepted:
                if self.score.text():
                    score = self.score.value()
                    if score is not None and score > 0:
                        penalize = self.penalize.checkState() == Qt.Checked
                        success = True
                if not success:
                    QMessageBox.critical(self, _("Error"), _("Enter a valid score."))
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
        super().__init__(parent)
        self.capture_context = capture_context
        self.setWindowTitle(_("Select a camera"))
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        self.camview = widgets.CamView((320, 240), self, border=True)
        self.label = QLabel(self)
        self.button = QPushButton(_("Try this camera"))
        self.camera_selector = QSpinBox(self)
        container = widgets.LineContainer(self, self.camera_selector, self.button)
        self.flip_combo = QComboBox(parent=self)
        self.flip_combo.addItem(_("No"))
        self.flip_combo.addItem(_("Horizontally"))
        self.flip_combo.addItem(_("Vertically"))
        self.flip_combo.addItem(_("Both axes"))
        self._init_flip_combo()
        flip_container = widgets.LineContainer(
            self, QLabel(_("Flip image")), self.flip_combo
        )
        self.button.clicked.connect(self._select_camera)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(self.accept)
        self.flip_combo.currentIndexChanged.connect(self._flip_changed)
        layout.addWidget(self.camview)
        layout.addWidget(self.label)
        layout.addWidget(container)
        layout.addWidget(flip_container)
        layout.addWidget(buttons)
        self.camera_error.connect(self._show_camera_error, type=Qt.QueuedConnection)
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
        return super().exec_()

    def _show_camera_error(self):
        QMessageBox.critical(
            self,
            _("Camera not available"),
            _("Eyegrade has not detected any camera in your system."),
        )
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
                    QMessageBox.critical(
                        self,
                        _("Camera not available"),
                        _("Camera {0} is not available.").format(new_camera),
                    )
                else:
                    self.flip_combo.setCurrentIndex(0)

    def _update_camera_label(self):
        camera_id = self.capture_context.current_camera_id()
        if camera_id is not None and camera_id >= 0:
            self.label.setText(
                _("<center>Viewing camera: {0}</center>").format(camera_id)
            )
            self.camera_selector.setValue(camera_id)
        else:
            self.label.setText(_("<center>No camera</center>"))

    def _flip_changed(self, index):
        if index == 0:
            transformation = detection.ImageTransformer.IDENTITY
        elif index == 1:
            transformation = detection.ImageTransformer.FLIP_H
        elif index == 2:
            transformation = detection.ImageTransformer.FLIP_V
        elif index == 3:
            transformation = detection.ImageTransformer.FLIP_BOTH
        self.capture_context.image_transformer = detection.ImageTransformer(
            transformation
        )

    def _init_flip_combo(self):
        transformation = self.capture_context.image_transformer.transformation
        if transformation == detection.ImageTransformer.IDENTITY:
            self.flip_combo.setCurrentIndex(0)
        elif transformation == detection.ImageTransformer.FLIP_H:
            self.flip_combo.setCurrentIndex(1)
        elif transformation == detection.ImageTransformer.FLIP_V:
            self.flip_combo.setCurrentIndex(2)
        elif transformation == detection.ImageTransformer.FLIP_BOTH:
            self.flip_combo.setCurrentIndex(3)

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

    _tuple_strxfrm = staticmethod(lambda x: locale.strxfrm(x[0]))

    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle(_("About"))
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(self.accept)
        tabs = QTabWidget(parent)
        tabs.setDocumentMode(True)
        tabs.addTab(self._create_about_tab(), _("About"))
        tabs.addTab(self._create_developers_tab(), _("Developers"))
        tabs.addTab(self._create_translators_tab(), _("Translators"))
        layout.addWidget(tabs)
        layout.addWidget(buttons)

    def _create_about_tab(self):
        text = _(
            u"""
             <center>
             <p><img src='{0}' width='64'> <br>
             {1} {2} <br>
             (c) 2010-2021 Jesús Arias Fisteus and contributors<br>
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
             <a href='https://www.gnu.org/licenses/gpl.txt'>
             https://www.gnu.org/licenses/gpl.txt</a>.
             </p>
             </center>
             """
        ).format(
            utils.resource_path("logo.svg"),
            utils.program_name,
            utils.version,
            utils.web_location,
            utils.source_location,
        )
        label = QLabel(text)
        label.setOpenExternalLinks(True)
        label.setTextInteractionFlags(
            (
                Qt.LinksAccessibleByKeyboard
                | Qt.LinksAccessibleByMouse
                | Qt.TextBrowserInteraction
                | Qt.TextSelectableByKeyboard
                | Qt.TextSelectableByMouse
            )
        )
        return label

    def _create_developers_tab(self):
        text = u"""<p><b>{0}:</b></p>
                   <ul><li>Jesús Arias Fisteus</li></ul>
                   <p><b>{1}:</b></p>
                   <ul><li>Jonathan Araneda Labarca</li></ul>
                   <p><b>{2}:</b></p>
                   <ul><li>Rodrigo Argüello</li></ul>
                   <p><b>{3}:</b></p>
                   <ul><li>Roberto González</li></ul>
                   """.format(
            _("Lead developers"),
            _("Exam configuration dialogs"),
            _("Manuscript digits recognition"),
            _("Testing and other contributions"),
        )
        label = QLabel(text)
        label.setTextInteractionFlags(
            (
                Qt.LinksAccessibleByKeyboard
                | Qt.LinksAccessibleByMouse
                | Qt.TextBrowserInteraction
                | Qt.TextSelectableByKeyboard
                | Qt.TextSelectableByMouse
            )
        )
        scroll_area = QScrollArea(self.parent())
        scroll_area.setWidget(label)
        return scroll_area

    def _create_translators_tab(self):
        translators = [
            (_("Catalan"), [u"Jaume Barcelo"]),
            (_("German"), []),
            (_("Galician"), [u"Jesús Arias Fisteus"]),
            (_("French"), []),
            (_("Portuguese"), []),
            (_("Spanish"), [u"Jesús Arias Fisteus"]),
        ]
        parts = []
        for language, names in sorted(translators, key=DialogAbout._tuple_strxfrm):
            if names:
                parts.append(u"<p><b>{0}:</b></p>".format(language))
                parts.append(u"<ul>")
                for name in names:
                    parts.append(u"<li>{0}</li>".format(name))
                parts.append(u"</ul>")
        label = QLabel(u"".join(parts))
        label.setTextInteractionFlags(
            (
                Qt.LinksAccessibleByKeyboard
                | Qt.LinksAccessibleByMouse
                | Qt.TextBrowserInteraction
                | Qt.TextSelectableByKeyboard
                | Qt.TextSelectableByMouse
            )
        )
        scroll_area = QScrollArea(self.parent())
        scroll_area.setWidget(label)
        return scroll_area
