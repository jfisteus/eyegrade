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
import math

import numpy as np

from . import sample
from . import classifiers
from . import evaluation


def decide_params(classifier, sample_set, c_values, gamma_values, threshold=None, k=10):
    results = []
    rmat = np.zeros(shape=(len(c_values), len(gamma_values)), dtype="float32")
    partitions = sample_set.partition(k)
    for i, c in enumerate(c_values):
        for j, gamma in enumerate(gamma_values):
            params = dict(C=c, gamma=gamma)
            print("C: {}, gamma: {}".format(c, gamma))
            e = evaluation.KFoldCrossEvaluation(
                classifier, partitions, training_params=params, threshold=threshold
            )
            result = (e.success_rate, e.success_rate_balanced, c, gamma)
            results.append(result)
            rmat[i, j] = e.success_rate
            print(result)
            print(rmat)
    return results, rmat


def _parse_args():
    parser = argparse.ArgumentParser(description="Look for the best SVM parameters.")
    parser.add_argument(
        "classifier", help='classifier to be evaluated ("digits" or "crosses")'
    )
    parser.add_argument(
        "sample_files",
        metavar="sample file",
        nargs="+",
        help="index file with the samples for training/evaluation",
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=10,
        help="number of rounds for k-fold cross evaluation (default 10)",
    )
    return parser.parse_args()


def main():
    args = _parse_args()
    sample_set = sample.SampleSet()
    for filename in args.sample_files:
        sample_set.load_from_loader(sample.SampleLoader(filename))
    if args.classifier == "digits":
        classifier = classifiers.DefaultDigitClassifier(
            load_from_file=None, confusion_matrix_from_file=None
        )
        threshold = 0.9
    else:
        classifier = classifiers.DefaultCrossesClassifier(load_from_file=None)
        threshold = 0.99
    c_values = [math.pow(10, i) for i in np.linspace(0, 4, 9)]
    gamma_values = [math.pow(10, i) for i in np.linspace(-3, -1, 5)]
    r = decide_params(
        classifier, sample_set, c_values, gamma_values, threshold=threshold
    )
    print(r)


if __name__ == "__main__":
    main()
