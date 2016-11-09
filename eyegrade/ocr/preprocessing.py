# Eyegrade: grading multiple choice questions with a webcam
# Copyright (C) 2015 Rodrigo Arguello, Jesus Arias Fisteus
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
from __future__ import division

import cv2
import numpy as np
import numpy.linalg as linalg

from .. import images


class FeatureExtractor(object):
    """Default feature extractor.

    It assumes that images contain just one digit
    and ignores image corners.

    """
    def __init__(self, dim=28):
        self.dim = dim

    def extract(self, sample):
        image = self.preprocess(sample)
        image_matrix = np.array(image, np.float32) / 255.0
        feature_vector = image_matrix.reshape(self.features_len, )
        return feature_vector

    def preprocess(self, sample):
        image = images.invert(images.rgb_to_gray(sample.image))
        image = images.clear_background(image)
        image = clear_boundbox(image, self.dim)
        image = resize(image, self.dim)
        return image

    @property
    def features_len(self):
        return self.dim * self.dim


## class NewFeatureExtractor(FeatureExtractor):
##     def __init__(self, **kwargs):
##         super(NewFeatureExtractor, self).__init__(**kwargs)

##     def preprocess(self, sample):
##         image = self._reshape(sample)
##         image = images.erode_dilate(image)
##         image = deskew(image, self.dim)
##         image = cv2.resize(image, (self.dim, self.dim))
##         return image


class CrossesFeatureExtractor(FeatureExtractor):
    """Feature extractor for crosses.

    """
    def __init__(self, dim=28):
        super(CrossesFeatureExtractor, self).__init__(dim=dim)

    def preprocess(self, sample):
        image = images.pre_process(sample.image)
        image = clear_boundbox(image, self.dim)
        image = resize(image, self.dim)
        return image

    ## def preprocess(self, sample):
    ##     image = images.pre_process(sample.image)
    ##     image = clear_boundbox(image, self.dim)
    ##     image = resize(image, self.dim)
    ##     return image


class OpenCVExampleExtractor(object):
    def __init__(self, dim=20, threshold=False):
        self.dim = dim
        self.threshold = threshold
        self._corners_dst = np.array([[0, 0],
                                      [dim - 1, 0],
                                      [0, dim - 1],
                                      [dim - 1, dim - 1]],
                                     dtype='float32')
        self.features_len = 64

    def extract(self, sample):
        corners = np.array(sample.corners, dtype='float32')
        h = cv2.findHomography(corners, self._corners_dst)
        image = cv2.warpPerspective(sample.image, h[0], (self.dim, self.dim))
        if self.threshold:
            image = cv2.threshold(image, 64, 255, cv2.THRESH_BINARY)[1]
        image = deskew(image, self.dim)
        feature_vector = self._preprocess_hog(image)
        return feature_vector

    def _preprocess_hog(self, image):
        gx = cv2.Sobel(image, cv2.CV_32F, 1, 0)
        gy = cv2.Sobel(image, cv2.CV_32F, 0, 1)
        mag, ang = cv2.cartToPolar(gx, gy)
        bin_n = 16
        bin_ = np.int32(bin_n * ang / (2 * np.pi))
        bin_cells = bin_[:10,:10], bin_[10:,:10], bin_[:10,10:], bin_[10:,10:]
        mag_cells = mag[:10,:10], mag[10:,:10], mag[:10,10:], mag[10:,10:]
        hists = [np.bincount(b.ravel(), m.ravel(), bin_n) \
                 for b, m in zip(bin_cells, mag_cells)]
        hist = np.hstack(hists)
        # transform to Hellinger kernel
        eps = 1e-7
        hist /= hist.sum() + eps
        hist = np.sqrt(hist)
        hist /= linalg.norm(hist) + eps
        return np.float32(hist)


def deskew(image, dim):
    """Deskew an image.

    It improves classifier performance.
    The image must be a cv2 image.

    """
    affine_flags = cv2.WARP_INVERSE_MAP | cv2.INTER_LINEAR
    m = cv2.moments(image)
    if abs(m['mu02']) < 1e-2:
        return image.copy()
    skew = m['mu11'] / m['mu02']
    M = np.float32([[1, skew, -0.5 * dim * skew], [0, 1, 0]])
    image = cv2.warpAffine(image, M, (dim, dim), flags=affine_flags)
    return image

def clear_boundbox(image, final_dim):
    """Clear the blank surrounding area of an image.

    It improves classifier performance.
    The image must be a cv2 image.

    """
    height, width = image.shape
    # delimit the image borders
    cleaned = images.erode_dilate(image)
    for i in range(height):
        if np.count_nonzero(cleaned[i, :] >= 128):
            top = i
            break
    else:
        top = 0
    for i in range(height - 1, top, -1):
        if np.count_nonzero(cleaned[i, :] >= 128):
            bottom = i
            break
    else:
        bottom = height - 1
    for i in range(width):
        if np.count_nonzero(cleaned[:, i] >= 128):
            left = i
            break
    else:
        left = 0
    for i in range(width - 1, left, -1):
        if np.count_nonzero(cleaned[:, i] >= 128):
            right = i
            break
    else:
        right = width - 1
    # Prevent the image from been later deformed
    new_width = right - left
    new_height = bottom - top
    dim = int(max(1.5 * new_width, 1.5 * new_height, 0.75 * final_dim))
    if dim > height and dim > width:
        dim = max(height, width)
    cleared_image = np.zeros((dim, dim), dtype=np.uint8)
    px_0 = (dim - new_width) // 2
    px_1 = px_0 + right - left
    py_0 = (dim - new_height) // 2
    py_1 = py_0 + bottom - top
    cleared_image[py_0:py_1, px_0:px_1] = image[top:bottom, left:right]
    image = cleared_image
    return image

def resize(image, dim):
    height, width = image.shape
    image = cv2.resize(image, (dim, dim))
    if ((height / dim < 0.75 or width / dim < 0.75)
        and np.count_nonzero(image) > 0.4 * dim * dim):
        image = images.erode(image)
    return image
