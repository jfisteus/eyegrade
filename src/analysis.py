#
# Module for analysis of results
#
import csv
import sys

# For plots
import numpy as np
import matplotlib.pyplot as plt

# Local imports
import utils

keys = ['seq-num', 'student-id', 'model', 'good', 'bad', 'unknown', 'answers']

def read_results(filename):
    csvfile = open(filename, 'rb')
    dialect = csv.Sniffer().sniff(csvfile.read(1024))
    csvfile.seek(0)
    reader = csv.DictReader(csvfile, fieldnames = keys, dialect = dialect)
    entries = [entry for entry in reader]
    csvfile.close()
    return entries

def process_results(results, permutations = []):
    for result in results:
        if result['model'].isdigit():
            result['model'] = int(result['model'])
        else:
            result['model'] = ord(result['model']) - ord('A')
        result['good'] = int(result['good'])
        result['bad'] = int(result['bad'])
        result['unknown'] = int(result['unknown'])
        answers = [int(n) for n in result['answers'].split('/')]
        if permutations != []:
            answers = __permute_answers(answers, permutations[result['model']])
        result['answers'] = answers

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
    counters = [0 for i in range(0, num_options + 1)]
    for answer in answers:
        if answer <= num_options:
            counters[answer] += 1
    return counters

def stats_by_question(results, num_questions):
    return [stats_for_question(results, i) for i in range(0, num_questions)]

def stats_for_model(results, model, num_questions):
    """Returns a tuple with the count of (correct, incorrect, blank)
       answers for the given model. Model is an integer, 0 for A, 1
       for B, etc."""
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

def stats_by_model(results, num_questions, num_models):
    return [stats_for_model(results, i, num_questions) \
                for i in range(0, num_models)]

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
    colors = 'bgrcmy'
    numq = len(stats)
    xvals = np.arange(numq)
    max_len = max([len(s) for s in stats])
    width = 0.35
    base = np.zeros(numq)
    for i in range(1, max_len):
        yvals = np.array([(s[i] if len(s) > i else 0) for s in stats])
        plt.bar(xvals, yvals, width, base, colors[(i - 1)%len(colors)],
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
        num_questions = sum(data)
        print 'Model %s; number of exams: %d'%(chr(65 + i), data[0])
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

def analyze(results_filename, exam_cfg_filename):
    exam_data = utils.ExamConfig(exam_cfg_filename)
    results = read_results(results_filename)
    process_results(results, exam_data.permutations)
    stats_q = stats_by_question(results, exam_data.num_questions)
    print_stats_by_question(stats_q)
    print
    stats_m = stats_by_model(results, exam_data.num_questions,
                             exam_data.num_models)
    print_stats_by_model(stats_m)
    plot_stats_by_question(stats_q)
    return results

def __permute_answers(answers, permutation):
    assert(len(answers) == len(permutation))
    permutted = [0] * len(answers)
    for i, option in enumerate(answers):
        if option == 0:
            resolved_option = 0
        else:
            resolved_option = permutation[i][1][option - 1]
        permutted[permutation[i][0] - 1] = resolved_option
    return permutted

def main():
    analyze(sys.argv[1], sys.argv[2])

if __name__ == "__main__":
    main()
