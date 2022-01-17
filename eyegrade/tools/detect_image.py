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
# <https://www.gnu.org/licenses/>.
#

import argparse

from .. import utils
from .. import detection
from .. import capture


def _cmd_options():
    parser = argparse.ArgumentParser(description="Process a single image from file.")
    parser.add_argument(
        "dimensions", help='Answer box dimensions spec. (e.g. "3,5;3,5")'
    )
    parser.add_argument("image", help="Filename of the image")
    parser.add_argument(
        "-t",
        "--hough-threshold",
        dest="hough_threshold",
        type=int,
        default=200,
        help="Hough threshold",
    )
    parser.add_argument(
        "-l",
        "--draw-lines-to",
        dest="draw_lines_to",
        type=str,
        default=None,
        help=("Write the image with the detected lines " "to the given file"),
    )
    parser.add_argument(
        "-p",
        "--save-image-proc-to",
        dest="image_proc_to",
        type=str,
        default=None,
        help="Write the processed image to the given file",
    )
    parser.add_argument(
        "-i",
        "--id-num-digits",
        dest="id_num_digits",
        type=int,
        default=0,
        help=("Detect student id with the given " "number of digits"),
    )
    return parser.parse_args()


def main():
    args = _cmd_options()
    context = detection.ExamDetectorContext(fixed_hough_threshold=args.hough_threshold)
    options = detection.ExamDetector.get_default_options()
    options["capture-from-file"] = True
    options["capture-raw-file"] = args.image
    if args.draw_lines_to is not None:
        options["show-lines"] = True
    if args.id_num_digits:
        options["read-id"] = True
        options["id-num-digits"] = 9
    dimensions, _ = utils.parse_dimensions(args.dimensions)
    detector = detection.ExamDetector(dimensions, context, options)
    success = detector.detect()
    if success:
        print("Detection succeeded :)")
    else:
        print("Detection failed :(")
        print(detector.status)
    if args.draw_lines_to is not None:
        detector.capture.save_image_drawn(args.draw_lines_to)
    if args.image_proc_to:
        capture.save_image(args.image_proc_to, detector.image_proc)


if __name__ == "__main__":
    main()
