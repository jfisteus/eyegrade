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

import gettext

# Try PyQt5 first, and then PyQt4 if it fails
try:
    from PyQt5.QtGui import QColor
except ImportError:
    from PyQt4.QtGui import QColor

from .. import utils

t = gettext.translation('eyegrade', utils.locale_dir(), fallback=True)
_ = t.ugettext

class FileNameFilters(object):
    exam_config = _('Exam configuration (*.eye)')
    session_db = _('Eyegrade session (*.eyedb)')
    student_list = _('Student list (*.csv *.tsv *.txt *.lst *.list)')

class Colors(object):
    eyegrade_blue = QColor(32, 73, 124)
