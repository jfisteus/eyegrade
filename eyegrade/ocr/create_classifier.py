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
from __future__ import unicode_literals

import sys
import json

from . import sample
from . import classifiers
from . import evaluation


def save_confusion_matrix(filename, matrix):
    with open(filename, mode='w') as f:
        json.dump(matrix.tolist(), f)

def main():
    if len(sys.argv) == 1:
        print('Usage: python create_classifier.py <digits_folders>')
        sys.exit(1)

    # Load the sample set:
    sample_set = sample.SampleSet()
    for filename in sys.argv[1:]:
        sample_set.load_from_loader(sample.SampleLoader(filename))

    # Perform a k-fold cross-evaluation and save the confusion matrix:
    classifier = classifiers.DefaultDigitClassifier()
    partitions = sample_set.partition(100)
    e = evaluation.KFoldCrossEvaluation(classifier, partitions)
    save_confusion_matrix(classifiers.DEFAULT_DIG_CONF_MAT_FILE,
                          e.confusion_matrix_r)
    print('Success rate: {} (balanced: {})'.format(e.success_rate,
                                                   e.success_rate_balanced))

    # Train the classifier with all the samples and save it:
    classifier.reset()
    classifier.train(sample_set.samples())
    classifier.save(classifiers.DEFAULT_DIG_CLASS_FILE)


if __name__ == '__main__':
    main()
