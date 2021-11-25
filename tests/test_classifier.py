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
import os
import unittest

import numpy as np

import eyegrade.ocr.sample as sample
import eyegrade.ocr.classifiers as classifiers


class TestClassifier(unittest.TestCase):
    def _get_test_file_path(self, filename):
        dirname = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(dirname, filename)

    def test_classify_digit(self):
        image_path = self._get_test_file_path("digit.png")
        corners = np.array([[0, 1], [19, 0], [0, 7], [21, 17]])
        samp = sample.Sample(corners, image_filename=image_path)
        classifier = classifiers.DefaultDigitClassifier()
        label = classifier.classify(samp)
        self.assertTrue(label in range(10))

    def test_classify_cross(self):
        image_path = self._get_test_file_path("cross.png")
        corners = np.array([[0, 0], [27, 0], [1, 32], [29, 32]])
        samp = sample.Sample(corners, image_filename=image_path)
        classifier = classifiers.DefaultCrossesClassifier()
        label = classifier.classify(samp)
        self.assertTrue(label == 0 or label == 1)
