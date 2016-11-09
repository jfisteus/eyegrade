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
from __future__ import unicode_literals, division

import json
import argparse
import logging
import sys

from . import sample
from . import classifiers
from . import evaluation
from . import deepclassifier
from . import preprocessing


def save_metadata(filename, metadata):
    with open(filename, mode='w') as f:
        json.dump(metadata, f, indent=4, sort_keys=True)

def k_fold_cross_evaluation(classifier, sample_set, rounds):
    classifier.reset()
    partitions = sample_set.partition(rounds)
    e = evaluation.KFoldCrossEvaluation(classifier, partitions)
    return e

def train_with_all(classifier, sample_set):
    classifier.reset()
    classifier.train(sample_set.samples())

def create_digit_classifier(train_set, validation_set, test_set, epochs):
    logging.info('Creating a digit classifier')
    mini_batch_size = 10
    layers = [
        deepclassifier.ConvPoolLayer(
              image_shape=(1, 28, 28),
              mini_batch_size=mini_batch_size,
              filter_shape=(20, 1, 5, 5),
              poolsize=(2, 2),
              activation_fn=deepclassifier.ActivationFunc.relu),
        deepclassifier.ConvPoolLayer(
              image_shape=(20, 12, 12),
              mini_batch_size=mini_batch_size,
              filter_shape=(40, 20, 5, 5),
              poolsize=(2, 2),
              activation_fn=deepclassifier.ActivationFunc.relu),
        deepclassifier.FullyConnectedLayer(
              n_in=40*4*4,
              n_out=1000,
              activation_fn=deepclassifier.ActivationFunc.relu,
              p_dropout=0.5),
        deepclassifier.FullyConnectedLayer(
              n_in=1000,
              n_out=1000,
              activation_fn=deepclassifier.ActivationFunc.relu, p_dropout=0.5),
        deepclassifier.SoftmaxLayer(
              n_in=1000,
              n_out=10,
              p_dropout=0.5)]
    classifier = deepclassifier.Classifier(layers=layers,
                                           mini_batch_size=mini_batch_size)
    classifier.train(train_set, epochs=epochs,
                     validation_sample_set=validation_set,
                     test_sample_set=test_set)
    logging.info('Saving classifier')
    classifier.save(classifiers.DEFAULT_DIG_CLASS_FILE)
    # Create a new classifier so that mini_batch_size is 1
    logging.info('Loading classifier for evaluation')
    classifier = deepclassifier.Classifier(
                        load_from_file=classifiers.DEFAULT_DIG_CLASS_FILE,
                        mini_batch_size=1)
    logging.info('Beginning evaluation')
    e = evaluation.Evaluation(classifier, test_set, 10)
    metadata = {
        'performance': {
            'success_rate': e.success_rate,
            'balanced_success_rate': e.success_rate_balanced,
            'num_samples': len(test_set),
            'epochs': epochs,
        },
        'confusion_matrix': e.confusion_matrix_r.tolist(),
        'training_samples': len(train_set),
    }
    print('Success rate: {} (balanced: {})'.format(e.success_rate,
                                                   e.success_rate_balanced))
    save_metadata(classifiers.DEFAULT_DIG_META_FILE, metadata)

def create_crosses_classifier(train_set, validation_set, test_set, epochs):
    logging.info('Creating a crosses classifier')
    mini_batch_size = 10
    ## layers = [
    ##     deepclassifier.FullyConnectedLayer(n_in=784, n_out=100,
    ##                         activation_fn=deepclassifier.ActivationFunc.relu),
    ##     deepclassifier.SoftmaxLayer(n_in=100, n_out=2),
    ## ]
    layers = [
        deepclassifier.ConvPoolLayer(
                image_shape=(1, 28, 28),
                mini_batch_size=mini_batch_size,
                filter_shape=(20, 1, 5, 5),
                poolsize=(2, 2),
                activation_fn=deepclassifier.ActivationFunc.relu),
        deepclassifier.ConvPoolLayer(
               image_shape=(20, 12, 12),
               mini_batch_size=mini_batch_size,
               filter_shape=(40, 20, 5, 5),
               poolsize=(2, 2),
               activation_fn=deepclassifier.ActivationFunc.relu),
        deepclassifier.FullyConnectedLayer(
               n_in=40*4*4,
               n_out=1000,
               activation_fn=deepclassifier.ActivationFunc.relu,
               p_dropout=0.5),
        deepclassifier.FullyConnectedLayer(
               n_in=1000,
               n_out=1000,
               activation_fn=deepclassifier.ActivationFunc.relu, p_dropout=0.5),
        deepclassifier.SoftmaxLayer(
               n_in=1000,
               n_out=2,
               p_dropout=0.5)]
    classifier = deepclassifier.Classifier(layers=layers,
                                           mini_batch_size=mini_batch_size)
    classifier.train(train_set, epochs=epochs,
                     validation_sample_set=validation_set,
                     test_sample_set=test_set)
    logging.info('Saving classifier')
    classifier.save(classifiers.DEFAULT_CROSS_CLASS_FILE)
    # Create a new classifier so that mini_batch_size is 1
    logging.info('Loading classifier for evaluation')
    classifier = deepclassifier.Classifier(
                        load_from_file=classifiers.DEFAULT_CROSS_CLASS_FILE,
                        mini_batch_size=1)
    logging.info('Beginning evaluation')
    e = evaluation.Evaluation(classifier, test_set, 2)
    print('Success rate: {} (balanced: {})'.format(e.success_rate,
                                                   e.success_rate_balanced))
    metadata = {
        'performance': {
            'success_rate': e.success_rate,
            'balanced_success_rate': e.success_rate_balanced,
            'num_samples': len(test_set),
            'epochs': epochs,
        },
        'confusion_matrix': e.confusion_matrix_r.tolist(),
    }
    save_metadata(classifiers.DEFAULT_CROSS_META_FILE, metadata)

def _save_images(train_set, validation_set, test_set):
    sample.ImageWriter.write_image('train_set.png',
                                   train_set.to_matrices())
    sample.ImageWriter.write_image('validation_set.png',
                                   validation_set.to_matrices())
    sample.ImageWriter.write_image('test_set.png',
                                   test_set.to_matrices())

def _parse_args():
    parser = argparse.ArgumentParser(description='Create OCR classifier.')
    parser.add_argument('classifier',
            help='classifier to be created ("digits" or "crosses")')
    parser.add_argument('sample_files', metavar='sample file', nargs='+',
            help='index file with the samples for training/evaluation')
    parser.add_argument('--epochs', type=int, default=40,
            help='number of training epochs (default 40)')
    parser.add_argument('--save-images', dest='save_images',
            action='store_true',
            help='save images with the sample sets')
    return parser.parse_args()

def main():
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(message)s')
    args = _parse_args()

    # Perform a k-fold cross-evaluation and create the classifier:
    if args.classifier == 'digits':
        logging.info('Loading samples')
        sample_sets = deepclassifier.load_data(args.sample_files[0])
        train_set, validation_set, test_set = sample_sets
        if args.save_images:
            _save_images(train_set, validation_set, test_set)
        create_digit_classifier(train_set, validation_set, test_set,
                                args.epochs)
    elif args.classifier == 'crosses':
    # Load the sample set:
        sample_set = sample.SampleSet(
                    feature_extractor=preprocessing.FeatureExtractor())
        for filename in args.sample_files:
            sample_set.load_from_loader(sample.SampleLoader(filename))
        train_set, validation_set, test_set = \
            sample_set.partition_with_fractions([0.8, 0.1, 0.1])
        if args.save_images:
            _save_images(train_set, validation_set, test_set)
        create_crosses_classifier(train_set, validation_set, test_set,
                                  args.epochs)
    else:
        print('Wrong classifier type: {}'.format(args.classifier))
        sys.exit(1)

if __name__ == '__main__':
    main()
