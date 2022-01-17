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
import numpy as np

from . import sample


class Evaluation:
    def __init__(self, classifier, samples):
        self.classifier = classifier
        self.samples = samples
        self._evaluate()

    @property
    def confusion_matrix_r(self):
        return (
            np.array(self.confusion_matrix, dtype="float32")
            / np.sum(self.confusion_matrix, axis=1)[np.newaxis].T
        )

    @property
    def success_rate_balanced(self):
        return np.mean(self.confusion_matrix_r.diagonal())

    def _evaluate(self):
        num_classes = self.classifier.num_classes
        self.results = np.zeros(len(self.samples), dtype=bool)
        self.confusion_matrix = np.zeros(shape=(num_classes, num_classes), dtype="int")
        for i, samp in enumerate(self.samples):
            detected = self.classifier.classify(samp)
            self.confusion_matrix[samp.label, detected] += 1
            self.results[i] = samp.check_label(detected)
        self.success_rate = sum(self.results) / len(self.results)


class KFoldCrossEvaluation(Evaluation):
    def __init__(
        self,
        classifier,
        sample_sets,
        oversampling=False,
        training_params=None,
        threshold=None,
    ):
        self.classifier = classifier
        self.sample_sets = sample_sets
        self.training_params = training_params
        self.threshold = threshold
        self._evaluate(oversampling=oversampling)

    def _evaluate(self, oversampling=False):
        num_classes = self.classifier.num_classes
        self.confusion_matrix = np.zeros(shape=(num_classes, num_classes), dtype="int")
        for i, evaluation_set in enumerate(self.sample_sets):
            training_set = sample.SampleSet()
            training_set.load_from_sample_sets(self.sample_sets[:i])
            training_set.load_from_sample_sets(self.sample_sets[i + 1 :])
            if oversampling:
                training_set = training_set.oversample()
            self.classifier.train(training_set.samples(), params=self.training_params)
            evaluation = Evaluation(self.classifier, evaluation_set)
            self.confusion_matrix += evaluation.confusion_matrix
            self.classifier.reset()
            total = self.confusion_matrix.sum()
            correct = self.confusion_matrix.diagonal().sum()
            self.success_rate = correct / total
            print("Round {}: {}".format(i, self.success_rate))
            if self.threshold is not None and self.success_rate < self.threshold:
                break
