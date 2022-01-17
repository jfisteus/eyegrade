# Eyegrade: grading multiple choice questions with a webcam
# Copyright (C) 2010-2021 Rodrigo Arguello, Jesus Arias Fisteus
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
import json
import os

import cv2
import numpy as np

from . import preprocessing
from .. import utils

DEFAULT_DIG_CLASS_FILE = "digit_classifier.dat.gz"
DEFAULT_DIG_META_FILE = "digit_classifier_metadata.txt"
DEFAULT_CROSS_CLASS_FILE = "cross_classifier.dat.gz"
DEFAULT_CROSS_META_FILE = "cross_classifier_metadata.json"
DEFAULT_DIR = "svm"


class SVMClassifier:
    def __init__(self, num_classes, features_extractor, load_from_file=None):
        self.num_classes = num_classes
        self.features_extractor = features_extractor
        if not load_from_file:
            self.svm = cv2.ml.SVM_create()
        else:
            self.svm = cv2.ml.SVM_load(SVMClassifier.resource(load_from_file))

    @property
    def features_len(self):
        return self.features_extractor.features_len

    def train(self, samples, params=None):
        features = np.ndarray(shape=(len(samples), self.features_len), dtype="float32")
        labels = np.ndarray(shape=(len(samples), 1), dtype="int32")
        for i, sample in enumerate(samples):
            features[i, :] = self.features_extractor.extract(sample)
            labels[i] = sample.label
        self.svm.trainAuto(features, cv2.ml.ROW_SAMPLE, labels)

    def classify(self, sample):
        features = np.ndarray(shape=(1, self.features_len), dtype="float32")
        features[0, :] = self.features_extractor.extract(sample)
        retval, prediction = self.svm.predict(features)
        return int(prediction[0, 0])

    def reset(self):
        self.svm = cv2.ml.SVM_create()

    def save(self, filename):
        self.svm.save(filename)

    @staticmethod
    def resource(filename):
        return utils.resource_path(os.path.join(DEFAULT_DIR, filename))


class SVMDigitClassifier(SVMClassifier):
    def __init__(
        self, features_extractor, load_from_file=None, confusion_matrix_from_file=None
    ):
        super().__init__(10, features_extractor, load_from_file=load_from_file)
        self.confusion_matrix = self._load_confusion_matrix(confusion_matrix_from_file)

    def classify_digit(self, sample):
        digit = self.classify(sample)
        weights = self.confusion_matrix[:, digit]
        return (digit, weights)

    @staticmethod
    def _load_confusion_matrix(filename):
        if filename:
            with open(SVMClassifier.resource(filename)) as f:
                metadata = json.load(f)
                matrix = np.array(metadata["confusion_matrix"], dtype=float)
        else:
            matrix = np.diag(np.ones(10, dtype=float))
        return matrix


class DefaultDigitClassifier(SVMDigitClassifier):
    def __init__(
        self,
        load_from_file=DEFAULT_DIG_CLASS_FILE,
        confusion_matrix_from_file=DEFAULT_DIG_META_FILE,
    ):
        super().__init__(
            preprocessing.FeatureExtractor(),
            load_from_file=load_from_file,
            confusion_matrix_from_file=confusion_matrix_from_file,
        )

    def train(self, samples, params=None):
        super().train(samples, dict(C=3.16227766, gamma=0.01))


class SVMCrossesClassifier(SVMClassifier):
    def __init__(self, features_extractor, load_from_file=None):
        super().__init__(2, features_extractor, load_from_file=load_from_file)

    def is_cross(self, sample):
        return self.classify(sample) == 1


class DefaultCrossesClassifier(SVMCrossesClassifier):
    def __init__(self, load_from_file=DEFAULT_CROSS_CLASS_FILE):
        super().__init__(
            preprocessing.CrossesFeatureExtractor(), load_from_file=load_from_file
        )

    def train(self, samples, params=None):
        super().train(samples, dict(C=100, gamma=0.01))
