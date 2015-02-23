import cv2, sys
import numpy as np
from os import walk, path

from . import preprocessing as imp

#################################################################################
#########################DATASET LOADING FUNCTIONS###############################
#################################################################################

def count(n,d):
    count=0
    for i in d:
        if i==n:
            count+=1
    return count

'''
This function obtains the label associated to an image.
'''
def get_label(image_name, labels_file):
	try:
		with open(labels_file) as f:
			for line_number, line in enumerate(f,1):
				word = line.strip()
				if image_name in word:
					return word.split('\t')[1]
	except e:
		print 'Error:', e
		return -1

'''
This function loads the dataset prepared for the classifier.
It receives de folder with the images and a text file with all
the labels for the digits.
'''
def load_dataset(folder, labels):
    f = []
    for (dirpath, dirnames, filenames) in walk(folder):
        f.extend(filenames)
        break

    m = len(f)

    #Initialize empty training set
    training_data = np.ndarray(shape=(m,imp.SZ*imp.SZ), dtype='float32')
    training_labels = np.ndarray(shape=(m,1), dtype='float32')

    for index, filename in enumerate(f):
        try:
            if folder[-1] == '/':
                img = cv2.imread(folder + filename, 0)
            else:
                img = cv2.imread(folder + '/' + filename, 0)
            sample = imp.image_preprocessing(img)
            training_data[index] = sample
            training_labels[index] = float(get_label(filename, labels))
        except:
            print "Error con '%s'" % filename

    print 'Displaying distribution of the digits in the dataset...'
    for i in range(10):
        print i, '->', count(i,training_labels)

    return (training_data, training_labels)


#################################################################################
#########################CLASSIFIER CREATION FUNCTIONS###########################
#################################################################################
try:
    digits_folder = sys.argv[1]
    labels_file = sys.argv[2]
except:
    print 'Usage: python create_classifier.py [digits_folder] [labels_textfile]'
    sys.exit(0)

'''
Function that tests a large range of parammeters for the SVM classifier
and returns the one with optimal results. Only use this function the first
time you are testing the best parameters for the SVM.
'''
def test_parameters(x_train, y_train, x_test, y_test):

    scores = []
    C=[]
    gamma=[]
    for i in range(21): C.append(10.0**(i-5))
    for i in range(17): gamma.append(10**(i-14))

    parameters = list(itertools.product(C, gamma))
    for param in parameters:

        svm_params = dict( kernel_type = cv2.SVM_RBF,
            svm_type = cv2.SVM_C_SVC,
            C=param[0], gamma=param[1])

        svm = cv2.SVM()
        svm.train(x_train,y_train, params=svm_params)
        result = svm.predict_all(x_test)
        mask = result==y_test
        correct = np.count_nonzero(mask)
        score = correct*100.0/result.size

        scores.append(score)
        print 'C: %s, Gamma: %s, Score: %s' % (str(param[0]), str(param[1]), score)

    max_score = max(scores)
    index_max = scores.index(max(scores))
    optimal = parameters[index_max]
    return (optimal, max_score)

'''
Main function for creating the SVM classifier
'''
def create_SVM(C=10, gamma=0.01, classifier_name='ocr_svm.dat'):
    print 'Loading dataset...'
    dataset, labels = load_dataset(digits_folder, labels_file)
    print 'Dataset loaded succesfully!'

    #100% of images are for training
    trainData = dataset[:][:]
    trainLabels = labels[:][:]

    m = trainData.shape[0] # Total size
    n = trainData.shape[1] # Number of features

    svm_params = dict(kernel_type = cv2.SVM_RBF,
                    svm_type = cv2.SVM_C_SVC, C=C, gamma=gamma)

    print 'Creating classifier...'
    svm = cv2.SVM()
    svm.train(trainData, trainLabels, params=svm_params)
    svm.save(classifier_name)
    print 'Classifier created succesfully and saved as %s!' % classifier_name

    return svm

create_SVM()

