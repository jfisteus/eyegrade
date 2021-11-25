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

import eyegrade.detection as detection


class _MockExamDetector(detection.ExamDetector):
    def __init__(self, dimensions):
        self.dimensions = dimensions
        self.status = {
            "lines": False,
            "boxes": False,
            "cells": False,
            "infobits": False,
            "id-box-hlines": False,
            "id-box": False,
        }
        self.success = False
        self.options = detection.ExamDetector.default_options
        self.image_to_show = None
        self.image_proc = None

    def _decide_cells(self, answer_cells):
        return None


def _mock_read_infobits(image, corner_matrixes):
    return [False, True, False, False, False, True]


detection.read_infobits = _mock_read_infobits


class TestDetection(unittest.TestCase):
    def _get_test_file_path(self, filename):
        dirname = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(dirname, filename)

    def test_detect_capture(self):
        image_path = self._get_test_file_path("capture.png")
        options = detection.ExamDetector.get_default_options()
        options["capture-from-file"] = True
        options["capture-raw-file"] = image_path
        dimensions = ((3, 5),)
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
        image_path = self._get_test_file_path("capture.png")
        options = detection.ExamDetector.get_default_options()
        options["capture-from-file"] = True
        options["capture-raw-file"] = image_path
        options["read-id"] = True
        options["id-num-digits"] = 9
        dimensions = ((3, 5),)
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

    def test_manual_detection(self):
        manual_points = [
            (113, 125),
            (251, 117),
            (304, 115),
            (447, 106),
            (117, 332),
            (259, 325),
            (312, 323),
            (458, 317),
        ]
        dimensions = [(3, 5), (3, 5)]
        detector = _MockExamDetector(dimensions)
        self.assertTrue(detector.detect_manual(manual_points))
        self.assertTrue(detector.success)
        corner_matrixes = detection.process_box_corners(manual_points, dimensions)
        # There are two answer boxes
        self.assertEqual(len(corner_matrixes), 2)
        # There are 5 + 1 = 6 lines in each answer box
        self.assertEqual(len(corner_matrixes[0]), 6)
        self.assertEqual(len(corner_matrixes[1]), 6)
        for box in corner_matrixes:
            for line in box:
                # There are 3 + 1 = 4 points in each line
                self.assertEqual(len(line), 4)
                for point in line:
                    self.assertEqual(len(point), 2)
        # Manual points are in the proper places:
        box_1, box_2 = corner_matrixes
        self.assertEqual(box_1[0][0], manual_points[0])
        self.assertEqual(box_1[0][3], manual_points[1])
        self.assertEqual(box_1[5][0], manual_points[4])
        self.assertEqual(box_1[5][3], manual_points[5])
        self.assertEqual(box_2[0][0], manual_points[2])
        self.assertEqual(box_2[0][3], manual_points[3])
        self.assertEqual(box_2[5][0], manual_points[6])
        self.assertEqual(box_2[5][3], manual_points[7])
        # Reordering points should have no effect:
        manual_points[1], manual_points[5] = manual_points[5], manual_points[1]
        manual_points[0], manual_points[4] = manual_points[4], manual_points[0]
        manual_points[3], manual_points[7] = manual_points[7], manual_points[3]
        self.assertTrue(detector.detect_manual(manual_points))
        corner_matrixes_2 = detection.process_box_corners(manual_points, dimensions)
        self.assertEqual(corner_matrixes, corner_matrixes_2)
