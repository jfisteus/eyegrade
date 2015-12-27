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
import json

import cv2
import numpy as np

from . import preprocessing
from .. import utils


DEFAULT_DIG_CLASS_FILE = 'digit_classifier.dat.gz'
DEFAULT_DIG_CONF_MAT_FILE = 'digit_confusion_matrix.txt'


class SVMClassifier(object):
    def __init__(self, num_classes, features_extractor, load_from_file=None):
        self.num_classes = num_classes
        self.features_extractor = features_extractor
        self.svm = cv2.SVM()
        if load_from_file:
            self.svm.load(utils.resource_path(load_from_file))

    @property
    def features_len(self):
        return self.features_extractor.features_len

    def train(self, samples, params=None):
        features = np.ndarray(shape=(len(samples), self.features_len),
                              dtype='float32')
        labels = np.ndarray(shape=(len(samples), 1), dtype='float32')
        for i, sample in enumerate(samples):
            features[i,:] = self.features_extractor.extract(sample)
            labels[i] = float(sample.label)
        svm_params = dict(kernel_type=cv2.SVM_RBF,
                          svm_type=cv2.SVM_C_SVC,
                          C=10,
                          gamma=0.01)
        if params:
            if 'C' in params:
                svm_params['C'] = params['C']
            if 'gamma' in params:
                svm_params['gamma'] = params['gamma']
        self.svm.train(features, labels, params=svm_params)

    def classify(self, sample):
        features = self.features_extractor.extract(sample)
        return int(round(self.svm.predict(features)))

    def reset(self):
        self.svm = cv2.SVM()

    def save(self, filename):
        self.svm.save(filename)


class SVMDigitClassifier(SVMClassifier):
    def __init__(self, features_extractor, load_from_file=None,
                 confusion_matrix_from_file=None):
        super(SVMDigitClassifier, self).__init__(10, features_extractor,
                                                 load_from_file=load_from_file)
        self.confusion_matrix = \
            self._load_confusion_matrix(confusion_matrix_from_file)

    def classify_digit(self, sample):
        digit = self.classify(sample)
        weights = self.confusion_matrix[:, digit]
        return (digit, weights)

    @staticmethod
    def _load_confusion_matrix(filename):
        if filename:
            with open(utils.resource_path(filename)) as f:
                matrix = np.array(json.load(f), dtype=float)
        else:
            matrix = np.diag(np.ones(10, dtype=float))
        return matrix


class DefaultDigitClassifier(SVMDigitClassifier):
    def __init__(self,
                 load_from_file=DEFAULT_DIG_CLASS_FILE,
                 confusion_matrix_from_file=DEFAULT_DIG_CONF_MAT_FILE):
        super(DefaultDigitClassifier, self).__init__( \
                        preprocessing.FeatureExtractor(),
                        load_from_file=load_from_file,
                        confusion_matrix_from_file=confusion_matrix_from_file)

    def train(self, samples, params=None):
        super(DefaultDigitClassifier, self).train( \
                                              samples,
                                              dict(C=3.16227766, gamma=0.01))
