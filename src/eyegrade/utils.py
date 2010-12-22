import ConfigParser
import csv
import os

program_name = 'eyegrade'
version = '0.1.6.1'
version_status = 'alpha'

csv.register_dialect('tabs', delimiter = '\t')

keys = ['seq-num', 'student-id', 'model', 'good', 'bad', 'unknown', 'answers']

def read_results(filename, permutations = []):
    """Parses an eyegrade results file.

       Results are returned as a list of dictionaries with the keys
       stored in the 'keys' variable. If 'permutations' is provided,
       answers are un-shuffled.

    """
    results = __read_results_file(filename)
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
    return results

def read_student_ids(filename):
    """Reads the list of student IDs from a CSV-formatted file.

       The format of the file is flexible: separators can be either
       tabs or commas. Student ids must be in the first column.

    """
    csvfile = open(filename, 'rb')
    try:
        dialect = csv.Sniffer().sniff(csvfile.read(1024))
    except:
        # Sniff complains about plain files with only one column (unquoted ID)
        csvfile.seek(0)
        if csvfile.readline().strip().isdigit():
            csv.register_dialect('student-id', delimiter=',')
            dialect = csv.get_dialect('student-id')
        else:
            raise Exception('Error while processing the students ID list')
    csvfile.seek(0)
    reader = csv.reader(csvfile, dialect)
    student_ids = [row[0] for row in reader]
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
    model_num = ord(model) - 65
    if model_num >= 2 ** (num_answers - 1):
        raise Exception('Model number too big given the number of answers')
    bit_list = __int_to_bin(model_num, 3, True)
    bit_list[2] = not bit_list[2]
    bit_list.append(reduce(lambda x, y: x ^ y, bit_list))
    bit_list[2] = not bit_list[2]
    return (num_tables * bit_list)[:num_tables * num_answers]

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
    """Returns the contest of a file as a string.

    """
    file_ = open(file_name, 'r')
    data = file_.read()
    file_.close()
    return data

class ExamConfig(object):
    """Class for representing exam configuration. Once an instance has
       been created and data loaded, access directly to the attributes
       to get the data. The constructor reads data from a file. See
       doc/exam-data.sample for an example of such a file."""

    def __init__(self, filename = None):
        """Loads data from file if 'filename' is not None. Otherwise,
           default values are assigned to the attributes."""
        if filename is not None:
            self.read_config(filename)
        else:
            self.num_models = 0
            self.num_questions = 0
            self.solutions = None
            self.id_num_digits = 0
            self.dimensions = []
            self.permutations = []

    def read_config(self, filename):
        """Reads exam configuration from the file named 'filename'."""
        exam_data = ConfigParser.SafeConfigParser()
        exam_data.read([filename])
        try:
            self.num_models = exam_data.getint('exam', 'num-models')
        except:
            self.num_models = 1
        try:
            self.id_num_digits = exam_data.getint('exam', 'id-num-digits')
        except:
            self.id_num_digits = 0
        self.__parse_dimensions(exam_data.get('exam', 'dimensions'))
        self.num_questions = sum(dim[1] for dim in self.dimensions)
        has_permutations = exam_data.has_section('permutations')
        self.solutions = []
        self.permutations = []
        for i in range(0, self.num_models):
            key = 'model-' + chr(65 + i)
            self.__parse_solutions(exam_data.get('solutions', key))
            if has_permutations:
                key = 'permutations-' + chr(65 + i)
                self.__parse_permutations(exam_data.get('permutations', key))

    def __parse_solutions(self, s):
        pieces = s.split('/')
        if len(pieces) != self.num_questions:
            raise Exception('Wrong number of solutions')
        self.solutions.append([int(num) for num in pieces])

    def __parse_dimensions(self, s):
        self.dimensions = []
        self.num_options = []
        boxes = s.split(';')
        for box in boxes:
            dims = box.split(',')
            self.dimensions.append((int(dims[0]), int(dims[1])))
            self.num_options.extend([int(dims[0])] * int(dims[1]))

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
        self.permutations.append(permutation)
