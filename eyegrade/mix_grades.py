# Eyegrade: grading multiple choice questions with a webcam
# Copyright (C) 2010-2011 Jesus Arias Fisteus
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

from optparse import OptionParser
import sys

from . import utils

def read_cmd_options():
    parser = OptionParser(usage = 'usage: %prog [options] <results_filename>'
                                  ' <ids_filename>',
                          version = utils.program_name + ' ' + utils.version)
    parser.add_option('-m', '--dump-model', dest='dump_model',
                      action='store_true', default=False,
                      help = 'add exam model')
    parser.add_option('-r', '--round', dest='round_score', default=-1,
                      type=int,
                      help='round score to the given number of digits')
    parser.add_option('-o', '--output-file', dest='output_file',
                      default=None, help='store the output in the given file')
    parser.add_option('-i', '--ignore-missing', action='store_false',
                      dest = 'dump_missing', default=True,
                      help = 'ignore grades of students not in the '
                              'student list')
    (options, args) = parser.parse_args()
    if len(args) != 2:
        parser.error('Required parameters expected')
    return options, args

def mix_grades(results_filename, ids_filename, output_filename,
               dump_missing, round_score, dump_model):
    results = utils.mix_results(results_filename, ids_filename,
                                dump_missing, round_score, dump_model)
    if output_filename is not None:
        file_ = open(output_filename, 'ab')
    else:
        file_ = sys.stdout
    utils.write_grades(results, file_, utils.config['csv-dialect'])
    if output_filename is not None:
        file_.close()

def main():
    options, args = read_cmd_options()
    mix_grades(args[0], args[1], options.output_file,
               options.dump_missing, options.round_score, options.dump_model)

if __name__ == '__main__':
    main()
