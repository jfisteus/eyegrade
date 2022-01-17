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
import json
import argparse

from . import sample
from . import classifiers
from . import evaluation


def save_metadata(filename, metadata):
    with open(filename, mode="w") as f:
        json.dump(metadata, f, indent=4, sort_keys=True)


def k_fold_cross_evaluation(classifier, sample_set, rounds):
    classifier.reset()
    partitions = sample_set.partition(rounds)
    e = evaluation.KFoldCrossEvaluation(classifier, partitions)
    return e


def train_with_all(classifier, sample_set):
    classifier.reset()
    classifier.train(sample_set.samples())


def create_digit_classifier(sample_set, rounds):
    classifier = classifiers.DefaultDigitClassifier(
        load_from_file=None, confusion_matrix_from_file=None
    )
    e = k_fold_cross_evaluation(classifier, sample_set, rounds)
    metadata = {
        "performance": {
            "success_rate": e.success_rate,
            "balanced_success_rate": e.success_rate_balanced,
            "evaluation_rounds": rounds,
            "num_samples": len(sample_set),
        },
        "confusion_matrix": e.confusion_matrix_r.tolist(),
    }
    print(
        "Success rate: {} (balanced: {})".format(
            e.success_rate, e.success_rate_balanced
        )
    )
    save_metadata(classifiers.DEFAULT_DIG_META_FILE, metadata)
    train_with_all(classifier, sample_set)
    classifier.save(classifiers.DEFAULT_DIG_CLASS_FILE)


def create_crosses_classifier(sample_set, rounds):
    classifier = classifiers.DefaultCrossesClassifier(load_from_file=None)
    e = k_fold_cross_evaluation(classifier, sample_set, rounds)
    print(
        "Success rate: {} (balanced: {})".format(
            e.success_rate, e.success_rate_balanced
        )
    )
    metadata = {
        "performance": {
            "success_rate": e.success_rate,
            "balanced_success_rate": e.success_rate_balanced,
            "evaluation_rounds": rounds,
            "num_samples": len(sample_set),
        },
        "confusion_matrix": e.confusion_matrix_r.tolist(),
    }
    save_metadata(classifiers.DEFAULT_CROSS_META_FILE, metadata)
    train_with_all(classifier, sample_set)
    classifier.save(classifiers.DEFAULT_CROSS_CLASS_FILE)


def _parse_args():
    parser = argparse.ArgumentParser(
        description="Create the SVM classifier for digits or crosses."
    )
    parser.add_argument(
        "classifier", help='classifier to be created ("digits" or "crosses")'
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
        help="number of rounds for k-fold cross evaluation (default 100)",
    )
    return parser.parse_args()


def main():
    args = _parse_args()

    # Load the sample set:
    sample_set = sample.SampleSet()
    for filename in args.sample_files:
        sample_set.load_from_loader(sample.SampleLoader(filename))

    # Perform a k-fold cross-evaluation and create the classifier:
    if args.classifier == "digits":
        create_digit_classifier(sample_set, args.rounds)
    else:
        create_crosses_classifier(sample_set, args.rounds)


if __name__ == "__main__":
    main()
