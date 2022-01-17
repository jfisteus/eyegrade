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
# <https://www.gnu.org/licenses/>.
#
import sys
import random
import logging

import numpy as np
import cv2

from .. import sessiondb
from .. import detection
from .. import images
from ..ocr import sample


class LabeledDigit:
    def __init__(self, digit, image_file, corners, identifier=None):
        self.digit = digit
        self.image_file = image_file
        self.corners = corners
        if identifier is not None:
            self.identifier = identifier
        else:
            self.identifier = random.randint(0, 1000000000000)

    def __str__(self):
        data = [self.image_file, str(self.digit)]
        data.extend(str(n) for n in self.corners.reshape(8).tolist())
        return "\t".join(data)

    def crop(self):
        original = images.load_image(self.image_file)
        pre_processed = np.asarray(detection.pre_process(original)[:, :])
        samp = sample.DigitSampleFromCam(self.corners, pre_processed)
        cropped = samp.crop()
        total = cropped.image.shape[0] * cropped.image.shape[1]
        active = sum(sum(cropped.image > 0))
        if active / total >= 0.01:
            cropped_file_path = "digit-{0}-{1}.png".format(self.digit, self.identifier)
            cv2.imwrite(cropped_file_path, cropped.image)
            cropped_digit = LabeledDigit(
                self.digit,
                cropped_file_path,
                cropped.corners,
                identifier=self.identifier,
            )
        else:
            cropped_digit = None
        return cropped_digit


def process_session(labeled_digits, session_path):
    session = sessiondb.SessionDB(session_path)
    for exam in session.exams_iterator():
        image_file = session.get_raw_capture_path(exam["exam_id"])
        cells = session._read_id_cells(exam["exam_id"])
        if exam["student_id"] and len(exam["student_id"]) == len(cells):
            for digit, cell in zip(exam["student_id"], cells):
                corners = np.array([cell.plu, cell.pru, cell.pld, cell.prd])
                labeled_digit = LabeledDigit(int(digit), image_file, corners)
                cropped_digit = labeled_digit.crop()
                if cropped_digit is not None:
                    labeled_digits[int(digit)].append(cropped_digit)
    session.close()


def dump_digit_list(labeled_digits):
    with open("digits.txt", "a") as f:
        for digit in range(10):
            for labeled_digit in labeled_digits[digit]:
                print(str(labeled_digit), file=f)


def _initialize_digits_dict():
    labeled_digits = {}
    for i in range(10):
        labeled_digits[i] = []
    return labeled_digits


def main():
    logging.basicConfig(level=logging.INFO)
    labeled_digits = _initialize_digits_dict()
    for session_path in sys.argv[1:]:
        logging.info("Processing session {}".format(session_path))
        process_session(labeled_digits, session_path)
    dump_digit_list(labeled_digits)


if __name__ == "__main__":
    main()
