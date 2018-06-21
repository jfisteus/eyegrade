# Eyegrade: grading multiple choice questions with a webcam
# Copyright (C) 2010-2018 Jesus Arias Fisteus
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


""" Compatibility module to detect OpenCV version"""


import cv2

from . import utils


def _check_version():
    version = cv2.__version__
    if version.startswith('2.4'):
        mode = 2
    elif version.startswith('3.'):
        mode = 3
    else:
        raise utils.EyegradeException(
            'Unsupported OpenCV version: {}'.format(version))
    return mode

cv_mode = _check_version()
