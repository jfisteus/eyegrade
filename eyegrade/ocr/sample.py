# Eyegrade: grading multiple choice questions with a webcam
# Copyright (C) 2015 Jesus Arias Fisteus
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

import os
import os.path
import collections
import random
import math
import re

import cv2
import numpy as np

from .. import geometry as g
from .. import images


class Sample(object):
    def __init__(self, image=None, image_filename=None, label=None,
                 feature_extractor=None):
        if image is None and not image_filename:
            raise ValueError('Either image of image_filename are needed')
        self.image_filename = image_filename
        self.label = label
        self._feature_extractor = feature_extractor
        self._image = image
        self._features = None

    @property
    def image(self):
        if self._image is None:
            self._image = images.load_image(self.image_filename)
            if self._image is None:
                raise ValueError('Cannot load image: {}'\
                                 .format(self.image_filename))
        return self._image

    @property
    def features(self):
        if self._features is None:
            if self.feature_extractor is not None:
                self._features = self.feature_extractor.extract(self)
            else:
                raise ValueError('No feature extractor has been set')
        return self._features

    @property
    def feature_extractor(self):
        return self._feature_extractor

    @feature_extractor.setter
    def feature_extractor(self, value):
        if self._features is not None:
            if self._feature_extractor != value:
                self._features = None
        self._feature_extractor = value

    def check_label(self, label):
        return self.label == label


class DigitSampleFromCam(Sample):
    def __init__(self, corners, orig_image, proc_image):
        corners = _adjust_cell_corners(proc_image, corners)
        image, corners = images.crop(orig_image, corners)
        ## image = images.invert(images.rgb_to_gray(image))
        ## corners, image = Sample.crop_to_corners(corners, inverted)
        ## image = images.clear_background(image)
        super(DigitSampleFromCam, self).__init__(image=image)


class CrossSampleFromCam(Sample):
    def __init__(self, corners, orig_image, proc_image):
        corners = self._adjust_cell_corners(proc_image, corners)
        image, corners = images.crop(orig_image, corners)
        super(CrossSampleFromCam, self).__init__(image=image)

    @staticmethod
    def _adjust_cell_corners(image, corners):
        plu, prd = g.closer_points_rel(corners[0, :], corners[3, :], 0.8)
        pru, pld = g.closer_points_rel(corners[1, :], corners[2, :], 0.8)
        return np.array((plu, pru, pld, prd))


class SampleSet(object):
    def __init__(self, feature_extractor=None):
        self.samples_dict = collections.defaultdict(list)
        self._feature_extractor = feature_extractor

    def __len__(self):
        return sum(len(self.samples_dict[label]) \
                   for label in self.samples_dict)

    def __iter__(self):
        return self.iterate_samples()

    @property
    def distribution(self):
        return [(label, len(self.samples_dict[label])) \
                for label in self.samples_dict]

    @property
    def feature_extractor(self):
        return self._feature_extractor

    def load_from_loader(self, loader):
        self.load_from_samples(loader.iterate_samples())

    def load_from_samples(self, samples):
        for sample in samples:
            self.load_sample(sample)

    def load_from_sample_set(self, sample_set):
        for sample in sample_set.iterate_samples():
            self.load_sample(sample)

    def load_from_sample_sets(self, sample_sets):
        for sample_set in sample_sets:
            self.load_from_sample_set(sample_set)

    def load_sample(self, sample):
        if sample.label is None:
            raise ValueError('Unlabelled sample in SampleSet')
        self.samples_dict[sample.label].append(sample)
        sample.feature_extractor = self._feature_extractor

    def samples(self, oversampling=False, downsampling=False):
        return [sample for sample \
                       in self.iterate_samples(oversampling=oversampling,
                                               downsampling=downsampling)]

    def iterate_samples(self, oversampling=False, downsampling=False):
        if oversampling and downsampling:
            raise ValueError('Over and donwsampling are mutually-exclusive')
        if oversampling:
            iterator = self._iterate_samples_oversampling()
        elif downsampling:
            iterator = self._iterate_samples_downsampling()
        else:
            iterator = self._iterate_samples()
        return iterator

    def partition(self, num_groups):
        total_samples = len(self)
        partition_lengths = [total_samples // num_groups] * num_groups
        for i in range(total_samples % num_groups):
            partition_lengths[i] += 1
        return self.partition_with_lengths(partition_lengths)

    def partition_with_fractions(self, fractions):
        total_samples = len(self)
        if sum(fractions) != 1.0:
            raise ValueError('Fractions must sum 1.0')
        partition_lengths = [int(total_samples * r) for r in fractions]
        for i in range(total_samples - sum(partition_lengths)):
            partition_lengths[i] += 1
        return self.partition_with_lengths(partition_lengths)

    def partition_with_lengths(self, partition_lengths):
        if len(self) != sum(partition_lengths):
            raise ValueError('Sizes must sum the total number of samples')
        partitions = []
        samples = set(self.samples())
        for partition_len in partition_lengths:
            partition = random.sample(samples, partition_len)
            samples -= set(partition)
            sample_set = SampleSet(feature_extractor=self._feature_extractor)
            sample_set.load_from_samples(partition)
            partitions.append(sample_set)
        return partitions

    def random_samples(self, num_samples):
        samples = random.sample(self.samples(), num_samples)
        sample_set = SampleSet(feature_extractor=self._feature_extractor)
        sample_set.load_from_samples(samples)
        return sample_set

    def oversample(self):
        sample_set = SampleSet(feature_extractor=self._feature_extractor)
        sample_set.load_from_samples(self.samples(oversampling=True))
        return sample_set

    def downsample(self):
        sample_set = SampleSet(feature_extractor=self._feature_extractor)
        sample_set.load_from_samples(self.samples(downsampling=True))
        return sample_set

    def to_matrices(self):
        features_matrix, labels, samples = self.to_matrices_complete()
        return features_matrix, labels

    def to_matrices_complete(self):
        num_samples = len(self)
        if num_samples == 0:
            raise ValueError('Empty sample set')
        if self._feature_extractor is None:
            raise ValueError('A feature extractor hasn\'t been set')
        features_len = self._feature_extractor.features_len
        features_matrix = np.zeros((num_samples, features_len),
                                   dtype=np.float32)
        samples = []
        labels = np.zeros(num_samples, dtype=int)
        for i, sample in enumerate(self.iterate_samples()):
            features_matrix[i, :] = sample.features
            labels[i] = sample.label
            samples.append(sample)
        return features_matrix, labels, samples

    def search_sample(self, image_filename):
        found_sample = None
        for sample in self.iterate_samples():
            if sample.image_filename == image_filename:
                found_sample = sample
        return found_sample

    def _iterate_samples(self):
        for samples in self.samples_dict.itervalues():
            for sample in samples:
                yield sample

    def _iterate_samples_oversampling(self):
        max_num = self._max_sample_num()
        for samples in self.samples_dict.itervalues():
            rounds = max_num // len(samples)
            remaining = max_num % len(samples)
            for i in range(rounds):
                for sample in samples:
                    yield sample
            for sample in random.sample(samples, remaining):
                yield sample

    def _iterate_samples_downsampling(self):
        min_num = self._min_sample_num()
        for samples in self.samples_dict.itervalues():
            for sample in random.sample(samples, min_num):
                yield sample

    def _max_sample_num(self):
        return max(len(self.samples_dict[label]) \
                   for label in self.samples_dict)

    def _min_sample_num(self):
        return min(len(self.samples_dict[label]) \
                   for label in self.samples_dict)


class SampleLoader(object):
    _sample_re = re.compile(r'sample-(\d)-\d{13}.png')

    def __init__(self, dirname):
        if not os.path.isdir(dirname):
            raise ValueError('Path {} isn\'t a directory'.format(dirname))
        self.dirname = dirname

    def samples(self):
        return [sample for sample in self.iterate_samples()]

    def iterate_samples(self):
        for filename in os.listdir(self.dirname):
            match = SampleLoader._sample_re.match(filename)
            if match:
                image_path = os.path.join(self.dirname, filename)
                label = int(match.groups()[0])
                yield Sample(image_filename=image_path, label=label)


class ImageWriter(object):

    @staticmethod
    def write_image(filename, data, num_columns=20):
        matrix, labels = data
        num_images = matrix.shape[0]
        dim = int(math.sqrt(matrix.shape[1]))
        if dim * dim != matrix.shape[1]:
            raise ValueError('Feature images should be squares')
        num_rows = int(math.ceil(num_images / num_columns))
        image_mat_width = 1 + num_columns * (1 + dim)
        image_mat_height = 1 + num_rows * (1 + dim)
        image_mat = np.zeros((image_mat_height, image_mat_width),
                             dtype=np.float32)
        for i in range(0, image_mat_width, 1 + dim):
            image_mat[:, i] = 1.0
        for i in range(0, image_mat_height, 1 + dim):
            image_mat[i, :] = 1.0
        for row in range(num_images):
            i = 1 + (row // 20) * (1 + dim)
            j = 1 + (row % 20) * (1 + dim)
            subimage = matrix[row, :].reshape((dim, dim))
            image_mat[i:i+dim, j:j+dim] = subimage
        image = np.array(255 * image_mat, dtype=np.uint8)
        cv2.imwrite(filename, image)

    @staticmethod
    def write_debug_info(filename_img, filename_text, sample_set,
                         **kwargs):
        features_matrix, labels, samples = sample_set.to_matrices_complete()
        ImageWriter.write_image(filename_img, (features_matrix, labels),
                                **kwargs)
        with open(filename_text, mode='w') as f:
            for i, sample in enumerate(samples):
                row = i // 20
                column = i % 20
                f.write('{}\t{}\t{}\t{}\n'.format(row, column, sample.label,
                                                  sample.image_filename))


def _adjust_cell_corners(image, corners):
    plu = _adjust_cell_corner(image, corners[0, :], corners[3, :])
    prd = _adjust_cell_corner(image, corners[3, :], corners[0, :])
    pru = _adjust_cell_corner(image, corners[1, :], corners[2, :])
    pld = _adjust_cell_corner(image, corners[2, :], corners[1, :])
    return np.array([plu, pru, pld, prd])

def _adjust_cell_corner(image, corner, towards_corner):
    margin = None
    for x, y in g.walk_line_ordered(corner, towards_corner):
        if margin is None:
            if image[y, x] == 0:
                margin = 2
        else:
            margin -= 1
            if margin == 0:
                return (x, y)
    # In case of failure, return the original point
    return corner
