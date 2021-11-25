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
# <http://www.gnu.org/licenses/>.
#

import unittest
import os.path

import eyegrade.exams as exams


class TestExamConfig(unittest.TestCase):
    def _get_test_file_path(self, filename):
        dirname = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(dirname, filename)

    def test_variations(self):
        exam_config = exams.ExamConfig(
            filename=self._get_test_file_path("test-variations.eye")
        )
        self.assertEqual(exam_config.variations["A"], [0, 0, 0, 0, 0])
        self.assertEqual(exam_config.variations["B"], [2, 1, 1, 2, 0])
