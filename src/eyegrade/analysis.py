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

#
# Module for analysis of results
#
from optparse import OptionParser

# Local imports
import utils

def stats_for_question(results, question, num_options = None):
    """Returns a tuple with the count of answers (blank, opt1,
       opt2,...) for the specified question number. Use 0 for the
       first question (instead of 1). If num_options is provided,
       the resulting tuple will have num_options + 1 components, even
       if it needed more. If not provided, the number of components is
       decided according to the maximum option answered."""
    answers = [r['answers'][question] for r in results]
    if num_options is None:
        num_options = max(answers)
        if num_options == -1:
            num_options = 0
    counters = [0 for i in range(0, num_options + 1)]
    for answer in answers:
        if answer == 0 or answer == -1:
            counters[0] += 1
        elif answer <= num_options:
            counters[answer] += 1
    return counters

def stats_by_question(results, num_questions):
    return [stats_for_question(results, i) for i in range(0, num_questions)]

def stats_for_model(results, num_questions, model=None):
    """Returns a tuple with the count of (correct, incorrect, blank) answers

       Applies to the given model. Model is an uppercase letter. If
       model is None, overall results are returned.

    """
    if model is None:
        data = [(r['good'], r['bad']) for r in results]
    else:
        data = [(r['good'], r['bad']) for r in results if r['model'] == model]
    if data != []:
        good = float(sum([d[0] for d in data])) / len(data)
        bad = float(sum([d[1] for d in data])) / len(data)
        blank = num_questions - good - bad
    else:
        good = 0
        bad = 0
        blank = 0
    return (len(data), good, bad, blank)

def stats_by_model(results, num_questions, models):
    stats = ([stats_for_model(results, num_questions, None)]
             + [stats_for_model(results, num_questions, model) \
                    for model in models])
    return stats

def print_stats_by_question(stats):
    for i, answers in enumerate(stats):
        count = sum(answers)
        print 'Question %d'%(i + 1)
        for j in range(1, len(answers)):
            percentage = float(answers[j]) * 100 / count
            if answers[j] > 0:
                data = (chr(64 + j), answers[j], percentage)
                print '  - Option %s: %d (%.1f%%)'%data
        percentage = float(answers[0]) * 100 / count
        print '  - Not answered: %d (%.1f%%)'%(answers[0], percentage)

def plot_stats_by_question(stats):
    try:
        import numpy as np
        import matplotlib.pyplot as plt
    except:
        # matplotlib or numpy not installed; just return
        return
    colors = 'bgrcmy'
    numq = len(stats)
    xvals = np.arange(numq)
    max_len = max([len(s) for s in stats])
    width = 0.35
    base = np.zeros(numq)
    for i in range(1, max_len):
        yvals = np.array([(s[i] if len(s) > i else 0) for s in stats])
        plt.bar(xvals, yvals, width, base, color = colors[(i - 1)%len(colors)],
                label = 'Opt. ' + chr(64 + i))
        base += yvals
    plt.ylabel('Number of answers')
    plt.xlabel('Question number')
    plt.title('Answers per question')
    plt.xticks(xvals + width / 2.0, range(1, numq + 1))
    plt.legend(bbox_to_anchor = (0.0, 1.02, 1.0, 0.102), loc = 3,
               ncol = max_len, mode = "expand", borderaxespad = 0.0)
    plt.show()

def print_stats_by_model(stats):
    for i, data in enumerate(stats):
        num_questions = sum(data[1:])
        if i > 0:
            print 'Model %s; number of exams: %d'%(chr(65 + i - 1), data[0])
        else:
            print 'All the exams; number of exams: %d'%data[0]
        if data[0] > 0:
            if num_questions > 0:
                percentages = (float(data[1]) * 100 / num_questions,
                               float(data[2]) * 100 / num_questions,
                               float(data[3]) * 100 / num_questions)
            else:
                percentages = (0, 0, 0)
            print '    - Correct: %.1f (%.1f%%)'%(data[1], percentages[0])
            print '    - Incorrect: %.1f (%.1f%%)'%(data[2], percentages[1])
            print '    - Not answered: %.1f (%.1f%%)'%(data[3], percentages[2])

def analyze(results_filenames, exam_cfg_filename):
    exam_data = utils.ExamConfig(exam_cfg_filename)
    results = []
    for results_file in results_filenames:
        results.extend(utils.read_results(results_file, exam_data.permutations))
    stats_q = stats_by_question(results, exam_data.num_questions)
    print_stats_by_question(stats_q)
    print
    stats_m = stats_by_model(results, exam_data.num_questions,
                             exam_data.models)
    print_stats_by_model(stats_m)
    plot_stats_by_question(stats_q)
    return results

def read_cmd_options():
    parser = OptionParser(usage = ('usage: %prog [options] <results_file1>'
                                   ' [<results_file2>...] <exam-config-file>'),
                          version = utils.program_name + ' ' + utils.version)
    (options, args) = parser.parse_args()
    if len(args) < 2:
        parser.error('Required parameters expected')
    options.results_files = args[:-1]
    options.exam_config = args[-1]
    return options, args

def main():
    options, args = read_cmd_options()
    analyze(options.results_files, options.exam_config)

if __name__ == "__main__":
    main()
