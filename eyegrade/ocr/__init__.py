# Eyegrade: grading multiple choice questions with a webcam
# Copyright (C) 2010-2015 Rodrigo Arguello, Jesus Arias Fisteus
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

# OCR for hand-written digits
#
import cv2
import numpy as np

# Import the cv module. It might be cv2.cv in newer versions.
try:
    import cv
except ImportError:
    import cv2.cv as cv

from . import preprocessing
from .. import geometry as g
from .. import utils

param_cell_margin = 2

# Load the classifier
classifier = cv2.SVM()
classifier.load(utils.resource_path('svm/ocr_svm.dat.gz'))


# Main module function (classify an image with a hand-written digit)
def digit_ocr(image, cell_corners, debug = None, image_drawn = None):
    assert(not debug or image_drawn is not None)
    subimage = crop_digit(image, cell_corners)
    as_vector = preprocessing.image_preprocessing(np.asarray(subimage[:,:]))
    prediction = int(classifier.predict(as_vector))
    weights = [0.0] * 10
    weights[prediction] = 1.0
    return (prediction, weights)

def adjust_cell_corners(image, corners):
    plu, pru, pld, prd = corners
    plu = adjust_cell_corner(image, plu, prd)
    prd = adjust_cell_corner(image, prd, plu)
    pru = adjust_cell_corner(image, pru, pld)
    pld = adjust_cell_corner(image, pld, pru)
    return(plu, pru, pld, prd)

def adjust_cell_corner(image, corner, towards_corner):
    margin = None
    for x, y in g.walk_line_ordered(corner, towards_corner):
        if margin is None:
            if image[y, x] == 0:
                margin = param_cell_margin
        else:
            margin -= 1
            if margin == 0:
                return (x, y)
    # In case of failure, return the original point
    return corner

def crop_digit(image, cell_corners):
    points = adjust_cell_corners(image, cell_corners)
    plu, pru, pld, prd = points
    min_x = min(plu[0], pld[0])
    max_x = max(pru[0], prd[0])
    min_y = min(plu[1], pru[1])
    max_y = max(pld[1], prd[1])
    offset_x = min_x
    offset_y = min_y
    width = max_x - offset_x
    height = max_y - offset_y
    cropped = cv.CreateImage((width, height), image.depth, 1)
    region = cv.GetSubRect(image, (offset_x, offset_y, width, height))
    cv.Copy(region, cropped)
    return cropped
