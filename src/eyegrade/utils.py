import ConfigParser
import csv
import os
import locale
import codecs
import sys
import random
import re

program_name = 'eyegrade'
version = '0.1.7'
version_status = 'alpha'

re_model_letter = re.compile('[a-zA-Z]')

csv.register_dialect('tabs', delimiter = '\t')

keys = ['seq-num', 'student-id', 'model', 'good', 'bad', 'unknown', 'answers']

def guess_data_dir():
    path = os.path.split(os.path.realpath(__file__))[0]
    if path.endswith('.zip'):
        path = os.path.split(path)[0]
    paths_to_try = [os.path.join(path, 'data'),
                    os.path.join(path, '..', 'data'),
                    os.path.join(path, '..', '..', 'data'),
                    os.path.join(path, '..', '..', '..', 'data')]
    for p in paths_to_try:
        if os.path.isdir(p):
            return os.path.abspath(p)
    raise Exception('Data path not found!')

data_dir = guess_data_dir()

def resource_path(file_name):
    return os.path.join(data_dir, file_name)

def read_results(filename, permutations = {}):
    """Parses an eyegrade results file.

       Results are returned as a list of dictionaries with the keys
       stored in the 'keys' variable. If 'permutations' is provided,
       answers are un-shuffled.

    """
    results = __read_results_file(filename)
    for result in results:
        if result['model'].isdigit():
            result['model'] = ord(65 + int(result['model']))
        else:
            result['model'] = check_model_letter(result['model'])
        result['good'] = int(result['good'])
        result['bad'] = int(result['bad'])
        result['unknown'] = int(result['unknown'])
        answers = [int(n) for n in result['answers'].split('/')]
        if len(permutations) > 0:
            answers = __permute_answers(answers, permutations[result['model']])
        result['answers'] = answers
    return results

def check_model_letter(model):
    if re_model_letter.match(model):
        return model.upper()
    else:
        raise Exception('Incorrect model letter: ' + model)

def read_student_ids(filename, with_names=False):
    """Reads the list of student IDs from a CSV-formatted file.

       The format of the file is flexible: separators can be either
       tabs or commas. Student ids must be in the first column. The
       second columns, if present, must be the name of the student.

    """
    csvfile = open(filename, 'rb')
    if csvfile.readline().strip().isdigit():
        csv.register_dialect('student-id', delimiter=',')
        dialect = csv.get_dialect('student-id')
    else:
        try:
            csvfile.seek(0)
            dialect = csv.Sniffer().sniff(csvfile.read(1024))
        except:
            raise Exception('Error while processing the students ID list')
    csvfile.seek(0)
    reader = csv.reader(csvfile, dialect)
    if not with_names:
        student_ids = [row[0] for row in reader]
    else:
        student_ids = {}
        for row in reader:
            sid = row[0]
            if len(row) > 1:
                name = row[1]
                student_ids[sid] = unicode(name, locale.getpreferredencoding())
            else:
                name = None
                student_ids[sid] = None
    csvfile.close()
    return student_ids

def mix_results(results_filename, student_list_filename, dump_missing):
    """Returns a list of tuples student_id, good_answers, bad_answers.

       Receives the names of the files with results and student list.
       If 'dump_missing' is True, grades of students not in the
       student list are dumped at the end of the list.

    """
    mixed_grades = []
    results = results_by_id(read_results(results_filename))
    ids = read_student_ids(student_list_filename)
    for student_id in ids:
        if student_id in results:
            mixed_grades.append((student_id, results[student_id][0],
                                 results[student_id][1]))
        else:
            mixed_grades.append((student_id, '', ''))
    if dump_missing:
        for student_id in results:
            if not student_id in ids:
                mixed_grades.append((student_id, results[student_id][0],
                                     results[student_id][1]))
    return mixed_grades

def write_grades(grades, file_, csv_dialect):
    """Writes the given grades to a file.

       Results are a list of tuples student_id, good_answers, bad_answers.

    """
    writer = csv.writer(file_, dialect = csv_dialect)
    for grade in grades:
        writer.writerow(grade)

def results_by_id(results):
    """Returns a dictionary student_id -> (num_good_answers, num_bad_answers).

       Results must be formatted as returned by read_results().

    """
    id_dict = {}
    for r in results:
        id_dict[r['student-id']] = (r['good'], r['bad'])
    return id_dict

def read_config():
    """Reads the general config file and returns the resulting config object.

    """
    config = {'camera-dev': '-1',
              'save-filename-pattern': 'exam-{student-id}-{seq-number}.png',
              'csv-dialect': 'excel'}
    parser = ConfigParser.SafeConfigParser()
    parser.read([os.path.expanduser('~/.eyegrade.cfg'),
                 os.path.expanduser('~/.camgrade.cfg')])
    if 'default' in parser.sections():
        for option in parser.options('default'):
            config[option] = parser.get('default', option)
    if not config['csv-dialect'] in csv.list_dialects():
        config['csv-dialect'] = 'excel'
    if 'error-logging' in config and config['error-logging'] == 'yes':
        config['error-logging'] = True
    else:
        config['error-logging'] = False
    config['camera-dev'] = int(config['camera-dev'])
    return config

def __read_results_file(filename):
    csvfile = open(filename, 'rb')
    dialect = csv.Sniffer().sniff(csvfile.read(1024))
    csvfile.seek(0)
    reader = csv.DictReader(csvfile, fieldnames = keys, dialect = dialect)
    entries = [entry for entry in reader]
    csvfile.close()
    return entries

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

def encode_model(model, num_tables, num_answers):
    """Given the letter of the model, returns the infobits pattern.

       It is formatted as an array of booleans string where the pos. 0
       is the one that goes in the column of the table at the left.
       The length of the string is 'num_tables' * 'num_answers', where
       'num_tables' is the number of answer tables and 'num_tables'
       the number of answers per question. The 'model' must be a
       capital ASCII letter.

    """
    if len(model) != 1 or model < 'A' or model > 'Z':
        raise Exception('Incorrect model letter')
    if model > 'H':
        raise Exception('Model is currently limited to A - H')
    model_num = ord(model) - 65
    num_bits = num_tables * num_answers
    if model_num >= 2 ** (num_bits - 1):
        raise Exception('Model number too big given the number of answers')
    seed = __int_to_bin(model_num, 3, True)
    seed[2] = not seed[2]
    seed.append(reduce(lambda x, y: x ^ y, seed))
    seed[2] = not seed[2]
    bit_list = seed * (1 + (num_bits - 1) // 4)
    return bit_list[:num_tables * num_answers]

def decode_model(bit_list):
    """Given the bits that encode the model, returns the associated letter.

       It decoding/checksum fails, None is returned. The list of bits must
       be a list of boolean variables.

    """
    # x3 = x0 ^ x1 ^ not x2; x0-x3 == x4-x7 == x8-x11 == ...
    valid = False
    if len(bit_list) == 3:
        valid = True
    elif len(bit_list) >= 4:
        if (bit_list[3] == bit_list[0] ^ bit_list[1] ^ (not bit_list[2])):
            valid = True
            for i in range(4, len(bit_list)):
                if bit_list[i] != bit_list[i - 4]:
                    valid = False
                    break
    if valid:
        return chr(65 + bit_list[0] | bit_list[1] << 1 | bit_list[2] << 2)
    else:
        return None

def __int_to_bin(n, num_digits, reverse = False):
    """Returns the binary representation of a number as a list of booleans.

       If the number of digits is less than 'num_digits', it is
       completed with False in the most-significative side. If
       'reverse' is True returns the least significative bit in the
       first position of the string.

       There is a bin() function in python >= 2.6, but by now we want
       the program to be compatible with 2.5. Anyway, the behaviour of
       that function is different.

    """
    bin = []
    while n > 0:
        n, r = divmod(n, 2)
        bin.append(True if r else False)
    if len(bin) < num_digits:
        bin.extend([False] * (num_digits - len(bin)))
    if reverse:
        return bin
    else:
        return bin[::-1]

def read_file(file_name):
    """Returns contents of a file as a Unicode string using terminal locale.

    """
    file_ = codecs.open(file_name, 'r', locale.getpreferredencoding())
    data = file_.read()
    file_.close()
    return data

def write_file(file_name, unicode_text):
    """Writes a Unicode string in a file using terminal locale.

    """
    file_ = codecs.open(file_name, 'w', locale.getpreferredencoding())
    file_.write(unicode_text)
    file_.close()

def write_to_stdout(unicode_text):
    """Writes a Unicode string in sys.stdout using terminal locale.

    """
    writer = codecs.getwriter(locale.getpreferredencoding())(sys.stdout)
    writer.write(unicode_text)

def increment_list(list_):
    """Adds one to every element in a list of integers. Returns a new list.

    """
    return [n + 1 for n in list_]

class ExamConfig(object):
    """Class for representing exam configuration. Once an instance has
       been created and data loaded, access directly to the attributes
       to get the data. The constructor reads data from a file. See
       doc/exam-data.sample for an example of such a file."""

    re_model = re.compile('model-[a-zA-Z]')

    def __init__(self, filename = None):
        """Loads data from file if 'filename' is not None. Otherwise,
           default values are assigned to the attributes."""
        if filename is not None:
            self.read(filename)
        else:
            self.num_questions = 0
            self.solutions = {}
            self.id_num_digits = 0
            self.dimensions = []
            self.permutations = {}
            self.models = []
            self.score_weights = None

    def set_solutions(self, model, solutions):
        if self.solutions is None:
            self.solutions = {}
        self.solutions[model] = solutions

    def set_permutations(self, model, permutations):
        self.permutations[model] = permutations

    def read(self, filename):
        """Reads exam configuration from the file named 'filename'."""
        exam_data = ConfigParser.SafeConfigParser()
        files_read = exam_data.read([filename])
        if len(files_read) != 1:
            raise IOError('Exam config file not found: ' + filename)
        try:
            self.id_num_digits = exam_data.getint('exam', 'id-num-digits')
        except:
            self.id_num_digits = 0
        self.__parse_dimensions(exam_data.get('exam', 'dimensions'))
        self.num_questions = sum(dim[1] for dim in self.dimensions)
        has_solutions = exam_data.has_section('solutions')
        has_permutations = exam_data.has_section('permutations')
        self.solutions = {}
        self.permutations = {}
        self.models = []
        if has_solutions:
            for key, value in exam_data.items('solutions'):
                if not self.re_model.match(key):
                    raise Exception('Incorrect key in exam config: ' + key)
                model = key[-1].upper()
                self.models.append(model)
                self.solutions[model] = self.__parse_solutions(value)
                if has_permutations:
                    key = 'permutations-' + model
                    value = exam_data.get('permutations', key)
                    self.permutations[model] = self.__parse_permutations(value)
        has_correct_weight = exam_data.has_option('exam', 'correct-weight')
        has_incorrect_weight = exam_data.has_option('exam', 'incorrect-weight')
        has_blank_weight = exam_data.has_option('exam', 'blank-weight')
        if has_correct_weight and has_incorrect_weight:
            cw = self.__parse_score(exam_data.get('exam', 'correct-weight'))
            iw = self.__parse_score(exam_data.get('exam', 'incorrect-weight'))
            if has_blank_weight:
                bw = self.__parse_score(exam_data.get('exam', 'blank-weight'))
            else:
                bw = 0.0
            self.score_weights = (cw, iw, bw)
        elif not has_correct_weight and not has_incorrect_weight:
            self.score_weights = None
        else:
           raise Exception('Exam config must contain correct and incorrect '
                           'weight or none')
        self.models.sort()

    def save(self, filename):
        data = []
        data.append('[exam]')
        data.append('dimensions: %s'%self.format_dimensions())
        data.append('id-num-digits: %d'%self.id_num_digits)
        if self.score_weights is not None:
            data.append('correct-weight: %.16f'%self.score_weights[0])
            data.append('incorrect-weight: %.16f'%self.score_weights[1])
            data.append('blank-weight: %.16f'%self.score_weights[2])
        if len(self.solutions) > 0:
            data.append('')
            data.append('[solutions]')
            for model in sorted(self.models):
                data.append('model-%s: %s'%(model,
                                            self.format_solutions(model)))
        if len(self.permutations) > 0:
            data.append('')
            data.append('[permutations]')
            for model in sorted(self.models):
                data.append('permutations-%s: %s'%(model,
                                            self.format_permutations(model)))
        data.append('')
        file_ = open(filename, 'w')
        file_.write('\n'.join(data))
        file_.close()

    def format_dimensions(self):
        return ';'.join(['%d,%d'%(cols, rows) \
                             for cols, rows in self.dimensions])

    def format_solutions(self, model):
        return '/'.join([str(n) for n in self.solutions[model]])

    def format_permutations(self, model):
        return '/'.join([self.__format_permutation(p) \
                             for p in self.permutations[model]])

    def __format_permutation(self, permutation):
        num_question, options = permutation
        return '%d{%s}'%(num_question, ','.join([str(n) for n in options]))

    def __parse_solutions(self, s):
        pieces = s.split('/')
        if len(pieces) != self.num_questions:
            raise Exception('Wrong number of solutions')
        return [int(num) for num in pieces]

    def __parse_dimensions(self, s):
        self.dimensions, self.num_options = parse_dimensions(s)

    def __parse_permutations(self, s):
        permutation = []
        pieces = s.split('/')
        if len(pieces) != self.num_questions:
            raise Exception('Wrong number of permutations')
        for i, piece in enumerate(pieces):
            splitted = piece.split('{')
            num_question = int(splitted[0])
            options = [int(p) for p in splitted[1][:-1].split(',')]
            if len(options) != self.num_options[i]:
                raise Exception('Wrong number of options in permutation')
            permutation.append((num_question, options))
        return permutation

    def __parse_score(self, score):
        if score.find('-') != -1:
            raise Exception('Scores in exam config must be positive'%score)
        parts = score.split('/')
        if len(parts) == 1:
            return float(parts[0])
        elif len(parts) == 2:
            return float(parts[0]) / float(parts[1])
        else:
            raise Exception('Bad score value: "%s"'%score)

def parse_dimensions(text, check_equal_num_choices=False):
    dimensions = []
    num_options = []
    boxes = text.split(';')
    for box in boxes:
        dims = box.split(',')
        data = (int(dims[0]), int(dims[1]))
        if data[0] <= 0 or data[1] <= 0:
            raise Exception('Incorrect number in exam geometry')
        dimensions.append(data)
        num_options.extend([data[0]] * data[1])
    if len(dimensions) == 0:
        raise Exception('Empty table dimensions')
    if check_equal_num_choices:
        for i in range(1, len(dimensions)):
            if dimensions[i][0] != dimensions[0][0]:
                raise Exception(('The number of choices per question must'
                                 ' be the same for all questions'))
    return dimensions, num_options

def read_exam_questions(exam_filename):
    import xml.dom.minidom
    import examparser
    dom_tree = xml.dom.minidom.parse(exam_filename)
    # By now, only one parser exists. In the future multiple parser can
    # be called from here, to allow multiple data formats.
    return examparser.parse_exam(dom_tree)

class ExamQuestions(object):
    def __init__(self):
        self.questions = []
        self.subject = None
        self.degree = None
        self.date = None
        self.duration = None
        self.shuffled_questions = {}
        self.permutations = {}

    def num_questions(self):
        """Returns the number of questions of the exam."""
        return len(self.questions)

    def num_choices(self):
        """Returns the number of choices of the questions.

           If all the questions have the same number of choices, returns
           that number. If not, returns None.

        """
        num = [len(q.correct_choices) + len(q.incorrect_choices) \
                   for q in self.questions]
        for n in num[1:]:
            if num[0] != n:
                return None
        return num[0]

    def shuffle(self, model):
        """Shuffles questions and options within questions for the given model.

        """
        shuffled, permutations = shuffle(self.questions)
        self.shuffled_questions[model] = shuffled
        self.permutations[model] = permutations
        for question in self.questions:
            question.shuffle(model)

    def set_permutation(self, model, permutation):
        self.permutations[model] = [p[0] - 1 for p in permutation]
        self.shuffled_questions[model] = \
            [self.questions[i] for i in self.permutations[model]]
        for q, p in zip(self.shuffled_questions[model], permutation):
            choices = q.correct_choices + q.incorrect_choices
            q.permutations[model] = [i - 1 for i in p[1]]
            q.shuffled_choices[model] = [choices[i - 1] for i in p[1]]

    def solutions_and_permutations(self, model):
        solutions = []
        permutations = []
        for qid in self.permutations[model]:
            answers_perm = self.questions[qid].permutations[model]
            solutions.append(1 + answers_perm.index(0))
            permutations.append((qid + 1, increment_list(answers_perm)))
        return solutions, permutations

class Question(object):
    def __init__(self):
        self.text = None
        self.correct_choices = []
        self.incorrect_choices = []
        self.shuffled_choices = {}
        self.permutations = {}

    def shuffle(self, model):
        shuffled, permutations = \
            shuffle(self.correct_choices + self.incorrect_choices)
        self.shuffled_choices[model] = shuffled
        self.permutations[model] = permutations

def shuffle(data):
    """Returns a tuple (list, permutations) with data shuffled.

       Permutations is another list with the original position of each
       term. That is, shuffled[i] was in the original list in
       permutations[i] position.

    """
    to_sort = [(random.random(), item, pos) for pos, item in enumerate(data)]
    shuffled_data = []
    permutations = []
    for val, item, pos in sorted(to_sort):
        shuffled_data.append(item)
        permutations.append(pos)
    return shuffled_data, permutations

class QuestionComponent(object):
    """A piece of text and optional figure or code.

       Represents both the text of a question and its choices.

    """
    def __init__(self, in_choice):
        self.in_choice = in_choice
        self.text = None
        self.code = None
        self.figure = None
        self.annex_width = None
        self.annex_pos = None

    def check_is_valid(self):
        if self.code is not None and self.figure is not None:
            raise Exception('Code and figure cannot be in the same block')
        if (self.in_choice and self.annex_pos != 'center' and
            (self.code is not None or self.figure is not None)):
            raise Exception('Figures and code in answers must be centered')
        if (self.code is not None and self.annex_pos == 'center' and
            self.annex_width != None):
            raise Exception('Centered code cannot have width')
        if not self.in_choice and self.text is None:
            raise Exception('Questions must have a text')
