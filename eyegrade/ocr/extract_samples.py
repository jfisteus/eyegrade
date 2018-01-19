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
import argparse

import numpy as np
import cv2

from .. import sessiondb
from .. import images
from . import sample


class LabeledSample(object):
    TYPE_DIGIT = 1
    TYPE_CROSS = 2
    TYPES = (TYPE_DIGIT, TYPE_CROSS)

    def __init__(self, sample_type, label, image_file,
                 corners=None, identifier=None):
        if not sample_type in self.TYPES:
            raise ValueError('Wrong sample type: {}'.format(sample_type))
        self.sample_type = sample_type
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
        if self.sample_type == self.TYPE_DIGIT:
            samp = sample.DigitSampleFromCam(self.corners, original,
                                             proc_image)
        else:
            samp = sample.CrossSampleFromCam(self.corners, original,
                                             proc_image)
        cropped_file_path = 'sample-{}-{:013d}.png'.format(self.label,
                                                           self.identifier)
        cv2.imwrite(cropped_file_path, samp.image)


class LabeledDigit(LabeledSample):
    def __init__(self, label, image_file, corners=None, identifier=None):
        if label < 0 or label > 9:
            raise ValueError('Label out of range: {}'.format(label))
        super(LabeledDigit, self).__init__(
            LabeledSample.TYPE_DIGIT, label, image_file,
            corners=corners, identifier=identifier)


class LabeledCross(LabeledSample):
    def __init__(self, label, image_file, corners=None, identifier=None):
        if label < 0 or label > 1:
            raise ValueError('Label out of range: {}'.format(label))
        super(LabeledCross, self).__init__(
            LabeledSample.TYPE_CROSS, label, image_file,
            corners=corners, identifier=identifier)

def process_session_crosses(session_path):
    logging.info('Processing session {}'.format(session_path))
    session = sessiondb.SessionDB(session_path)
    for exam in session.exams_iterator():
        image_file = session.get_raw_capture_path(exam['exam_id'])
        all_cells = session._read_answer_cells(exam['exam_id'])
        answers = session.read_answers(exam['exam_id'])
        for cells, answer in zip(all_cells, answers):
            crosses = [LabeledCross(0, image_file,
                                    np.array([cell.plu, cell.pru,
                                              cell.pld, cell.prd]))
                       for cell in cells]
            if answer > 0:
                crosses[answer - 1].label = 1
            for cross in crosses:
                cross.save()
    session.close()

def process_session_digits(session_path):
    logging.info('Processing session {}'.format(session_path))
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

def _parse_args():
    parser = argparse.ArgumentParser(description='Extract OCR samples.')
    parser.add_argument('classifier',
            help='type of samples to be extracted ("digits" or "crosses")')
    parser.add_argument('sessions', metavar='sessions', nargs='+',
            help='session directories')
    return parser.parse_args()

def main():
    logging.basicConfig(level=logging.INFO)
    args = _parse_args()
    if args.classifier == 'digits':
        for session_path in args.sessions:
            process_session_digits(session_path)
    elif args.classifier == 'crosses':
        for session_path in args.sessions:
            process_session_crosses(session_path)
    else:
        print('Wrong classifier type: {}'.format(args.classifier))
        sys.exit(1)


if __name__ == '__main__':
    main()
