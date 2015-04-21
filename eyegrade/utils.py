# Eyegrade: grading multiple choice questions with a webcam
# Copyright (C) 2010-2015 Jesus Arias Fisteus
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

from __future__ import unicode_literals

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
web_location = 'http://www.eyegrade.org/'
source_location = 'https://github.com/jfisteus/eyegrade'
help_location = 'http://www.eyegrade.org/doc/user-manual/'
version = '0.5.1'
version_status = 'alpha'

re_exp_email = r'^[a-zA-Z0-9._%-\+]+@[a-zA-Z0-9._%-]+.[a-zA-Z]{2,6}$'
re_email = re.compile(re_exp_email)
re_model_letter = re.compile('[0a-zA-Z]')

csv.register_dialect('tabs', delimiter=str('\t'))

results_file_keys = ['seq-num', 'student-id', 'model', 'good', 'bad',
                     'score', 'answers']

_default_capture_pattern = 'exam-{student-id}-{seq-number}.png'

def _read_config():
    """Reads the general config file and returns the resulting config object.

    Other modules can get the config object by accessing the
    utils.config variable.

    """
    config = {'camera-dev': '0',
              'save-filename-pattern': _default_capture_pattern,
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


class ExportSortKey(object):
    """Constants for the export dialog."""
    STUDENT_LIST = 1
    STUDENT_LAST_NAME = 2
    GRADING_SEQUENCE = 3


class ComparableMixin(object):
    """For implementing comparable classes.

    As seen on http://regebro.wordpress.com/2010/12/13/
                      python-implementing-rich-comparison-the-correct-way/

    """
    def _compare(self, other, method):
        try:
            return method(self._cmpkey(), other._cmpkey())
        except (AttributeError, TypeError):
            # _cmpkey not implemented, or return different type,
            # so I can't compare with "other".
            return NotImplemented

    def __lt__(self, other):
        return self._compare(other, lambda s,o: s < o)

    def __le__(self, other):
        return self._compare(other, lambda s,o: s <= o)

    def __eq__(self, other):
       return self._compare(other, lambda s,o: s == o)

    def __ge__(self, other):
        return self._compare(other, lambda s,o: s >= o)

    def __gt__(self, other):
        return self._compare(other, lambda s,o: s > o)

    def __ne__(self, other):
        return self._compare(other, lambda s,o: s != o)


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
    writer = csv.writer(file_, dialect=csv_dialect)
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

def read_student_ids(filename=None, file_=None, data=None):
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
                                           data=data)
    students_dict = {}
    for sid, full_name, first_name, last_name, email in students:
        students_dict[sid] = (full_name, first_name, last_name, email)
    return students_dict

def read_student_ids_same_order(filename=None, file_=None, data=None):
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
    student_ids = []
    for row in reader:
        name1 = ''
        name2 = ''
        email = ''
        if len(row) == 0:
            raise EyegradeException('Empty line in student list',
                                    key='error_student_list')
        sid = _read_unicode_string(row[0],
                                   'error_student_list_encoding')
        _check_student_id(sid)
        if len(row) > 1:
            name1 = _read_unicode_string(row[1],
                                         'error_student_list_encoding')
        if len(row) > 2:
            item = _read_unicode_string(row[2],
                                        'error_student_list_encoding')
            if _check_email(item):
                email = item
            else:
                name2 = item
        if len(row) > 3:
            item = _read_unicode_string(row[3],
                                        'error_student_list_encoding')
            if _check_email(item):
                email = item
        if not name2:
            full_name = name1
            first_name = ''
            last_name = ''
        else:
            full_name = ''
            first_name = name1
            last_name = name2
        student_ids.append((sid, full_name, first_name, last_name, email))
    if csvfile is not None:
        csvfile.close()
    return student_ids

def _read_unicode_string(text, error_key):
    try:
        value = unicode(text, config['default-charset'])
    except ValueError:
        raise EyegradeException('Error while processing {0} data'\
                                .format(config['default-charset']),
                                key=error_key)
    return value


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

def read_student_ids_multiple(filenames):
    """Reads student ids from multiple files.

    `filenames` is an iterable of filenames. It may be empty.
    Returns a dictionary.

    """
    st = {}
    for f in filenames:
        st.update(read_student_ids(filename=f))
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
    writer = csv.writer(file_, dialect=csv_dialect)
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
    def __init__(self, answers, solutions, question_scores):
        if (answers is not None and solutions
            and len(answers) != len(solutions)):
            raise ValueError('Parameters must have the same length in Score')
        if (solutions and question_scores is not None
            and len(solutions) != len(question_scores)):
            raise ValueError('Parameters must have the same length in Score')
        self.correct = None
        self.incorrect = None
        self.blank = None
        self.score = None
        self.max_score = None
        self.answer_status = None
        self.answers = answers
        self.solutions = solutions
        self.question_scores = question_scores
        if answers and solutions:
            self.update()

    def update(self):
        self.correct = 0
        self.incorrect = 0
        self.blank = 0
        self.answer_status = []
        question_scores = self.question_scores
        if question_scores is None:
            question_scores = [None] * len(self.answers)
            has_scores = False
        else:
            has_scores = True
        if has_scores:
            for answer, solution, q in zip(self.answers, self.solutions,
                                           question_scores):
                if q is not None and q.weight == 0:
                    self.answer_status.append(QuestionScores.VOID)
                elif answer == 0:
                    self.blank += 1
                    self.answer_status.append(QuestionScores.BLANK)
                elif answer == solution:
                    self.correct += 1
                    self.answer_status.append(QuestionScores.CORRECT)
                else:
                    self.incorrect += 1
                    self.answer_status.append(QuestionScores.INCORRECT)
            self.score = float(sum([q.score(status) \
                                    for q, status in zip(question_scores,
                                                         self.answer_status)]))
            self.max_score = float(sum([q.score(QuestionScores.CORRECT)
                                        for q in self.question_scores]))
        else:
            self.score = None
            self.max_score = None


class Student(object):
    def __init__(self, db_id, student_id, full_name,
                 first_name, last_name, email, group_id,
                 sequence_num, is_in_database=False):
        if full_name and (first_name or last_name):
            raise ValueError('Full name incompatible with first / last name')
        self.db_id = db_id
        self.student_id = student_id
        self.full_name = full_name
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.group_id = group_id
        self.sequence_num = sequence_num
        self.is_in_database = is_in_database

    @property
    def name(self):
        if self.full_name:
            return self.full_name
        elif self.last_name:
            if self.first_name:
                return '{0} {1}'.format(self.first_name, self.last_name)
            else:
                return self.last_name
        elif self.first_name:
            return self.first_name
        else:
            return ''

    @property
    def last_comma_first_name(self):
        if self.last_name:
            if self.first_name:
                return '{0}, {1}'.format(self.last_name, self.first_name)
            else:
                return self.last_name
        else:
            return self.name

    @property
    def id_and_name(self):
        if self.name:
            return ' '.join((self.student_id, self.name))
        else:
            return self.student_id

    @property
    def name_or_id(self):
        if self.name:
            return self.name
        elif self.student_id:
            return self.student_id
        else:
            return ''

    def __unicode__(self):
        return u'student: ' + self.id_and_name


class StudentGroup(object):
    def __init__(self, identifier, name):
        self.identifier = identifier
        self.name = name

    def __unicode__(self):
        return u'Group #{0.identifier} ({0.name})'.format(self)


class Exam(object):
    def __init__(self, capture_, decisions, solutions, valid_students,
                 exam_id, question_scores, sessiondb=None):
        self.capture = capture_
        self.decisions = decisions
        if valid_students is not None:
            self.students = valid_students
        else:
            self.students = {}
        self.exam_id = exam_id
        self.score = Score(decisions.answers, solutions, question_scores)
        rank = self.rank_students()
        self.decisions.set_students_rank(rank)
        if len(rank) > 0:
            self.decisions.set_student(rank[0])
        self.sessiondb = sessiondb

    def update_grade(self):
        self.score.update()

    def reset_image(self):
        self.capture.reset_image()

    def draw_answers(self):
        self.capture.draw_answers(self.score)

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
        self.draw_answers()

    def rank_students(self):
        if self.decisions.detected_id is not None:
            if self.students:
                rank = [(self._id_rank(s, self.decisions.id_scores), s) \
                         for s in self.students.itervalues() \
                         if s.group_id > 0]
                students_rank = [student for score, student \
                                 in sorted(rank, reverse = True)]
            else:
                students_rank = []
            if students_rank == []:
                students_rank = [Student(None, self.decisions.detected_id,
                                         None, None, None, None, None, None)]
        else:
            students_rank = list(self.students.itervalues())
        return students_rank

    def get_student_id_and_name(self):
        if self.decisions.student is not None:
            return self.decisions.student.id_and_name
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
            if self.decisions.student in rank:
                rank.remove(self.decisions.student)
            rank.insert(0, self.decisions.student)
        else:
            rank = self.decisions.students_rank
        return rank

    def update_student_id(self, student):
        """Updates the student id of the current exam.

        Receives the Student object of the new identity
        (or None for clearing the student identity).

        """
        self.decisions.set_student(student)

    def load_capture(self):
        if self.capture is None:
            self.capture = self.sessiondb.read_capture(self.exam_id)

    def clear_capture(self):
        if self.capture is not None:
            self.capture = None

    def image_drawn_path(self):
        image_name = capture_name(self.sessiondb.exam_config.capture_pattern,
                                  self.exam_id, self.decisions.student)
        path = os.path.join(self.sessiondb.session_dir, 'captures', image_name)
        if not os.path.isfile(path):
            path = resource_path('not_found.png')
        return path

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

    SCORES_MODE_NONE = 1
    SCORES_MODE_WEIGHTS = 2
    SCORES_MODE_INDIVIDUAL = 3

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
            self.dimensions = []
            self.permutations = {}
            self.models = []
            self.scores = {}
            self.base_scores = None
            self.left_to_right_numbering = False
            self.survey_mode = None
            self.scores_mode = ExamConfig.SCORES_MODE_NONE
        if capture_pattern is not None:
            self.capture_pattern = capture_pattern
        else:
            self.capture_pattern = _default_capture_pattern

    def add_model(self, model):
        if not model in self.models:
            self.models.append(model)

    def set_solutions(self, model, solutions):
        if not isinstance(solutions, list):
            solutions = self._parse_solutions(solutions)
        if len(solutions) != self.num_questions:
            raise ValueError('Solutions with incorrect number of questions')
        self.solutions[model] = solutions
        self.add_model(model)

    def get_solutions(self, model):
        """Returns the solutions for the given model.

        If in survey mode it returns []. If there are no solutions for
        this model, it returns None.

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
        elif len(permutations) > 0 and isinstance(permutations[0], basestring):
            permutations = [self._parse_permutation(p, i) \
                            for i, p in enumerate(permutations)]
        if len(permutations) != self.num_questions:
            raise ValueError('Permutations with incorrect number of questions')
        self.permutations[model] = permutations
        self.add_model(model)

    def get_permutations(self, model):
        """Returns the permutations for the given model.

        If there are no permutations for this model, it returns None.

        """
        if model in self.permutations:
            return self.permutations[model]
        else:
            return None

    def set_dimensions(self, dimensions):
        self.dimensions, self.num_options = parse_dimensions(dimensions)
        self.num_questions = sum(dim[1] for dim in self.dimensions)

    def enter_score_mode_none(self):
        """Resets the object to no scores."""
        self.scores_mode = ExamConfig.SCORES_MODE_NONE
        self.base_scores = None
        self.scores = {}

    def set_base_scores(self, scores, same_weights=False):
        """Set the base scores for the questions of this exam.

        The `scores` parameter must be an instance of QuestionScores.
        It must be done before setting the weights of each question.

        """
        if scores.weight != 1:
            raise ValueError('The base score must have weigth 1')
        if self.scores_mode == ExamConfig.SCORES_MODE_NONE:
            self.scores_mode = ExamConfig.SCORES_MODE_WEIGHTS
        elif self.scores_mode != ExamConfig.SCORES_MODE_WEIGHTS:
            raise ValueError('The score mode does not allow base scores')
        self.base_scores = scores
        if same_weights:
            self.reset_question_weights()
            for model in self.models:
                self.set_equal_scores(model)

    def set_equal_scores(self, model):
        """Set the base scores for the questions of this exam.

        The `scores` parameter must be an instance of QuestionScores.
        It must be done before setting the weights of each question.

        """
        if (self.scores_mode != ExamConfig.SCORES_MODE_WEIGHTS
            or self.base_scores is None):
            raise ValueError('Invalid scores mode for set_equal_scores')
        scores = [self.base_scores.clone(new_weight=1) \
                  for i in range(self.num_questions)]
        self._set_question_scores_internal(model, scores)

    def set_question_weights(self, model, weights):
        """Set the scores for a given model from question weights.

        The `weights` parameter can be a list with the weight of each
        question of that model.
        The final scores must be the same as in the scores for the rest of
        the models, possibly in a different order.

        A base score must have already been set.

        """
        if self.scores_mode != ExamConfig.SCORES_MODE_WEIGHTS:
            raise ValueError('Not in scores weight mode.')
        if isinstance(weights, basestring):
            weights = self._parse_weights(weights)
        scores = [self.base_scores.clone(new_weight=weight) \
                  for weight in weights]
        self._set_question_scores_internal(model, scores)

    def get_question_weights(self, model, formatted=False):
        """Return the list of question weights for a given model.

        Returns None if scores are not set by means of a base score,
        or there are no scores for this model.

        """
        if (self.scores_mode != ExamConfig.SCORES_MODE_WEIGHTS
            or self.base_scores is None or not model in self.scores):
            return None
        elif not formatted:
            return [s.weight for s in self.scores[model]]
        else:
            return [s.format_weight() for s in self.scores[model]]

    def reset_question_weights(self):
        self.scores = {}

    def all_weights_are_one(self):
        """Return True if all the score weights are 1.

        It returns False if there are no scores set for at least one model.

        """
        if len(self.scores) > 0:
            # We only need to check one list of scores
            return all(s.weight == 1 for s in self.scores.values()[0])
        else:
            return False

    def set_question_scores(self, model, scores):
        """Set the scores for a given model from question weights.

        The `scores` parameter must be a list of QuestionScores objects.
        The scores must be the same as in the scores for the rest of
        the models, possibly in a different order.

        A base score cannot have already been set.

        """
        if self.scores_mode == ExamConfig.SCORES_MODE_NONE:
            self.scores_mode = ExamConfig.SCORES_MODE_INDIVIDUAL
        elif self.scores_mode != ExamConfig.SCORES_MODE_INDIVIDUAL:
            raise ValueError('Invalid scores mode at set_question_scores')
        for s in scores:
            if s.weight != 1:
                raise ValueError('Only weight 1 scores allowed')
        self._set_question_scores_internal(model, scores)

    def _set_question_scores_internal(self, model, scores):
        """Set the scores for a given model from question weights.

        Internal method that does not check the current mode.

        The `scores` parameter must be a list of QuestionScores objects.
        The scores must be the same as in the scores for the rest of
        the models, possibly in a different order.

        """
        if len(scores) != self.num_questions:
            raise ValueError('Scores with an incorrect number of questions')
        if self.scores and sorted(scores) != sorted(self.scores.values()[0]):
            raise ValueError('Scores for all models must be equal '
                             'but their order')
        self.scores[model] = scores
        self.add_model(model)

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
                self.set_solutions(model, value)
                if has_permutations:
                    key = 'permutations-' + model
                    value = exam_data.get('permutations', key)
                    self.set_permutations(model, value)
        has_correct_weight = exam_data.has_option('exam', 'correct-weight')
        has_incorrect_weight = exam_data.has_option('exam', 'incorrect-weight')
        has_blank_weight = exam_data.has_option('exam', 'blank-weight')
        self.scores = {}
        if has_correct_weight and has_incorrect_weight:
            cw = exam_data.get('exam', 'correct-weight')
            iw = exam_data.get('exam', 'incorrect-weight')
            if has_blank_weight:
                bw = exam_data.get('exam', 'blank-weight')
            else:
                bw = 0
            self.scores_mode = ExamConfig.SCORES_MODE_WEIGHTS
            base_scores = QuestionScores(cw, iw, bw)
            if not exam_data.has_section('question-score-weights'):
                self.set_base_scores(base_scores, same_weights=True)
            else:
                self.set_base_scores(base_scores)
                for model in self.models:
                    key = 'weights-' + model
                    value = exam_data.get('question-score-weights', key)
                    self.set_question_weights(model, value)
        elif not has_correct_weight and not has_incorrect_weight:
            self.base_scores = None
            self.scores_mode = ExamConfig.SCORES_MODE_NONE
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
        if self.base_scores is not None:
            data.append('correct-weight: {0}'\
              .format(self.base_scores.format_correct_score()))
            data.append('incorrect-weight: {0}'\
              .format(self.base_scores.format_incorrect_score()))
            data.append('blank-weight: {0}'\
              .format(self.base_scores.format_blank_score()))
        if len(self.solutions) > 0:
            data.append('')
            data.append('[solutions]')
            for model in sorted(self.models):
                data.append('model-{0}: {1}'\
                            .format(model, self.format_solutions(model)))
        if len(self.permutations) > 0:
            data.append('')
            data.append('[permutations]')
            for model in sorted(self.models):
                data.append('permutations-{0}: {1}'\
                            .format(model, self.format_permutations(model)))
        if (self.scores_mode == ExamConfig.SCORES_MODE_WEIGHTS
            and len(self.scores)
            and not self.all_weights_are_one()):
            # If all the scores are equal, there is no need to specify weights
            data.append('')
            data.append('[question-score-weights]')
            for model in sorted(self.models):
                data.append('weights-{0}: {1}'\
                            .format(model, self.format_weights(model)))
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
        return '/'.join([self.format_permutation(p) \
                         for p in self.permutations[model]])

    def format_permutation(self, permutation):
        num_question, options = permutation
        return '%d{%s}'%(num_question, ','.join([str(n) for n in options]))

    def format_weights(self, model):
        return ','.join([s.format_weight() for s in self.scores[model]])

    def _parse_solutions(self, s):
        pieces = s.split('/')
        if len(pieces) != self.num_questions:
            raise Exception('Wrong number of solutions')
        return [int(num) for num in pieces]

    def _parse_permutations(self, s):
        permutations = []
        pieces = s.split('/')
        if len(pieces) != self.num_questions:
            raise Exception('Wrong number of permutations')
        for i, piece in enumerate(pieces):
            permutations.append(self._parse_permutation(piece, i))
        return permutations

    def _parse_permutation(self, str_value, question_number):
        splitted = str_value.split('{')
        num_question = int(splitted[0])
        options = [int(p) for p in splitted[1][:-1].split(',')]
        if len(options) > self.num_options[question_number]:
            raise Exception('Wrong number of options in permutation')
        return (num_question, options)

    def _parse_weights(self, s):
        pieces = s.split(',')
        if len(pieces) != self.num_questions:
            raise Exception('Wrong number of weight items')
        return [p for p in pieces]


class QuestionScores(ComparableMixin):
    """Compute the score of a question."""
    CORRECT = 1
    INCORRECT = 2
    BLANK = 3
    VOID = 4

    def __init__(self, correct_score, incorrect_score, blank_score,
                 weight=1):
        if isinstance(correct_score, basestring):
            self.correct_score = self._parse_score(correct_score)
        else:
            self.correct_score = correct_score
        if isinstance(incorrect_score, basestring):
            self.incorrect_score = self._parse_score(incorrect_score)
        else:
            self.incorrect_score = incorrect_score
        if isinstance(blank_score, basestring):
            self.blank_score = self._parse_score(blank_score)
        else:
            self.blank_score = blank_score
        if isinstance(weight, basestring):
            self.weight = self._parse_score(weight)
        else:
            self.weight = weight

    def score(self, answer_type):
        if answer_type == QuestionScores.CORRECT:
            return self.weight * self.correct_score
        elif answer_type == QuestionScores.INCORRECT:
            return -self.weight * self.incorrect_score
        elif answer_type == QuestionScores.BLANK:
            return -self.weight * self.blank_score
        elif answer_type == QuestionScores.VOID:
            return 0
        else:
            raise Exception('Bad answer_type value in QuestionScore')

    def format_all(self):
        data = (self._format_score(self.correct_score),
                self._format_score(self.incorrect_score),
                self._format_score(self.blank_score))
        return ';'.join(data)

    def format_weight(self):
        return self._format_score(self.weight)

    def format_score(self, answer_type, signed=False):
        if answer_type == QuestionScores.CORRECT:
            return self._format_score(self.correct_score, signed=False)
        elif answer_type == QuestionScores.INCORRECT:
            return self._format_score(self.incorrect_score, signed=signed)
        elif answer_type == QuestionScores.BLANK:
            return self._format_score(self.blank_score, signed=signed)
        else:
            raise ValueError('Bad answer_type value in QuestionScore')

    def format_correct_score(self, signed=False):
        return self._format_score(self.correct_score, signed=False)

    def format_incorrect_score(self, signed=False):
        return self._format_score(self.incorrect_score, signed=signed)

    def format_blank_score(self, signed=False):
        return self._format_score(self.blank_score, signed=signed)

    def clone(self, new_weight=None):
        if new_weight is not None:
            weight = new_weight
        else:
            weight = self.weight
        return QuestionScores(self.correct_score, self.incorrect_score,
                              self.blank_score, weight=weight)

    def __str__(self):
        return '({0}) * {1}'.format(self.format_all(), self.format_weight())

    def _parse_score(self, score):
        return parse_number(score)

    def _format_score(self, score, signed=False):
        if signed:
            score = -score
        return format_number(score)

    def _cmpkey(self):
        return (self.correct_score, self.incorrect_score,
                self.blank_score, self.weight)


def parse_number(number):
    if number.find('-') != -1:
        raise ValueError('The number must be positive: {0}'\
                         .format(number))
    if not _re_score.match(number):
        raise ValueError('Syntax error in number: "{0}"'.format(number))
    parts = [p.strip() for p in number.split('/')]
    if len(parts) == 1:
        if not '.' in number:
            return int(number)
        else:
            return float(number)
    elif len(parts) == 2:
        return fractions.Fraction(int(parts[0]), int(parts[1]))

def format_number(number, short=False, no_fraction=False):
    if number is None:
        return None
    elif no_fraction and type(number) == fractions.Fraction:
        if number.denominator != 1:
            number = float(number)
        else:
            number = number.numerator
    if type(number) == fractions.Fraction:
        if number.denominator != 1:
            return '{0}/{1}'.format(number.numerator, number.denominator)
        else:
            return unicode(number.numerator)
    elif type(number) == float:
        if short:
            return '{0:.2f}'.format(number)
        else:
            return '{0:.16f}'.format(number)
    else:
        return unicode(number)

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
