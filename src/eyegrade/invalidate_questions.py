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

import utils

def read_cmd_options():
    parser = OptionParser(usage = 'usage: %prog [options] <results_filename>'
                          ' <exam_config> question_1 [question_2 ...]\n'
                          'Questions are specified by their number 1...N'
                          ' in the model 0 exam.',
                          version = utils.program_name + ' ' + utils.version)
    parser.add_option('-o', '--output-file', dest='output_file',
                      default=None, help='store the output in the given file')
    (options, args) = parser.parse_args()
    if len(args) < 3:
        parser.error('Required parameters expected')
    options.results_file = args[0]
    options.exam_config = args[1]
    options.questions = [int(q) for q in args[2:]]
    return options, args

def invalidate_questions(results_filename, exam_config_filename,
                         output_filename, questions):
    config = utils.read_config()
    results = utils.read_results(results_filename)
    exam_data = utils.ExamConfig(exam_config_filename)
    for result in results:
        invalidate(result, exam_data, questions)
    utils.write_results(results, output_filename, config['csv-dialect'])

def invalidate(result, exam_data, questions):
    answers = result['answers']
    solutions = exam_data.solutions[result['model']]
    permutations = exam_data.permutations[result['model']]
    assert(len(answers) == len(permutations))
    assert(len(answers) == len(solutions))
    good = 0
    bad = 0
    for i in range(0, len(answers)):
        if not permutations[i][0] in questions:
            if answers[i] > 0:
                if answers[i] == solutions[i]:
                    good += 1
                else:
                    bad += 1
        else:
            answers[i] = -1
    result['good'] = good
    result['bad'] = bad

def main():
    options, args = read_cmd_options()
    invalidate_questions(options.results_file, options.exam_config,
                         options.output_file, options.questions)

if __name__ == '__main__':
    main()
