# Eyegrade: grading multiple choice questions with a webcam
# Copyright (C) 2016 Jesus Arias Fisteus
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
# Some code derived from:
# https://github.com/mnielsen/neural-networks-and-deep-learning
# MIT License, copyright (c) 2012-2015 Michael Nielsen
#
from __future__ import print_function, division

import gzip
import cPickle
import json
import logging

import numpy as np
import theano
import theano.tensor as T
import theano.tensor.nnet as nnet
import theano.tensor.signal.pool
import theano.tensor.shared_randomstreams


# Configure Theano
## theano.config.device = 'gpu'
theano.config.floatX = 'float32'


class Classifier(object):
    """Neural networks classifier built on top of Theano.

    Derived from https://github.com/mnielsen/neural-networks-and-deep-learning
    MIT License
    Copyright (c) 2012-2015 Michael Nielsen

    """
    def __init__(self, layers=None, mini_batch_size=1, load_from_file=None):
        if layers is None and load_from_file is None:
            raise ValueError('Either layers or load_from_file must be set')
        elif layers is not None and load_from_file is not None:
            raise ValueError('Layers and load_from_file '
                             'are mutually exclusive')
        if layers is not None:
            self.layers = layers
        else:
            params  = self._load(load_from_file)
            Layer.apply_mini_batch_size(params['layers'], mini_batch_size)
            self.layers = Layer.create_layers(params['layers'])
        self.mini_batch_size = mini_batch_size
        self.params = [param for layer in self.layers
                             for param in layer.params]
        self.x = T.matrix("x")
        self.y = T.ivector("y")
        init_layer = self.layers[0]
        init_layer.set_inpt(self.x, self.x, self.mini_batch_size)
        for j in xrange(1, len(self.layers)):
            prev_layer, layer  = self.layers[j-1], self.layers[j]
            layer.set_inpt(prev_layer.output, prev_layer.output_dropout,
                           self.mini_batch_size)
        self.output = self.layers[-1].output
        self.output_dropout = self.layers[-1].output_dropout
        predict_x = T.matrix("x")
        self._predict = theano.function(
            [predict_x], self.layers[-1].y_out,
            givens={
                self.x: predict_x,
            }
        )

    @property
    def full_params(self):
        return {
            'layers': [layer.full_params for layer in self.layers],
            'hyperparams': {
                'mini_batch_size': self.mini_batch_size,
            },
        }

    def train(self, training_sample_set, epochs=40, eta=0.03, lmbda=0.0,
              validation_sample_set=None, test_sample_set=None):
        training_data = shared(training_sample_set.to_matrices())
        if validation_sample_set is not None:
            validation_data = shared(validation_sample_set.to_matrices())
        else:
            validation_data = None
        if test_sample_set is not None:
            test_data = shared(test_sample_set.to_matrices())
        else:
            validation_data = None
        self._train_sgd(training_data, epochs, eta, lmbda,
                        validation_data, test_data)

    def classify(self, sample):
        if self.mini_batch_size != 1:
            raise ValueError('mini_batch_size should be 1')
        features = sample.features
        x = features.reshape((1, len(features)))
        y = self._predict(x)
        return y[0]

    def save(self, filename):
        with gzip.GzipFile(filename, mode='w') as f:
            json.dump(self.full_params, f)

    @staticmethod
    def _load(filename):
        with gzip.GzipFile(filename) as f:
            return json.load(f)

    def _train_sgd(self, training_data, epochs, eta, lmbda,
                   validation_data, test_data):
        """Train the network using mini-batch stochastic gradient descent."""
        training_x, training_y = training_data
        validation_x, validation_y = validation_data
        test_x, test_y = test_data

        # compute number of minibatches for training, validation and testing:
        num_training_batches = _size(training_data) // self.mini_batch_size
        num_validation_batches = _size(validation_data) // self.mini_batch_size
        num_test_batches = _size(test_data) // self.mini_batch_size

        # define the (regularized) cost function, symbolic gradients,
        # and updates:
        l2_norm_squared = sum([(layer.w ** 2).sum() for layer in self.layers])
        cost = (self.layers[-1].cost(self)
                + 0.5 * lmbda * l2_norm_squared / num_training_batches)
        grads = T.grad(cost, self.params)
        updates = [(param, param-eta * grad)
                   for param, grad in zip(self.params, grads)]

        # define functions to train a mini-batch, and to compute the
        # accuracy in validation and test mini-batches:
        i = T.lscalar() # mini-batch index
        train_mb = theano.function(
            [i], cost, updates=updates,
            givens={
                self.x: training_x[i * self.mini_batch_size
                                   : (i + 1) * self.mini_batch_size],
                self.y: training_y[i * self.mini_batch_size
                                   : (i + 1) * self.mini_batch_size]
            }
        )
        validate_mb_accuracy = theano.function(
            [i], self.layers[-1].accuracy(self.y),
            givens={
                self.x: validation_x[i * self.mini_batch_size
                                     : (i + 1) * self.mini_batch_size],
                self.y: validation_y[i * self.mini_batch_size
                                     : (i + 1) * self.mini_batch_size]
            }
        )
        test_mb_accuracy = theano.function(
            [i], self.layers[-1].accuracy(self.y),
            givens={
                self.x: test_x[i * self.mini_batch_size
                               : (i + 1) * self.mini_batch_size],
                self.y: test_y[i * self.mini_batch_size
                               : (i + 1) * self.mini_batch_size]
            }
        )
        ## self.test_mb_predictions = theano.function(
        ##     [i], self.layers[-1].y_out,
        ##     givens={
        ##         self.x: test_x[i * self.mini_batch_size
        ##                        : (i + 1) * self.mini_batch_size]
        ##     }
        ## )
        # do the actual training:
        best_validation_accuracy = 0.0
        for epoch in xrange(epochs):
            for mini_batch_index in xrange(num_training_batches):
                iteration = num_training_batches * epoch + mini_batch_index
                if iteration % 1000 == 0:
                    logging.info('Training mini-batch number {}'\
                                 .format(iteration))
                c = train_mb(mini_batch_index) # drop return value cost_ij
                if (iteration + 1) % num_training_batches == 0:
                    validation_accuracy = np.mean(
                        [validate_mb_accuracy(j)
                         for j in xrange(num_validation_batches)])
                    logging.info('Epoch {}: validation accuracy {:.2%}'
                                 '; cost {}'\
                                 .format(epoch, validation_accuracy, c))
                    if validation_accuracy >= best_validation_accuracy:
                        logging.info('This is the best validation accuracy '
                                     'to date.')
                        best_validation_accuracy = validation_accuracy
                        best_iteration = iteration
                        if test_data:
                            test_accuracy = np.mean(
                                [test_mb_accuracy(j)
                                 for j in xrange(num_test_batches)])
                            logging.info('The corresponding test accuracy '
                                         'is {:.2%}'.format(test_accuracy))
        logging.info('Finished training network.')
        logging.info('Best validation accuracy of {:.2%} '
                     'obtained at iteration {}'\
                     .format(best_validation_accuracy, best_iteration))
        logging.info('Corresponding test accuracy of {:.2%}'\
                     .format(test_accuracy))


class ActivationFunc(object):
    """Activation functions for neurons."""
    @staticmethod
    def linear(z):
        return z

    @staticmethod
    def relu(z):
        return T.maximum(0.0, z)


class Layer(object):
    """Base class for all the layers.

    It implements the methods needed for persistency.

    """
    _activation_fn_map = {
        ActivationFunc.linear: 'linear',
        ActivationFunc.relu: 'relu',
        nnet.sigmoid: 'sigmoid',
    }

    _activation_fn_rev_map = {v: k for k, v in _activation_fn_map.iteritems()}

    @property
    def full_params(self):
        """The whole params and hyperparams that define this layer."""
        params = {
            'params': {p.name: p.eval().tolist() for p in self.params},
            'hyperparams': self.hyperparams,
            'class': {
                'module': self.__class__.__module__,
                'name': self.__class__.__name__,
            },
        }
        self._apply_map(params['hyperparams'], 'activation_fn',
                        self._activation_fn_map)
        return params

    def check_full_params(self, params):
        """Restore the params and check the hyperparams."""
        if (params['class']['module'] != self.__class__.__module__
            or params['class']['name'] != self.__class__.__name__):
            raise ValueError('Wrong class')
        if params['hyperparams'].viewkeys() != self.hyperparams.viewkeys():
            raise ValueError('Incompatible hyperparams')

    @staticmethod
    def create_layer(layer_params):
        if layer_params['class']['module'] != __name__:
            raise ValueError('Unable to create layer of module {}'\
                             .format(layer_params['class']['module']))
        # Decide the layer class to instantiate
        if layer_params['class']['name'] == 'ConvPoolLayer':
            class_ = ConvPoolLayer
        elif layer_params['class']['name'] == 'FullyConnectedLayer':
            class_ = FullyConnectedLayer
        elif layer_params['class']['name'] == 'SoftmaxLayer':
            class_ = SoftmaxLayer
        else:
            raise ValueError('Unknown class {}'\
                             .format(layer_params['class']['name']))
        # Prepare the constructor's parameters
        constructor_params = dict(layer_params['hyperparams'])
        constructor_params['full_params'] = layer_params
        Layer._apply_map(constructor_params, 'activation_fn',
                         Layer._activation_fn_rev_map)
        return class_(**constructor_params)

    @staticmethod
    def create_layers(layers_params):
        return [Layer.create_layer(p) for p in layers_params]

    @staticmethod
    def apply_mini_batch_size(layers_params, mini_batch_size):
        for layer in layers_params:
            if 'mini_batch_size' in layer['hyperparams']:
                layer['hyperparams']['mini_batch_size'] = mini_batch_size

    @staticmethod
    def _cast_param(name, params_dict):
        data = np.array(params_dict['params'][name], dtype=np.float32)
        return theano.shared(data, name=name, borrow=True)

    @staticmethod
    def _apply_map(dict_, key, map_):
        if key in dict_:
            try:
                dict_[key] = map_[dict_[key]]
            except KeyError:
                raise ValueError('Wrong value for key {}: '\
                                 .format(key, dict_[key]))


class ConvPoolLayer(Layer):
    """Combination of a convolutional and a max-pooling layer

    Derived from https://github.com/mnielsen/neural-networks-and-deep-learning
    MIT License
    Copyright (c) 2012-2015 Michael Nielsen

    """
    def __init__(self, filter_shape, image_shape, mini_batch_size,
                 poolsize=(2, 2),
                 activation_fn=nnet.sigmoid, full_params=None):
        """
        `filter_shape` is a tuple of length 4, whose entries are the number
        of filters, the number of input feature maps, the filter height,
        and the filter width.

        `image_shape` is a tuple of length 3, whose entries are the
        the number of input feature maps, the image
        height, and the image width.

        `poolsize` is a tuple of length 2, whose entries are the y and
        x pooling sizes.

        """
        self.filter_shape = filter_shape
        self.image_shape = image_shape
        self.mini_batch_size = mini_batch_size
        self.poolsize = poolsize
        self.activation_fn = activation_fn
        self.actual_image_shape = (mini_batch_size, image_shape[0],
                                   image_shape[1], image_shape[2])
        # Initialize weights and biases:
        if full_params is None:
            self.w = self._random_weights()
            self.b = self._random_biases()
        else:
            self.check_full_params(full_params)
            self.w = self._cast_param('w', full_params)
            self.b = self._cast_param('b', full_params)
        self.params = [self.w, self.b]

    @property
    def hyperparams(self):
        return {
            'filter_shape': self.filter_shape,
            'image_shape': self.image_shape,
            'mini_batch_size': self.mini_batch_size,
            'poolsize': self.poolsize,
            'activation_fn': self.activation_fn,
        }

    def set_inpt(self, inpt, inpt_dropout, mini_batch_size):
        self.inpt = inpt.reshape(self.actual_image_shape)
        conv_out = nnet.conv.conv2d(input=self.inpt,
                                    filters=self.w,
                                    filter_shape=self.filter_shape,
                                    image_shape=self.actual_image_shape)
        pooled_out = theano.tensor.signal.pool.pool_2d(
                                    input=conv_out,
                                    ds=self.poolsize,
                                    ignore_border=True)
        self.output = self.activation_fn(pooled_out
                                    + self.b.dimshuffle('x', 0, 'x', 'x'))
        # no dropout in the convolutional layers:
        self.output_dropout = self.output

    def _random_weights(self):
        n_out = (self.filter_shape[0] * np.prod(self.filter_shape[2:])
                 // np.prod(self.poolsize))
        return theano.shared(
            np.asarray(np.random.normal(loc=0, scale=np.sqrt(1.0 / n_out),
                                        size=self.filter_shape),
                                        dtype=theano.config.floatX),
            name='w',
            borrow=True
        )

    def _random_biases(self):
        return theano.shared(
            np.asarray(np.random.normal(loc=0, scale=1.0,
                                        size=(self.filter_shape[0], )),
                       dtype=theano.config.floatX),
            name='b',
            borrow=True
        )


class FullyConnectedLayer(Layer):
    """A fully connected layer

    Derived from https://github.com/mnielsen/neural-networks-and-deep-learning
    MIT License
    Copyright (c) 2012-2015 Michael Nielsen

    """
    def __init__(self, n_in, n_out, activation_fn=nnet.sigmoid,
                 p_dropout=0.0, full_params=None):
        self.n_in = n_in
        self.n_out = n_out
        self.activation_fn = activation_fn
        self.p_dropout = p_dropout
        # Initialize weights and biases:
        if full_params is None:
            self.w = self._random_weights()
            self.b = self._random_biases()
        else:
            self.check_full_params(full_params)
            self.w = self._cast_param('w', full_params)
            self.b = self._cast_param('b', full_params)
        self.params = [self.w, self.b]

    @property
    def hyperparams(self):
        return {
            'n_in': self.n_in,
            'n_out': self.n_out,
            'activation_fn': self.activation_fn,
            'p_dropout': self.p_dropout,
        }

    def set_inpt(self, inpt, inpt_dropout, mini_batch_size):
        self.inpt = inpt.reshape((mini_batch_size, self.n_in))
        self.output = self.activation_fn(
            (1 - self.p_dropout) * T.dot(self.inpt, self.w) + self.b)
        self.y_out = T.argmax(self.output, axis=1)
        self.inpt_dropout = _dropout_layer(
            inpt_dropout.reshape((mini_batch_size, self.n_in)), self.p_dropout)
        self.output_dropout = self.activation_fn(
            T.dot(self.inpt_dropout, self.w) + self.b)

    def accuracy(self, y):
        """Return the accuracy for the mini-batch."""
        return T.mean(T.eq(y, self.y_out))

    def _random_weights(self):
        return theano.shared(
            np.asarray(
                np.random.normal(
                    loc=0.0, scale=np.sqrt(1.0/self.n_out),
                    size=(self.n_in, self.n_out)),
                dtype=theano.config.floatX),
            name='w', borrow=True
        )

    def _random_biases(self):
        return theano.shared(
            np.asarray(np.random.normal(loc=0.0, scale=1.0,
                                        size=(self.n_out,)),
                       dtype=theano.config.floatX),
            name='b', borrow=True
        )


class SoftmaxLayer(Layer):
    """A softmax output layer

    Derived from https://github.com/mnielsen/neural-networks-and-deep-learning
    MIT License
    Copyright (c) 2012-2015 Michael Nielsen

    """
    def __init__(self, n_in, n_out, p_dropout=0.0, full_params=None):
        self.n_in = n_in
        self.n_out = n_out
        self.p_dropout = p_dropout
        # Initialize weights and biases:
        if full_params is None:
            self.w = self._random_weights()
            self.b = self._random_biases()
        else:
            self.check_full_params(full_params)
            self.w = self._cast_param('w', full_params)
            self.b = self._cast_param('b', full_params)
        self.params = [self.w, self.b]

    @property
    def hyperparams(self):
        return {
            'n_in': self.n_in,
            'n_out': self.n_out,
            'p_dropout': self.p_dropout,
        }

    def set_inpt(self, inpt, inpt_dropout, mini_batch_size):
        self.inpt = inpt.reshape((mini_batch_size, self.n_in))
        self.output = nnet.softmax((1-self.p_dropout)
                                   * T.dot(self.inpt, self.w) + self.b)
        self.y_out = T.argmax(self.output, axis=1)
        self.inpt_dropout = _dropout_layer(
            inpt_dropout.reshape((mini_batch_size, self.n_in)), self.p_dropout)
        self.output_dropout = nnet.softmax(T.dot(self.inpt_dropout, self.w)
                                           + self.b)

    def cost(self, net):
        "Return the log-likelihood cost."
        return -T.mean(T.log(self.output_dropout)[T.arange(net.y.shape[0]),
                                                  net.y])

    def accuracy(self, y):
        """Return the accuracy for the mini-batch."""
        return T.mean(T.eq(y, self.y_out))

    def _set_params(self, params_dict):
        self.w = theano.shared(np.array(params_dict['w'], dtype=np.float32),
                               name='w', borrow=True)
        self.b = theano.shared(np.array(params_dict['b'], dtype=np.float32),
                               name='b', borrow=True)

    def _random_weights(self):
        return theano.shared(np.zeros((self.n_in, self.n_out),
                                       dtype=theano.config.floatX),
                             name='w', borrow=True)

    def _random_biases(self):
        return theano.shared(np.zeros((self.n_out, ),
                                      dtype=theano.config.floatX),
                             name='b', borrow=True)


class PickledSampleSet(object):
    """Simple class intended to be compatible with samples.SampleSet."""
    def __init__(self, data):
        self.data = data

    def __len__(self):
        return self.data[0].shape[0]

    def __iter__(self):
        for feature_row, label in zip(self.data[0], self.data[1]):
            yield PickledSample(feature_row, label)

    def to_matrices(self):
        return self.data


class PickledSample(object):
    """Simple class intended to be compatible with samples.Sample."""
    def __init__(self, features, label):
        self.features = features
        self.label = label

    def check_label(self, label):
        return self.label == label


def load_data(filename):
    """Loads the training dataset from a cPickle file.

    The input file should be as defined in:
    https://github.com/mnielsen/neural-networks-and-deep-learning

    (e.g. the files data/mnist.pkl.gz or data/mnist_expanded.pkl.gz)

    """
    with gzip.open(filename, mode='rb') as f:
        training_data, validation_data, test_data = cPickle.load(f)
    return (PickledSampleSet(training_data),
            PickledSampleSet(validation_data),
            PickledSampleSet(test_data))


# Other utility functions
def shared(data):
    """Place the data into shared variables.

    This allows Theano to copy the data to the GPU, if one is available.

    """
    shared_x = theano.shared(
        np.asarray(data[0], dtype=theano.config.floatX), borrow=True)
    shared_y = theano.shared(
        np.asarray(data[1], dtype=theano.config.floatX), borrow=True)
    return shared_x, T.cast(shared_y, "int32")

def _size(data):
    """Return the size of the dataset `data`."""
    return data[0].get_value(borrow=True).shape[0]

def _dropout_layer(layer, p_dropout):
    srng = theano.tensor.shared_randomstreams.RandomStreams(
                                  np.random.RandomState(0).randint(999999))
    mask = srng.binomial(n=1, p=1-p_dropout, size=layer.shape)
    return layer * T.cast(mask, theano.config.floatX)
