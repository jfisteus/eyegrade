# Eyegrade: grading multiple choice questions with a webcam
# Copyright (C) 2015 Rodrigo Arguello
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

import cv2
import numpy as np

SZ = 28 #image size

def deskew(image):
    """Deskew an image.

    It improves classifier performance.
    The image must be a cv2 image.

    """
    affine_flags = cv2.WARP_INVERSE_MAP | cv2.INTER_LINEAR
    m = cv2.moments(image)
    if abs(m['mu02']) < 1e-2:
        return image.copy()
    skew = m['mu11'] / m['mu02']
    M = np.float32([[1, skew, -0.5 * SZ * skew], [0, 1, 0]])
    image = cv2.warpAffine(image, M, (SZ, SZ), flags=affine_flags)
    return image

def clear_boundbox(image):
    """Clear the blank surrounding area of an image.

    It improves classifier performance.
    The image must be a cv2 image.

    """
    top = 0
    bot = image.shape[0]
    right = image.shape[1]
    left = 0
    it = 0
    for index, row in enumerate(image):
        if (not np.all(row==0)) and it == 0:
            if not np.all(image[index + 1] == 0):
                top = index
                it = 1
        elif np.all(row == 0) and it == 1:
            bot = index
            break
    it = 0
    for index, col in enumerate(image.T):
        if (not np.all(col == 0)) and it == 0:
            if not np.all(image.T[index + 2] == 0):
                left = index
                it = 1
        elif np.all(col == 0) and it == 1:
            right = index
            break
    cleared_image = image[top:bot, left:right]
    return cleared_image

def image_preprocessing(image):
    """Preprocesses the image of a digit.

    Returns a numpy feature vector ready to be introduced
    to train the classifier.

    The function receives a cv2 image.

    """
    image = deskew(image)
    image = clear_boundbox(image)
    image = cv2.resize(image, (SZ, SZ))
    image_matrix = np.array(image, np.float32)/255.0
    feature_vector = image_matrix.reshape(SZ*SZ,)
    return feature_vector


## import matplotlib.pyplot as plt
## def draw(matrix1, matrix2 = None):
##     plt.subplot(2, 4, 1)
##     plt.axis('off')
##     plt.imshow(matrix1, cmap=plt.cm.gray_r, interpolation='nearest')
##     if matrix2 != None:
##         plt.subplot(2, 4, 2)
##         plt.axis('off')
##         plt.imshow(matrix2, cmap=plt.cm.gray_r, interpolation='nearest')
##     plt.show()
