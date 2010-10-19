#
# Module for analysis of results
#
import csv

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
        answers = [int(n) for n in result['answers'].split('/')]
        if permutations != []:
            answers = __permute_answers(answers, permutations[result['model']])
        result['answers'] = answers

def stats_for_question(results, question, num_options = None):
    """Returns the tuple with the count of answers (blank, opt1,
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

def print_stats_by_question(stats):
    for i, answers in enumerate(stats):
        count = sum(answers)
        print 'Question %d'%(i + 1)
        for j in range(1, len(answers)):
            percentage = float(answers[j]) * 100 / count
            print '  - Option %d: %d (%.1f%%)'%(j, answers[j], percentage)
        percentage = float(answers[0]) * 100 / count
        print '  - Blank: %d (%.1f%%)'%(answers[0], percentage)

def analyze(results_filename, exam_cfg_filename):
    exam_data = utils.ExamConfig(exam_cfg_filename)
    results = read_results(results_filename)
    process_results(results, exam_data.permutations)
    stats = stats_by_question(results, exam_data.num_questions)
    print_stats_by_question(stats)
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
