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
import os
import unittest

import eyegrade.detection as detection


class TestDetection(unittest.TestCase):

    def _get_test_file_path(self, filename):
        dirname = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(dirname, filename)

    def test_detect_capture(self):
        image_path = self._get_test_file_path('capture.png')
        options = detection.ExamDetector.get_default_options()
        options['capture-from-file'] = True
        options['capture-raw-file'] = image_path
        dimensions = ((3, 5), )
        for th in (170, 180, 190):
            context = detection.ExamDetectorContext(fixed_hough_threshold=th)
            detector = detection.ExamDetector(dimensions, context, options)
            success = detector.detect()
            if success:
                break
        self.assertTrue(success)
        self.assertEqual(len(detector.decisions.answers), 5)
        self.assertTrue(detector.decisions.answers[0] in range(4))
        self.assertTrue(detector.decisions.answers[1] in range(4))
        self.assertTrue(detector.decisions.answers[2] in range(4))
        self.assertTrue(detector.decisions.answers[3] in range(4))
        self.assertTrue(detector.decisions.answers[4] in range(4))
        self.assertEqual(len(detector.decisions.model), 1)

    def test_detect_capture_with_id(self):
        image_path = self._get_test_file_path('capture.png')
        options = detection.ExamDetector.get_default_options()
        options['capture-from-file'] = True
        options['capture-raw-file'] = image_path
        options['read-id'] = True
        options['id-num-digits'] = 9
        dimensions = ((3, 5), )
        for th in (170, 180, 190):
            context = detection.ExamDetectorContext(fixed_hough_threshold=th)
            detector = detection.ExamDetector(dimensions, context, options)
            success = detector.detect()
            if success:
                break
        self.assertTrue(success)
        self.assertEqual(len(detector.decisions.answers), 5)
        self.assertEqual(len(detector.decisions.detected_id), 9)
        self.assertEqual(len(detector.decisions.model), 1)
