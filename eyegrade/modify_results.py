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

utils.EyegradeException.register_error('bad_choice_letter',
     "Choices must be specified as letters 'a', 'b',...")

def choice_letter_to_num(letter):
    if len(letter) == 1 and ord(letter) >= 97 and ord(letter) <= 122:
        return ord(letter) - 96
    else:
        raise utils.EyegradeException(None, key='bad_choice_letter')

def read_cmd_options():
    parser = OptionParser(usage = 'usage: %prog [options] <results_filename>'
                          ' <exam_config> modification_1 [modification_2...]\n'
                          'Modifications are specified by:\n'
                          '- Invalidated questions: /1, /2, etc.\n'
                          '    /1 invalidates the first question in model 0.\n'
                          '- Set choice to correct: +1b, +1c, etc.\n'
               '    +2c sets the 3rd choice of the 2nd question of model 0'
                          ' as correct.',
                          version = utils.program_name + ' ' + utils.version)
    parser.add_option('-o', '--output-file', dest='output_file',
                      default=None, help='store the output in the given file')
    (options, args) = parser.parse_args()
    if len(args) < 3:
        parser.error('Required parameters expected')
    options.results_file = args[0]
    options.exam_config = args[1]
    options.invalidate = []
    options.set_correct = {}
    try:
        for value in args[2:]:
            if value.startswith('/'):
                options.invalidate.append(int(value[1:]))
            elif value.startswith('+'):
                q = int(value[1:-1])
                if not q in options.set_correct:
                    options.set_correct[q] = []
                    options.set_correct[q].append( \
                        choice_letter_to_num(value[-1]))
            else:
                parser.error('Bad modification spec')
    except ValueError:
        parser.error('Bad modification spec')
    return options, args

def modify_results(results_filename, exam_config_filename,
                   output_filename, invalidate, set_correct):
    results = utils.read_results(results_filename)
    exam_data = utils.ExamConfig(exam_config_filename)
    for result in results:
        modify(result, exam_data, invalidate, set_correct)
    utils.write_results(results, output_filename, utils.config['csv-dialect'])

def modify(result, exam_data, invalidate, set_correct):
    answers = result['answers']
    solutions = exam_data.solutions[result['model']]
    permutations = exam_data.permutations[result['model']]
    assert(len(answers) == len(permutations))
    assert(len(answers) == len(solutions))
    good = 0
    bad = 0
    for i in range(0, len(answers)):
        q = permutations[i][0]
        if not q in invalidate:
            if answers[i] > 0:
                if answers[i] == solutions[i]:
                    good += 1
                elif (q in set_correct
                      and permutations[i][1][answers[i] - 1] in set_correct[q]):
                    good += 1
                else:
                    bad += 1
    result['good'] = good
    result['bad'] = bad
    blank = exam_data.num_questions - good - bad
    if exam_data.score_weights is not None and result['score'] is not None:
        result['score'] = float(good * exam_data.score_weights[0]
                                - bad * exam_data.score_weights[1]
                                - blank * exam_data.score_weights[2])

def main():
    try:
        options, args = read_cmd_options()
        modify_results(options.results_file, options.exam_config,
                       options.output_file, options.invalidate,
                       options.set_correct)
    except utils.EyegradeException as ex:
        print >>sys.stderr, ex

if __name__ == '__main__':
    main()
