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
from __future__ import print_function, division

import sys
import random
import logging

import numpy as np
import cv2

from .. import sessiondb
from .. import images
from . import sample


class LabeledSample(object):

    def __init__(self, label, image_file, corners=None, identifier=None):
        self.label = label
        self.image_file = image_file
        self.corners = corners
        if identifier is not None:
            self.identifier = identifier
        else:
            self.identifier = random.randint(0, 10000000000000)

    def __str__(self):
        data = [self.image_file, str(self.label)]
        return ','.join(data)

    def save(self):
        if self.corners is None:
            raise ValueError('Corners must be set in order to crop')
        original = images.load_image(self.image_file)
        proc_image = images.pre_process(original)
        samp = sample.DigitSampleFromCam(self.corners, original, proc_image)
        cropped_file_path = 'sample-{}-{:013d}.png'.format(self.label,
                                                           self.identifier)
        cv2.imwrite(cropped_file_path, samp.image)


def process_session(session_path):
    session = sessiondb.SessionDB(session_path)
    for exam in session.exams_iterator():
        image_file = session.get_raw_capture_path(exam['exam_id'])
        cells = session._read_id_cells(exam['exam_id'])
        if exam['student_id'] and len(exam['student_id']) == len(cells):
            for digit, cell in zip(exam['student_id'], cells):
                corners = np.array([cell.plu, cell.pru, cell.pld, cell.prd])
                labeled_digit = LabeledSample(int(digit), image_file,
                                              corners=corners)
                labeled_digit.save()
    session.close()

def _initialize_digits_dict():
    labeled_digits = {}
    for i in range(10):
        labeled_digits[i] = []
    return labeled_digits

def main():
    logging.basicConfig(level=logging.INFO)
    for session_path in sys.argv[1:]:
        logging.info('Processing session {}'.format(session_path))
        process_session(session_path)

if __name__ == '__main__':
    main()
