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

VALID_LABELS = (0, 1)


class LabeledCross:
    def __init__(self, label, image_file, corners, identifier=None):
        if not label in VALID_LABELS:
            raise ValueError("Wrong label value")
        self.label = label
        self.image_file = image_file
        self.corners = corners
        if identifier is not None:
            self.identifier = identifier
        else:
            self.identifier = random.randint(0, 100000000000000)

    def __str__(self):
        data = [self.image_file, str(self.label)]
        data.extend(str(n) for n in self.corners.reshape(8).tolist())
        return "\t".join(data)

    def crop(self):
        original = images.load_image(self.image_file)
        pre_processed = np.asarray(detection.pre_process(original)[:, :])
        samp = sample.CrossSampleFromCam(self.corners, pre_processed)
        cropped = samp.crop()
        cropped_file_path = "cross-{0}-{1}.png".format(self.label, self.identifier)
        cv2.imwrite(cropped_file_path, cropped.image)
        cropped_cross = LabeledCross(
            self.label, cropped_file_path, cropped.corners, identifier=self.identifier
        )
        return cropped_cross


def process_session(labeled_crosses, session_path):
    session = sessiondb.SessionDB(session_path)
    for exam in session.exams_iterator():
        image_file = session.get_raw_capture_path(exam["exam_id"])
        all_cells = session._read_answer_cells(exam["exam_id"])
        answers = session.read_answers(exam["exam_id"])
        for cells, answer in zip(all_cells, answers):
            crosses = [
                LabeledCross(
                    0, image_file, np.array([cell.plu, cell.pru, cell.pld, cell.prd])
                )
                for cell in cells
            ]
            if answer > 0:
                crosses[answer - 1].label = 1
            for cross in crosses:
                cropped_cross = cross.crop()
                if cropped_cross is not None:
                    labeled_crosses[cropped_cross.label].append(cropped_cross)
    session.close()


def dump_cross_list(labeled_crosses):
    with open("crosses.txt", "a") as f:
        for label in VALID_LABELS:
            for labeled_cross in labeled_crosses[label]:
                print(str(labeled_cross), file=f)


def _initialize_crosses_dict():
    labeled_crosses = {}
    for label in VALID_LABELS:
        labeled_crosses[label] = []
    return labeled_crosses


def main():
    logging.basicConfig(level=logging.INFO)
    labeled_crosses = _initialize_crosses_dict()
    for session_path in sys.argv[1:]:
        logging.info("Processing session {}".format(session_path))
        process_session(labeled_crosses, session_path)
    dump_cross_list(labeled_crosses)


if __name__ == "__main__":
    main()
