# Eyegrade: grading multiple choice questions with a webcam
# Copyright (C) 2010-2011 Jesus Arias Fisteus
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

import sys

from .. import imageproc
from .. import ocr

class Digit(object):
    def __init__(self, image_path, position, correct_digit,
                 plu, pru, pld, prd):
        self.image_path = image_path
        self.position = position
        self.correct_digit = correct_digit
        self.plu = plu
        self.pru = pru
        self.pld = pld
        self.prd = prd
        self.detected_digit = None
        self.scores = None

    def set_image(self, image):
        self.image = image

    def get_cell_corners(self):
        return (self.plu, self.pru, self.pld, self.prd)

    def get_success(self):
        assert self.detected_digit is not None
        if self.correct_digit == self.detected_digit:
            return 1
        else:
            return 0

    def get_failure(self):
        assert self.detected_digit is not None
        if self.correct_digit == self.detected_digit:
            return 0
        else:
            return 1

    def __str__(self):
        if self.detected_digit is not None:
            return '%s@%d: %d (detected %d)'%(self.image_path, self.position,
                                              self.correct_digit,
                                              self.detected_digit)
        else:
            return '%s@%d: %d (none detected)'%(self.image_path, self.position,
                                                self.correct_digit)
    @staticmethod
    def parse_digit(line):
        parts = [p.strip() for p in line.split('\t')]
        assert len(parts) == 11
        image_path = parts[0]
        correct_digit = int(parts[1])
        position = int(parts[2])
        plu = Digit.parse_point(parts[3])
        pru = Digit.parse_point(parts[4])
        pld = Digit.parse_point(parts[5])
        prd = Digit.parse_point(parts[6])
        return Digit(image_path, position, correct_digit, plu, pru, pld, prd)

    @staticmethod
    def parse_point(point_str):
        assert point_str[0] == '('
        assert point_str[-1] == ')'
        parts = [p.strip() for p in point_str[1:-1].split(',')]
        assert len(parts) == 2
        return (int(parts[0]), int(parts[1]))


def eval_digit(digit):
    decision, scores = ocr.digit_ocr(digit.image, digit.get_cell_corners())
    digit.scores = scores
    if decision is not None:
        digit.detected_digit = int(decision)
    else:
        digit.detected_digit = 0

def main():
    evaluated_digits = []
    with open(sys.argv[1], 'r') as file_:
        image = None
        last_image_path = None
        for line in file_:
            if line.strip() == '':
                continue
            digit = Digit.parse_digit(line)
            if digit.image_path == last_image_path:
                digit.set_image(image)
            else:
                image = imageproc.load_image_grayscale(digit.image_path)
                last_image_path = digit.image_path
                digit.set_image(image)
            eval_digit(digit)
            evaluated_digits.append(digit)
            print digit
    num_correct = sum([d.get_success() for d in evaluated_digits])
    print 'Decisions: %d; correct: %d; incorrect: %d; success_rate: %.4f'%\
        (len(evaluated_digits), num_correct,
         len(evaluated_digits) - num_correct,
         float(num_correct) / len(evaluated_digits))

if __name__ == '__main__':
    main()
