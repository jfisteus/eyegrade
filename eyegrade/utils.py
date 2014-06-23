# Eyegrade: grading multiple choice questions with a webcam
# Copyright (C) 2010-2014 Jesus Arias Fisteus
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

import ConfigParser
import csv
import os
import locale
import codecs
import sys
import random
import re
import io
import fractions

program_name = 'eyegrade'
web_location = 'http://eyegrade.org/'
source_location = 'https://github.com/jfisteus/eyegrade'
help_location = 'http://eyegrade.org/doc/user-manual/'
version = '0.4.1'
version_status = 'alpha'

re_email = re.compile(r'^[a-zA-Z0-9._%-\+]+@[a-zA-Z0-9._%-]+.[a-zA-Z]{2,6}$')
re_model_letter = re.compile('[0a-zA-Z]')

csv.register_dialect('tabs', delimiter = '\t')

results_file_keys = ['seq-num', 'student-id', 'model', 'good', 'bad',
                     'score', 'answers']

def _read_config():
    """Reads the general config file and returns the resulting config object.

    Other modules can get the config object by accessing the
    utils.config variable.

    """
    config = {'camera-dev': '0',
              'save-filename-pattern': 'exam-{student-id}-{seq-number}.png',
              'csv-dialect': 'tabs',
              'default-charset': 'utf8', # special value: 'system-default'
              }
    parser = ConfigParser.SafeConfigParser()
    parser.read([os.path.expanduser('~/.eyegrade.cfg'),
                 os.path.expanduser('~/.camgrade.cfg')])
    if 'default' in parser.sections():
        for option in parser.options('default'):
            config[option] = parser.get('default', option)
    if not config['csv-dialect'] in csv.list_dialects():
        config['csv-dialect'] = 'tabs'
    if 'error-logging' in config and config['error-logging'] == 'yes':
        config['error-logging'] = True
    else:
        config['error-logging'] = False
    config['camera-dev'] = int(config['camera-dev'])
    if config['default-charset'] == 'system-default':
        config['default-charset'] = locale.getpreferredencoding()
    return config

# The global configuration object:
config = _read_config()


class EyegradeException(Exception):
    """An Eyegrade-specific exception.

    In addition to what a normal exception would do, it encapsulates
    user-friendly messages for some common causes of error due to
    the user.

    """

    _error_messages = {}
    _short_messages = {}

    def __init__(self, message, key=None, format_params=None):
        """Creates a new exception.

        If `key` is in `_error_messages`, a prettier version of the
        exception will be shown to the user, with the explanation appended
        to the end of what you provide in `message`.

        """
        self.key = key
        if (key in EyegradeException._error_messages
            or key in EyegradeException._short_messages):
            parts = []
            if message:
                parts.append(message)
            elif key in EyegradeException._short_messages:
                short_msg = EyegradeException._short_messages[key]
                if not format_params:
                    parts.append(short_msg)
                else:
                    parts.append(short_msg.format(*format_params))
            if key in EyegradeException._error_messages:
                parts.append('\n\n')
                parts.append(EyegradeException._error_messages[key])
            parts.append('\n')
            self.full_message = ''.join(parts)
            super(EyegradeException, self).__init__(self.full_message)
        else:
            self.full_message = None
            super(EyegradeException, self).__init__(message)

    def __str__(self):
        """Prints the exception.

        A user-friendly message, without the stack trace, is shown when such
        user-friendly message is available.

        """
        if self.full_message is not None:
            return self.full_message
        else:
            return super(EyegradeException, self).__str__()

    def __unicode__(self):
        if self.full_message is not None:
            if isinstance(self.full_message, unicode):
                return self.full_message
            else:
                return unicode(self.full_message, encoding='utf-8')
        else:
            return unicode(super(EyegradeException, self).__str__(),
                           encoding='utf-8')

    @staticmethod
    def register_error(key, detailed_message='', short_message=''):
        """Registers a new error message associated to a key.

        `key` is just a string used to identify this error message,
        that must be passed when creating exception
        objects. `detailed_message` is a (possibly long and with end
        of line characters inside) explanation of the
        error. `short_message` is a one line error message to be used
        only when a blank message is passed when creating the
        exception.

        Being this method static, messages added through it will be
        shared for all the instances of the exception.

        """
        if (not key in EyegradeException._error_messages
            and not key in EyegradeException._short_messages):
            if detailed_message:
                EyegradeException._error_messages[key] = detailed_message
            if short_message:
                EyegradeException._short_messages[key] = short_message
        else:
            raise EyegradeException('Duplicate error key in register_error')


EyegradeException.register_error('bad_dimensions',
    "Dimensions must be specified as a ';' separated list of tables.\n"
    "For each table, specify the number of choices + comma + the number of\n"
    "questions in that table. For example, '4,10;4,9' configures two\n"
    "tables, the left-most with 9 questions and 4 choices per question,\n"
    "and the right-most with 10 questions and the same number of choices."
    'Bad dimensions value.')

EyegradeException.register_error('same_num_choices',
    "By now, Eyegrade needs you to use the same number of choices in\n"
    "all the questions of the exam.",
    'There are questions with a different number of choices')

_student_list_message = (
    'The file is expected to contain one line per student.\n'
    'Each line can contain one or more TAB-separated columns.\n'
    'The first column must be the student id (a number).\n'
    'The second column, if present, is interpreted as the student name.\n'
    'The rest of the columns are ignored.')

EyegradeException.register_error('error_student_list',
    'The syntax of the student list is not correct.\n' + _student_list_message)

EyegradeException.register_error('error_student_id',
    'At least one student id is not a number.\n' + _student_list_message)

EyegradeException.register_error('error_student_list_encoding',
    'The student list contains erroneously-encoded characters.')


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

def locale_dir():
    return os.path.join(data_dir, 'locale')

def qt_translations_dir():
    return os.path.join(data_dir, 'qt-translations')

def resource_path(file_name):
    return os.path.join(data_dir, file_name)

def read_results(filename, permutations = {}, allow_question_mark=False):
    """Parses an eyegrade results file.

       Results are returned as a list of dictionaries with the keys
       stored in the 'results_file_keys' variable. If 'permutations'
       is provided, answers are un-shuffled.

    """
    results = _read_results_file(filename)
    for result in results:
        result['model'] = check_model_letter(result['model'],
                                       allow_question_mark=allow_question_mark)
        result['good'] = int(result['good'])
        result['bad'] = int(result['bad'])
        if result['score'] != '?':
            result['score'] = float(result['score'])
        else:
            result['score'] = None
        answers = [int(n) for n in result['answers'].split('/')]
        if len(permutations) > 0:
            answers = _permute_answers(answers, permutations[result['model']])
        result['answers'] = answers
    return results

def write_results(results, filename, csv_dialect, append=False):
    """Writes exam results to a file.

       If filename is None, results are written to stdout. The output
       file is overwritting by default. Use append=True to append
       instead of overwriting.

    """
    if filename is not None:
        if not append:
            file_ = open(filename, 'wb')
        else:
            file_ = open(filename, 'ab')
    else:
        file_ = sys.stdout
    writer = csv.writer(file_, dialect = csv_dialect)
    for result in results:
        data = [str(result['seq-num']),
                result['student-id'],
                result['model'],
                str(result['good']),
                str(result['bad']),
                str(result['score']),
                '/'.join([str(d) for d in result['answers']])]
        writer.writerow(data)
    if filename is not None:
        file_.close()

def check_model_letter(model, allow_question_mark=False):
    """Checks if a model letter is correct.

    The special value '?' is considered valid only if the parameter
    `allow_question_mark` is set.

    """
    if re_model_letter.match(model):
        return model.upper()
    elif allow_question_mark and model == '?':
        return '?'
    else:
        raise Exception('Incorrect model letter: ' + model)

def read_student_ids(filename=None, file_=None, data=None, with_names=False):
    """Reads the list of student IDs from a CSV-formatted file (tab-separated).

    Either 'filename', 'file_' or 'data' must be provided.  'filename'
    specifies the name of a file to read.  'file_' is a file object
    instead of a file name.  'data' must be a string that contains the
    actual content of the config file to be parsed. Only one of them
    should not be None, although this restriction is not enforced: the
    first one not to be None, in the same order they are specified in
    the function, is used.

    """
    students = read_student_ids_same_order(filename=filename, file_=file_,
                                           data=data, with_names=with_names)
    if not with_names:
        return [s[0] for s in students]
    else:
        students_dict = {}
        for student_id, name, email in students:
            students_dict[student_id] = name
        return students_dict

def read_student_ids_same_order(filename=None, file_=None, data=None,
                                with_names=False):
    """Reads the list of student IDs from a CSV-formatted file (tab-separated).

    Either 'filename', 'file_' or 'data' must be provided.  'filename'
    specifies the name of a file to read.  'file_' is a file object
    instead of a file name.  'data' must be a string that contains the
    actual content of the config file to be parsed. Only one of them
    should not be None, although this restriction is not enforced: the
    first one not to be None, in the same order they are specified in
    the function, is used.

    Returns the results as a list of tuples (id, name, email).

    """
    assert((filename is not None) or (file_ is not None)
           or (data is not None))
    csvfile = None
    if filename is not None:
        csvfile = open(filename, 'rb')
        reader = csv.reader(_UTF8Recoder(csvfile), 'tabs')
    elif file_ is not None:
        reader = csv.reader(file_, 'tabs')
    elif data is not None:
        reader = csv.reader(io.BytesIO(data), 'tabs')
    if not with_names:
        student_ids = [(row[0], '', '') for row in reader]
        for sid in student_ids:
            _check_student_id(sid[0])
    else:
        student_ids = []
        for row in reader:
            name = ''
            email = ''
            if len(row) == 0:
                raise EyegradeException('Empty line in student list',
                                        key='error_student_list')
            sid = row[0]
            _check_student_id(sid)
            if len(row) > 1:
                try:
                    name = unicode(row[1], config['default-charset'])
                except ValueError:
                    raise EyegradeException('Error while processing {0} data'\
                                            .format(config['default-charset']),
                                            key='error_student_list_encoding')
            if len(row) > 2:
                if _check_email(row[2]):
                    email = row[2]
            student_ids.append((sid, name, email))
    if csvfile is not None:
        csvfile.close()
    return student_ids


class _UTF8Recoder:
    """
    Iterator that reads an encoded stream and reencodes the input to UTF-8
    """
    def __init__(self, file_, encoding=None):
        if encoding is None:
            encoding = config['default-charset']
        self.reader = codecs.getreader(encoding)(file_)
        self.first_line = True

    def __iter__(self):
        return self

    def next(self):
        data = self.reader.next().encode('utf-8')
        if self.first_line:
            self.first_line = False
            if (len(data) >= 3 and data[0] == '\xef'
                and data[1] == '\xbb' and data[2] == '\xbf'):
                data = data[3:]
        return data


def _check_student_id(student_id):
    """Checks the student id.

    Raises the appropriate exception in case of error.

    """
    try:
        int(student_id)
    except:
        raise EyegradeException('Wrong id in student list: ' + student_id,
                                key='error_student_id')

def _check_email(email):
    """Checks syntactically an email address.

    Returns True if correct, False if incorrect.

    """
    if re_email.match(email):
        return True
    else:
        return False

def read_student_ids_multiple(filenames, with_names=False):
    """Reads student ids from multiple files.

    `filenames` is an iterable of filenames. It may be empty. `with_names`
    has the same meaning as in `read_student_ids(...)`.

    Returns a combined list or dictionary, depending on the value of
    `with_names`.

    """
    if not with_names:
        st = []
        for f in filenames:
            st.extend(read_student_ids(filename=f, with_names=False))
    else:
        st = {}
        for f in filenames:
            st.update(read_student_ids(filename=f, with_names=True))
    return st

def mix_results(results_filename, student_list_filename, dump_missing,
                round_score, dump_model):
    """Returns a list of tuples student_id, good_answers, bad_answers, score.

       - Receives the names of the files with results and student list.

       - If 'dump_missing' is True, grades of students not in the
       student list are dumped at the end of the list.

       - If 'round_score' is -1, scores are dumped as they are in the
       file. If it is another value, it is interpreted as the number of
       decimal digits to which the the score has to be rounded.

       - If 'dump_model' is True, the exam model is also dumped as
       another column at the end.

    """
    mixed_grades = []
    results = results_by_id(read_results(results_filename))
    ids = read_student_ids(filename=student_list_filename)
    for student_id in ids:
        mixed_grades.append(_student_result(student_id, results,
                                            round_score, dump_model))
    if dump_missing:
        for student_id in results:
            if not student_id in ids:
                mixed_grades.append(_student_result(student_id, results,
                                                    round_score, dump_model))
    return mixed_grades

def _student_result(student_id, results, round_score, dump_model):
    """Auxiliary funtion for 'mix_results'."""
    if student_id in results:
        result = results[student_id]
        if round_score == -1:
            score = result['score']
        else:
            score = round(result['score'], round_score)
        parts = [student_id, result['good'], result['bad'], score]
        model = result['model']
    else:
        parts = [student_id, '', '', '']
        model = ''
    if dump_model:
        parts.extend(model)
    return parts

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
        id_dict[r['student-id']] = r
    return id_dict

def _read_results_file(filename):
    csvfile = open(filename, 'rb')
    dialect = csv.Sniffer().sniff(csvfile.read(1024))
    csvfile.seek(0)
    reader = csv.DictReader(csvfile, fieldnames = results_file_keys,
                            dialect = dialect)
    entries = [entry for entry in reader]
    csvfile.close()
    return entries

def _permute_answers(answers, permutation):
    assert(len(answers) == len(permutation))
    permutted = [0] * len(answers)
    for i, option in enumerate(answers):
        if option == 0 or option == -1:
            resolved_option = option
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
    seed = _int_to_bin(model_num, 3, True)
    seed[2] = not seed[2]
    seed.append(reduce(lambda x, y: x ^ y, seed))
    seed[2] = not seed[2]
    bit_list = seed * (1 + (num_bits - 1) // 4)
    return bit_list[:num_tables * num_answers]

def decode_model(bit_list, accept_model_0=False):
    """Given the bits that encode the model, returns the associated letter.

       It decoding/checksum fails, None is returned. The list of bits must
       be a list of boolean variables.

       The special model 0 is not valid unless `accept_model_0` is set.

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
        return chr(65 + (int(bit_list[0]) | int(bit_list[1]) << 1 |
                  int(bit_list[2]) << 2))
    elif accept_model_0 and max(bit_list) == False:
        return '0'
    else:
        return None

def _int_to_bin(n, num_digits, reverse = False):
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
    file_ = codecs.open(file_name, 'r', config['default-charset'])
    data = file_.read()
    file_.close()
    return data

def write_file(file_name, unicode_text):
    """Writes a Unicode string in a file using terminal locale.

    """
    file_ = codecs.open(file_name, 'w', config['default-charset'])
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


class Score(object):
    def __init__(self, answers, solutions, score_weights):
        self.correct = None
        self.incorrect = None
        self.blank = None
        self.score = None
        self.max_score = None
        self.answers = answers
        self.solutions = solutions
        self.score_weights = score_weights
        if answers and solutions:
            self.update()

    def update(self):
        self._count_answers()
        if self.score_weights is not None:
            self._compute_score()
        else:
            self.score = None
            self.max_score = None

    def _count_answers(self):
        self.correct = 0
        self.incorrect = 0
        self.blank = 0
        for answer, solution in zip(self.answers, self.solutions):
            if answer == 0:
                self.blank += 1
            elif answer == solution:
                self.correct += 1
            else:
                self.incorrect += 1

    def _compute_score(self):
        self.score = float(self.correct * self.score_weights[0]
                           - self.incorrect * self.score_weights[1]
                           - self.blank * self.score_weights[2])
        self.max_score = float(len(self.answers) * self.score_weights[0])


class Student(object):
    def __init__(self, db_id, student_id, name, email, group_id,
                 sequence_num, is_in_database=False):
        self.db_id = db_id
        self.student_id = student_id
        self.name = name
        self.email = email
        self.group_id = group_id
        self.sequence_num = sequence_num
        self.is_in_database = is_in_database

    def get_id_and_name(self):
        if self.name:
            return ' '.join((self.student_id, self.name))
        else:
            return self.student_id

    def get_name_or_id(self):
        if self.name:
            return self.name
        elif self.student_id:
            return self.student_id
        else:
            return ''

    def __unicode__(self):
        return u'student: ' + self.get_id_and_name()


class Exam(object):
    def __init__(self, capture_, decisions, solutions, valid_students,
                 exam_id, score_weights):
        self.capture = capture_
        self.decisions = decisions
        if valid_students is not None:
            self.students = valid_students
        else:
            self.students = {}
        self.exam_id = exam_id
        self.score = Score(decisions.answers, solutions, score_weights)
        rank = self.rank_students()
        self.decisions.set_students_rank(rank)
        if len(rank) > 0:
            self.decisions.set_student(rank[0])

    def update_grade(self):
        self.score.update()

    def reset_image(self):
        self.capture.reset_image()

    def draw_answers(self):
        self.capture.draw_answers(self.decisions.answers, self.score.solutions)

    def draw_status(self):
        self.capture.draw_status()

    def draw_corner(self, point):
        self.capture.draw_corner(point)

    def get_image_drawn(self):
        return self.capture.image_drawn

    def toggle_answer(self, question, answer):
        if self.decisions.answers[question] == answer:
            self.decisions.change_answer(question, 0)
        else:
            self.decisions.change_answer(question, answer)
        self.score.update()
        self.capture.reset_image()
        self.capture.draw_answers(self.decisions.answers,
                                  self.score.solutions)

    def rank_students(self):
        if self.decisions.detected_id is not None:
            if self.students:
                rank = [(self._id_rank(s, self.decisions.id_scores), s) \
                         for s in self.students.itervalues()]
                students_rank = [student for score, student \
                                 in sorted(rank, reverse = True)]
            else:
                students_rank = [Student(None, self.decisions.detected_id,
                                         None, None, None, None)]
        else:
            students_rank = list(self.students.itervalues())
        return students_rank

    def get_student_id_and_name(self):
        if self.decisions.student is not None:
            return self.decisions.student.get_id_and_name()
        else:
            return None

    def ranked_student_ids(self):
        """Returns the ranked list of students as taken from the decision.

        Each entry is a student object. They are ranked according to
        their probability to be the actual student id. The most probable
        is the first in the list.

        """
        if (len(self.decisions.students_rank) > 0
            and self.decisions.students_rank[0] != self.decisions.student):
            rank = list(self.decisions.students_rank)
            rank.remove(self.decisions.student)
            rank.insert(0, self.decisions.student)
        else:
            rank = self.decisions.students_rank
        return rank

    def update_student_id(self, new_id, name=None):
        """Updates the student id of the current exam.

        If a student name is given and there is no name for the
        student, this name is added to the list of extra student
        names, with validity only for this exam.

        """
        if new_id is None or new_id == '-1':
            student = None
        elif new_id in self.students:
            student = self.students[new_id]
        else:
            student = Student(None, self.decisions.detected_id, name,
                              None, None, None)
        self.decisions.set_student(student)

    def _id_rank(self, student, scores):
        rank = 0.0
        for i, digit in enumerate(student.student_id):
            rank += scores[i][int(digit)]
        return rank


# A score is a float number or a fraction, e.g.: '0.8' or '4/5'
_re_score = re.compile(r'^\s*((\d+(\.\d+)?)|(\d+\s*\/\s*\d+))\s*$')

class ExamConfig(object):
    """Class for representing exam configuration. Once an instance has
       been created and data loaded, access directly to the attributes
       to get the data. The constructor reads data from a file. See
       doc/exam-data.sample for an example of such a file."""

    re_model = re.compile('model-[0a-zA-Z]')

    def __init__(self, filename=None, capture_pattern=None):
        """Loads data from file if 'filename' is not None. Otherwise,
           default values are assigned to the attributes."""
        if filename is not None:
            self.read(filename=filename)
        else:
            self.num_questions = 0
            self.solutions = {}
            self.id_num_digits = 0
            self.capture_pattern = capture_pattern
            self.dimensions = []
            self.permutations = {}
            self.models = []
            self.score_weights = None
            self.left_to_right_numbering = False
            self.survey_mode = None

    def set_solutions(self, model, solutions):
        if not isinstance(solutions, list):
            solutions = self._parse_solutions(solutions)
        self.solutions[model] = solutions
        if not model in self.models:
            self.models.append(model)

    def get_solutions(self, model):
        """Returns the solutions for the given model.

        If in survey mode it returns []. If there are no solutions for
        this, model it returns None.

        """
        if not self.survey_mode:
            if model in self.solutions:
                return self.solutions[model]
            else:
                return None
        else:
            return []

    def set_permutations(self, model, permutations):
        if not isinstance(permutations, list):
            permutations = self._parse_permutations(permutations)
        self.permutations[model] = permutations

    def set_dimensions(self, dimensions):
        self.dimensions, self.num_options = parse_dimensions(dimensions)
        self.num_questions = sum(dim[1] for dim in self.dimensions)

    def set_score_weights(self, correct_weight, incorrect_weight, blank_weight):
        if isinstance(correct_weight, basestring):
            correct_weight = self._parse_score(correct_weight)
        if isinstance(incorrect_weight, basestring):
            incorrect_weight = self._parse_score(incorrect_weight)
        if isinstance(blank_weight, basestring):
            blank_weight = self._parse_score(blank_weight)
        self.score_weights = (correct_weight, incorrect_weight, blank_weight)

    def get_num_choices(self):
        """Returns the number of choices per question.

        If not all the questions have the same number of choices, it returns
        the maximum number of choices. If there are no questions, it returns
        None.

        """
        choices = [dim[0] for dim in self.dimensions]
        if len(choices) > 0:
            return max(choices)
        else:
            return None

    def read(self, filename=None, file_=None, data=None):
        """Reads exam configuration.

           Either 'filename', 'file_' or 'data' must be provided.
           'filename' specifies the name of a file to read.  'file_' is
           a file object instead of a file name.  'data' must be a
           string that contains the actual content of the config file
           to be parsed. Only one of them should not be None, although
           this restriction is not enforced: the first one not to be
           None, in the same order they are specified in the function,
           is used.

        """
        assert((filename is not None) or (file_ is not None)
               or (data is not None))
        exam_data = ConfigParser.SafeConfigParser()
        if filename is not None:
            files_read = exam_data.read([filename])
            if len(files_read) != 1:
                raise IOError('Exam config file not found: ' + filename)
        elif file_ is not None:
            exam_data.readfp(file_)
        elif data is not None:
            exam_data.readfp(io.BytesIO(data))
        try:
            self.id_num_digits = exam_data.getint('exam', 'id-num-digits')
        except:
            self.id_num_digits = 0
        self.set_dimensions(exam_data.get('exam', 'dimensions'))
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
                self.solutions[model] = self._parse_solutions(value)
                if has_permutations:
                    key = 'permutations-' + model
                    value = exam_data.get('permutations', key)
                    self.permutations[model] = self._parse_permutations(value)
        has_correct_weight = exam_data.has_option('exam', 'correct-weight')
        has_incorrect_weight = exam_data.has_option('exam', 'incorrect-weight')
        has_blank_weight = exam_data.has_option('exam', 'blank-weight')
        if has_correct_weight and has_incorrect_weight:
            cw = self._parse_score(exam_data.get('exam', 'correct-weight'))
            iw = self._parse_score(exam_data.get('exam', 'incorrect-weight'))
            if has_blank_weight:
                bw = self._parse_score(exam_data.get('exam', 'blank-weight'))
            else:
                bw = 0.0
            self.score_weights = (cw, iw, bw)
        elif not has_correct_weight and not has_incorrect_weight:
            self.score_weights = None
        else:
            raise Exception('Exam config must contain correct and incorrect '
                            'weight or none')
        if exam_data.has_option('exam', 'left-to-right-numbering'):
            self.left_to_right_numbering = \
                       exam_data.getboolean('exam', 'left-to-right-numbering')
        else:
            self.left_to_right_numbering = False
        if exam_data.has_option('exam', 'survey-mode'):
            self.survey_mode = exam_data.getboolean('exam', 'survey-mode')
        else:
            self.survey_mode = False
        self.models.sort()

    def save(self, filename):
        data = []
        data.append('[exam]')
        data.append('dimensions: %s'%self.format_dimensions())
        data.append('id-num-digits: %d'%self.id_num_digits)
        if self.left_to_right_numbering:
            data.append('left-to-right-numbering: yes')
        if self.survey_mode:
            data.append('survey-mode: yes')
        if self.score_weights is not None:
            data.append(('correct-weight: '
                         + self.format_weight(self.score_weights[0])))
            data.append(('incorrect-weight: '
                         + self.format_weight(self.score_weights[1])))
            data.append(('blank-weight: '
                         + self.format_weight(self.score_weights[2])))
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

    def format_weight(self, weight):
        if weight is None:
            return None
        elif type(weight) == fractions.Fraction:
            if weight.denominator != 1:
                return '{0}/{1}'.format(weight.numerator, weight.denominator)
            else:
                return str(weight.numerator)
        elif type(weight) == float:
            return '{0:.16f}'.format(weight)
        else:
            return str(weight)

    def format_dimensions(self):
        return ';'.join(['%d,%d'%(cols, rows) \
                             for cols, rows in self.dimensions])

    def format_solutions(self, model):
        return '/'.join([str(n) for n in self.solutions[model]])

    def format_permutations(self, model):
        return '/'.join([self._format_permutation(p) \
                             for p in self.permutations[model]])

    def _format_permutation(self, permutation):
        num_question, options = permutation
        return '%d{%s}'%(num_question, ','.join([str(n) for n in options]))

    def _parse_solutions(self, s):
        pieces = s.split('/')
        if len(pieces) != self.num_questions:
            raise Exception('Wrong number of solutions')
        return [int(num) for num in pieces]

    def _parse_permutations(self, s):
        permutation = []
        pieces = s.split('/')
        if len(pieces) != self.num_questions:
            raise Exception('Wrong number of permutations')
        for i, piece in enumerate(pieces):
            splitted = piece.split('{')
            num_question = int(splitted[0])
            options = [int(p) for p in splitted[1][:-1].split(',')]
            if len(options) > self.num_options[i]:
                raise Exception('Wrong number of options in permutation')
            permutation.append((num_question, options))
        return permutation

    def _parse_score(self, score):
        if score.find('-') != -1:
            raise Exception('Scores in exam config must be positive'%score)
        if not _re_score.match(score):
            raise Exception('Bad score value: "{0}"'.format(score))
        parts = [p.strip() for p in score.split('/')]
        if len(parts) == 1:
            return float(parts[0])
        elif len(parts) == 2:
            return fractions.Fraction(int(parts[0]), int(parts[1]))


def parse_dimensions(text, check_equal_num_choices=False):
    dimensions = []
    num_options = []
    boxes = text.split(';')
    for box in boxes:
        dims = box.split(',')
        try:
            data = (int(dims[0]), int(dims[1]))
        except ValueError:
            raise EyegradeException('Incorrect number in exam dimensions',
                                    'bad_dimensions')
        if data[0] <= 0 or data[1] <= 0:
            raise EyegradeException('Incorrect number in exam dimensions',
                                    'bad_dimensions')
        dimensions.append(data)
        num_options.extend([data[0]] * data[1])
    if len(dimensions) == 0:
        raise EyegradeException('Dimensions are empty', 'bad_dimensions')
    if check_equal_num_choices:
        for i in range(1, len(dimensions)):
            if dimensions[i][0] != dimensions[0][0]:
                raise EyegradeException('', 'same_num_choices')
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

           If not all the questions have the same number of choices,
           it returns the maximum. If there are no exams, it returns None.

        """
        num = [len(q.correct_choices) + len(q.incorrect_choices) \
                   for q in self.questions]
        if len(num) > 0:
            return max(num)
        else:
            return None

    def homogeneous_num_choices(self):
        """Returns True if all the questions have the same number of choices.

        Returns None if the list of questions is empty.

        """
        num = [len(q.correct_choices) + len(q.incorrect_choices) \
                   for q in self.questions]
        if len(num) > 0:
            return min(num) == max(num)
        else:
            return None

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

def fraction_to_str(fraction):
    """Returns as a string the given fraction, simplified if possible.

    The return string can be things such as '-5/2', '2', etc.

    """
    if fraction.denominator != 1:
        return str(fraction.numerator) + '/' + str(fraction.denominator)
    else:
        return str(fraction.numerator)

# Regular expressions used for capture filename patterns
regexp_id = re.compile('\{student-id\}')
regexp_seqnum = re.compile('\{seq-number\}')

def capture_name(filename_pattern, exam_id, student):
    if student is not None:
        sid = student.student_id
    else:
        sid = 'noid'
    filename = regexp_seqnum.sub(str(exam_id), filename_pattern)
    filename = regexp_id.sub(sid, filename)
    return filename

def encode_string(text):
    return text.encode(config['default-charset'])
