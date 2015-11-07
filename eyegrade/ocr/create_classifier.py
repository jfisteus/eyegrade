# Eyegrade: grading multiple choice questions with a webcam
# Copyright (C) 2015 Rodrigo Arguello
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

import sys
import os
import itertools
import numpy as np
import cv2

from . import preprocessing as imp


def count(n, d):
    count=0
    for i in d:
        if i==n:
            count+=1
    return count

def load_labels(labels_file):
    """Get the labels of all the images as a dictionary."""
    labels = {}
    with open(labels_file) as f:
        for line in f:
            parts = line.strip().split('\t')
            labels[parts[0]] = parts[1]
    return labels

def load_dataset(folder, labels_dict):
    """Loads the dataset and prepares it for the classifier.

    It receives de folder with the images and a text file with all
    the labels for the digits.

    """
    f = []
    for (dirpath, dirnames, filenames) in os.walk(folder):
        f.extend(filenames)
        break
    m = len(f)
    # Initialize an empty training set:
    training_data = np.ndarray(shape=(m, imp.SZ * imp.SZ), dtype='float32')
    training_labels = np.ndarray(shape=(m, 1), dtype='float32')
    for index, filename in enumerate(f):
        img = cv2.imread(os.path.join(folder, filename), 0)
        sample = imp.image_preprocessing(img)
        training_data[index] = sample
        training_labels[index] = float(labels_dict[filename])
    print 'Displaying distribution of the digits in the dataset...'
    for i in range(10):
        print i, '->', count(i,training_labels)
    return (training_data, training_labels)

def test_parameters(x_train, y_train, x_test, y_test):
    """Tests a large range of parammeters for the SVM classifier.

    Returns the one with optimal results.
    Use this function only the first
    time you are testing the best parameters for the SVM.

    """
    scores = []
    C = []
    gamma = []
    for i in range(21):
        C.append(10.0 ** (i - 5))
    for i in range(17):
        gamma.append(10 ** (i - 14))
    parameters = list(itertools.product(C, gamma))
    for param in parameters:
        svm_params = {
            'kernel_type': cv2.SVM_RBF,
            'svm_type': cv2.SVM_C_SVC,
            'C': param[0],
            'gamma': param[1],
        }
        svm = cv2.SVM()
        svm.train(x_train, y_train, params=svm_params)
        result = svm.predict_all(x_test)
        mask = (result == y_test)
        correct = np.count_nonzero(mask)
        score = correct * 100.0 / result.size
        scores.append(score)
        print 'C: {1}, Gamma: {2}, Score: {3}'\
          .format(param[0], param[1], score)
    max_score = max(scores)
    index_max = scores.index(max(scores))
    optimal = parameters[index_max]
    return (optimal, max_score)

def create_SVM(digits_folder, labels_file,
               C=10, gamma=0.01, classifier_name='ocr_svm.dat.gz'):
    """Creates the SVM classifier."""
    print 'Loading dataset...'
    labels_dict = load_labels(labels_file)
    dataset, labels = load_dataset(digits_folder, labels_dict)
    print 'Dataset loaded succesfully!'
    # All the images are for training
    trainData = dataset[:][:]
    trainLabels = labels[:][:]
    ## m = trainData.shape[0] # Total size
    ## n = trainData.shape[1] # Number of features
    svm_params = dict(kernel_type = cv2.SVM_RBF,
                      svm_type = cv2.SVM_C_SVC, C=C, gamma=gamma)
    print 'Creating classifier...'
    svm = cv2.SVM()
    svm.train(trainData, trainLabels, params=svm_params)
    svm.save(classifier_name)
    print 'Classifier created succesfully and saved as %s!' % classifier_name
    return svm

def main():
    try:
        digits_folder = sys.argv[1]
        labels_file = sys.argv[2]
    except:
        print ('Usage: python create_classifier.py digits_folder '
               'labels_textfile')
        sys.exit(0)
    create_SVM(digits_folder, labels_file)

if __name__ == '__main__':
    main()
