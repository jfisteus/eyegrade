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

from PyQt5.QtGui import QColor

from .. import utils

t = gettext.translation("eyegrade", utils.locale_dir(), fallback=True)
_ = t.gettext


class FileNameFilters:
    exam_config = _("Exam configuration (*.eye)")
    session_db = _("Eyegrade session (*.eyedb)")
    student_list = _("Student list (*.xlsx *.csv *.tsv *.txt *.lst *.list)")
    xlsx_file = _("Excel spreadsheet (*.xlsx)")
    csv_file = _("Data file (*.csv *.tsv)")


class Colors:
    eyegrade_blue = QColor(32, 73, 124)
