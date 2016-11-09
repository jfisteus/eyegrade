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

from __future__ import division

import math

import cv2
import numpy as np

from . import geometry as g


# Adaptive threshold algorithm
param_adaptive_threshold_block_size = 45
param_adaptive_threshold_offset = 0


# Main image processing functions on numpy images
#
def width(image):
    """Returns the width of the numpy image in pixels."""
    return image.shape[1]

def height(image):
    """Returns the height of the numpy image in pixels."""
    return image.shape[0]

def new_image(width, height, num_channels):
    if num_channels == 1:
        image = np.zeros((height, width), np.uint8)
    elif num_channels == 3:
        image = np.zeros((height, width, 3), np.uint8)
    else:
        raise ValueError('Wrong number of channels in _new_image()')
    return image

def zero_image(image):
    image[:, :] = 0

def gray_to_rgb(image):
    return cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)

def rgb_to_gray(image):
    return cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)

def histogram_grayscale(image):
    return cv2.calcHist([image], [0], None, [256], [0,256]).reshape(256)

def invert(image):
    return 255 - image

def clear_background(image):
    size = image.shape[0] * image.shape[1]
    hist = histogram_grayscale(image)
    diff = np.diff(hist)
    pos_max = np.argmax(hist)
    pos_growth = np.argmax(diff[pos_max + 4:] > 0) + pos_max + 4
    pos_ini = np.argmin(hist[pos_growth:pos_growth + 4]) + pos_growth
    while hist[pos_ini] > 0.2 * hist[pos_max]:
        pos_ini += 1
    cumsum = np.cumsum(hist)
    while cumsum[pos_ini] < 0.75 * size:
        pos_ini += 1
    lim = cumsum[pos_ini - 1] + (cumsum[-1] - cumsum[pos_ini - 1]) / 2
    pos_end = np.argmax(cumsum[pos_ini:] > lim) + pos_ini
    if pos_ini > 170:
        # For cleared cross cells
        pos_ini = 170
        pos_end = 200
    lut = np.zeros(256, dtype=np.uint8)
    lut[pos_end:] = 255
    lut[pos_ini:pos_end] = np.linspace(0, 255, num=pos_end - pos_ini,
                                       endpoint=False)
    ## print repr(hist)
    ## print repr(diff)
    ## print repr(cumsum)
    ## print 'max', pos_max, pos_growth
    ## print pos_ini, pos_end
    ## print lut
    return cv2.LUT(image, lut)

def project_to_rectangle(image, corners, width, height):
    corners_dst = np.array([[0, 0],
                            [width - 1, 0],
                            [0, height - 1],
                            [width - 1, height - 1]],
                            dtype='float32')
    h = cv2.findHomography(np.array(corners, dtype='float32'), corners_dst)
    return cv2.warpPerspective(image, h[0], (width, height)), corners_dst

def crop(image, corners):
    p = corners
    width = int((cv2.norm(p[0,:], p[1,:]) + cv2.norm(p[2,:], p[3,:])) / 2)
    height = int((cv2.norm(p[0,:], p[2,:]) + cv2.norm(p[1,:], p[3,:])) / 2)
    return project_to_rectangle(image, corners, width, height)

# Pre-processing and thresholding
def pre_process(image):
    gray = rgb_to_gray(image)
    thr = cv2.adaptiveThreshold(gray, 255,
                                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                cv2.THRESH_BINARY_INV,
                                param_adaptive_threshold_block_size,
                                param_adaptive_threshold_offset)
    return thr


# Image reading and writing
#
def load_image_grayscale(filename):
    return cv2.imread(filename, flags=cv2.IMREAD_GRAYSCALE)

def load_image(filename):
    return cv2.imread(filename)


# Drawing functions
#
def draw_line(image, line, color=(0, 0, 255, 0)):
    theta = line[1]
    points = set()
    if math.sin(theta) != 0.0:
        points.add(g.line_point(line, x=0))
        points.add(g.line_point(line, x=g.width(image) - 1))
    if math.cos(theta) != 0.0:
        points.add(g.line_point(line, y=0))
        points.add(g.line_point(line, y=g.height(image) - 1))
    p_draw = [p for p in points if p[0] >= 0 and p[1] >= 0
              and p[0] < g.width(image) and p[1] < g.height(image)]
    if len(p_draw) == 2:
        cv2.line(image, p_draw[0], p_draw[1], color, thickness=1)

def draw_point(image, point, color=(255, 0, 0, 0), radius=2):
    x, y = point
    if x >= 0 and x < g.width(image) and y >= 0 and y < g.height(image):
        cv2.circle(image, point, radius, color, thickness=-1)
    else:
        print "draw_point: bad point (%d, %d)"%(x, y)

def draw_text(image, text, color=(255, 0, 0), position=(10, 30)):
    cv2.putText(image, text, position, cv2.FONT_HERSHEY_SIMPLEX, 1.0, color,
                thickness=3)

# Dilating and eroding
def erode(image):
    return cv2.erode(image, cv2.getStructuringElement(cv2.MORPH_CROSS,(2,2)))

def dilate(image):
    return cv2.dilate(image, cv2.getStructuringElement(cv2.MORPH_CROSS,(2,2)))

def erode_dilate(image):
    return dilate(erode(image))

def dilate_erode(image):
    return erode(dilate(image))
