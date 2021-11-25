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
import os
import collections
import random

import cv2
import numpy as np

from .. import geometry as g


class Sample:
    def __init__(self, corners, image=None, image_filename=None, label=None):
        if image is None and not image_filename:
            raise ValueError("Either image of image_filename are needed")
        if corners.shape != (4, 2):
            raise ValueError("Corners must be a 4x2 matrix")
        self.corners = corners
        self.image_filename = image_filename
        self.label = label
        self._image = image
        self._features = None

    @property
    def image(self):
        if self._image is None:
            self._image = cv2.imread(self.image_filename, 0)
            if self._image is None:
                raise ValueError("Cannot load image: {}".format(self.image_filename))
        return self._image

    def check_label(self, label):
        return self.label == label

    def crop(self):
        min_x = min(self.corners[:, 0])
        max_x = max(self.corners[:, 0])
        min_y = min(self.corners[:, 1])
        max_y = max(self.corners[:, 1])
        new_corners = self.corners - np.array([(min_x, min_y)] * 4)
        new_image = self.image[min_y : max_y + 1, min_x : max_x + 1]
        return Sample(new_corners, image=new_image)


class DigitSampleFromCam(Sample):
    def __init__(self, corners, image):
        corners = adjust_cell_corners(image, corners)
        super().__init__(corners, image=image)


class CrossSampleFromCam(Sample):
    def __init__(self, corners, image):
        corners = self._adjust_cell_corners(image, corners)
        super().__init__(corners, image=image)

    @staticmethod
    def _adjust_cell_corners(image, corners):
        plu, prd = g.closer_points_rel(corners[0, :], corners[3, :], 0.8)
        pru, pld = g.closer_points_rel(corners[1, :], corners[2, :], 0.8)
        return np.array((plu, pru, pld, prd))


class SampleSet:
    def __init__(self):
        self.samples_dict = collections.defaultdict(list)

    def __len__(self):
        return sum(len(self.samples_dict[label]) for label in self.samples_dict)

    def __iter__(self):
        return self.iterate_samples()

    @property
    def distribution(self):
        return [(label, len(self.samples_dict[label])) for label in self.samples_dict]

    def load_from_loader(self, loader):
        self.load_from_samples(loader.iterate_samples())

    def load_from_samples(self, samples):
        for sample in samples:
            if sample.label is None:
                raise ValueError("Unlabelled sample in SampleSet")
            self.samples_dict[sample.label].append(sample)

    def load_from_sample_set(self, sample_set):
        for sample in sample_set.iterate_samples():
            if sample.label is None:
                raise ValueError("Unlabelled sample in SampleSet")
            self.samples_dict[sample.label].append(sample)

    def load_from_sample_sets(self, sample_sets):
        for sample_set in sample_sets:
            self.load_from_sample_set(sample_set)

    def samples(self, oversampling=False, downsampling=False):
        return [
            sample
            for sample in self.iterate_samples(
                oversampling=oversampling, downsampling=downsampling
            )
        ]

    def iterate_samples(self, oversampling=False, downsampling=False):
        if oversampling and downsampling:
            raise ValueError("Over and donwsampling are mutually-exclusive")
        if oversampling:
            iterator = self._iterate_samples_oversampling()
        elif downsampling:
            iterator = self._iterate_samples_downsampling()
        else:
            iterator = self._iterate_samples()
        return iterator

    def partition(self, num_groups):
        total_samples = len(self)
        partition_lens = [total_samples // num_groups] * num_groups
        for i in range(total_samples % num_groups):
            partition_lens[i] += 1
        partitions = []
        samples = set(self.samples())
        for partition_len in partition_lens:
            partition = random.sample(samples, partition_len)
            samples -= set(partition)
            sample_set = SampleSet()
            sample_set.load_from_samples(partition)
            partitions.append(sample_set)
        return partitions

    def oversample(self):
        sample_set = SampleSet()
        sample_set.load_from_samples(self.samples(oversampling=True))
        return sample_set

    def downsample(self):
        sample_set = SampleSet()
        sample_set.load_from_samples(self.samples(downsampling=True))
        return sample_set

    def _iterate_samples(self):
        for samples in self.samples_dict.values():
            for sample in samples:
                yield sample

    def _iterate_samples_oversampling(self):
        max_num = self._max_sample_num()
        for samples in self.samples_dict.values():
            rounds = max_num // len(samples)
            remaining = max_num % len(samples)
            for i in range(rounds):
                for sample in samples:
                    yield sample
            for sample in random.sample(samples, remaining):
                yield sample

    def _iterate_samples_downsampling(self):
        min_num = self._min_sample_num()
        for samples in self.samples_dict.values():
            for sample in random.sample(samples, min_num):
                yield sample

    def _max_sample_num(self):
        return max(len(self.samples_dict[label]) for label in self.samples_dict)

    def _min_sample_num(self):
        return min(len(self.samples_dict[label]) for label in self.samples_dict)


class SampleLoader:
    def __init__(self, filename):
        self.filename = filename
        self.dirname = os.path.dirname(filename)

    def samples(self):
        return [sample for sample in self.iterate_samples()]

    def iterate_samples(self):
        with open(self.filename, mode="r") as f:
            for line in f:
                if line.strip():
                    yield self._parse_sample(line)

    def _parse_sample(self, line):
        parts = [p.strip() for p in line.split("\t")]
        if len(parts) != 10:
            raise ValueError("Syntax error in samples file")
        image_path = os.path.join(self.dirname, parts[0])
        label = int(parts[1])
        corners = np.zeros((4, 2), dtype=np.uint16)
        corners[0, 0] = int(parts[2])  # left top
        corners[0, 1] = int(parts[3])
        corners[1, 0] = int(parts[4])  # right top
        corners[1, 1] = int(parts[5])
        corners[2, 0] = int(parts[6])  # left bottom
        corners[2, 1] = int(parts[7])
        corners[3, 0] = int(parts[8])  # right bottom
        corners[3, 1] = int(parts[9])
        return Sample(corners, image_filename=image_path, label=label)


def adjust_cell_corners(image, corners):
    plu = adjust_cell_corner(image, corners[0, :], corners[3, :])
    prd = adjust_cell_corner(image, corners[3, :], corners[0, :])
    pru = adjust_cell_corner(image, corners[1, :], corners[2, :])
    pld = adjust_cell_corner(image, corners[2, :], corners[1, :])
    return np.array([plu, pru, pld, prd])


def adjust_cell_corner(image, corner, towards_corner):
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
