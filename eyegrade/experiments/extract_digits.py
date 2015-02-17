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
from __future__ import print_function, division

import sys
import random

# Import the cv module. It might be cv2.cv in newer versions.
try:
    import cv
except ImportError:
    import cv2.cv as cv

from .. import sessiondb
from .. import imageproc
from .. import capture
from .. import ocr


class LabeledDigit(object):

    def __init__(self, digit, image_file, cell_geometry, identifier=None):
        self.digit = digit
        self.image_file = image_file
        self.cell_geometry = cell_geometry
        if identifier is not None:
            self.identifier = identifier
        else:
            self.identifier = random.randint(0, 1000000000000)

    def __str__(self):
        data = [
            self.image_file, str(self.digit),
            str(self.cell_geometry.plu[0]), str(self.cell_geometry.plu[1]),
            str(self.cell_geometry.pru[0]), str(self.cell_geometry.pru[1]),
            str(self.cell_geometry.pld[0]), str(self.cell_geometry.pld[1]),
            str(self.cell_geometry.prd[0]), str(self.cell_geometry.prd[1]),
        ]
        return '\t'.join(data)

    def crop(self):
        original = imageproc.load_image(self.image_file)
        pre_processed = imageproc.pre_process(original)
        plu, pru, pld, prd = ocr.adjust_cell_corners(pre_processed,
                                                     (self.cell_geometry.plu,
                                                      self.cell_geometry.pru,
                                                      self.cell_geometry.pld,
                                                      self.cell_geometry.prd))
        total, active = imageproc.count_pixels_in_cell(pre_processed,
                                                       plu, pru, pld, prd)
        if (active / total >= 0.01):
            min_x = min(plu[0], pld[0])
            max_x = max(pru[0], prd[0])
            min_y = min(plu[1], pru[1])
            max_y = max(pld[1], prd[1])
            offset_x = min_x
            offset_y = min_y
            width = max_x - offset_x
            height = max_y - offset_y
            cropped = cv.CreateImage((width, height), pre_processed.depth, 1)
            region = cv.GetSubRect(pre_processed,
                                   (offset_x, offset_y, width, height))
            cv.Copy(region, cropped)
            cropped_file_path = 'digit-{0}-{1}.png'.format(self.digit,
                                                           self.identifier)
            imageproc.save_image(cropped_file_path, cropped)
            new_geometry = capture.CellGeometry(
                (plu[0] - offset_x, plu[1] - offset_y),
                (pru[0] - offset_x, pru[1] - offset_y),
                (pld[0] - offset_x, pld[1] - offset_y),
                (prd[0] - offset_x, prd[1] - offset_y),
                None, None
            )
            cropped_digit = LabeledDigit(self.digit, cropped_file_path,
                                         new_geometry,
                                         identifier=self.identifier)
        else:
            cropped_digit = None
        return cropped_digit


def process_session(labeled_digits, session_path):
    session = sessiondb.SessionDB(session_path)
    for exam in session.exams_iterator():
        image_file = session.get_raw_capture_path(exam['exam_id'])
        cells = session._read_id_cells(exam['exam_id'])
        if exam['student_id'] and len(exam['student_id']) == len(cells):
            for digit, cell in zip(exam['student_id'], cells):
                labeled_digit = LabeledDigit(int(digit), image_file, cell)
                cropped_digit = labeled_digit.crop()
                if cropped_digit is not None:
                    labeled_digits[int(digit)].append(cropped_digit)
    session.close()


def dump_digit_list(labeled_digits):
    with open('digits.txt', 'a') as f:
        for digit in range(10):
            for labeled_digit in labeled_digits[digit]:
                print(str(labeled_digit), file=f)

def _initialize_digits_dict():
    labeled_digits = {}
    for i in range(10):
        labeled_digits[i] = []
    return labeled_digits

def main():
    labeled_digits = _initialize_digits_dict()
    for session_path in sys.argv[1:]:
        process_session(labeled_digits, session_path)
    dump_digit_list(labeled_digits)

if __name__ == '__main__':
    main()
